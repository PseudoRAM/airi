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
    import random

    # Simple, clean startup message
    print("", file=sys.stderr)
    print(f"🎙️  Airi is running...", file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)

    # Initialize components (this may take a moment for Whisper model loading)
    print("🔧 Loading AI models...", file=sys.stderr, flush=True)
    recorder = VoiceRecorder(model_size="base")

    # Force Whisper model to load now (lazy loading otherwise happens on first use)
    _ = recorder.whisper_model

    manager = load_conversation()
    print("✅ Ready!", file=sys.stderr, flush=True)
    print("", file=sys.stderr, flush=True)

    # Main conversation loop
    turn_count = len(manager.conversation_history) // 2
    turn_number = turn_count + 1

    try:
        while True:

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
                continue

            print(f"📝 You: {question}", file=sys.stderr, flush=True)

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

            print(f"🤖 Airi: {answer}", file=sys.stderr, flush=True)

            # Output answer to stdout (for shell script to capture for TTS)
            print(answer)
            sys.stdout.flush()

            # Increment turn counter
            turn_number += 1

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!", file=sys.stderr)


if __name__ == "__main__":
    main()
