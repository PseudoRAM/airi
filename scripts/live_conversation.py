#!/usr/bin/env python3
# scripts/live_conversation.py
"""
Live hands-free conversation mode.

Continuously listens for voice input, auto-detects when you stop speaking,
transcribes, gets AI response, and speaks it back. Loops until interrupted.

Usage:
    python scripts/live_conversation.py
"""
import os
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from voice_recorder import VoiceRecorder
    from conversation_manager import ConversationManager
    from conversation_cli import load_conversation, save_conversation
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    """Run the live conversation loop."""
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("   🎙️  LIVE CONVERSATION MODE", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("", file=sys.stderr)
    print("This mode will:", file=sys.stderr)
    print("  • Start recording automatically", file=sys.stderr)
    print("  • Detect when you stop speaking (2s silence)", file=sys.stderr)
    print("  • Get AI response and speak it back", file=sys.stderr)
    print("  • Loop continuously", file=sys.stderr)
    print("", file=sys.stderr)
    print("Press Ctrl+C at any time to exit", file=sys.stderr)
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("", file=sys.stderr)

    # Initialize components
    print("🔧 Initializing...", file=sys.stderr, flush=True)
    recorder = VoiceRecorder(model_size="base")

    # Load or create conversation
    manager = load_conversation()
    turn_count = len(manager.conversation_history) // 2

    if turn_count > 0:
        print(f"✅ Loaded existing conversation ({turn_count} exchanges)", file=sys.stderr, flush=True)
    else:
        print("✅ Starting new conversation", file=sys.stderr, flush=True)

    print("", file=sys.stderr, flush=True)

    # Main conversation loop
    turn_number = turn_count + 1

    try:
        while True:
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
            print(f"Turn {turn_number}", file=sys.stderr)
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
            print("", file=sys.stderr, flush=True)

            # Record with silence detection
            try:
                audio_path = recorder.record_until_silence(
                    silence_threshold=0.01,
                    silence_duration=2.0
                )
            except KeyboardInterrupt:
                print("\n\n👋 Exiting live conversation mode...", file=sys.stderr)
                break
            except Exception as e:
                print(f"\n❌ Error during recording: {e}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc(file=sys.stderr)
                continue

            # Transcribe
            print("", file=sys.stderr, flush=True)
            try:
                question = recorder.transcribe_audio(audio_path)
            except Exception as e:
                print(f"❌ Transcription failed: {e}", file=sys.stderr, flush=True)
                # Clean up audio file
                try:
                    os.unlink(audio_path)
                except:
                    pass
                continue
            finally:
                # Clean up audio file
                try:
                    os.unlink(audio_path)
                except:
                    pass

            # Check if transcription is empty
            if not question.strip():
                print("⚠️  No speech detected, listening again...", file=sys.stderr, flush=True)
                print("", file=sys.stderr, flush=True)
                continue

            print("", file=sys.stderr, flush=True)
            print(f"📝 You: {question}", file=sys.stderr, flush=True)
            print("", file=sys.stderr, flush=True)

            # Get AI response
            print("💭 Thinking...", file=sys.stderr, flush=True)
            try:
                answer = manager.ask(question)
                save_conversation(manager)
            except Exception as e:
                print(f"❌ Error getting AI response: {e}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc(file=sys.stderr)
                continue

            print("", file=sys.stderr, flush=True)
            print(f"🤖 AI: {answer}", file=sys.stderr, flush=True)
            print("", file=sys.stderr, flush=True)

            # Output answer to stdout (for shell script to capture if needed)
            print(answer)
            sys.stdout.flush()

            # Increment turn counter
            turn_number += 1

            print("", file=sys.stderr, flush=True)

    except KeyboardInterrupt:
        print("\n\n👋 Exiting live conversation mode...", file=sys.stderr)

    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Conversation ended. History has been saved.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()
