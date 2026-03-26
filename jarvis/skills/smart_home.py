# =============================================================================
# smart_home.py — Smart Home Integration Module for J.A.R.V.I.S
# =============================================================================
# This module handles integration with Home Assistant, an open-source
# smart home automation platform.
#
# HOW IT WORKS:
# - If you have Home Assistant running locally, set HA_URL and HA_TOKEN
#   in your .env file and this module will actually control your devices.
# - If those variables aren't set, it will tell you what it WOULD do,
#   acting as a modular placeholder ready for when you set up Home Assistant.
#
# HOME ASSISTANT SETUP:
# 1. Install Home Assistant: https://www.home-assistant.io/installation/
# 2. Create a Long-Lived Access Token:
#    Profile → Long-Lived Access Tokens → Create Token
# 3. Add to .env:
#    HA_URL=http://homeassistant.local:8123
#    HA_TOKEN=your_token_here
# =============================================================================

import os                   # For reading environment variables
import re                   # For pattern matching in natural language commands

import requests             # For making HTTP requests to Home Assistant
from dotenv import load_dotenv  # For loading .env file

# Load environment variables from .env
load_dotenv()

# Read Home Assistant connection details from environment
HA_URL = os.getenv("HA_URL", "")    # e.g., "http://homeassistant.local:8123"
HA_TOKEN = os.getenv("HA_TOKEN", "") # Long-lived access token

# Check if Home Assistant is configured
HA_CONFIGURED = bool(HA_URL and HA_TOKEN)


# ---------------------------------------------------------------------------
# DEVICE CONTROL
# ---------------------------------------------------------------------------

