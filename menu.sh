#!/usr/bin/env bash


# Resolve script dir and project root regardless of bundling
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect if running from Platypus bundle or directly
if [[ "$SCRIPT_DIR" == *.app/Contents/Resources ]]; then
  # Running from bundled app - script is in Resources, project root is Resources too
  ROOT_DIR="$SCRIPT_DIR"
else
  # Running directly - script is in project root
  ROOT_DIR="$SCRIPT_DIR"
fi
STATE_DIR="$HOME/Library/Application Support/AnythingLLM-Menu"
mkdir -p "$STATE_DIR"
LAST_TXT="$STATE_DIR/last.txt"
CONFIG_FILE="$STATE_DIR/.env"
LOG_FILE="$STATE_DIR/debug.log"

# Logging function
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

log "========== Menu.sh started =========="
log "SCRIPT_DIR: $SCRIPT_DIR"
log "ROOT_DIR: $ROOT_DIR"
log "STATE_DIR: $STATE_DIR"
log "CONFIG_FILE: $CONFIG_FILE"


# Setup: Copy .env.sample to persistent location if no config exists
if [[ ! -f "$CONFIG_FILE" ]] && [[ -f "$ROOT_DIR/.env.sample" ]]; then
  log "Config not found, copying .env.sample to $CONFIG_FILE"
  cp "$ROOT_DIR/.env.sample" "$CONFIG_FILE"
  osascript -e 'display notification "Please configure your settings" with title "AnythingLLM Menu" subtitle "Edit: ~/Library/Application Support/AnythingLLM-Menu/.env"' 2>/dev/null || true
else
  log "Config check: CONFIG_FILE exists=$([[ -f "$CONFIG_FILE" ]] && echo yes || echo no), .env.sample exists=$([[ -f "$ROOT_DIR/.env.sample" ]] && echo yes || echo no)"
fi

# Load .env from persistent location (works both when running raw and when bundled)
if [[ -f "$CONFIG_FILE" ]]; then
  log "Loading config from: $CONFIG_FILE"
  set -a  # Auto-export all variables
  source "$CONFIG_FILE"
  set +a
  log "Config loaded. ANYTHINGLLM_API_KEY=${ANYTHINGLLM_API_KEY:0:10}..., ANYTHINGLLM_OPENAI_BASE=$ANYTHINGLLM_OPENAI_BASE, ANYTHINGLLM_WORKSPACE_SLUG=$ANYTHINGLLM_WORKSPACE_SLUG"
elif [[ -f "$ROOT_DIR/.env" ]]; then
  # Fallback: load from project root (for development)
  log "Loading config from fallback: $ROOT_DIR/.env"
  set -a
  source "$ROOT_DIR/.env"
  set +a
  log "Config loaded from fallback. ANYTHINGLLM_API_KEY=${ANYTHINGLLM_API_KEY:0:10}..., ANYTHINGLLM_OPENAI_BASE=$ANYTHINGLLM_OPENAI_BASE"
else
  log "ERROR: No config file found at $CONFIG_FILE or $ROOT_DIR/.env"
fi


ask() {
  log "ask() called"
  # Prompt user for a question via AppleScript dialog
  local prompt
  prompt=$(osascript -e 'display dialog "Ask the local AI:" default answer "" with title "AnythingLLM" buttons {"Cancel","Ask"} default button "Ask"' \
                      -e 'text returned of result' 2>/dev/null || true)
  if [[ -z "${prompt:-}" ]]; then
    log "ask() cancelled or empty prompt"
    exit 0
  fi
  log "ask() prompt: $prompt"

  # Run the Python CLI and capture the answer
  log "ask() running Python from: $ROOT_DIR"
  log "ask() Python path check: venv=$([[ -f "$ROOT_DIR/.venv/bin/python" ]] && echo exists || echo missing)"
  local answer
  local python_output
  local python_errors

  cd "$ROOT_DIR"
  if [[ -f ./.venv/bin/python ]]; then
    log "ask() using venv python: ./.venv/bin/python"
    python_errors=$(mktemp)
    answer=$(./.venv/bin/python scripts/ask_anythingllm.py "$prompt" 2>"$python_errors")
    log "ask() Python stderr: $(cat "$python_errors")"
    rm "$python_errors"
  else
    log "ask() using system python3"
    python_errors=$(mktemp)
    answer=$(python3 scripts/ask_anythingllm.py "$prompt" 2>"$python_errors")
    log "ask() Python stderr: $(cat "$python_errors")"
    rm "$python_errors"
  fi

  log "ask() answer received (${#answer} chars): ${answer:0:100}..."

  # Save and show
  echo "$answer" > "$LAST_TXT"
  # Brief notification (non-blocking)
  osascript -e "display notification \"$(/bin/echo "$answer" | head -c 180 | sed 's/\\/\\\\/g; s/\"/\\\"/g')\" with title \"AnythingLLM\" subtitle \"Answer\""
  log "ask() completed successfully"
}


