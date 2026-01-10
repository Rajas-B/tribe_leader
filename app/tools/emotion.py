# app/tools/emotion.py

"""
Emotion classification utilities for Tribe Leader.

MVP version:
- Deterministic heuristic-based classifier
- Conservative (bias toward stabilization)
- No LLM calls yet

This module MUST return structured emotion state.
"""

from typing import Dict, Any
import re


# ---------------------------------------------------------------------
# Heuristic signals
# ---------------------------------------------------------------------

STRESS_KEYWORDS = [
    "overwhelmed",
    "stressed",
    "burned out",
    "anxious",
    "panicking",
    "exhausted",
    "can't think",
    "lost",
    "confused",
    "pressure",
    "too much",
    "breaking",
]

INTENSIFIERS = [
    "very",
    "extremely",
    "really",
    "so much",
    "completely",
    "totally",
]

NEGATIONS = [
    "not stressed",
    "not overwhelmed",
    "calm",
    "fine",
    "okay",
]


# ---------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------

def classify(text: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Classify emotional state from user text.

    Returns:
    {
        label: str,
        confidence: float,
        stress_score: float,
        needs_stabilization: bool,
        pacing: "slow" | "normal"
    }
    """

    text_l = text.lower()

    # Quick negation override
    for phrase in NEGATIONS:
        if phrase in text_l:
            return _result(
                label="calm",
                stress_score=0.2,
                confidence=0.6,
            )

    keyword_hits = sum(1 for k in STRESS_KEYWORDS if k in text_l)
    intensifier_hits = sum(1 for i in INTENSIFIERS if i in text_l)
    exclamation_hits = text.count("!")

    # Simple stress score heuristic
    stress_score = (
        (keyword_hits * 0.25) +
        (intensifier_hits * 0.15) +
        (exclamation_hits * 0.1)
    )

    # Clamp score
    stress_score = min(stress_score, 1.0)

    # Determine label
    if stress_score >= 0.6:
        label = "high_stress"
    elif stress_score >= 0.35:
        label = "moderate_stress"
    else:
        label = "calm"

    confidence = min(0.4 + stress_score, 0.9)

    return _result(
        label=label,
        stress_score=stress_score,
        confidence=confidence,
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _result(label: str, stress_score: float, confidence: float) -> Dict[str, Any]:
    needs_stabilization = stress_score >= 0.5

    return {
        "label": label,
        "confidence": round(confidence, 2),
        "stress_score": round(stress_score, 2),
        "needs_stabilization": needs_stabilization,
        "pacing": "slow" if needs_stabilization else "normal",
    }
