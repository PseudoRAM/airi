# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a macOS menu bar application that provides quick access to AnythingLLM through a simple dialog interface. The app uses Python + LangChain on the backend and a bash script for the menu interface, bundled as a macOS .app using Platypus.

## Architecture

- **menu.sh**: Main bash script that handles the menu bar UI (via Platypus) and dispatches user actions
  - Renders menu items when called with no arguments
  - Dispatches to specific functions based on selected menu item
  - Prompts user via AppleScript dialogs
  - Stores last answer at `~/Library/Application Support/AnythingLLM-Menu/last.txt`

- **scripts/langchain_client.py**: LangChain wrapper for AnythingLLM's OpenAI-compatible API
  - Initializes ChatOpenAI with AnythingLLM base URL
  - Uses workspace slug as the "model" parameter (AnythingLLM convention)
  - `ask_llm()` is the main interface for querying the LLM

- **scripts/ask_anythingllm.py**: CLI entry point called by menu.sh
  - Takes question as command-line argument
  - Supports optional SYSTEM_PROMPT environment variable
  - Prints response to stdout

- **Menu.app/**: Bundled macOS application (created via Platypus) containing menu.sh

## Setup and Configuration

1. **Python environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment variables** (copy `.env.sample` to `.env`):
   - `ANYTHINGLLM_OPENAI_BASE`: OpenAI-compatible API endpoint (default: `http://localhost:3001/api/v1/openai`)
   - `ANYTHINGLLM_API_KEY`: API key from AnythingLLM (Settings → API Keys)
   - `ANYTHINGLLM_WORKSPACE_SLUG`: Workspace slug (used as "model" parameter)
   - `SYSTEM_PROMPT`: Optional system prompt for the assistant

## Development Commands

**Test AnythingLLM connectivity**:
```bash
source .venv/bin/activate
python scripts/test_anythingllm.py
# or with custom prompt:
python scripts/test_anythingllm.py "your question here"
```

**Test the ask script directly**:
```bash
source .venv/bin/activate
python scripts/ask_anythingllm.py "your question"
```

**Run the menu script manually**:
```bash
./menu.sh          # Shows menu items
./menu.sh "Ask…"   # Triggers ask dialog
```

## Key Implementation Details

- The bash script resolves its own directory to find the project root, allowing it to work both when run directly and when bundled in Menu.app
- Environment variables are loaded from `.env` in the project root by menu.sh (line 13-16)
- AnythingLLM uses workspace slug as the model name in OpenAI-compatible API calls
- The Python virtual environment path is hardcoded in menu.sh:30 as `./.venv/bin/python`
- Last answer is cached to support "Copy last answer" functionality