conversation_ask() {
  log "conversation_ask() called"
  # Prompt user for a question via AppleScript dialog
  local prompt
  prompt=$(osascript -e 'display dialog "Continue conversation:" default answer "" with title "AnythingLLM Conversation" buttons {"Cancel","Ask"} default button "Ask"' \
                      -e 'text returned of result' 2>/dev/null || true)
  if [[ -z "${prompt:-}" ]]; then
    log "conversation_ask() cancelled or empty prompt"
    exit 0
  fi
  log "conversation_ask() prompt: $prompt"

  # Run the conversation CLI
  log "conversation_ask() running Python from: $ROOT_DIR"
  local answer
  local python_errors

  cd "$ROOT_DIR"
  if [[ -f ./.venv/bin/python ]]; then
    log "conversation_ask() using venv python"
    python_errors=$(mktemp)
    answer=$(./.venv/bin/python scripts/conversation_cli.py ask "$prompt" 2>"$python_errors")
    log "conversation_ask() Python stderr: $(cat "$python_errors")"
    rm "$python_errors"
  else
    log "conversation_ask() using system python3"
    python_errors=$(mktemp)
    answer=$(python3 scripts/conversation_cli.py ask "$prompt" 2>"$python_errors")
    log "conversation_ask() Python stderr: $(cat "$python_errors")"
    rm "$python_errors"
  fi

  log "conversation_ask() answer received (${#answer} chars): ${answer:0:100}..."

  # Save and show
  echo "$answer" > "$LAST_TXT"
  osascript -e "display notification \"$(/bin/echo "$answer" | head -c 180 | sed 's/\\/\\\\/g; s/\"/\\\"/g')\" with title \"AnythingLLM\" subtitle \"Conversation\""
  log "conversation_ask() completed successfully"
}


conversation_clear() {
  log "conversation_clear() called"
  cd "$ROOT_DIR"
  if [[ -f ./.venv/bin/python ]]; then
    ./.venv/bin/python scripts/conversation_cli.py clear
  else
    python3 scripts/conversation_cli.py clear
  fi
  osascript -e 'display notification "Conversation history cleared" with title "AnythingLLM"'
  log "conversation_clear() completed"
}


conversation_status() {
  log "conversation_status() called"
  cd "$ROOT_DIR"
  local status
  local python_errors
  python_errors=$(mktemp)

  if [[ -f ./.venv/bin/python ]]; then
    status=$(./.venv/bin/python scripts/conversation_cli.py status 2>"$python_errors")
  else
    status=$(python3 scripts/conversation_cli.py status 2>"$python_errors")
  fi

  local exit_code=$?
  log "conversation_status() stderr: $(cat "$python_errors")"
  rm "$python_errors"

  if [[ $exit_code -ne 0 ]] || [[ -z "$status" ]]; then
    log "conversation_status() failed with exit code $exit_code"
    echo "No active conversation"
  else
    log "conversation_status() result: $status"
    echo "$status"
  fi
}


