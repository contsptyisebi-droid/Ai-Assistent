# =============================================================================
# pc_control.py — PC Control Skills for J.A.R.V.I.S
# =============================================================================
# This module contains all the functions Jarvis can use to control your
# computer: launching apps, taking screenshots, controlling volume,
# managing power states, and more.
#
# It works on Windows, macOS, and Linux (where possible).
# =============================================================================

import os           # OS operations
import platform     # Detect which OS we're on
import subprocess   # Run system commands
import webbrowser   # Open URLs in the default browser
from datetime import datetime  # For timestamps and formatting
from pathlib import Path       # Modern file path handling

import pyautogui    # For taking screenshots

# Detect the current operating system once at module load
# This saves us from checking platform.system() in every function
CURRENT_OS = platform.system()  # Returns "Windows", "Darwin" (macOS), or "Linux"


# ---------------------------------------------------------------------------
# APPLICATION LAUNCHER
# ---------------------------------------------------------------------------

# Map of friendly app names to their actual executables on each platform
# This lets users say "open chrome" instead of "open google-chrome-stable"
APP_MAP = {
    "windows": {
        "chrome":         "chrome.exe",
        "google chrome":  "chrome.exe",
        "firefox":        "firefox.exe",
        "edge":           "msedge.exe",
        "spotify":        "spotify.exe",
        "notepad":        "notepad.exe",
        "calculator":     "calc.exe",
        "file explorer":  "explorer.exe",
        "explorer":       "explorer.exe",
        "terminal":       "cmd.exe",
        "cmd":            "cmd.exe",
        "powershell":     "powershell.exe",
        "paint":          "mspaint.exe",
        "word":           "winword.exe",
        "excel":          "excel.exe",
        "vlc":            "vlc.exe",
        "discord":        "discord.exe",
        "steam":          "steam.exe",
        "vscode":         "code.exe",
        "visual studio code": "code.exe",
        "task manager":   "taskmgr.exe",
    },
    "darwin": {  # macOS
        "chrome":         "open -a 'Google Chrome'",
        "google chrome":  "open -a 'Google Chrome'",
        "firefox":        "open -a Firefox",
        "safari":         "open -a Safari",
        "spotify":        "open -a Spotify",
        "notepad":        "open -a TextEdit",
        "textedit":       "open -a TextEdit",
        "calculator":     "open -a Calculator",
        "file explorer":  "open ~",
        "finder":         "open ~",
        "terminal":       "open -a Terminal",
        "vlc":            "open -a VLC",
        "discord":        "open -a Discord",
        "steam":          "open -a Steam",
        "vscode":         "open -a 'Visual Studio Code'",
        "visual studio code": "open -a 'Visual Studio Code'",
    },
    "linux": {
        "chrome":         "google-chrome",
        "google chrome":  "google-chrome",
        "chromium":       "chromium-browser",
        "firefox":        "firefox",
        "spotify":        "spotify",
        "notepad":        "gedit",
        "text editor":    "gedit",
        "calculator":     "gnome-calculator",
        "file explorer":  "nautilus",
        "files":          "nautilus",
        "terminal":       "gnome-terminal",
        "vlc":            "vlc",
        "discord":        "discord",
        "steam":          "steam",
        "vscode":         "code",
        "visual studio code": "code",
    }
}


def open_application(app_name: str) -> str:
    """
    Open an application by its common name.
    
    Args:
        app_name: The friendly name of the app (e.g., "spotify", "chrome")
        
    Returns:
        A status message describing what happened.
    """
    
    # Normalize the app name — lowercase and strip whitespace
    app_key = app_name.lower().strip()
    
    # Determine which OS map to use
    os_key = CURRENT_OS.lower()
    if os_key == "darwin":
        os_key = "darwin"
    elif os_key == "windows":
        os_key = "windows"
    else:
        os_key = "linux"
    
    # Look up the executable in our app map
    app_map = APP_MAP.get(os_key, {})
    
    try:
        if app_key in app_map:
            command = app_map[app_key]
            
            if CURRENT_OS == "Windows":
                # On Windows, use subprocess to launch the executable
                subprocess.Popen(command, shell=True)
            else:
                # On macOS and Linux, use the shell command
                subprocess.Popen(command, shell=True)
                
            return f"Opening {app_name} for you, sir."
            
        else:
            # App not in our map — try to open it directly by name
            # This might work for many installed applications
            if CURRENT_OS == "Windows":
                subprocess.Popen(f"start {app_name}", shell=True)
            elif CURRENT_OS == "Darwin":
                subprocess.Popen(f"open -a '{app_name}'", shell=True)
            else:
                subprocess.Popen(app_name, shell=True)
                
            return f"Attempting to open {app_name}, sir. I hope it's in your PATH."
            
    except FileNotFoundError:
        return (
            f"I'm afraid I couldn't locate {app_name} on your system, sir. "
            "It may not be installed or its path may not be configured."
        )
    except Exception as e:
        return (
            f"I encountered a difficulty opening {app_name}, sir. "
            f"Technical details: {str(e)}"
        )