def control_device(entity_id: str, action: str) -> str:
    """
    Control a Home Assistant device (entity).
    
    Home Assistant uses "entity IDs" to identify devices.
    Examples:
    - "light.living_room" — a light in the living room
    - "switch.bedroom_fan" — a fan switch in the bedroom
    - "cover.garage_door" — a garage door cover
    
    Args:
        entity_id: The Home Assistant entity ID of the device.
        action: The action to perform ("turn_on", "turn_off", "toggle")
        
    Returns:
        A status message describing what happened or what would happen.
    """
    
    # If Home Assistant is not configured, return an informative message
    if not HA_CONFIGURED:
        return (
            f"I would {action.replace('_', ' ')} the device '{entity_id}', sir, "
            "but Home Assistant is not yet configured. "
            "Please add HA_URL and HA_TOKEN to your .env file to enable smart home control."
        )
    
    try:
        # Determine the service to call based on the entity domain
        # Entity IDs are formatted as "domain.name" (e.g., "light.bedroom")
        domain = entity_id.split(".")[0]  # "light" from "light.bedroom"
        
        # Build the Home Assistant REST API URL
        # Services are called at: POST /api/services/{domain}/{service}
        url = f"{HA_URL}/api/services/{domain}/{action}"
        
        # Set up authentication headers
        headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # The request body tells HA which entity to control
        payload = {"entity_id": entity_id}
        
        # Make the HTTP POST request to Home Assistant
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        # Parse the response
        action_word = action.replace("_", " ")
        return f"Done, sir. I've {action_word}ed {entity_id}."
        
    except requests.exceptions.ConnectionError:
        return (
            "I'm unable to reach your Home Assistant instance, sir. "
            "Please verify it's running and the HA_URL in .env is correct."
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return (
                "Home Assistant rejected my authentication, sir. "
                "Please verify your HA_TOKEN in the .env file is valid."
            )
        return f"Home Assistant returned an error, sir: {str(e)}"
    except Exception as e:
        return f"Smart home control encountered an error, sir: {str(e)}"


# ---------------------------------------------------------------------------
# LIST DEVICES
# ---------------------------------------------------------------------------

def list_devices() -> str:
    """
    List all available Home Assistant entities/devices.
    
    Returns:
        A formatted list of available devices, or an informative message.
    """
    
    if not HA_CONFIGURED:
        return (
            "Home Assistant is not configured, sir. "
            "Once you set up HA_URL and HA_TOKEN in your .env file, "
            "I'll be able to list all your connected smart home devices."
        )
    
    try:
        # The Home Assistant API endpoint for listing all states (entities)
        url = f"{HA_URL}/api/states"
        
        headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        entities = response.json()
        
        if not entities:
            return "No devices found in your Home Assistant instance, sir."
        
        # Organize entities by domain (lights, switches, etc.)
        domains = {}
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            domain = entity_id.split(".")[0]
            
            if domain not in domains:
                domains[domain] = []
            
            # Get friendly name if available
            friendly_name = entity.get("attributes", {}).get("friendly_name", entity_id)
            state = entity.get("state", "unknown")
            domains[domain].append(f"  • {friendly_name} ({entity_id}) — {state}")
        
        # Build the output
        output = ["Your connected devices, sir:\n"]
        for domain, devices in sorted(domains.items()):
            output.append(f"[{domain.upper()}]")
            output.extend(devices)
            output.append("")
        
        return "\n".join(output)
        
    except requests.exceptions.ConnectionError:
        return "Cannot connect to Home Assistant, sir. Is it running?"
    except Exception as e:
        return f"I encountered an error listing devices, sir: {str(e)}"


# ---------------------------------------------------------------------------
# NATURAL LANGUAGE COMMAND PROCESSING
# ---------------------------------------------------------------------------

def process_command(command: str) -> str:
    """
    Process a natural language smart home command.
    
    This function parses commands like:
    - "turn on the lights"
    - "turn off bedroom light"
    - "toggle the fan"
    - "turn on kitchen light"
    
    It extracts the action (on/off/toggle) and device name,
    then calls control_device() with the appropriate entity_id.
    
    Args:
        command: A natural language command string.
        
    Returns:
        A status message.
    """
    
    # Convert to lowercase for easier matching
    command_lower = command.lower().strip()
    
    # Detect the action (on, off, or toggle)
    if "turn on" in command_lower or "switch on" in command_lower or "enable" in command_lower:
        action = "turn_on"
    elif "turn off" in command_lower or "switch off" in command_lower or "disable" in command_lower:
        action = "turn_off"
    elif "toggle" in command_lower:
        action = "toggle"
    else:
        # If we can't determine the action, default to toggle
        action = "toggle"
    
    # Try to extract the device name from the command
    # Patterns to match device names in common phrases
    device_patterns = [
        r"turn (?:on|off) (?:the )?(.+?)(?:\s+light(?:s)?)?$",
        r"toggle (?:the )?(.+?)(?:\s+light(?:s)?)?$",
        r"switch (?:on|off) (?:the )?(.+?)(?:\s+light(?:s)?)?$",
    ]
    
    device_name = None
    
    for pattern in device_patterns:
        match = re.search(pattern, command_lower)
        if match:
            device_name = match.group(1).strip()
            # Remove common filler words
            for filler in ["the", "a", "an", "my"]:
                device_name = device_name.replace(f" {filler} ", " ").strip()
                if device_name.startswith(f"{filler} "):
                    device_name = device_name[len(filler) + 1:]
            break
    
    if not device_name:
        # If we can't identify the specific device, try to control "all lights"
        # as a reasonable default for ambiguous commands
        if "light" in command_lower or "lamp" in command_lower:
            device_name = "all lights"
            entity_id = "light.all"
        else:
            return (
                f"I understand you'd like me to control something, sir, "
                f"but I wasn't sure which device you meant. "
                f"Could you be more specific? For example: 'turn on the bedroom light'"
            )
    
    # Convert the device name to a likely Home Assistant entity ID
    # HA uses format: "light.device_name" with spaces replaced by underscores
    if "light" in command_lower or "lamp" in command_lower:
        domain = "light"
    elif "fan" in command_lower:
        domain = "fan"
    elif "tv" in command_lower or "television" in command_lower:
        domain = "media_player"
    elif "lock" in command_lower:
        domain = "lock"
    elif "thermostat" in command_lower or "temperature" in command_lower:
        domain = "climate"
    else:
        domain = "switch"  # Default to switch for unknown device types
    
    # Convert device name to entity ID format
    # "bedroom light" -> "light.bedroom_light"
    entity_name = device_name.replace(" ", "_").replace("-", "_")
    entity_id = f"{domain}.{entity_name}"
    
    # Now call the actual control function
    result = control_device(entity_id, action)
    
    return result