voice_ask() {
  log "voice_ask() called"
  
  # Create a temporary script that will run in Terminal
  local temp_script
  temp_script=$(mktemp)
  
  cat > "$temp_script" << 'VOICE_SCRIPT_EOF'
#!/usr/bin/env bash
set -e

# Add Homebrew to PATH (required for ffmpeg)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "=========================================="
echo "   🎤 Voice Ask - AI Walkie-Talkie"
echo "=========================================="
echo ""

# Verify ffmpeg is available
if command -v ffmpeg &> /dev/null; then
  echo "✓ ffmpeg found: $(which ffmpeg)"
else
  echo "❌ Error: ffmpeg not found in PATH"
  echo "   Install with: brew install ffmpeg"
  echo "   Press any key to close..."
  read -n 1 -s
  exit 1
fi
echo ""

# Determine ROOT_DIR and Python
if [[ -f "/Users/pseudoram/Developer/ai-walkie/Menu.app/Contents/Resources/.venv/bin/python" ]]; then
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie/Menu.app/Contents/Resources"
  PYTHON="$ROOT_DIR/.venv/bin/python"
  echo "✓ Using Menu.app venv"
elif [[ -f "/Users/pseudoram/Developer/ai-walkie/.venv/bin/python" ]]; then
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie"
  PYTHON="$ROOT_DIR/.venv/bin/python"
  echo "✓ Using project venv"
else
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie"
  PYTHON="python3"
  echo "✓ Using system python3"
fi

STATE_DIR="$HOME/Library/Application Support/AnythingLLM-Menu"
LAST_TXT="$STATE_DIR/last.txt"
mkdir -p "$STATE_DIR"

echo "✓ Python: $PYTHON"
echo "✓ Scripts: $ROOT_DIR/scripts"
echo ""

cd "$ROOT_DIR" || {
  echo "❌ Error: Cannot change to directory $ROOT_DIR"
  echo "Press any key to close..."
  read -n 1 -s
  exit 1
}

# Check if voice script exists
if [[ ! -f "scripts/voice_ask.py" ]]; then
  echo "❌ Error: voice_ask.py not found at $ROOT_DIR/scripts/voice_ask.py"
  echo "Press any key to close..."
  read -n 1 -s
  exit 1
fi

# Run voice recording
echo "Starting voice recording..."
echo ""

if "$PYTHON" scripts/voice_ask.py 2>&1 | tee /tmp/voice_output.txt; then
  # Get the last line as the answer
  answer=$(tail -1 /tmp/voice_output.txt)
  
  echo ""
  echo "✅ Response received!"
  echo ""
  
  # Save answer
  echo "$answer" > "$LAST_TXT"
  
  # Speak the answer
  VOICE="${TTS_VOICE:-Lee (Premium)}"
  say -v "$VOICE" "$answer" &
  
  echo "=========================================="
  echo "Press any key to close..."
  read -n 1 -s
else
  echo ""
  echo "❌ Voice recording failed or was cancelled"
  echo ""
  echo "Press any key to close..."
  read -n 1 -s
fi

rm -f /tmp/voice_output.txt
VOICE_SCRIPT_EOF

  chmod +x "$temp_script"
  
  # Open Terminal and run the script
  osascript <<EOF
tell application "Terminal"
  activate
  do script "$temp_script && rm '$temp_script'"
end tell
EOF

  log "voice_ask() Terminal window opened"
}


