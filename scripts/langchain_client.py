# scripts/langchain_client.py
import os
from pathlib import Path
from typing import Optional
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


# Load environment variables from config file
# Try the persistent location first, then fallback to project root
config_file = Path.home() / "Library" / "Application Support" / "AnythingLLM-Menu" / ".env"
if config_file.exists():
    load_dotenv(config_file)
else:
    # Fallback to project root .env for development
    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / ".env")

OPENAI_BASE = os.getenv("ANYTHINGLLM_OPENAI_BASE", "http://localhost:3001/api/v1/openai")
API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "")
WORKSPACE_SLUG = os.getenv("ANYTHINGLLM_WORKSPACE_SLUG", "local")


# AnythingLLM’s OpenAI-compatible API expects `model` to be the workspace slug.
_llm = ChatOpenAI(
  openai_api_key=API_KEY,
  openai_api_base=OPENAI_BASE,
  model=WORKSPACE_SLUG,
  temperature=0.2,
)


def ask_llm(question: str, system: Optional[str] = None) -> str:
  messages = []
  if system:
    messages.append(("system", system))
  messages.append(("user", question))
  # Simple one-shot invoke; you can swap in LangChain Runnables/Tools later
  res = _llm.invoke(messages)
  return (res.content or "").strip()