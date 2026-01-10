
# app/llm.py
import os
from langchain_openai import AzureChatOpenAI

def build_llm():
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("OPENAI_API_VERSION"),   # set in env
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        temperature=0.2,
    )
