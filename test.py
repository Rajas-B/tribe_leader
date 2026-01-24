from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
import certifi
import httpx

os.environ["SSL_CERT_FILE"] = certifi.where()
load_dotenv()


llm = ChatOpenAI(
    openai_api_key=os.getenv("GROQ_API_KEY"),
    openai_api_base="https://api.groq.com/openai/v1",
    model="llama-3.1-8b-instant",
    http_client = httpx.Client(verify=False)
,
)

print(llm.invoke([HumanMessage(content="Say hello calmly.")]).content)