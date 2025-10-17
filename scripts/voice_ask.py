#!/usr/bin/env python3
# scripts/voice_ask.py
"""
Voice-activated question asking.

Records audio from microphone, transcribes with Whisper, and sends to AnythingLLM.
Can optionally use conversation mode for multi-turn conversations.

Usage:
    python scripts/voice_ask.py              # One-shot question
    python scripts/voice_ask.py --conversation  # Add to ongoing conversation
"""
import os
import sys
import argparse
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from voice_recorder import record_until_enter
    from langchain_client import ask_llm
    from conversation_manager import ConversationManager
    from conversation_cli import load_conversation, save_conversation
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    sys.exit(1)


def voice_ask_oneshot(model_size: str = "base"):
    """
    Record a voice question and get a one-shot answer.

    Args:
        model_size: Whisper model size to use
    """
    print("🎤 Press Enter to start recording your question...", file=sys.stderr, flush=True)
    
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        sys.exit(0)

    # Record and transcribe
    print("\n🎙️  Recording...", file=sys.stderr, flush=True)
    try:
        question = record_until_enter(model_size=model_size)
    except KeyboardInterrupt:
        print("\n\nRecording cancelled.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error recording: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    if not question.strip():
        print("\n❌ Error: No speech detected or transcription was empty", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ Transcription successful!", file=sys.stderr, flush=True)
    print(f"📝 You said: {question}", file=sys.stderr, flush=True)
    print(f"\n💭 Asking AI...", file=sys.stderr, flush=True)

    # Get system prompt from environment
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a concise, accurate assistant.")

    # Ask the LLM
    try:
        answer = ask_llm(question, system=system_prompt)
        print(answer)  # Print to stdout for shell script to capture
    except Exception as e:
        print(f"\n❌ Error getting AI response: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def voice_ask_conversation(model_size: str = "base"):
    """
    Record a voice question and add to ongoing conversation.

    Args:
        model_size: Whisper model size to use
    """
    print("🎤 Press Enter to start recording your question...", file=sys.stderr, flush=True)
    
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        sys.exit(0)

    # Record and transcribe
    print("\n🎙️  Recording...", file=sys.stderr, flush=True)
    try:
        question = record_until_enter(model_size=model_size)
    except KeyboardInterrupt:
        print("\n\nRecording cancelled.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error recording: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    if not question.strip():
        print("\n❌ Error: No speech detected or transcription was empty", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ Transcription successful!", file=sys.stderr, flush=True)
    print(f"📝 You said: {question}", file=sys.stderr, flush=True)
    print(f"\n💭 Asking AI...", file=sys.stderr, flush=True)

    # Load or create conversation
    manager = load_conversation()

    # Ask and get response
    try:
        answer = manager.ask(question)
        save_conversation(manager)
        print(answer)  # Print to stdout for shell script to capture
    except Exception as e:
        print(f"\n❌ Error getting AI response: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Voice-activated AI assistant"
    )
    parser.add_argument(
        "--conversation",
        action="store_true",
        help="Use conversation mode (maintains history)"
    )
    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size (default: base)"
    )

    args = parser.parse_args()

    if args.conversation:
        voice_ask_conversation(model_size=args.model)
    else:
        voice_ask_oneshot(model_size=args.model)


if __name__ == "__main__":
    main()

