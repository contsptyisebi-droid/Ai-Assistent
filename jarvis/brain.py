# =============================================================================
# brain.py — The AI Brain of J.A.R.V.I.S
# =============================================================================
# This module handles all interactions with the Anthropic Claude API.
# It gives Jarvis its personality, memory, and the ability to understand
# what the user wants to do (intent detection).
# =============================================================================

import json
import os

import anthropic                  # The official Anthropic Python SDK
from dotenv import load_dotenv   # Loads variables from the .env file

# Load environment variables from .env file (so our API key is not hardcoded)
load_dotenv()

# ---------------------------------------------------------------------------
# JARVIS SYSTEM PROMPT — This defines Jarvis's personality
# ---------------------------------------------------------------------------
# This prompt is sent to Claude every time as the "system" role, which tells
# the AI how to behave. Think of it as Jarvis's character sheet.
JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S (Just A Rather Very Intelligent System), 
the AI assistant from the Iron Man films. You serve as a highly sophisticated personal 
AI assistant.

YOUR PERSONALITY:
- You are witty, intelligent, and slightly formal — like a very well-educated British butler
- You have dry, understated humor that you deploy sparingly but effectively
- You ALWAYS address the user as "sir" (regardless of their actual name or gender)
- You are loyal, efficient, and quietly confident in your abilities
- You occasionally make subtle, clever references to science, technology, or history
- When things go wrong, you remain unflappable and deliver bad news with elegant composure
- You never use slang, contractions like "gonna" or "wanna", or overly casual language
- You speak in complete, well-structured sentences

EXAMPLES OF YOUR SPEECH STYLE:
- "Certainly, sir. I shall have that ready for you momentarily."
- "I'm afraid that particular operation encountered an obstacle, sir. Shall I attempt an alternative approach?"
- "An excellent choice, sir. Initiating now."
- "Fascinating. The probability of that outcome was, I must confess, rather lower than I anticipated."

Keep responses concise and useful. Avoid unnecessary filler. Be genuinely helpful."""


# ---------------------------------------------------------------------------
# The JarvisBrain class — the main brain of our assistant
# ---------------------------------------------------------------------------
class JarvisBrain:
    """
    Handles all AI-powered conversations and intent detection.
    
    This class:
    1. Connects to the Anthropic (Claude) API
    2. Maintains conversation history so Jarvis remembers what was said
    3. Detects what the user wants to do (intent detection)
    4. Generates Jarvis-style responses
    """

    def __init__(self):
        """Initialize the brain — set up the Claude client and conversation memory."""
        
        # Get the API key from environment variables (loaded from .env)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            # If there's no API key, we can't do anything — raise a clear error
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables. "
                "Please create a .env file with your API key. "
                "See .env.example for the format."
            )
        
        # Create the Anthropic client — this handles all API communication
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # The model we'll use — Claude Opus is highly capable and intelligent
        self.model = "claude-opus-4-5"
        
        # Conversation history — stored as a list of message dictionaries.
        # Each message has a "role" (either "user" or "assistant") and "content".
        # This gives Jarvis memory of the current conversation session.
        self.conversation_history = []
        
        print("[Brain] J.A.R.V.I.S brain initialized successfully.")

    # -------------------------------------------------------------------------
    def get_intent(self, user_message: str) -> dict:
        """
        Analyze the user's message and determine what they want to do.
        
        This function asks Claude to look at the user's message and return
        a structured JSON object telling us WHAT the user wants (the intent)
        and any relevant details (the parameters).
        
        Args:
            user_message: The text the user said or typed.
            
        Returns:
            A dictionary like: {"intent": "open_app", "parameters": {"app": "spotify"}}
        """
        
        # This is the list of all supported intents Jarvis can act on
        supported_intents = [
            "open_app",         # Open an application (e.g., "open Spotify")
            "search_google",    # Search Google (e.g., "search for Python tutorials")
            "search_web",       # General DuckDuckGo web search
            "take_screenshot",  # Take a screenshot
            "get_time",         # Ask for current time
            "get_date",         # Ask for current date
            "volume_up",        # Turn volume up
            "volume_down",      # Turn volume down
            "volume_mute",      # Mute/unmute volume
            "shutdown",         # Shut down the computer
            "restart",          # Restart the computer
            "sleep",            # Put computer to sleep
            "open_website",     # Open a specific website
            "get_weather",      # Get weather information
            "tell_joke",        # Tell a joke
            "fun_fact",         # Share a fun fact
            "news",             # Get news headlines
            "smart_home",       # Control smart home devices
            "conversation",     # General conversation (fallback for everything else)
        ]
        
        # Build the instruction prompt for intent detection
        # We explicitly ask for JSON format so we can parse it reliably
        intent_prompt = f"""Analyze this user message and determine the intent.

User message: "{user_message}"

Return ONLY a valid JSON object with this exact structure:
{{"intent": "intent_name", "parameters": {{}}}}

