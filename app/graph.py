# StateGraph + nodes + compile
from datetime import datetime
from langgraph.graph import StateGraph, END
from app.state import TribeLeaderState
from langchain_core.messages import SystemMessage
from app.prompts import SYSTEM_PROMPT, STABILIZE_PROMPT, GUIDE_PROMPT, REGENERATION_PROMPT
from langchain_core.messages import AIMessage
from app.tools.emotion import classify
from app.tools.guardrails import validate
from app.tools.commitments import detect_commitments
from app.tools.db import insert_episodic_event
from app.tools.memory import upsert


def ensure_system(state: TribeLeaderState) -> TribeLeaderState:
    """
    Ensures the Tribe Leader system prompt is present exactly once.

    This node:
    - Locks persona and hard behavioral rules
    - Is idempotent (safe to run every turn)
    - Must run before any other reasoning
    """

    messages = state.get("messages", [])

    # Check if a system message already exists
    has_system = any(
        isinstance(msg, SystemMessage)
        for msg in messages
    )

    if not has_system:
        system_msg = SystemMessage(content=SYSTEM_PROMPT)
        messages = [system_msg] + messages

    state["messages"] = messages
    return state

def classify_emotion(state: TribeLeaderState) -> TribeLeaderState:
    """
    Classifies the user's emotional state and stores it in state.

    This node:
    - Never generates text
    - Never alters messages
    - Only computes emotion gating signals
    """

    messages = state.get("messages", [])
    if not messages:
        return state

    # Last user message is the signal source
    last_msg = messages[-1]
    user_text = getattr(last_msg, "content", "")

    emotion = classify(user_text)

    state["emotion"] = emotion
    return state


def apply_caps(state: TribeLeaderState) -> TribeLeaderState:
    """
    Applies response caps based on emotional state.

    This node:
    - Enforces slow pacing under stress
    - Prevents advice leakage during stabilization
    - Sets hard structural limits for downstream generation
    """

    emotion = state.get("emotion")

    # Fallback safety
    if not emotion:
        state["caps"] = {
            "max_tokens": 200,
            "max_questions": 1,
            "max_options": 2,
            "history_window": 6,
        }
        return state

    stress_score = emotion.get("stress_score", 0)
    needs_stabilization = emotion.get("needs_stabilization", False)

    # High stress → stabilize only
    if needs_stabilization:
        caps = {
            "max_tokens": 120,
            "max_questions": 1,
            "max_options": 0,   # CRITICAL: no options allowed
            "history_window": 4,
        }

    # Moderate stress → constrained guidance
    elif stress_score >= 0.35:
        caps = {
            "max_tokens": 220,
            "max_questions": 1,
            "max_options": 3,
            "history_window": 6,
        }

    # Calm → full guidance
    else:
        caps = {
            "max_tokens": 350,
            "max_questions": 2,
            "max_options": 4,
            "history_window": 8,
        }

    state["caps"] = caps
    return state

def stabilize(state: TribeLeaderState, llm) -> TribeLeaderState:
    """
    Grounding-only response for high stress states.

    This node:
    - Uses STABILIZE_PROMPT
    - Obeys caps strictly
    - Generates NO advice or options
    """

    caps = state.get("caps", {})
    messages = state.get("messages", [])

    # Safety defaults
    max_tokens = caps.get("max_tokens", 120)

    prompt_messages = [
        *messages,
        AIMessage(content=STABILIZE_PROMPT),
    ]

    response = llm.invoke(
        prompt_messages,
        max_tokens=max_tokens,
    )

    text = (response.content or "").strip()

    # ✅ Hard safety fallback (never allow silence)
    if not text:
        text = (
            "I hear that this feels heavy. Let’s slow this down together.\n\n"
            "What part of this feels most urgent right now?"
        )

    ai_msg = AIMessage(content=response.content)

    state["messages"] = messages + [ai_msg]
    state["draft_response"] = text
    state["final_response"] = text

    return state

def guide(state: TribeLeaderState, llm) -> TribeLeaderState:
    """
    Decision reflection node for emotionally stable states.

    This node:
    - Uses GUIDE_PROMPT
    - Obeys caps for pacing and structure
    - Does NOT decide or recommend
    - Does NOT validate yet (guardrails come later)
    """

    messages = state.get("messages", [])
    caps = state.get("caps", {})

    # Safety defaults
    max_tokens = caps.get("max_tokens", 300)

    # Build prompt context
    prompt_messages = [
        *messages,
        AIMessage(content=GUIDE_PROMPT),
    ]

    response = llm.invoke(
        prompt_messages,
        max_tokens=max_tokens,
    )

    ai_msg = AIMessage(content=response.content)

    state["messages"] = messages + [ai_msg]
    state["draft_response"] = response.content
    state["final_response"] = response.content

    return state

