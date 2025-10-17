# scripts/ask_anythingllm.py
import os
import sys
from langchain_client import ask_llm


if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("Usage: ask_anythingllm.py \"your question\"")
    sys.exit(1)
  question = sys.argv[1]
  system = os.getenv("SYSTEM_PROMPT", "You are a concise, accurate assistant.")
  print(ask_llm(question, system=system))