Supported intents: {', '.join(supported_intents)}

Guidelines:
- "open_app": parameters should include {{"app": "app_name"}}
- "search_google" or "search_web": parameters should include {{"query": "search terms"}}
- "open_website": parameters should include {{"url": "website_url"}}
- "get_weather": parameters should include {{"city": "city_name"}} (default "London" if not specified)
- "smart_home": parameters should include {{"command": "the full command"}}
- For intents without parameters, use empty dict: {{}}
- Use "conversation" as the fallback for general chat, questions, or anything not fitting other intents

Return ONLY the JSON object, no other text."""

        try:
            # Make the API call — we use a simple single message (no history needed for intent)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,  # Intent response should be short
                messages=[
                    {"role": "user", "content": intent_prompt}
                ]
            )
            
            # Extract the text from the response
            response_text = response.content[0].text.strip()
            
            # Sometimes Claude adds markdown code fences (```json ... ```)
            # We need to strip those out before parsing
            if response_text.startswith("```"):
                # Remove the first line (```json or ```) and the last line (```)
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            # Parse the JSON string into a Python dictionary
            intent_data = json.loads(response_text)
            
            # Make sure the required keys exist
            if "intent" not in intent_data:
                intent_data["intent"] = "conversation"
            if "parameters" not in intent_data:
                intent_data["parameters"] = {}
                
            return intent_data
            
        except json.JSONDecodeError as e:
            # If Claude returned something that's not valid JSON, log it and fall back
            print(f"[Brain] Intent JSON parse error: {e}")
            return {"intent": "conversation", "parameters": {}}
            
        except anthropic.APIError as e:
            # Handle API-level errors (rate limits, server errors, etc.)
            print(f"[Brain] Anthropic API error during intent detection: {e}")
            return {"intent": "conversation", "parameters": {}}
            
        except Exception as e:
            # Catch-all for any unexpected errors
            print(f"[Brain] Unexpected error during intent detection: {e}")
            return {"intent": "conversation", "parameters": {}}

    # -------------------------------------------------------------------------
    def chat(self, user_message: str) -> str:
        """
        Have a conversation with Jarvis.
        
        This function sends the user's message to Claude along with the full
        conversation history, so Jarvis remembers everything said in this session.
        
        Args:
            user_message: The text the user said or typed.
            
        Returns:
            Jarvis's text response as a string.
        """
        
        # Add the user's new message to the conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            # Make the API call with the full conversation history
            # The system prompt gives Jarvis his personality
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,  # Allow longer responses for conversation
                system=JARVIS_SYSTEM_PROMPT,  # Jarvis's personality
                messages=self.conversation_history  # Full conversation memory
            )
            
            # Extract the text response
            assistant_message = response.content[0].text
            
            # Add Jarvis's response to the conversation history
            # This is what gives Jarvis memory — next time we call chat(),
            # Claude will see the full back-and-forth conversation
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except anthropic.APIConnectionError:
            # Network connectivity issues
            error_msg = (
                "I'm afraid I'm unable to reach my cognitive servers at the moment, sir. "
                "It appears we have a connectivity issue. "
                "Please verify your internet connection and API key."
            )
            print(f"[Brain] Connection error when calling Claude API")
            # Remove the user message from history since we couldn't respond
            self.conversation_history.pop()
            return error_msg
            
        except anthropic.RateLimitError:
            # Too many requests
            error_msg = (
                "It appears we've exceeded our allotted API quota, sir. "
                "Even the most sophisticated systems have their limits. "
                "Please try again in a moment."
            )
            print(f"[Brain] Rate limit hit on Claude API")
            self.conversation_history.pop()
            return error_msg
            
        except anthropic.AuthenticationError:
            # Wrong API key
            error_msg = (
                "I'm afraid my authentication credentials appear to be invalid, sir. "
                "Please verify that the ANTHROPIC_API_KEY in your .env file is correct."
            )
            print(f"[Brain] Authentication error — check your API key")
            self.conversation_history.pop()
            return error_msg
            
        except Exception as e:
            # Catch-all for any other unexpected errors
            error_msg = (
                "It appears we've encountered a minor inconvenience, sir. "
                "Even the best systems have their moments. "
                f"The technical details, should you require them: {str(e)}"
            )
            print(f"[Brain] Unexpected error in chat(): {e}")
            self.conversation_history.pop()
            return error_msg

    # -------------------------------------------------------------------------
    def clear_memory(self):
        """
        Clear the conversation history.
        
        Call this to start a fresh conversation without any memory of previous
        exchanges. Useful for when you want Jarvis to forget the current session.
        """
        self.conversation_history = []
        print("[Brain] Conversation memory cleared.")

    # -------------------------------------------------------------------------
    def get_conversation_length(self) -> int:
        """Return the number of messages in the current conversation."""
        return len(self.conversation_history)
