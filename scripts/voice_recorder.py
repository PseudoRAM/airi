#!/usr/bin/env python3
# scripts/voice_recorder.py
"""
Voice recording and transcription module using Whisper.

This module provides functionality to:
- Record audio from the microphone
- Transcribe audio using OpenAI's Whisper model
- Save recordings to temporary files
"""
import os
import sys
import time
import wave
import tempfile
import threading
from pathlib import Path
from typing import Optional

try:
    import pyaudio
    import whisper
    import numpy as np
except ImportError as e:
    print(f"Error: Missing required package: {e}", file=sys.stderr)
    print("Please install dependencies: pip install openai-whisper pyaudio numpy", file=sys.stderr)
    sys.exit(1)


class VoiceRecorder:
    """Records and transcribes audio using Whisper."""

    def __init__(self, model_size: str = "base"):
        """
        Initialize the voice recorder.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                       - tiny: fastest, least accurate
                       - base: good balance (recommended)
                       - small: better accuracy, slower
                       - medium/large: best accuracy, slowest
        """
        self.model_size = model_size
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.audio = None

        # Audio recording settings
        self.chunk = 1024
        self.sample_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # 16kHz is optimal for Whisper

        # Load Whisper model (lazy loading)
        self._whisper_model = None

    @property
    def whisper_model(self):
        """Lazy load Whisper model."""
        if self._whisper_model is None:
            print(f"\n🔧 Loading Whisper model ({self.model_size})...", file=sys.stderr, flush=True)
            print(f"   This may take 30-60 seconds on first run...", file=sys.stderr, flush=True)
            print(f"   Starting model download/load...", file=sys.stderr, flush=True)
            sys.stderr.flush()

            try:
                import time
                start_time = time.time()
                print(f"   [DEBUG] Calling whisper.load_model('{self.model_size}')...", file=sys.stderr, flush=True)
                sys.stderr.flush()

                self._whisper_model = whisper.load_model(self.model_size)

                elapsed = time.time() - start_time
                print(f"   [DEBUG] Model loaded in {elapsed:.1f} seconds", file=sys.stderr, flush=True)
                print("✅ Model loaded successfully!", file=sys.stderr, flush=True)
                sys.stderr.flush()
            except Exception as e:
                print(f"❌ Failed to load model: {e}", file=sys.stderr, flush=True)
                print(f"   Error type: {type(e).__name__}", file=sys.stderr, flush=True)
                import traceback
                print("   Full traceback:", file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                raise
        return self._whisper_model

    def start_recording(self):
        """Start recording audio from the microphone."""
        if self.is_recording:
            raise RuntimeError("Already recording")

        self.frames = []
        self.is_recording = True

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()

        # Open stream
        try:
            self.stream = self.audio.open(
                format=self.sample_format,
                channels=self.channels,
                rate=self.rate,
                frames_per_buffer=self.chunk,
                input=True
            )
            print("🎤 Recording started... (press Enter to stop)", file=sys.stderr)
        except Exception as e:
            self.is_recording = False
            raise RuntimeError(f"Failed to start recording: {e}")

    def stop_recording(self) -> str:
        """
        Stop recording and save to a temporary WAV file.

        Returns:
            Path to the temporary WAV file
        """
        print("   [DEBUG] stop_recording() called", file=sys.stderr, flush=True)
        
        if not self.is_recording:
            raise RuntimeError("Not currently recording")

        print("   [DEBUG] Setting is_recording = False", file=sys.stderr, flush=True)
        self.is_recording = False

        # Stop and close the stream
        print("   [DEBUG] Stopping audio stream...", file=sys.stderr, flush=True)
        if self.stream:
            self.stream.stop_stream()
            print("   [DEBUG] Stream stopped", file=sys.stderr, flush=True)
            self.stream.close()
            print("   [DEBUG] Stream closed", file=sys.stderr, flush=True)

        print("   [DEBUG] Terminating PyAudio...", file=sys.stderr, flush=True)
        if self.audio:
            self.audio.terminate()
            print("   [DEBUG] PyAudio terminated", file=sys.stderr, flush=True)

        print("🛑 Recording stopped", file=sys.stderr, flush=True)

        # Save to temporary file
        print("   [DEBUG] Creating temp file...", file=sys.stderr, flush=True)
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        print(f"   [DEBUG] Temp file created: {temp_path}", file=sys.stderr, flush=True)

        print(f"   [DEBUG] Writing WAV file with {len(self.frames)} frames...", file=sys.stderr, flush=True)
        try:
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.sample_format) if self.audio else 2)
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))
            print("   [DEBUG] WAV file written successfully", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"   [DEBUG] ERROR writing WAV: {e}", file=sys.stderr, flush=True)
            raise

        print(f"📁 Audio saved to: {temp_path}", file=sys.stderr, flush=True)
        print("   [DEBUG] stop_recording() returning", file=sys.stderr, flush=True)
        return temp_path

    def record_chunk(self):
        """Record a single chunk of audio (call repeatedly while recording)."""
        if not self.is_recording or not self.stream:
            return

        try:
            data = self.stream.read(self.chunk, exception_on_overflow=False)
            self.frames.append(data)
        except Exception as e:
            print(f"Warning: Error reading audio chunk: {e}", file=sys.stderr)

    def get_audio_level(self, data: bytes) -> float:
        """
        Calculate the RMS (Root Mean Square) audio level of a chunk.

        Args:
            data: Audio data bytes

        Returns:
            RMS level (0.0 to 1.0 normalized)
        """
        # Convert bytes to numpy array
        audio_array = np.frombuffer(data, dtype=np.int16)
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
        # Normalize to 0-1 range (int16 max is 32767)
        normalized = rms / 32767.0
        return normalized

    def record_until_silence(self, silence_threshold: float = 0.01, silence_duration: float = 2.0) -> str:
        """
        Record audio until silence is detected for a specified duration.

        Args:
            silence_threshold: RMS level below which audio is considered silence (0.0-1.0)
            silence_duration: Duration of silence in seconds before stopping

        Returns:
            Path to the temporary WAV file
        """
        self.start_recording()

        silence_start = None
        consecutive_silence = 0.0
        chunk_duration = self.chunk / self.rate  # Duration of one chunk in seconds

        print(f"🎤 Recording... (will auto-stop after {silence_duration}s of silence)", file=sys.stderr, flush=True)

        try:
            while self.is_recording:
                if not self.stream:
                    break

                try:
                    # Read audio chunk
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    self.frames.append(data)

                    # Calculate audio level
                    level = self.get_audio_level(data)

                    # Check if this chunk is silent
                    if level < silence_threshold:
                        if silence_start is None:
                            silence_start = time.time()
                        consecutive_silence += chunk_duration

                        # Check if we've had enough consecutive silence
                        if consecutive_silence >= silence_duration:
                            print(f"🔇 Silence detected for {silence_duration}s, stopping...", file=sys.stderr, flush=True)
                            break
                    else:
                        # Reset silence counter if we detect sound
                        silence_start = None
                        consecutive_silence = 0.0

                except Exception as e:
                    print(f"Warning: Error reading audio chunk: {e}", file=sys.stderr)
                    break

        except KeyboardInterrupt:
            print("\n⚠️  Recording interrupted by user", file=sys.stderr, flush=True)

        # Stop recording and return path
        return self.stop_recording()

    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio file using Whisper.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            Transcribed text
        """
        print("🔄 Transcribing audio...", file=sys.stderr, flush=True)
        sys.stderr.flush()

        # Verify audio file exists
        if not os.path.exists(audio_path):
            raise RuntimeError(f"Audio file not found: {audio_path}")

        file_size = os.path.getsize(audio_path)
        print(f"   Audio file size: {file_size} bytes", file=sys.stderr, flush=True)
        sys.stderr.flush()

        if file_size < 1000:  # Less than 1KB is suspicious
            print(f"   ⚠️  Warning: Audio file is very small ({file_size} bytes)", file=sys.stderr, flush=True)
            sys.stderr.flush()

        try:
            print("   Loading audio and transcribing (this may take 10-30 seconds)...", file=sys.stderr, flush=True)
            sys.stderr.flush()

            print(f"   [DEBUG] About to call whisper_model.transcribe()...", file=sys.stderr, flush=True)
            sys.stderr.flush()

            result = self.whisper_model.transcribe(
                audio_path,
                language=language,
                fp16=False,  # Disable FP16 for CPU compatibility
                verbose=False  # Suppress Whisper's internal output
            )

            print(f"   [DEBUG] Transcription returned, extracting text...", file=sys.stderr, flush=True)
            sys.stderr.flush()

            transcribed_text = result["text"].strip()

            if transcribed_text:
                print(f"✅ Transcription complete!", file=sys.stderr, flush=True)
                preview = transcribed_text[:100] + ("..." if len(transcribed_text) > 100 else "")
                print(f"   Preview: {preview}", file=sys.stderr, flush=True)
                sys.stderr.flush()
            else:
                print(f"⚠️  Warning: Transcription returned empty text", file=sys.stderr, flush=True)
                sys.stderr.flush()

            return transcribed_text
        except Exception as e:
            print(f"❌ Transcription failed!", file=sys.stderr, flush=True)
            print(f"   Error: {e}", file=sys.stderr, flush=True)
            import traceback
            print("   Full traceback:", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            raise RuntimeError(f"Transcription failed: {e}")

    def record_and_transcribe(self, duration: Optional[float] = None) -> str:
        """
        Record audio and transcribe it.

        Args:
            duration: Optional recording duration in seconds. If None, record until stopped manually.

        Returns:
            Transcribed text
        """
        self.start_recording()

        if duration:
            # Record for specified duration
            start_time = time.time()
            while time.time() - start_time < duration and self.is_recording:
                self.record_chunk()
                time.sleep(0.01)
        else:
            # Record until user stops (you need to call stop_recording() externally)
            while self.is_recording:
                self.record_chunk()
                time.sleep(0.01)

        audio_path = self.stop_recording()

        try:
            transcription = self.transcribe_audio(audio_path)
            return transcription
        finally:
            # Clean up temporary file
            try:
                os.unlink(audio_path)
            except Exception:
                pass


def record_until_enter(model_size: str = "base") -> str:
    """
    Record audio until user presses Enter, then transcribe.

    Args:
        model_size: Whisper model size

    Returns:
        Transcribed text
    """
    print(f"\n🔧 Initializing VoiceRecorder with model '{model_size}'...", file=sys.stderr, flush=True)
    sys.stderr.flush()
    recorder = VoiceRecorder(model_size=model_size)
    print(f"✅ VoiceRecorder initialized", file=sys.stderr, flush=True)
    sys.stderr.flush()

    # Start recording in a separate thread
    recording_thread = threading.Thread(target=lambda: recorder.start_recording())
    recording_thread.start()
    recording_thread.join()

    # Record chunks until Enter is pressed
    def record_loop():
        while recorder.is_recording:
            recorder.record_chunk()
            time.sleep(0.01)

    record_thread = threading.Thread(target=record_loop)
    record_thread.start()

    # Wait for Enter key
    try:
        input()  # Wait for Enter
    except KeyboardInterrupt:
        pass

    # Stop recording
    print(f"\n🔧 Stopping recording...", file=sys.stderr, flush=True)
    sys.stderr.flush()
    audio_path = recorder.stop_recording()
    print(f"   [DEBUG] stop_recording() returned, path: {audio_path}", file=sys.stderr, flush=True)
    sys.stderr.flush()
    print(f"   [DEBUG] Waiting for record_thread to finish (join)...", file=sys.stderr, flush=True)
    sys.stderr.flush()
    record_thread.join(timeout=5)  # Add 5 second timeout
    if record_thread.is_alive():
        print(f"   [DEBUG] WARNING: record_thread is still alive after 5 seconds!", file=sys.stderr, flush=True)
    else:
        print(f"   [DEBUG] record_thread finished successfully", file=sys.stderr, flush=True)
    sys.stderr.flush()
    print(f"✅ Recording stopped, audio saved", file=sys.stderr, flush=True)
    sys.stderr.flush()

    # Transcribe
    print(f"\n🔧 Starting transcription process...", file=sys.stderr, flush=True)
    sys.stderr.flush()
    try:
        print(f"   [DEBUG] Calling recorder.transcribe_audio({audio_path})...", file=sys.stderr, flush=True)
        sys.stderr.flush()
        transcription = recorder.transcribe_audio(audio_path)
        print(f"   [DEBUG] transcribe_audio() returned: '{transcription[:50]}...'", file=sys.stderr, flush=True)
        sys.stderr.flush()
        print(f"✅ Transcription complete!", file=sys.stderr, flush=True)
        sys.stderr.flush()
        return transcription
    except Exception as e:
        print(f"❌ Transcription failed: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise
    finally:
        # Clean up
        print(f"🔧 Cleaning up audio file...", file=sys.stderr, flush=True)
        sys.stderr.flush()
        try:
            os.unlink(audio_path)
            print(f"✅ Audio file deleted", file=sys.stderr, flush=True)
            sys.stderr.flush()
        except Exception as e:
            print(f"⚠️  Warning: Could not delete audio file: {e}", file=sys.stderr, flush=True)
            sys.stderr.flush()


if __name__ == "__main__":
    # Simple test
    print("Voice Recorder Test")
    print("=" * 50)
    print("Press Enter to start recording...")
    input()

    transcription = record_until_enter(model_size="base")
    print(f"\nTranscription: {transcription}")

