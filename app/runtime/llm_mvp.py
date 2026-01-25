# app/runtime/llm_mvp.py

import os
from langchain_openai import ChatOpenAI

from app.graph import build_graph


def build_llm():
    """
    Build an OpenAI-compatible LLM client backed by Groq.
    """

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    llm_model = os.getenv("GROQ_MODEL")
    if not llm_model:
        raise RuntimeError("GROQ_MODEL is not set")

    return ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://api.groq.com/openai/v1",
        model=llm_model,
        temperature=0.3,
        max_tokens=700,
        timeout=30,
    )


def build_mvp_graph():
    """
    Build and return the Tribe Leader MVP graph.
    """
    llm = build_llm()
    return build_graph(llm)