voice_conversation() {
  log "voice_conversation() called"
  
  # Create a temporary script that will run in Terminal
  local temp_script
  temp_script=$(mktemp)
  
  cat > "$temp_script" << 'VOICE_SCRIPT_EOF'
#!/usr/bin/env bash
set -e

# Add Homebrew to PATH (required for ffmpeg)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "=========================================="
echo "   🎤 Voice Conversation - AI Walkie"
echo "=========================================="
echo ""

# Verify ffmpeg is available
if command -v ffmpeg &> /dev/null; then
  echo "✓ ffmpeg found: $(which ffmpeg)"
else
  echo "❌ Error: ffmpeg not found in PATH"
  echo "   Install with: brew install ffmpeg"
  echo "   Press any key to close..."
  read -n 1 -s
  exit 1
fi
echo ""

# Determine ROOT_DIR and Python
if [[ -f "/Users/pseudoram/Developer/ai-walkie/Menu.app/Contents/Resources/.venv/bin/python" ]]; then
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie/Menu.app/Contents/Resources"
  PYTHON="$ROOT_DIR/.venv/bin/python"
  echo "✓ Using Menu.app venv"
elif [[ -f "/Users/pseudoram/Developer/ai-walkie/.venv/bin/python" ]]; then
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie"
  PYTHON="$ROOT_DIR/.venv/bin/python"
  echo "✓ Using project venv"
else
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie"
  PYTHON="python3"
  echo "✓ Using system python3"
fi

STATE_DIR="$HOME/Library/Application Support/AnythingLLM-Menu"
LAST_TXT="$STATE_DIR/last.txt"
mkdir -p "$STATE_DIR"

echo "✓ Python: $PYTHON"
echo "✓ Scripts: $ROOT_DIR/scripts"
echo ""

cd "$ROOT_DIR" || {
  echo "❌ Error: Cannot change to directory $ROOT_DIR"
  echo "Press any key to close..."
  read -n 1 -s
  exit 1
}

# Check if voice script exists
if [[ ! -f "scripts/voice_ask.py" ]]; then
  echo "❌ Error: voice_ask.py not found at $ROOT_DIR/scripts/voice_ask.py"
  echo "Press any key to close..."
  read -n 1 -s
  exit 1
fi

# Run voice recording with conversation mode
echo "Starting voice conversation..."
echo ""

# Load TTS voice from config
STATE_DIR="$HOME/Library/Application Support/AnythingLLM-Menu"
CONFIG_FILE="$STATE_DIR/.env"
if [[ -f "$CONFIG_FILE" ]]; then
  source "$CONFIG_FILE"
fi
VOICE="${TTS_VOICE:-Lee (Premium)}"

# Use a temp file to capture just the answer (stdout)
ANSWER_FILE=$(mktemp)

# Run with unbuffered output, show all progress, capture answer separately
"$PYTHON" -u scripts/voice_ask.py --conversation 2>&1 | tee "$ANSWER_FILE"
EXIT_CODE=${PIPESTATUS[0]}

if [[ $EXIT_CODE -eq 0 ]]; then
  # Get the last line as the answer
  answer=$(tail -1 "$ANSWER_FILE")

  echo ""
  echo "✅ Response received!"
  echo ""

  # Save answer
  echo "$answer" > "$LAST_TXT"

  # Speak the answer (blocking - wait for it to finish)
  say -v "$VOICE" "$answer"

  echo "=========================================="
  echo "Press any key to close..."
  read -n 1 -s
else
  echo ""
  echo "❌ Voice recording failed or was cancelled"
  echo ""
  echo "Press any key to close..."
  read -n 1 -s
fi

rm -f "$ANSWER_FILE"
VOICE_SCRIPT_EOF

  chmod +x "$temp_script"
  
  # Open Terminal and run the script
  osascript <<EOF
tell application "Terminal"
  activate
  do script "$temp_script && rm '$temp_script'"
end tell
EOF

  log "voice_conversation() Terminal window opened"
}


live_conversation() {
  log "live_conversation() called"

  # Create a temporary script that will run in Terminal
  local temp_script
  temp_script=$(mktemp)

  cat > "$temp_script" << 'LIVE_SCRIPT_EOF'
#!/usr/bin/env bash
set -e

# Add Homebrew to PATH (required for ffmpeg)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "=========================================="
echo "   🎙️  Live Conversation Mode"
echo "=========================================="
echo ""

# Verify ffmpeg is available
if command -v ffmpeg &> /dev/null; then
  echo "✓ ffmpeg found: $(which ffmpeg)"
else
  echo "❌ Error: ffmpeg not found in PATH"
  echo "   Install with: brew install ffmpeg"
  echo "   Press any key to close..."
  read -n 1 -s
  exit 1
fi
echo ""

# Determine ROOT_DIR and Python
if [[ -f "/Users/pseudoram/Developer/ai-walkie/Menu.app/Contents/Resources/.venv/bin/python" ]]; then
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie/Menu.app/Contents/Resources"
  PYTHON="$ROOT_DIR/.venv/bin/python"
  echo "✓ Using Menu.app venv"
elif [[ -f "/Users/pseudoram/Developer/ai-walkie/.venv/bin/python" ]]; then
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie"
  PYTHON="$ROOT_DIR/.venv/bin/python"
  echo "✓ Using project venv"
else
  ROOT_DIR="/Users/pseudoram/Developer/ai-walkie"
  PYTHON="python3"
  echo "✓ Using system python3"
fi

STATE_DIR="$HOME/Library/Application Support/AnythingLLM-Menu"
CONFIG_FILE="$STATE_DIR/.env"
mkdir -p "$STATE_DIR"

echo "✓ Python: $PYTHON"
echo "✓ Scripts: $ROOT_DIR/scripts"
echo ""

# Load TTS voice setting from config
if [[ -f "$CONFIG_FILE" ]]; then
  source "$CONFIG_FILE"
fi
VOICE="${TTS_VOICE:-Lee (Premium)}"
echo "✓ TTS Voice: $VOICE"
echo ""

cd "$ROOT_DIR" || {
  echo "❌ Error: Cannot change to directory $ROOT_DIR"
  echo "Press any key to close..."
  read -n 1 -s
  exit 1
}

# Check if live conversation script exists
if [[ ! -f "scripts/live_conversation.py" ]]; then
  echo "❌ Error: live_conversation.py not found at $ROOT_DIR/scripts/live_conversation.py"
  echo "Press any key to close..."
  read -n 1 -s
  exit 1
fi

# Start live conversation loop with TTS
echo ""

# Announce startup with TTS
say -v "$VOICE" "Airi is running"

# Run the Python script with unbuffered output (-u flag) and handle TTS in real-time
"$PYTHON" -u scripts/live_conversation.py 2>&1 | while IFS= read -r line; do
  # Always echo the line to show progress
  echo "$line"

  # Check if this line looks like an AI response (not stderr output with emojis/formatting)
  # The Python script prints the answer to stdout after the "AI:" message to stderr
  if [[ ! "$line" =~ ^[🎙️🔧🔇📝💭🤖✅❌⚠️━═👂🔊] ]] && \
     [[ ! "$line" =~ ^Turn ]] && \
     [[ ! "$line" =~ ^=+ ]] && \
     [[ ! "$line" =~ ^LIVE ]] && \
     [[ -n "$line" ]]; then
    # This is the AI response, speak it (blocking - wait for it to finish)
    say -v "$VOICE" "$line"
  fi
done

echo ""
echo "Press any key to close..."
read -n 1 -s
LIVE_SCRIPT_EOF

  chmod +x "$temp_script"

  # Open Terminal and run the script
  osascript <<EOF
tell application "Terminal"
  activate
  do script "$temp_script && rm '$temp_script'"
end tell
EOF

  log "live_conversation() Terminal window opened"
}


