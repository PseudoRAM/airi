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
  echo "----"
  echo "Conversation…"

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
  "Conversation…")
    log "Action: conversation_ask"
    conversation_ask
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