#!/usr/bin/env python3
"""
CLI for managing conversations with AnythingLLM.
Supports starting conversations, continuing them, and clearing history.
"""
import sys
import os
import pickle
from pathlib import Path
from conversation_manager import ConversationManager


# State directory
STATE_DIR = Path.home() / "Library" / "Application Support" / "AnythingLLM-Menu"
STATE_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATION_STATE = STATE_DIR / "conversation.pkl"


def load_conversation() -> ConversationManager:
    """Load existing conversation or create new one."""
    if CONVERSATION_STATE.exists():
        try:
            with open(CONVERSATION_STATE, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading conversation: {e}", file=sys.stderr)
            # Fall through to create new conversation

    # Create new conversation
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a helpful, concise assistant.")
    return ConversationManager(system_prompt=system_prompt)


def save_conversation(manager: ConversationManager) -> None:
    """Save conversation state."""
    try:
        with open(CONVERSATION_STATE, "wb") as f:
            pickle.dump(manager, f)
    except Exception as e:
        print(f"Error saving conversation: {e}", file=sys.stderr)


def ask(question: str) -> None:
    """Ask a question in the current conversation."""
    manager = load_conversation()
    answer = manager.ask(question)
    save_conversation(manager)
    print(answer)


def clear() -> None:
    """Clear the conversation history."""
    if CONVERSATION_STATE.exists():
        CONVERSATION_STATE.unlink()
    print("Conversation cleared")


def status() -> None:
    """Show conversation status."""
    if CONVERSATION_STATE.exists():
        manager = load_conversation()
        history_count = len(manager.get_history())
        exchanges = history_count // 2  # Each exchange is user + assistant
        print(f"Active conversation: {exchanges} exchange{'s' if exchanges != 1 else ''}")
    else:
        print("No active conversation")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: conversation_cli.py <command> [args]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  ask <question>  - Ask a question in conversation", file=sys.stderr)
        print("  clear           - Clear conversation history", file=sys.stderr)
        print("  status          - Show conversation status", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "ask":
        if len(sys.argv) < 3:
            print("Error: question required", file=sys.stderr)
            sys.exit(1)
        ask(sys.argv[2])
    elif command == "clear":
        clear()
    elif command == "status":
        status()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
