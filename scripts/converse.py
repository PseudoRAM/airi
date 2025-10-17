#!/usr/bin/env python3
# scripts/converse.py
"""
Interactive conversation CLI with AnythingLLM.

Usage:
    python scripts/converse.py

Commands:
    /exit, /quit, /q  - Exit the conversation
    /clear            - Clear conversation history
    /history          - Show conversation history
    /save [filepath]  - Save conversation to file
"""
import os
import sys
from conversation_manager import ConversationManager


def print_help():
    """Print available commands."""
    print("\nAvailable commands:")
    print("  /exit, /quit, /q  - Exit the conversation")
    print("  /clear            - Clear conversation history")
    print("  /history          - Show conversation history")
    print("  /save [filepath]  - Save conversation to file")
    print("  /help             - Show this help message")
    print()


def print_history(manager: ConversationManager):
    """Print the conversation history."""
    history = manager.get_history()
    if not history:
        print("\nNo conversation history yet.\n")
        return

    print("\n" + "=" * 80)
    print("CONVERSATION HISTORY")
    print("=" * 80)
    for role, content in history:
        print(f"\n{role.upper()}: {content}")
    print("\n" + "=" * 80 + "\n")


def main():
    # Get system prompt from environment or use default
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a helpful, conversational assistant.")

    # Initialize conversation manager
    manager = ConversationManager(system_prompt=system_prompt)

    # Print welcome message
    print("=== AI Walkie-Talkie ===")
    print("Type your message and press Enter. Type /help for commands.\n")

    while True:
        # Get user input
        try:
            user_input = input("You: ").strip()
        except EOFError:
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

        # Handle empty input
        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            command_parts = user_input.split(maxsplit=1)
            command = command_parts[0].lower()

            if command in ["/exit", "/quit", "/q"]:
                print("Goodbye!")
                break

            elif command == "/clear":
                manager.clear_history()
                print("Conversation history cleared.\n")
                continue

            elif command == "/history":
                print_history(manager)
                continue

            elif command == "/save":
                if len(command_parts) < 2:
                    # Default save location
                    state_dir = os.path.expanduser("~/Library/Application Support/AnythingLLM-Menu")
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = os.path.join(state_dir, f"conversation_{timestamp}.txt")
                else:
                    filepath = os.path.expanduser(command_parts[1])

                manager.save_conversation(filepath)
                print(f"Conversation saved to: {filepath}\n")
                continue

            elif command == "/help":
                print_help()
                continue

            else:
                print(f"Unknown command: {command}. Type /help for available commands.\n")
                continue

        # Get AI response
        try:
            response = manager.ask(user_input)
            print(f"AI: {response}\n")
        except Exception as e:
            print(f"Error: {e}\n", file=sys.stderr)
            continue


if __name__ == "__main__":
    main()
