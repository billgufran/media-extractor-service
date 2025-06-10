import os
from pydantic import SecretStr
from langchain_openai import ChatOpenAI

OPENROUTER_API_KEY: SecretStr = SecretStr(os.getenv("OPENROUTER_API_KEY", ""))
MODEL = "google/gemma-3n-e4b-it:free"

# Shared ChatOpenAI instance for reuse across services
llm = ChatOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model=MODEL,
    temperature=0,
)
