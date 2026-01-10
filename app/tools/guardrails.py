# app/tools/guardrails.py

"""
Structural guardrails for Tribe Leader.

These guardrails enforce:
- Option count
- Question count
- No prescriptive language

They are intentionally simple and conservative.
"""

import re
from typing import Dict, List


PRESCRIPTIVE_PATTERNS = [
    r"\byou should\b",
    r"\bi recommend\b",
    r"\bthe best (option|choice)\b",
    r"\bdo this\b",
    r"\bmy advice\b",
    r"\bi think you should\b",
]


OPTION_PATTERN = re.compile(r"option\s*\d+|[-*]\s", re.IGNORECASE)
QUESTION_PATTERN = re.compile(r"\?")


def validate(text: str, caps: Dict) -> Dict:
    options = count_options(text)
    questions = count_questions(text)
    prescriptive_hits = detect_prescriptive(text)

    violations: List[str] = []

    if options < 2 and caps.get("max_options", 0) > 0:
        violations.append("too_few_options")

    if options > caps.get("max_options", options):
        violations.append("too_many_options")

    if questions < 1:
        violations.append("no_questions")

    if questions > caps.get("max_questions", questions):
        violations.append("too_many_questions")

    if prescriptive_hits:
        violations.append("prescriptive_language")

    return {
        "options_count": options,
        "questions_count": questions,
        "prescriptive_flags": prescriptive_hits,
        "violations": violations,
    }


def count_options(text: str) -> int:
    """
    Counts options heuristically:
    - Numbered options
    - Bullet points
    """
    matches = OPTION_PATTERN.findall(text)
    return len(matches)


def count_questions(text: str) -> int:
    return len(QUESTION_PATTERN.findall(text))


def detect_prescriptive(text: str) -> List[str]:
    hits = []
    text_l = text.lower()

    for pattern in PRESCRIPTIVE_PATTERNS:
        if re.search(pattern, text_l):
            hits.append(pattern)

    return hits