# ---------------------------------------------------------------------------
# WEB SEARCH
# ---------------------------------------------------------------------------

def search_google(query: str) -> str:
    """
    Open a Google search for the given query in the default browser.
    
    Args:
        query: The search terms to look up.
        
    Returns:
        A status message.
    """
    try:
        # Construct the Google search URL
        # urllib.parse.quote() encodes special characters for safe URL use
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        
        # Open in the default web browser
        webbrowser.open(url)
        return f"Opening Google search for '{query}', sir."
        
    except Exception as e:
        return f"I couldn't open the browser, sir. Error: {str(e)}"


# ---------------------------------------------------------------------------
# SCREENSHOT
# ---------------------------------------------------------------------------

def take_screenshot() -> str:
    """
    Take a screenshot of the entire screen and save it.
    
    Returns:
        The file path where the screenshot was saved, or an error message.
    """
    try:
        # Create a 'screenshots' folder in the user's home directory
        # (We don't want to save them in the project folder)
        screenshots_dir = Path.home() / "jarvis_screenshots"
        screenshots_dir.mkdir(exist_ok=True)  # Create if it doesn't exist
        
        # Generate a filename with the current timestamp
        # e.g., "screenshot_2024-01-15_14-30-45.png"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = screenshots_dir / f"screenshot_{timestamp}.png"
        
        # Take the screenshot using pyautogui
        screenshot = pyautogui.screenshot()
        
        # Save it to our file
        screenshot.save(str(filename))
        
        return f"Screenshot saved to: {filename}"
        
    except Exception as e:
        return (
            f"I was unable to capture the screen, sir. "
            f"Error: {str(e)}"
        )


# ---------------------------------------------------------------------------
# TIME AND DATE
# ---------------------------------------------------------------------------

def get_current_time() -> str:
    """
    Get the current time in a friendly format.
    
    Returns:
        A formatted time string like "3:45 PM"
    """
    try:
        now = datetime.now()
        # Format: "3:45 PM" — 12-hour format without leading zero
        # Windows doesn't support the %-I format (no-pad), so we strip the leading zero manually
        if CURRENT_OS == "Windows":
            return now.strftime("%I:%M %p").lstrip("0")
        else:
            return now.strftime("%-I:%M %p")
    except Exception:
        # Windows doesn't support %-I (no padding), so we handle both
        return datetime.now().strftime("%I:%M %p")


def get_current_date() -> str:
    """
    Get the current date in a friendly format.
    
    Returns:
        A formatted date string like "Monday, January 15, 2024"
    """
    try:
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y")
    except Exception as e:
        return f"I was unable to retrieve the date, sir. Error: {str(e)}"


# ---------------------------------------------------------------------------
# VOLUME CONTROL
# ---------------------------------------------------------------------------

def volume_up() -> str:
    """
    Increase the system volume.
    
    Returns:
        A status message.
    """
    try:
        if CURRENT_OS == "Windows":
            # Use pyautogui to press the volume up key
            pyautogui.press("volumeup")
            
        elif CURRENT_OS == "Darwin":  # macOS
            # Use AppleScript to control volume on macOS
            subprocess.run(
                ["osascript", "-e", 
                 "set volume output volume (output volume of (get volume settings) + 10)"],
                check=True
            )
            
        else:  # Linux
            # Use amixer (common on Linux distributions)
            subprocess.run(["amixer", "-q", "sset", "Master", "10%+"], check=True)
            
        return "Volume increased, sir."
        
    except Exception as e:
        return f"I was unable to adjust the volume, sir. Error: {str(e)}"


