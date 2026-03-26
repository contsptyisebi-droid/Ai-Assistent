# =============================================================================
# main.py — J.A.R.V.I.S Entry Point
# =============================================================================
# This is the main file that ties everything together.
#
# HOW IT WORKS:
# 1. We initialize all the modules (brain, voice, skills)
# 2. We create the dashboard GUI
# 3. When the user sends a message (text or voice):
#    a. Show "Thinking..." status
#    b. Ask Claude what the user wants (intent detection)
#    c. Execute the appropriate skill (take screenshot, search web, etc.)
#    d. Have Jarvis generate a response using the skill result
#    e. Speak the response out loud
#    f. Show the response in the conversation log
# 4. The dashboard runs on the main thread; voice runs on a background thread
# =============================================================================

import sys
import os
import threading

# Add the jarvis directory to Python's path so we can import our modules
# This is needed when running as "python main.py" from inside the jarvis folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file BEFORE importing other modules
from dotenv import load_dotenv
load_dotenv()

# Import our custom modules
from brain import JarvisBrain
from voice_output import speak_sync
from voice_input import VoiceInput
from dashboard.ui import JarvisDashboard

# Import skill modules
from skills.pc_control import (
    open_application, search_google, take_screenshot,
    get_current_time, get_current_date,
    volume_up, volume_down, volume_mute,
    shutdown_pc, restart_pc, sleep_pc, open_website
)
from skills.web_search import (
    search_web, get_weather, tell_joke, get_fun_fact, get_news
)
from skills.smart_home import process_command as smart_home_command


# ---------------------------------------------------------------------------
# The main JarvisAssistant class
# ---------------------------------------------------------------------------

