# app/tools/memory.py

"""
Semantic memory interface for Tribe Leader.

Vector memory stores:
- Distilled, reusable insights
- NOT raw conversations
- NOT authoritative commitments
"""

from typing import Dict, Any, List
from datetime import datetime


def upsert(user_id: str, memory: Dict[str, Any]) -> None:
    """
    Write a semantic memory object to vector DB.

    This should:
    - Embed `memory["text"]`
    - Store metadata for filtering
    """
    # TODO: replace with real vector DB call
    pass


def search(user_id: str, query: str, k: int = 5, filters: Dict | None = None) -> List[Dict]:
    """
    Retrieve semantic memories by similarity.
    """
    # TODO: replace with real vector DB call
    return []