def volume_down() -> str:
    """
    Decrease the system volume.
    
    Returns:
        A status message.
    """
    try:
        if CURRENT_OS == "Windows":
            pyautogui.press("volumedown")
            
        elif CURRENT_OS == "Darwin":
            subprocess.run(
                ["osascript", "-e",
                 "set volume output volume (output volume of (get volume settings) - 10)"],
                check=True
            )
            
        else:
            subprocess.run(["amixer", "-q", "sset", "Master", "10%-"], check=True)
            
        return "Volume decreased, sir."
        
    except Exception as e:
        return f"I was unable to adjust the volume, sir. Error: {str(e)}"


def volume_mute() -> str:
    """
    Toggle mute/unmute the system audio.
    
    Returns:
        A status message.
    """
    try:
        if CURRENT_OS == "Windows":
            pyautogui.press("volumemute")
            
        elif CURRENT_OS == "Darwin":
            # Toggle mute on macOS using AppleScript
            subprocess.run(
                ["osascript", "-e",
                 "set volume output muted not (output muted of (get volume settings))"],
                check=True
            )
            
        else:
            # Toggle mute on Linux
            subprocess.run(["amixer", "-q", "sset", "Master", "toggle"], check=True)
            
        return "Audio mute toggled, sir."
        
    except Exception as e:
        return f"I was unable to toggle the mute, sir. Error: {str(e)}"


# ---------------------------------------------------------------------------
# POWER MANAGEMENT
# ---------------------------------------------------------------------------

def shutdown_pc() -> str:
    """
    Shut down the computer after a 30-second delay.
    
    The delay gives the user time to cancel if it was a mistake.
    Cancel with: 'shutdown -a' (Windows) or 'shutdown -c' (Linux/macOS)
    
    Returns:
        A status message.
    """
    try:
        if CURRENT_OS == "Windows":
            # /s = shutdown, /t 30 = 30-second timer
            subprocess.run(["shutdown", "/s", "/t", "30"], check=True)
        elif CURRENT_OS == "Darwin":
            # macOS shutdown with 30-second delay (requires sudo in some cases)
            subprocess.run(["shutdown", "-h", "+1"], check=True)  # +1 = 1 minute
        else:
            # Linux shutdown in 30 seconds
            subprocess.run(["shutdown", "-h", "+1"], check=True)
            
        return (
            "Initiating shutdown sequence, sir. "
            "You have 30 seconds to cancel if this was unintentional. "
            "To cancel: type 'shutdown -a' on Windows or 'shutdown -c' on Linux/macOS."
        )
        
    except Exception as e:
        return f"Shutdown failed, sir. Error: {str(e)}"


def restart_pc() -> str:
    """
    Restart the computer after a 30-second delay.
    
    Returns:
        A status message.
    """
    try:
        if CURRENT_OS == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "30"], check=True)
        elif CURRENT_OS == "Darwin":
            subprocess.run(["shutdown", "-r", "+1"], check=True)
        else:
            subprocess.run(["shutdown", "-r", "+1"], check=True)
            
        return (
            "Initiating restart sequence, sir. "
            "System will restart in approximately 30 seconds."
        )
        
    except Exception as e:
        return f"Restart failed, sir. Error: {str(e)}"


def sleep_pc() -> str:
    """
    Put the computer to sleep immediately.
    
    Returns:
        A status message.
    """
    try:
        if CURRENT_OS == "Windows":
            # On Windows, use rundll32 to trigger sleep mode
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                check=True
            )
        elif CURRENT_OS == "Darwin":
            # macOS sleep command
            subprocess.run(["pmset", "sleepnow"], check=True)
        else:
            # Linux sleep using systemd
            subprocess.run(["systemctl", "suspend"], check=True)
            
        return "Initiating sleep mode, sir. Pleasant standby."
        
    except Exception as e:
        return f"Sleep mode failed, sir. Error: {str(e)}"


# ---------------------------------------------------------------------------
# WEB BROWSER
# ---------------------------------------------------------------------------

def open_website(url: str) -> str:
    """
    Open a URL in the default web browser.
    
    Automatically adds 'https://' if no protocol is specified.
    
    Args:
        url: The website URL to open (e.g., "github.com" or "https://github.com")
        
    Returns:
        A status message.
    """
    try:
        # Add https:// if the URL doesn't have a protocol
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            
        webbrowser.open(url)
        return f"Opening {url} in your browser, sir."
        
    except Exception as e:
        return f"I was unable to open the website, sir. Error: {str(e)}"
