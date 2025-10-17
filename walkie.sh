#!/usr/bin/env bash
# walkie.sh - AI Walkie-Talkie with text-to-speech
#
# Usage: ./walkie.sh
#
# This script provides an interactive conversation interface with AnythingLLM
# that speaks responses using macOS text-to-speech (Lee Premium voice).

set -euo pipefail

# Resolve script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# State directory
STATE_DIR="$HOME/Library/Application Support/AnythingLLM-Menu"
mkdir -p "$STATE_DIR"

# Config file locations
CONFIG_FILE="$STATE_DIR/.env"
FALLBACK_CONFIG="$ROOT_DIR/.env"

# Load environment variables
if [[ -f "$CONFIG_FILE" ]]; then
  set -a
  source "$CONFIG_FILE"
  set +a
elif [[ -f "$FALLBACK_CONFIG" ]]; then
  set -a
  source "$FALLBACK_CONFIG"
  set +a
else
  echo "Error: No configuration file found at $CONFIG_FILE or $FALLBACK_CONFIG"
  echo "Please copy .env.sample to .env and configure your settings."
  exit 1
fi

# Voice to use for text-to-speech
VOICE="${TTS_VOICE:-Lee (Premium)}"

# Python interpreter
if [[ -f "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

# Check if Python script exists
CONVERSE_SCRIPT="$ROOT_DIR/scripts/converse.py"
if [[ ! -f "$CONVERSE_SCRIPT" ]]; then
  echo "Error: Conversation script not found at $CONVERSE_SCRIPT"
  exit 1
fi

# Function to speak text
speak() {
  local text="$1"
  # Run say in background so it doesn't block the conversation
  say -v "$VOICE" "$text" &
}

# Print banner
echo "=========================================="
echo "   AI Walkie-Talkie with Text-to-Speech"
echo "=========================================="
echo "Voice: $VOICE"
echo "Workspace: $ANYTHINGLLM_WORKSPACE_SLUG"
echo ""
echo "Commands: /help, /exit, /clear, /history"
echo "=========================================="
echo ""

# Create a named pipe for communication
PIPE_DIR=$(mktemp -d)
PIPE_IN="$PIPE_DIR/pipe_in"
PIPE_OUT="$PIPE_DIR/pipe_out"

mkfifo "$PIPE_IN"
mkfifo "$PIPE_OUT"

# Cleanup function
cleanup() {
  rm -rf "$PIPE_DIR"
  # Kill any remaining say processes
  pkill -f "say -v \"$VOICE\"" 2>/dev/null || true
}

trap cleanup EXIT

# Start the Python conversation script in background
cd "$ROOT_DIR"
"$PYTHON" "$CONVERSE_SCRIPT" < "$PIPE_IN" > "$PIPE_OUT" 2>&1 &
PYTHON_PID=$!

# Function to handle Python process exit
check_python() {
  if ! kill -0 $PYTHON_PID 2>/dev/null; then
    echo "Conversation process ended."
    exit 0
  fi
}

# Read output from Python and handle TTS
(
  while IFS= read -r line; do
    echo "$line"

    # If line starts with "AI: ", speak it
    if [[ "$line" =~ ^AI:\ (.+)$ ]]; then
      ai_response="${BASH_REMATCH[1]}"
      speak "$ai_response"
    fi
  done < "$PIPE_OUT"
) &
OUTPUT_PID=$!

# Read user input and send to Python
(
  while IFS= read -r -p "" user_input; do
    check_python
    echo "$user_input" > "$PIPE_IN"

    # Check for exit commands
    if [[ "$user_input" =~ ^/(exit|quit|q)$ ]]; then
      break
    fi
  done

  # Send EOF to Python script
  exec 3>&-
) &
INPUT_PID=$!

# Open pipe for writing
exec 3>"$PIPE_IN"

# Wait for processes to finish
wait $PYTHON_PID 2>/dev/null || true
wait $OUTPUT_PID 2>/dev/null || true
wait $INPUT_PID 2>/dev/null || true

echo ""
echo "Goodbye!"