class JarvisAssistant:
    """
    The main orchestrator class that connects all J.A.R.V.I.S components.
    
    This class:
    - Holds references to all modules (brain, voice, dashboard)
    - Processes messages from the user (text or voice)
    - Executes the right skills based on intent
    - Updates the dashboard with responses
    """
    
    def __init__(self):
        """Initialize all J.A.R.V.I.S components."""
        
        print("=" * 60)
        print("  J.A.R.V.I.S — Initializing...")
        print("=" * 60)
        
        # Initialize the AI brain
        print("\n[Main] Initializing AI brain...")
        try:
            self.brain = JarvisBrain()
        except ValueError as e:
            # This happens if the API key is missing
            print(f"\n[ERROR] {e}")
            print("\nPlease create a .env file with your ANTHROPIC_API_KEY.")
            print("See .env.example for the format.\n")
            sys.exit(1)
        
        # Initialize voice input (Whisper model loading may take a moment)
        print("\n[Main] Initializing voice input...")
        try:
            self.voice_input = VoiceInput()
        except Exception as e:
            print(f"[Main] Voice input unavailable: {e}")
            self.voice_input = None
        
        # Flag to control background processing
        self.is_processing = False
        
        # Flag to know if voice is currently active
        self.voice_listening = False
        
        # The dashboard will be created in start()
        self.dashboard = None
        
        print("\n[Main] All components initialized.")
    
    # -------------------------------------------------------------------------
    def _execute_skill(self, intent: str, parameters: dict) -> str:
        """
        Execute the appropriate skill based on the detected intent.
        
        Args:
            intent: The intent string (e.g., "open_app", "take_screenshot")
            parameters: A dictionary of parameters for the skill
            
        Returns:
            A string describing what happened (the skill result)
        """
        
        # Extract common parameters (with defaults)
        app_name = parameters.get("app", "")
        query = parameters.get("query", "")
        url = parameters.get("url", "")
        city = parameters.get("city", "London")
        command = parameters.get("command", "")
        
        # Route to the correct skill function based on intent
        if intent == "open_app":
            return open_application(app_name)
        
        elif intent == "search_google":
            return search_google(query)
        
        elif intent == "search_web":
            return search_web(query)
        
        elif intent == "take_screenshot":
            return take_screenshot()
        
        elif intent == "get_time":
            return f"The current time is {get_current_time()}."
        
        elif intent == "get_date":
            return f"Today is {get_current_date()}."
        
        elif intent == "volume_up":
            return volume_up()
        
        elif intent == "volume_down":
            return volume_down()
        
        elif intent == "volume_mute":
            return volume_mute()
        
        elif intent == "shutdown":
            return shutdown_pc()
        
        elif intent == "restart":
            return restart_pc()
        
        elif intent == "sleep":
            return sleep_pc()
        
        elif intent == "open_website":
            return open_website(url)
        
        elif intent == "get_weather":
            return get_weather(city)
        
        elif intent == "tell_joke":
            return tell_joke()
        
        elif intent == "fun_fact":
            return get_fun_fact()
        
        elif intent == "news":
            return get_news()
        
        elif intent == "smart_home":
            return smart_home_command(command)
        
        elif intent == "conversation":
            # No skill to execute — just return empty string
            # The brain will handle generating a response directly
            return ""
        
        else:
            # Unknown intent — treat as conversation
            return ""
    
    # -------------------------------------------------------------------------
    def process_message(self, user_message: str):
        """
        Process a user message from start to finish.
        
        This is the main pipeline:
        1. Update status to "Thinking"
        2. Detect intent using Claude
        3. Execute the matching skill
        4. Generate Jarvis's response
        5. Speak the response
        6. Update the conversation log
        
        This runs in a background thread to avoid freezing the GUI.
        
        Args:
            user_message: The text message from the user.
        """
        
        if self.is_processing:
            # Don't process a new message while one is already being processed
            print("[Main] Already processing a message, skipping.")
            return
        
        # Run the processing in a background thread so the GUI stays responsive
        processing_thread = threading.Thread(
            target=self._process_message_thread,
            args=(user_message,),
            daemon=True
        )
        processing_thread.start()
    
    def _process_message_thread(self, user_message: str):
        """
        The actual message processing logic (runs in a background thread).
        
        Args:
            user_message: The text message to process.
        """
        
        self.is_processing = True
        
        try:
            # 1. Update dashboard to show the user's message
            if self.dashboard:
                self.dashboard.add_user_message(user_message)
                self.dashboard.set_state("thinking")
            
            print(f"\n[Main] Processing: '{user_message}'")
            
            # 2. Detect intent — what does the user want to do?
            print("[Main] Detecting intent...")
            intent_data = self.brain.get_intent(user_message)
            intent = intent_data.get("intent", "conversation")
            parameters = intent_data.get("parameters", {})
            
            print(f"[Main] Intent: {intent}, Parameters: {parameters}")
            
            # 3. Execute the matching skill
            skill_result = ""
            if intent != "conversation":
                print(f"[Main] Executing skill: {intent}")
                skill_result = self._execute_skill(intent, parameters)
                print(f"[Main] Skill result: {skill_result[:100]}...")  # Print first 100 chars
            
            # 4. Generate Jarvis's response using Claude
            # We include the skill result so Jarvis can comment on it intelligently
            print("[Main] Generating response...")
            
            if skill_result:
                # If we have a skill result, ask Jarvis to acknowledge it
                chat_message = (
                    f"The user said: '{user_message}'\n"
                    f"I executed the relevant action and got this result: {skill_result}\n"
                    f"Please respond as J.A.R.V.I.S acknowledging what was done. "
                    f"Keep your response concise (1-2 sentences)."
                )
            else:
                # Pure conversation — just pass the message
                chat_message = user_message
            
            response = self.brain.chat(chat_message)
            
            # 5. Update dashboard status to "Speaking"
            if self.dashboard:
                self.dashboard.set_state("speaking")
                self.dashboard.add_jarvis_message(response)
            
            print(f"[Main] Jarvis: {response}")
            
            # 6. Speak the response
            print("[Main] Speaking response...")
            speak_sync(response)
            
        except Exception as e:
            # Handle any unexpected errors gracefully
            error_message = (
                "I appear to have encountered an unexpected situation, sir. "
                f"The details: {str(e)}"
            )
            print(f"[Main] Error processing message: {e}")
            
            if self.dashboard:
                self.dashboard.add_jarvis_message(error_message)
                
            speak_sync(error_message)
        
        finally:
            # Always reset status back to idle when done
            self.is_processing = False
            if self.dashboard:
                self.dashboard.set_state("idle")
    
    # -------------------------------------------------------------------------
    def _voice_callback(self, transcribed_text: str):
        """
        Called by the voice input system when a command is detected.
        
        This is the callback function we pass to voice_input.start_listening().
        
        Args:
            transcribed_text: The text transcribed from the user's speech.
        """
        if transcribed_text.strip():
            print(f"[Main] Voice command received: '{transcribed_text}'")
            # Process it just like a text message
            self.process_message(transcribed_text)
    
    # -------------------------------------------------------------------------
    def toggle_voice(self):
        """Toggle voice listening on/off."""
        if self.voice_input is None:
            print("[Main] Voice input not available.")
            if self.dashboard:
                self.dashboard.add_system_message(
                    "Voice input is not available. "
                    "Please check that your microphone is connected and Whisper is installed."
                )
            return
        
        if self.voice_listening:
            # Stop listening
            self.voice_input.stop_listening()
            self.voice_listening = False
            if self.dashboard:
                self.dashboard.set_voice_active(False)
                self.dashboard.add_system_message("Voice listening stopped.")
            print("[Main] Voice listening stopped.")
        else:
            # Start listening
            self.voice_input.start_listening(self._voice_callback)
            self.voice_listening = True
            if self.dashboard:
                self.dashboard.set_voice_active(True)
                self.dashboard.add_system_message(
                    "Voice listening active. Say 'Hey Jarvis' to give a command."
                )
            print("[Main] Voice listening started.")
    
    # -------------------------------------------------------------------------
    def start(self):
        """
        Start J.A.R.V.I.S — create the dashboard and run the main loop.
        
        This method blocks until the user closes the window.
        """
        
        print("\n[Main] Creating dashboard...")
        
        # Create the dashboard with our callbacks
        self.dashboard = JarvisDashboard(
            on_send_message=self.process_message,  # Called when user sends text
            on_toggle_voice=self.toggle_voice       # Called when mic button clicked
        )
        
        print("[Main] Starting J.A.R.V.I.S... Welcome, sir.\n")
        
        # Run the dashboard main loop
        # This blocks here until the user closes the window
        self.dashboard.run()
        
        # After window closes, clean up
        self._shutdown()
    
    # -------------------------------------------------------------------------
    def _shutdown(self):
        """Clean up all resources when shutting down."""
        print("\n[Main] Shutting down J.A.R.V.I.S...")
        
        # Stop voice listening if active
        if self.voice_input and self.voice_listening:
            self.voice_input.stop_listening()
        
        # Clean up voice input resources
        if self.voice_input:
            self.voice_input.cleanup()
        
        print("[Main] J.A.R.V.I.S shut down. Goodbye, sir.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Create and start the assistant
    jarvis = JarvisAssistant()
    jarvis.start()
