# =============================================================================
# voice_input.py — Voice Input Module for J.A.R.V.I.S
# =============================================================================
# This module handles listening to the microphone and converting speech to text.
#
# HOW IT WORKS:
# 1. A background thread continuously listens for audio
# 2. When it detects the wake word "hey jarvis" or "jarvis", it signals
#    that someone wants to talk
# 3. It records the user's full command and transcribes it using Whisper
# 4. The transcribed text is passed to a callback function for processing
#
# WAKE WORD DETECTION:
# - First tries to use pvporcupine (Picovoice) — very accurate, but needs
#   an API key (free tier available at https://picovoice.ai/)
# - If pvporcupine is unavailable, falls back to recording short clips and
#   checking if "jarvis" appears in the Whisper transcription
# =============================================================================

import io          # For in-memory byte streams
import threading   # For running the listener in a background thread
import time        # For sleep/timing

import numpy as np     # Numerical array operations (audio data is numpy arrays)
import sounddevice as sd  # For recording audio from the microphone
import whisper         # OpenAI's Whisper speech recognition model

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Whisper model size — "base" is a good balance of speed and accuracy
# Options: "tiny", "base", "small", "medium", "large"
# Larger = more accurate but slower. "base" works well for most systems.
WHISPER_MODEL_SIZE = "base"

# Audio recording settings
SAMPLE_RATE = 16000   # Whisper works best with 16kHz audio
CHANNELS = 1          # Mono audio (one microphone channel)

# How long to record when listening for the wake word (seconds)
WAKE_WORD_LISTEN_DURATION = 3

# How long to record after the wake word is detected (the actual command)
COMMAND_LISTEN_DURATION = 5

# Wake words that trigger Jarvis to listen
WAKE_WORDS = ["jarvis", "hey jarvis", "ok jarvis"]


# ---------------------------------------------------------------------------
# The VoiceInput class
# ---------------------------------------------------------------------------

