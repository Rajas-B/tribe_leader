# app/cli/run_local.py

import sys
from typing import Dict
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage

from app.runtime.llm_mvp import build_mvp_graph
from app.state import TribeLeaderState


def initial_state() -> TribeLeaderState:
    return {
        "messages": [],
        "emotion": {},
        "caps": {},
        "identity_snapshot": {},
        "active_commitments": [],
        "retrieved_memories": [],
        "draft_response": None,
        "final_response": None,
        "guardrails": {},
        "artifacts": {
            "commitments_detected": [],
            "commitment_confirmations_needed": False,
            "identity_update_requests": [],
            "memory_write_intents": [],
        },
    }


def main():
    load_dotenv()
    print("\n🟢 Tribe Leader MVP (Local)")
    print("Type 'exit' or 'quit' to end.\n")

    graph = build_mvp_graph()
    state: Dict = initial_state()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        state["messages"].append(HumanMessage(content=user_input))

        try:
            state = graph.invoke(state)
        except Exception as e:
            print("\n[Error running agent]")
            print(e)
            continue

        response = state.get("final_response")
        if response:
            print("\nTribe Leader:")
            print(response)
            print("")
        else:
            print("\n[No response generated]\n")


if __name__ == "__main__":
    main()
