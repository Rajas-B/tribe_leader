# StateGraph + nodes + compile
from langgraph.graph import StateGraph, END
from app.state import TribeLeaderState
from langchain_core.messages import SystemMessage
from app.prompts import SYSTEM_PROMPT, STABILIZE_PROMPT, GUIDE_PROMPT
from langchain_core.messages import AIMessage
from app.tools.emotion import classify
from app.tools.guardrails import validate

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

    ai_msg = AIMessage(content=response.content)

    state["messages"] = messages + [ai_msg]
    state["draft_response"] = response.content
    state["final_response"] = response.content

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

    draft = state.get("draft_response")
    caps = state.get("caps", {})

    if not draft:
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

    regenerated = response.content

    # Validate regenerated output once more (no further retries)
    final_report = validate(regenerated, caps)

    state["guardrails"] = final_report
    state["final_response"] = regenerated

    # Replace last AI message with regenerated output
    state["messages"] = messages[:-1] + [AIMessage(content=regenerated)]

    return state

graph = StateGraph(TribeLeaderState)

graph.add_node("ensure_system", ensure_system)
graph.add_node("load_context", load_context)
graph.add_node("classify_emotion", classify_emotion)
graph.add_node("apply_caps", apply_caps)
graph.add_node("stabilize", stabilize)
graph.add_node("guide", guide)
graph.add_node("guardrail_validate", guardrail_validate)
graph.add_node("extract_commitments", extract_commitments)
graph.add_node("persist_event", persist_event)
graph.add_node("update_semantic_memory", update_semantic_memory)
graph.add_node("trim_messages", trim_messages)

graph.set_entry_point("ensure_system")

graph.add_edge("ensure_system", "load_context")
graph.add_edge("load_context", "classify_emotion")
graph.add_edge("classify_emotion", "apply_caps")

graph.add_conditional_edges(
    "apply_caps",
    lambda s: "stabilize" if s["emotion"]["needs_stabilization"] else "guide",
)

graph.add_edge("stabilize", "extract_commitments")
graph.add_edge("guide", "guardrail_validate")
graph.add_edge("guardrail_validate", "extract_commitments")

graph.add_edge("extract_commitments", "persist_event")
graph.add_edge("persist_event", "update_semantic_memory")
graph.add_edge("update_semantic_memory", "trim_messages")
graph.add_edge("trim_messages", END)