class VoiceInput:
    """
    Handles all voice input — recording audio and transcribing it.
    
    Usage:
        voice = VoiceInput()
        # Listen once:
        text = voice.listen()
        # Start background listening with wake word:
        voice.start_listening(callback_function)
        # Stop listening:
        voice.stop_listening()
    """
    
    def __init__(self):
        """Initialize the voice input system — load Whisper model."""
        
        # This event is used to stop the background listening thread
        # When we call stop_event.set(), the thread will stop
        self.stop_event = threading.Event()
        
        # Whether we're currently running the background listener
        self.is_listening = False
        
        # The background thread (stored so we can check its status)
        self.listening_thread = None
        
        # The porcupine wake word detector (if available)
        self.porcupine = None
        
        # Load the Whisper model
        print(f"[Voice Input] Loading Whisper '{WHISPER_MODEL_SIZE}' model...")
        print("[Voice Input] This may take a moment on first run as the model downloads...")
        
        try:
            self.whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
            print("[Voice Input] Whisper model loaded successfully.")
        except Exception as e:
            print(f"[Voice Input] Failed to load Whisper model: {e}")
            print("[Voice Input] Voice input will not be available.")
            self.whisper_model = None
        
        # Try to initialize pvporcupine for accurate wake word detection
        self._try_init_porcupine()
    
    # -------------------------------------------------------------------------
    def _try_init_porcupine(self):
        """
        Attempt to initialize the pvporcupine wake word detector.
        
        pvporcupine provides very accurate, low-latency wake word detection.
        It requires a free API key from https://picovoice.ai/
        
        If it's not available or not configured, we fall back to
        Whisper-based keyword detection.
        """
        try:
            import pvporcupine  # Picovoice wake word library
            
            # Check if an API key is available
            porcupine_key = os.getenv("PORCUPINE_API_KEY", "")
            
            if porcupine_key:
                # Initialize with the built-in "jarvis" keyword
                # pvporcupine has "jarvis" as a built-in keyword!
                self.porcupine = pvporcupine.create(
                    access_key=porcupine_key,
                    keywords=["jarvis"]
                )
                print("[Voice Input] pvporcupine wake word detection active.")
            else:
                print(
                    "[Voice Input] No PORCUPINE_API_KEY found. "
                    "Falling back to Whisper-based wake word detection."
                )
        except ImportError:
            print(
                "[Voice Input] pvporcupine not installed. "
                "Using Whisper-based wake word detection instead."
            )
        except Exception as e:
            print(f"[Voice Input] pvporcupine init failed: {e}. Using fallback.")
    
    # -------------------------------------------------------------------------
    def _record_audio(self, duration: float) -> np.ndarray:
        """
        Record audio from the microphone for a specified duration.
        
        Args:
            duration: How many seconds to record.
            
        Returns:
            A numpy array containing the audio data.
        """
        try:
            # Record audio — sounddevice records into a numpy array
            audio_data = sd.rec(
                int(duration * SAMPLE_RATE),  # Total number of samples
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32"               # Whisper expects float32
            )
            
            # Wait for the recording to complete
            sd.wait()
            
            # Flatten from shape (samples, channels) to (samples,) for Whisper
            return audio_data.flatten()
            
        except sd.PortAudioError as e:
            print(f"[Voice Input] Microphone error: {e}")
            return np.array([])  # Return empty array on error
        except Exception as e:
            print(f"[Voice Input] Recording error: {e}")
            return np.array([])
    
    # -------------------------------------------------------------------------
    def _transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio data to text using OpenAI Whisper.
        
        Args:
            audio_data: NumPy array of float32 audio samples at 16kHz.
            
        Returns:
            The transcribed text, or empty string if transcription failed.
        """
        if self.whisper_model is None:
            return ""
        
        if len(audio_data) == 0:
            return ""
        
        try:
            # Whisper's transcribe() accepts a numpy array or file path
            # fp16=False is needed on CPU (most computers don't have CUDA)
            result = self.whisper_model.transcribe(
                audio_data,
                fp16=False,
                language="en"  # Specify English for better accuracy
            )
            
            text = result.get("text", "").strip()
            return text
            
        except Exception as e:
            print(f"[Voice Input] Transcription error: {e}")
            return ""
    
    # -------------------------------------------------------------------------
    def _contains_wake_word(self, text: str) -> bool:
        """
        Check if the transcribed text contains a wake word.
        
        Args:
            text: The transcribed text to check.
            
        Returns:
            True if a wake word was detected, False otherwise.
        """
        text_lower = text.lower()
        return any(wake_word in text_lower for wake_word in WAKE_WORDS)
    
    # -------------------------------------------------------------------------
    def listen(self) -> str:
        """
        Record audio from the microphone and transcribe it to text.
        
        This is a one-shot function — it records for COMMAND_LISTEN_DURATION
        seconds and returns the transcription.
        
        Returns:
            The transcribed text as a string.
        """
        if self.whisper_model is None:
            return ""
        
        print("[Voice Input] Listening for command...")
        audio = self._record_audio(COMMAND_LISTEN_DURATION)
        
        if len(audio) == 0:
            return ""
        
        text = self._transcribe(audio)
        print(f"[Voice Input] Transcribed: '{text}'")
        return text
    
    # -------------------------------------------------------------------------
    def start_listening(self, callback):
        """
        Start listening in the background for the wake word, then commands.
        
        This runs in a separate thread so it doesn't block the GUI.
        When the wake word is detected, it records the user's command
        and calls callback(transcribed_text).
        
        Args:
            callback: A function that receives the transcribed command text.
                     Example: callback("open spotify")
        """
        if self.is_listening:
            print("[Voice Input] Already listening.")
            return
        
        if self.whisper_model is None:
            print("[Voice Input] Whisper model not available — cannot start listening.")
            return
        
        # Clear the stop event so the thread will run
        self.stop_event.clear()
        self.is_listening = True
        
        # Start the background thread
        self.listening_thread = threading.Thread(
            target=self._listening_loop,
            args=(callback,),
            daemon=True  # Daemon thread dies when the main program exits
        )
        self.listening_thread.start()
        print("[Voice Input] Background voice listening started.")
    
    # -------------------------------------------------------------------------
    def stop_listening(self):
        """Stop the background voice listening thread."""
        if not self.is_listening:
            return
        
        print("[Voice Input] Stopping voice listener...")
        self.stop_event.set()  # Signal the thread to stop
        self.is_listening = False
        
        # Wait for the thread to finish (with timeout)
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=5.0)
        
        print("[Voice Input] Voice listener stopped.")
    
    # -------------------------------------------------------------------------
    def _listening_loop(self, callback):
        """
        The main background listening loop.
        
        Continuously:
        1. Records a short audio clip
        2. Checks for the wake word
        3. If wake word detected, records the full command
        4. Calls the callback with the transcribed command
        
        Args:
            callback: Function to call with transcribed command text.
        """
        print("[Voice Input] Listening loop started. Say 'Hey Jarvis' to wake me.")
        
        while not self.stop_event.is_set():
            try:
                if self.porcupine is not None:
                    # Use porcupine for wake word detection (more accurate)
                    wake_detected = self._porcupine_listen_for_wake_word()
                else:
                    # Use Whisper-based wake word detection (fallback)
                    wake_detected = self._whisper_listen_for_wake_word()
                
                if wake_detected and not self.stop_event.is_set():
                    print("[Voice Input] Wake word detected! Recording command...")
                    
                    # Small pause to let the user start speaking
                    time.sleep(0.3)
                    
                    # Record the actual command
                    audio = self._record_audio(COMMAND_LISTEN_DURATION)
                    
                    if len(audio) > 0:
                        # Transcribe the command
                        command_text = self._transcribe(audio)
                        
                        if command_text.strip():
                            print(f"[Voice Input] Command: '{command_text}'")
                            # Call the callback with the transcribed command
                            callback(command_text)
                        else:
                            print("[Voice Input] Command was empty or inaudible.")
                            
            except Exception as e:
                print(f"[Voice Input] Error in listening loop: {e}")
                # Brief pause before retrying to avoid tight error loops
                time.sleep(1)
        
        print("[Voice Input] Listening loop ended.")
    
    # -------------------------------------------------------------------------
    def _porcupine_listen_for_wake_word(self) -> bool:
        """
        Use pvporcupine to detect the wake word.
        
        Returns:
            True if wake word was detected, False otherwise.
        """
        try:
            # Porcupine requires audio in int16 format at its frame length
            frame_length = self.porcupine.frame_length
            
            # Record one frame of audio
            audio_frame = sd.rec(
                frame_length,
                samplerate=self.porcupine.sample_rate,
                channels=1,
                dtype="int16"
            )
            sd.wait()
            
            # Flatten the array and pass to porcupine
            audio_int16 = audio_frame.flatten()
            result = self.porcupine.process(audio_int16)
            
            # result >= 0 means a keyword was detected
            return result >= 0
            
        except Exception as e:
            print(f"[Voice Input] Porcupine error: {e}")
            return False
    
    # -------------------------------------------------------------------------
    def _whisper_listen_for_wake_word(self) -> bool:
        """
        Use Whisper to check for the wake word in a short audio clip.
        
        This is less accurate and uses more CPU than porcupine,
        but doesn't require an API key.
        
        Returns:
            True if wake word was detected in the recording, False otherwise.
        """
        # Record a short clip
        audio = self._record_audio(WAKE_WORD_LISTEN_DURATION)
        
        if len(audio) == 0:
            return False
        
        # Transcribe and check for wake word
        text = self._transcribe(audio)
        
        if text:
            detected = self._contains_wake_word(text)
            if detected:
                print(f"[Voice Input] Wake word detected in: '{text}'")
            return detected
        
        return False
    
    # -------------------------------------------------------------------------
    def cleanup(self):
        """Clean up resources when shutting down."""
        self.stop_listening()
        
        if self.porcupine is not None:
            try:
                self.porcupine.delete()
            except Exception:
                pass
        
        print("[Voice Input] Cleaned up.")


# ---------------------------------------------------------------------------
# Quick test — run this file directly to test voice input
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing voice input...")
    voice = VoiceInput()
    
    print("\nSay something (recording for 5 seconds)...")
    result = voice.listen()
    print(f"You said: '{result}'")
    
    voice.cleanup()