def guardrail_validate(state: TribeLeaderState, llm) -> TribeLeaderState:
    """
    Validates generated guidance against structural guardrails.

    If violations are found:
    - Regenerates ONCE using REGENERATION_PROMPT
    - Does not loop endlessly
    """

    draft = (state.get("draft_response") or "").strip()
    caps = state.get("caps", {})

    if not draft:
        state["final_response"] = (
            "Let’s pause for a moment so I can stay aligned with how we work here.\n\n"
            "Could you share a bit more about what you’re trying to decide?"
        )
        state["guardrails"] = {"violations": ["empty_output"]}
        return state

    report = validate(draft, caps)
    state["guardrails"] = report

    # If no violations, accept draft
    if not report["violations"]:
        state["final_response"] = draft
        return state

    # Regenerate once
    messages = state.get("messages", [])

    regen_prompt = (
        REGENERATION_PROMPT
        + "\n\nOriginal response:\n"
        + draft
    )

    response = llm.invoke(
        messages + [AIMessage(content=regen_prompt)],
        max_tokens=caps.get("max_tokens", 300),
    )

    regenerated = (response.content or "").strip()

    # Validate regenerated output once more (no further retries)
    final_report = validate(regenerated, caps)

    state["guardrails"] = final_report
    if not regenerated or final_report["violations"]:
        fallback = (
            "I want to stay within the boundaries that make this useful for you.\n\n"
            "What feels most important to clarify before we go further?"
        )

        state["final_response"] = fallback
        state["messages"] = messages + [AIMessage(content=fallback)]
        return state

    # Accept regenerated output
    state["final_response"] = regenerated

    # Replace last AI message with regenerated output
    state["messages"] = messages[:-1] + [AIMessage(content=regenerated)]

    return state

def extract_commitments(state: TribeLeaderState) -> TribeLeaderState:
    """
    Detects potential commitments and requests confirmation.

    This node:
    - Scans the latest USER message only
    - Detects explicit or implied commitments
    - Asks for confirmation before anything is stored
    """

    messages = state.get("messages", [])
    artifacts = state.get("artifacts", {})

    artifacts.setdefault("commitments_detected", [])
    artifacts.setdefault("commitment_confirmations_needed", False)

    if not messages:
        state["artifacts"] = artifacts
        return state

    # Only scan last USER message
    last_msg = messages[-1]
    if last_msg.type != "human":
        state["artifacts"] = artifacts
        return state

    user_text = last_msg.content
    detected = detect_commitments(user_text)

    if not detected:
        state["artifacts"] = artifacts
        return state

    # Record detected commitments
    artifacts["commitments_detected"].extend(detected)
    artifacts["commitment_confirmations_needed"] = True

    # Append confirmation question to final response
    confirmation_prompt = (
        "\n\nI want to check something before we go further.\n"
        "It sounds like you may be committing to something.\n"
        "Do you want me to treat this as a real commitment and check back on it later?"
    )

    final_response = state.get("final_response", "")
    state["final_response"] = final_response + confirmation_prompt

    # Replace last AI message to include confirmation
    state["messages"] = messages[:-1] + [
        AIMessage(content=state["final_response"])
    ]

    state["artifacts"] = artifacts
    return state

def persist_event(
    state: TribeLeaderState,
    user_id: str,
    thread_id: str,
) -> TribeLeaderState:
    """
    Persist the conversational event as an append-only record.

    This node:
    - Logs what happened (not interpretations)
    - Never mutates behavior
    - Must not fail the graph if persistence fails
    """

    messages = state.get("messages", [])
    emotion = state.get("emotion", {})
    artifacts = state.get("artifacts", {})

    if len(messages) < 2:
        return state

    # Extract last user + final bot message
    user_message = None
    for msg in reversed(messages):
        if msg.type == "human":
            user_message = msg.content
            break

    bot_message = state.get("final_response")

    if not user_message or not bot_message:
        return state

    commitments = artifacts.get("commitments_detected", [])

    try:
        insert_episodic_event(
            user_id=user_id,
            thread_id=thread_id,
            user_message=user_message,
            bot_message=bot_message,
            emotion=emotion,
            commitments=commitments,
        )
    except Exception:
        # Persistence must never crash the agent
        pass

    return state

