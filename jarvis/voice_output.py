# =============================================================================
# voice_output.py — Voice Output Module for J.A.R.V.I.S
# =============================================================================
# This module handles converting text to speech so Jarvis can "speak".
# We use Microsoft's Edge TTS service which provides free, high-quality
# text-to-speech with many natural-sounding voices.
#
# The voice "en-GB-RyanNeural" is a British male voice that sounds
# very close to Jarvis from the Iron Man movies.
# =============================================================================

import asyncio    # For running async functions (edge-tts is async)
import os         # For file operations
import tempfile   # For creating temporary files

import edge_tts   # Microsoft Edge TTS — converts text to speech audio
import pygame     # Used to play the generated audio file

# The voice we want to use — British male, similar to Jarvis from Iron Man
JARVIS_VOICE = "en-GB-RyanNeural"


# ---------------------------------------------------------------------------
async def speak(text: str) -> None:
    """
    Convert text to speech and play it aloud. (Async version)
    
    This function:
    1. Creates a text-to-speech audio file using Edge TTS
    2. Plays it using pygame
    3. Cleans up the temporary file when done
    
    Args:
        text: The text you want Jarvis to say out loud.
    """
    
    # Create a temporary file to store the audio
    # We use .mp3 extension because edge-tts outputs MP3 format
    temp_file = None
    
    try:
        # Create a named temporary file — we need a real file path for pygame to play
        # delete=False means the file won't be auto-deleted when we close it
        # We'll manually delete it after playback
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_file = f.name  # Save the file path for later use
        
        # Create the Edge TTS communication object
        # This connects to Microsoft's TTS service and generates the audio
        communicate = edge_tts.Communicate(text, JARVIS_VOICE)
        
        # Save the generated speech audio to our temp file
        await communicate.save(temp_file)
        
        # Initialize pygame mixer for audio playback
        # frequency=44100 is CD quality, size=-16 is 16-bit audio, channels=2 is stereo
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # Load the audio file into pygame
        pygame.mixer.music.load(temp_file)
        
        # Start playing the audio
        pygame.mixer.music.play()
        
        # Wait until the audio is finished playing
        # We check every 100ms so we don't waste CPU cycles
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
            
    except edge_tts.exceptions.NoAudioReceived:
        # Sometimes edge-tts returns no audio (usually for very short text)
        print(f"[Voice Output] No audio received for text: '{text[:50]}...'")
        
    except pygame.error as e:
        # pygame might fail if there's no audio device (e.g., on a server)
        print(f"[Voice Output] Audio playback error: {e}")
        
    except Exception as e:
        # Catch any other unexpected errors
        print(f"[Voice Output] Unexpected error during speech: {e}")
        
    finally:
        # Always clean up the temporary file, even if something went wrong
        if temp_file and os.path.exists(temp_file):
            try:
                # Make sure pygame has released the file before deleting it
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                os.remove(temp_file)
            except Exception as cleanup_error:
                # If cleanup fails, just log it — not critical
                print(f"[Voice Output] Could not clean up temp file: {cleanup_error}")


# ---------------------------------------------------------------------------
def speak_sync(text: str) -> None:
    """
    Synchronous wrapper around the async speak() function.
    
    Most of our code is not async (doesn't use await), so we need this
    wrapper to call the async speak() function from regular (sync) code.
    
    Args:
        text: The text you want Jarvis to say out loud.
    """
    
    if not text or not text.strip():
        # Don't try to speak empty text
        print("[Voice Output] No text provided to speak.")
        return
    
    try:
        # asyncio.run() creates a new event loop, runs the async function,
        # and then closes the loop when done. This is the simplest way to
        # run an async function from synchronous code.
        asyncio.run(speak(text))
        
    except RuntimeError as e:
        # This can happen if there's already an event loop running
        # (e.g., in Jupyter notebooks or certain testing environments)
        if "Event loop is closed" in str(e) or "already running" in str(e):
            # Get the existing event loop and schedule our coroutine on it
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(speak(text))
            finally:
                loop.close()
        else:
            print(f"[Voice Output] Runtime error in speak_sync: {e}")
            
    except Exception as e:
        print(f"[Voice Output] Error in speak_sync: {e}")


# ---------------------------------------------------------------------------
# Quick test — run this file directly to hear Jarvis speak
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing voice output...")
    speak_sync("Good evening, sir. J.A.R.V.I.S voice systems are fully operational.")
    print("Voice test complete.")
