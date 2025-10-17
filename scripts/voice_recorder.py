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
            try:
                import os
                import contextlib

                # Suppress Whisper's verbose output during loading
                with open(os.devnull, 'w') as devnull:
                    with contextlib.redirect_stderr(devnull):
                        self._whisper_model = whisper.load_model(self.model_size)

            except Exception as e:
                print(f"❌ Failed to load Whisper model: {e}", file=sys.stderr, flush=True)
                import traceback
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
        if not self.is_recording:
            raise RuntimeError("Not currently recording")

        self.is_recording = False

        # Stop and close the stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        if self.audio:
            self.audio.terminate()

        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.sample_format) if self.audio else 2)
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))
        except Exception as e:
            raise RuntimeError(f"Failed to save audio: {e}")

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

    def is_speech(self, data: bytes, energy_threshold: float = 0.02) -> bool:
        """
        Detect if audio contains speech using energy and spectral analysis.

        This helps distinguish actual speech from constant background noise.

        Args:
            data: Audio data bytes
            energy_threshold: Minimum energy level for speech

        Returns:
            True if speech is detected, False otherwise
        """
        # Convert bytes to numpy array
        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)

        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_array ** 2)) / 32767.0

        # If energy is too low, it's not speech
        if rms < energy_threshold:
            return False

        # Check zero-crossing rate (speech has moderate ZCR, noise is often very low or very high)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_array)))) / 2
        zcr = zero_crossings / len(audio_array)

        # Speech typically has ZCR between 0.02 and 0.3
        # Pure tones/hums have very low ZCR
        # High-frequency noise has very high ZCR
        if zcr < 0.01 or zcr > 0.4:
            return False

        # Check spectral characteristics using FFT
        fft = np.fft.rfft(audio_array)
        magnitude = np.abs(fft)

        # Speech has significant energy in multiple frequency bands
        # Divide spectrum into low (0-500Hz), mid (500-2000Hz), high (2000-4000Hz)
        freq_bins = len(magnitude)
        low_band = magnitude[:int(freq_bins * 0.125)]  # ~0-1000Hz at 16kHz sample rate
        mid_band = magnitude[int(freq_bins * 0.125):int(freq_bins * 0.5)]  # ~1000-4000Hz
        high_band = magnitude[int(freq_bins * 0.5):int(freq_bins * 0.75)]  # ~4000-6000Hz

        low_energy = np.mean(low_band)
        mid_energy = np.mean(mid_band)
        high_energy = np.mean(high_band)

        # Speech typically has higher mid-band energy
        # Background hum/noise often concentrated in low frequencies
        total_energy = low_energy + mid_energy + high_energy
        if total_energy == 0:
            return False

        mid_ratio = mid_energy / total_energy

        # Speech should have at least 25% of energy in mid-band
        if mid_ratio < 0.25:
            return False

        return True

    def wait_for_sound(self, sound_threshold: float = 0.02, check_duration: float = 0.5,
                      consecutive_chunks: int = 3) -> bool:
        """
        Wait until speech is detected above the threshold.

        Args:
            sound_threshold: RMS level above which audio is considered sound (0.0-1.0)
            check_duration: How long to wait before checking again (seconds)
            consecutive_chunks: Number of consecutive chunks with speech to confirm (reduces false positives)

        Returns:
            True if speech was detected, False if interrupted
        """
        print(f"👂 Listening...", end='', file=sys.stderr, flush=True)

        # Initialize PyAudio temporarily just to listen
        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(
                format=self.sample_format,
                channels=self.channels,
                rate=self.rate,
                frames_per_buffer=self.chunk,
                input=True
            )

            try:
                speech_count = 0
                while True:
                    # Read a chunk
                    data = stream.read(self.chunk, exception_on_overflow=False)

                    # Use speech detection instead of just level
                    if self.is_speech(data, energy_threshold=sound_threshold):
                        speech_count += 1
                        if speech_count >= consecutive_chunks:
                            # Clear the "Listening..." line and print speech detected
                            print(f"\r👂 Listening... ✓", file=sys.stderr, flush=True)
                            stream.stop_stream()
                            stream.close()
                            audio.terminate()
                            return True
                    else:
                        # Reset counter if we don't detect speech
                        speech_count = 0

                    time.sleep(0.01)

            except KeyboardInterrupt:
                print(f"\r👂 Listening... cancelled", file=sys.stderr, flush=True)
                stream.stop_stream()
                stream.close()
                audio.terminate()
                return False

        except Exception as e:
            if audio:
                audio.terminate()
            raise e

    def record_until_silence(self, silence_threshold: float = 0.01, silence_duration: float = 2.0,
                            wait_for_sound: bool = True) -> str:
        """
        Record audio until silence is detected for a specified duration.
        Uses speech detection to ignore background noise.

        Args:
            silence_threshold: RMS level below which audio is considered silence (0.0-1.0)
            silence_duration: Duration of silence in seconds before stopping
            wait_for_sound: If True, wait for sound before starting recording

        Returns:
            Path to the temporary WAV file
        """
        # First, wait for sound to be detected
        if wait_for_sound:
            if not self.wait_for_sound(sound_threshold=silence_threshold * 2):
                # User interrupted
                raise KeyboardInterrupt("Interrupted while waiting for sound")

        self.start_recording()

        silence_start = None
        consecutive_silence = 0.0
        chunk_duration = self.chunk / self.rate  # Duration of one chunk in seconds
        has_recorded_speech = False  # Track if we've recorded any actual speech

        print(f"🎤 Recording...", file=sys.stderr, flush=True)

        try:
            while self.is_recording:
                if not self.stream:
                    break

                try:
                    # Read audio chunk
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    self.frames.append(data)

                    # Use speech detection instead of just audio level
                    # This way background noise won't prevent silence detection
                    is_speaking = self.is_speech(data, energy_threshold=silence_threshold)

                    # Check if this chunk contains speech or is silent
                    if not is_speaking:
                        # Only start counting silence after we've recorded some speech
                        if has_recorded_speech:
                            if silence_start is None:
                                silence_start = time.time()
                            consecutive_silence += chunk_duration

                            # Check if we've had enough consecutive silence
                            if consecutive_silence >= silence_duration:
                                print(f"🔇 Stopped speaking", file=sys.stderr, flush=True)
                                break
                    else:
                        # We've detected speech
                        has_recorded_speech = True
                        # Reset silence counter if we detect speech
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
        print("🔄 Transcribing...", file=sys.stderr, flush=True)

        # Verify audio file exists
        if not os.path.exists(audio_path):
            raise RuntimeError(f"Audio file not found: {audio_path}")

        try:
            result = self.whisper_model.transcribe(
                audio_path,
                language=language,
                fp16=False,  # Disable FP16 for CPU compatibility
                verbose=False  # Suppress Whisper's internal output
            )

            transcribed_text = result["text"].strip()

            if not transcribed_text:
                print(f"⚠️  No speech detected", file=sys.stderr, flush=True)

            return transcribed_text
        except Exception as e:
            print(f"❌ Transcription failed: {e}", file=sys.stderr, flush=True)
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
    recorder = VoiceRecorder(model_size=model_size)

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
    audio_path = recorder.stop_recording()
    record_thread.join(timeout=5)

    # Transcribe
    try:
        transcription = recorder.transcribe_audio(audio_path)
        return transcription
    except Exception as e:
        print(f"❌ Transcription failed: {e}", file=sys.stderr, flush=True)
        raise
    finally:
        # Clean up
        try:
            os.unlink(audio_path)
        except Exception as e:
            print(f"⚠️  Warning: Could not delete audio file: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    # Simple test
    print("Voice Recorder Test")
    print("=" * 50)
    print("Press Enter to start recording...")
    input()

    transcription = record_until_enter(model_size="base")
    print(f"\nTranscription: {transcription}")

