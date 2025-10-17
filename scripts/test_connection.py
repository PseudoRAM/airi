#!/usr/bin/env python3
"""
Quick diagnostic script to test AnythingLLM connection.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests
import time

# Load config
config_file = Path.home() / "Library" / "Application Support" / "AnythingLLM-Menu" / ".env"
if config_file.exists():
    load_dotenv(config_file)
else:
    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / ".env")

OPENAI_BASE = os.getenv("ANYTHINGLLM_OPENAI_BASE", "http://localhost:3001/api/v1/openai")
API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "")
WORKSPACE_SLUG = os.getenv("ANYTHINGLLM_WORKSPACE_SLUG", "local")

print("=" * 60)
print("AnythingLLM Connection Diagnostic")
print("=" * 60)
print()

print(f"📍 Base URL: {OPENAI_BASE}")
print(f"🔑 API Key: {API_KEY[:10]}..." if len(API_KEY) > 10 else "🔑 API Key: (not set)")
print(f"💼 Workspace: {WORKSPACE_SLUG}")
print()

# Test 1: Basic connectivity
print("Test 1: Checking server connectivity...")
try:
    # Parse base URL to get host
    from urllib.parse import urlparse
    parsed = urlparse(OPENAI_BASE)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"  Pinging: {base_url}")
    start = time.time()
    response = requests.get(base_url, timeout=5)
    elapsed = time.time() - start
    print(f"  ✅ Server reachable ({elapsed:.2f}s, status {response.status_code})")
except requests.exceptions.Timeout:
    print(f"  ❌ Connection timed out - server may be down")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    print(f"  ❌ Connection failed: {e}")
    print(f"  💡 Is AnythingLLM running? Check http://localhost:3001")
    sys.exit(1)
except Exception as e:
    print(f"  ⚠️  Warning: {e}")

print()

# Test 2: API endpoint
print("Test 2: Testing OpenAI-compatible API endpoint...")
try:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": WORKSPACE_SLUG,
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7,
        "max_tokens": 50
    }

    endpoint = f"{OPENAI_BASE}/chat/completions"
    print(f"  Calling: {endpoint}")
    print(f"  Model: {WORKSPACE_SLUG}")

    start = time.time()
    response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
    elapsed = time.time() - start

    if response.status_code == 200:
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            reply = data["choices"][0]["message"]["content"]
            print(f"  ✅ API working! ({elapsed:.2f}s)")
            print(f"  📝 Response: {reply[:100]}...")
        else:
            print(f"  ⚠️  Got response but unexpected format: {data}")
    elif response.status_code == 401:
        print(f"  ❌ Authentication failed - check your API key")
        sys.exit(1)
    elif response.status_code == 404:
        print(f"  ❌ Endpoint not found - check ANYTHINGLLM_OPENAI_BASE")
        print(f"  💡 Current: {OPENAI_BASE}")
        sys.exit(1)
    else:
        print(f"  ❌ API error (status {response.status_code})")
        print(f"  Response: {response.text[:200]}")
        sys.exit(1)

except requests.exceptions.Timeout:
    print(f"  ❌ API request timed out after 30 seconds")
    print(f"  💡 Your LLM may be slow or the server is overloaded")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("✅ All tests passed! AnythingLLM connection is working.")
print("=" * 60)
