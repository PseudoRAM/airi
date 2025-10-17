#!/usr/bin/env python3
"""
Quick connectivity test for AnythingLLM OpenAI-compatible endpoint via LangChain.
Run: python scripts/test_anythingllm.py
or: python scripts/test_anythingllm.py "Reply with the word: pong"
"""
import os
import sys
import time
from pathlib import Path


# Lightweight .env loader (no external deps)
def load_dotenv(path: str):
  p = Path(path)
  if not p.exists():
    return
  for raw in p.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue
    k, _, v = line.partition("=")
    k = k.strip()
    v = v.strip().strip('"').strip("'")
    os.environ.setdefault(k, v)


if __name__ == "__main__":
  # Load root .env (script lives in scripts/)
  repo_root = Path(__file__).resolve().parents[1]
  load_dotenv(repo_root / ".env")


  # Import LangChain wrapper
  sys.path.insert(0, str(Path(__file__).parent))
  from langchain_client import ask_llm, OPENAI_BASE, WORKSPACE_SLUG


  question = "Reply with the single word: pong"
  if len(sys.argv) > 1:
    question = " ".join(sys.argv[1:])


  print("== AnythingLLM Test ==")
  print(f"Base: {os.getenv('ANYTHINGLLM_OPENAI_BASE', str(OPENAI_BASE))}")
  print(f"Workspace (model): {os.getenv('ANYTHINGLLM_WORKSPACE_SLUG', WORKSPACE_SLUG)}")


  t0 = time.time()
  try:
    answer = ask_llm(question)
  except Exception as e:
    print("❌ Error calling LLM:", e)
    sys.exit(2)
  dt = time.time() - t0


  print(f"Latency: {dt:.2f}s")
  print("Answer: \n" + answer)
  
  print("-----")


  if "pong" in answer.lower():
    print("✅ Basic round-trip OK")
    sys.exit(0)
  else:
    print("ℹ️ Response didn't match 'pong' exactly (models can be chatty).")
    sys.exit(0)