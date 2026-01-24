# app/tools/commitments.py

"""
Commitment detection utilities.

This module:
- Detects explicit or strong implied commitments
- NEVER persists commitments
- Returns candidates that require user confirmation
"""

import re
from typing import List, Dict


COMMITMENT_PATTERNS = [
    r"\bi will\b",
    r"\bi am going to\b",
    r"\bi plan to\b",
    r"\bi intend to\b",
    r"\bi'll\b",
    r"\bfrom now on\b",
]

SOFT_INTENT_PATTERNS = [
    r"\bi should\b",
    r"\bi want to\b",
    r"\bnext time i\b",
]


def detect_commitments(text: str) -> List[Dict]:
    """
    Detect possible commitments from user text.

    Returns a list of commitment candidates.
    """
    text_l = text.lower()
    commitments = []

    for pattern in COMMITMENT_PATTERNS:
        if re.search(pattern, text_l):
            commitments.append({
                "type": "explicit",
                "pattern": pattern,
                "text": text.strip(),
            })

    for pattern in SOFT_INTENT_PATTERNS:
        if re.search(pattern, text_l):
            commitments.append({
                "type": "implicit",
                "pattern": pattern,
                "text": text.strip(),
            })

    return commitments
