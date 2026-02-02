# StateGraph + nodes + compile
from datetime import datetime
from langgraph.graph import StateGraph, END
from app.state import TribeLeaderState
from app.graph_nodes.nodes import ensure_system
from app.graph_nodes.nodes import load_context
from app.graph_nodes.nodes import classify_emotion 
from app.graph_nodes.nodes import apply_caps
from app.graph_nodes.nodes import stabilize
from app.graph_nodes.nodes import guide
from app.graph_nodes.nodes import guardrail_validate
from app.graph_nodes.nodes import extract_commitments
from app.graph_nodes.nodes import persist_event
from app.graph_nodes.nodes import update_semantic_memory
from app.graph_nodes.nodes import trim_messages


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