def trim_messages(state: TribeLeaderState) -> TribeLeaderState:
    """
    Trim message history according to caps.history_window.

    Rules:
    - Always preserve the system message
    - Keep the last N non-system messages
    - Drop older context deterministically
    """

    messages = state.get("messages", [])
    caps = state.get("caps", {})

    if not messages:
        return state

    history_window = caps.get("history_window", 6)

    # Separate system message(s) and others
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    non_system_messages = [m for m in messages if not isinstance(m, SystemMessage)]

    # Keep only the last N non-system messages
    trimmed_non_system = non_system_messages[-history_window:]

    # Reassemble: system message(s) first, then recent history
    state["messages"] = system_messages + trimmed_non_system

    return state

def update_semantic_memory(
    state: TribeLeaderState,
    user_id: str,
) -> TribeLeaderState:
    """
    Gated semantic memory writer.

    This node:
    - Writes NOTHING by default
    - Only writes when explicit memory intent exists
    - Never writes raw conversation
    """

    artifacts = state.get("artifacts", {})
    emotion = state.get("emotion", {})

    memory_intents = artifacts.get("memory_write_intents", [])

    if not memory_intents:
        return state

    # Only allow one memory write per turn (MVP safety)
    intent = memory_intents[0]

    memory_text = intent.get("text")
    memory_type = intent.get("type")

    if not memory_text or not memory_type:
        return state

    # Final safety gating
    allowed_types = {"emotional_pattern", "win", "failure", "commitment_summary"}
    if memory_type not in allowed_types:
        return state

    memory_obj = {
        "text": memory_text,
        "type": memory_type,
        "emotion_label": emotion.get("label"),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        upsert(user_id=user_id, memory=memory_obj)
    except Exception:
        # Memory failure must never crash the agent
        pass

    return state

def load_context(state: TribeLeaderState) -> TribeLeaderState:
    """
    Load user context for the current turn.

    MVP STUB:
    - No databases
    - No vector search
    - No Redis
    - Injects empty but well-formed context

    This function exists to satisfy the graph contract
    and will be replaced with real implementations later.
    """

    # Identity (authoritative later via SQL)
    state["identity_snapshot"] = {}

    # Active commitments (authoritative later via SQL)
    state["active_commitments"] = []

    # Retrieved semantic memories (later via vector DB)
    state["retrieved_memories"] = []

    # Artifacts scratchpad (side-effect intents)
    state.setdefault("artifacts", {
        "commitments_detected": [],
        "commitment_confirmations_needed": False,
        "identity_update_requests": [],
        "memory_write_intents": [],
    })

    return state

def build_graph(llm):
    """
    Build and compile the Tribe Leader MVP StateGraph.

    This version:
    - Uses in-memory state
    - No Redis
    - No SQL
    - No Vector DB
    """

    graph = StateGraph(TribeLeaderState)

    # --- Register nodes ---
    graph.add_node("ensure_system", ensure_system)
    graph.add_node("load_context", load_context)
    graph.add_node("classify_emotion", classify_emotion)
    graph.add_node("apply_caps", apply_caps)

    # Text generation paths
    graph.add_node("stabilize", lambda s: stabilize(s, llm))
    graph.add_node("guide", lambda s: guide(s, llm))

    # Enforcement + side effects
    graph.add_node("guardrail_validate", lambda s: guardrail_validate(s, llm))
    graph.add_node("extract_commitments", extract_commitments)
    graph.add_node("persist_event", lambda s: persist_event(
        s,
        user_id="local_user",
        thread_id="local_thread",
    ))
    graph.add_node("update_semantic_memory", lambda s: update_semantic_memory(
        s,
        user_id="local_user",
    ))
    graph.add_node("trim_messages", trim_messages)

    # --- Entry point ---
    graph.set_entry_point("ensure_system")

    # --- Linear setup ---
    graph.add_edge("ensure_system", "load_context")
    graph.add_edge("load_context", "classify_emotion")
    graph.add_edge("classify_emotion", "apply_caps")

    # --- Conditional routing ---
    graph.add_conditional_edges(
        "apply_caps",
        lambda state: (
            "stabilize"
            if state["emotion"]["needs_stabilization"]
            else "guide"
        ),
    )

    # --- Post-generation flow ---
    graph.add_edge("stabilize", "extract_commitments")

    graph.add_edge("guide", "guardrail_validate")
    graph.add_edge("guardrail_validate", "extract_commitments")

    graph.add_edge("extract_commitments", "persist_event")
    graph.add_edge("persist_event", "update_semantic_memory")
    graph.add_edge("update_semantic_memory", "trim_messages")

    graph.add_edge("trim_messages", END)

    return graph.compile()

