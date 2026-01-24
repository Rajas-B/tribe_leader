# app/tools/db.py

"""
SQL persistence utilities for Tribe Leader.

This module provides authoritative, append-only storage.
No business logic lives here.
"""

from typing import Dict, List, Any
from datetime import datetime


def insert_episodic_event(
    user_id: str,
    thread_id: str,
    user_message: str,
    bot_message: str,
    emotion: Dict[str, Any],
    commitments: List[Dict[str, Any]],
) -> str:
    """
    Persist a single conversational event.

    This should be written as an append-only row.
    Returns an event_id.
    """

    # --- PLACEHOLDER IMPLEMENTATION ---
    # Replace with real SQL execution later.

    event_id = f"evt_{datetime.utcnow().isoformat()}"

    # Example payload for future SQL layer
    record = {
        "event_id": event_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "user_message": user_message,
        "bot_message": bot_message,
        "emotion": emotion,
        "commitments_detected": commitments,
        "created_at": datetime.utcnow(),
    }

    # TODO: write `record` to SQL database

    return event_id
