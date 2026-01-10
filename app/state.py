# TribeLeaderState TypedDict
# app/state.py

from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import AnyMessage

class EmotionState(TypedDict):
    label: str
    confidence: float
    stress_score: float
    needs_stabilization: bool
    pacing: str  # "slow" | "normal"

class CapsState(TypedDict):
    max_tokens: int
    max_questions: int
    max_options: int
    history_window: int

class GuardrailReport(TypedDict):
    options_count: int
    questions_count: int
    prescriptive_flags: List[str]
    violations: List[str]

class Artifacts(TypedDict):
    commitments_detected: List[Dict[str, Any]]
    commitment_confirmations_needed: bool
    identity_update_requests: List[Dict[str, Any]]
    memory_write_intents: List[Dict[str, Any]]

class TribeLeaderState(TypedDict):
    messages: List[AnyMessage]          # reducer = add_messages
    emotion: EmotionState
    caps: CapsState

    identity_snapshot: Dict[str, Any]   # bounded, SQL-backed
    active_commitments: List[Dict[str, Any]]
    retrieved_memories: List[Dict[str, Any]]

    draft_response: Optional[str]
    final_response: Optional[str]

    guardrails: GuardrailReport
    artifacts: Artifacts