copy_last() {
  [[ -f "$LAST_TXT" ]] || exit 0
  cat "$LAST_TXT" | pbcopy
  osascript -e 'display notification "Copied to clipboard" with title "AnythingLLM"'
}


view_logs() {
  log "view_logs() called"
  open -a Console "$LOG_FILE"
}


# -------- Status Menu rendering / dispatch --------
# No args: print menu items (one per line)
if [[ $# -eq 0 ]]; then
  log "Rendering menu items (no args)"
  echo "Ask…"
  echo "🎤 Voice Ask…"
  echo "----"
  echo "Conversation…"
  echo "🎤 Voice Conversation…"
  echo "🎙️ Start Live Conversation"
  echo "----"

  # Show conversation status if available
  conv_status=$(conversation_status)
  if [[ "$conv_status" == "No active conversation" ]] || [[ "$conv_status" == "Active conversation: 0 exchanges" ]]; then
    echo "Clear Conversation (disabled)"
  else
    echo "$conv_status"
    echo "Clear Conversation"
  fi

  echo "----"
  if [[ -s "$LAST_TXT" ]]; then
    # Show a preview line of last answer
    preview=$(tr -d '\n' < "$LAST_TXT" | head -c 60)
    echo "Copy last answer"
    echo "Last: $preview…"
  fi
  echo "View Logs"
  # Platypus will append a default "Quit" item automatically
  exit 0
fi


# With arg: dispatch by selected menu item text
log "Dispatching menu action: $1"
case "$1" in
  "Ask…")
    log "Action: ask"
    ask
    ;;
  "🎤 Voice Ask…")
    log "Action: voice_ask"
    voice_ask
    ;;
  "Conversation…")
    log "Action: conversation_ask"
    conversation_ask
    ;;
  "🎤 Voice Conversation…")
    log "Action: voice_conversation"
    voice_conversation
    ;;
  "🎙️ Start Live Conversation")
    log "Action: live_conversation"
    live_conversation
    ;;
  "Clear Conversation")
    log "Action: conversation_clear"
    conversation_clear
    ;;
  "Copy last answer")
    log "Action: copy_last"
    copy_last
    ;;
  "View Logs")
    log "Action: view_logs"
    view_logs
    ;;
  "Last: "*)
    log "Action: open last answer in TextEdit"
    open -a TextEdit "$LAST_TXT"
    ;;
  "Active conversation: "*)
    log "Action: show conversation status (no-op)"
    # This is just a status display, do nothing
    ;;
  "Clear Conversation (disabled)")
    log "Action: clear conversation disabled (no-op)"
    # Disabled item, do nothing
    ;;
  *)
    log "Unknown action: $1"
    ;; # fallthrough
esac

log "========== Menu.sh ended ==========="