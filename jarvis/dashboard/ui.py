# =============================================================================
# ui.py — The J.A.R.V.I.S HUD Dashboard
# =============================================================================
# This module creates the futuristic Iron Man-inspired GUI dashboard.
#
# COMPONENTS:
# - Startup animation (types in "J.A.R.V.I.S" with progress bar)
# - Animated orb that pulses/glows based on Jarvis's current state
# - Conversation log (color-coded messages with timestamps)
# - Live clock and date
# - System stats (CPU, RAM) updated in real-time
# - Weather widget
# - Text input with Send button
# - Microphone toggle button
# - Status bar at the bottom
#
# THREADING NOTE:
# The dashboard MUST run on the main thread (tkinter requirement).
# Background tasks (voice, API calls) run on separate threads and
# communicate with the GUI safely using the after() method.
# =============================================================================

import math         # For calculating orb animation values
import queue        # For thread-safe communication with the GUI
import threading    # For background tasks
import time         # For timing and delays
from datetime import datetime  # For clock display

import customtkinter as ctk  # Modern-looking tkinter widgets
import psutil                # For CPU and RAM usage stats
from PIL import Image        # For image processing (weather icons, etc.)

# ---------------------------------------------------------------------------
# Version and model info
# ---------------------------------------------------------------------------
VERSION = "2.0"
AI_MODEL = "claude-opus-4-5"  # Must match the model in brain.py

# ---------------------------------------------------------------------------
# Color scheme — Iron Man HUD inspired
# ---------------------------------------------------------------------------
# These are the colors we'll use throughout the dashboard
COLORS = {
    "bg_primary":    "#0a0a0f",   # Very dark background (almost black with blue tint)
    "bg_secondary":  "#0d1117",   # Slightly lighter dark for panels
    "bg_panel":      "#0f1923",   # Panel background (dark blue-grey)
    "accent_cyan":   "#00d4ff",   # Bright cyan — the main accent color
    "accent_blue":   "#0099cc",   # Slightly darker blue
    "accent_dim":    "#003d52",   # Dimmed cyan for borders and subtle elements
    "text_primary":  "#e0f4ff",   # Very light blue-white for primary text
    "text_secondary":"#7ab8cc",   # Muted blue-grey for secondary text
    "text_user":     "#00d4ff",   # Bright cyan for user messages
    "text_jarvis":   "#ffffff",   # White for Jarvis messages
    "text_timestamp":"#3a6070",   # Dim color for timestamps
    "status_idle":   "#1a4a5a",   # Dim blue for idle state
    "status_listen": "#00d4ff",   # Bright cyan for listening
    "status_think":  "#ff9500",   # Amber for thinking
    "status_speak":  "#0066ff",   # Bright blue for speaking
    "orb_idle":      "#002233",   # Dark blue orb when idle
    "orb_listen":    "#00d4ff",   # Bright cyan orb when listening
    "orb_speak":     "#0044ff",   # Blue orb when speaking
    "orb_think":     "#ff6600",   # Orange orb when thinking
    "error":         "#ff4444",   # Red for errors
    "success":       "#00ff88",   # Green for success
    "warning":       "#ffaa00",   # Yellow for warnings
}

# Set up customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# ---------------------------------------------------------------------------
# The main Dashboard class
# ---------------------------------------------------------------------------

class JarvisDashboard:
    """
    The main J.A.R.V.I.S HUD Dashboard.
    
    This creates and manages the entire GUI. It should always run on the
    main thread. Background updates are handled through the GUI's after()
    method to ensure thread safety.
    """
    
    def __init__(self, on_send_message=None, on_toggle_voice=None):
        """
        Initialize the dashboard.
        
        Args:
            on_send_message: Callback function called when user sends a message.
                           Receives the message text as a string.
            on_toggle_voice: Callback function called when microphone button is clicked.
        """
        
        # Store callback functions
        self.on_send_message = on_send_message
        self.on_toggle_voice = on_toggle_voice
        
        # Current state of Jarvis — affects orb color and status bar
        # States: "idle", "listening", "thinking", "speaking"
        self.state = "idle"
        
        # Whether voice is currently active
        self.voice_active = False
        
        # Queue for thread-safe GUI updates
        # Background threads put updates here; the GUI processes them
        self.update_queue = queue.Queue()
        
        # Animation variables for the pulsing orb
        self.orb_angle = 0          # Current angle for rotation animation
        self.orb_pulse = 0          # Current pulse size multiplier
        self.orb_pulse_dir = 1      # Pulse direction (1 = growing, -1 = shrinking)
        
        # Create the main application window
        self.root = ctk.CTk()
        self._setup_window()
        
        # Build all the UI components
        self._build_ui()
        
        # Show the startup animation first, then the main dashboard
        self._show_startup_animation()
    
    # =========================================================================
    # WINDOW SETUP
    # =========================================================================
    
    def _setup_window(self):
        """Configure the main window properties."""
        self.root.title("J.A.R.V.I.S — Just A Rather Very Intelligent System")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(fg_color=COLORS["bg_primary"])
        
        # Try to make the window slightly transparent (not supported on all platforms)
        try:
            self.root.attributes("-alpha", 0.97)
        except Exception:
            pass  # Not critical if this doesn't work
        
        # Handle window close — we need to clean up background threads
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================
    
    def _build_ui(self):
        """Build all the main dashboard components."""
        
        # Configure the grid layout for the root window
        # We'll use a grid layout with the orb area on top and content below
        self.root.grid_columnconfigure(0, weight=0)  # Left sidebar — fixed width
        self.root.grid_columnconfigure(1, weight=1)  # Center — expands
        self.root.grid_columnconfigure(2, weight=0)  # Right sidebar — fixed width
        self.root.grid_rowconfigure(0, weight=0)     # Top bar — fixed
        self.root.grid_rowconfigure(1, weight=1)     # Main content — expands
        self.root.grid_rowconfigure(2, weight=0)     # Bottom bar — fixed
        
        self._build_top_bar()
        self._build_left_panel()
        self._build_center_panel()
        self._build_right_panel()
        self._build_bottom_bar()
    
    # -------------------------------------------------------------------------
    def _build_top_bar(self):
        """Build the top bar with the Jarvis logo/title and live clock."""
        
        top_bar = ctk.CTkFrame(
            self.root,
            height=70,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["accent_dim"]
        )
        top_bar.grid(row=0, column=0, columnspan=3, sticky="ew", padx=0, pady=0)
        top_bar.grid_columnconfigure(1, weight=1)
        
        # Jarvis logo/title on the left
        title_label = ctk.CTkLabel(
            top_bar,
            text="◈  J.A.R.V.I.S",
            font=ctk.CTkFont(family="Courier New", size=22, weight="bold"),
            text_color=COLORS["accent_cyan"]
        )
        title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            top_bar,
            text=f"Just A Rather Very Intelligent System  |  v{VERSION}",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color=COLORS["text_secondary"]
        )
        subtitle_label.grid(row=0, column=1, padx=10, pady=15)
        
        # Live clock on the right
        self.clock_label = ctk.CTkLabel(
            top_bar,
            text="00:00:00",
            font=ctk.CTkFont(family="Courier New", size=20, weight="bold"),
            text_color=COLORS["accent_cyan"]
        )
        self.clock_label.grid(row=0, column=2, padx=20, pady=15, sticky="e")
        
        # Date below the clock
        self.date_label = ctk.CTkLabel(
            top_bar,
            text="Loading...",
            font=ctk.CTkFont(family="Courier New", size=10),
            text_color=COLORS["text_secondary"]
        )
        self.date_label.grid(row=1, column=2, padx=20, pady=(0, 5), sticky="e")
    
    # -------------------------------------------------------------------------
    def _build_left_panel(self):
        """Build the left sidebar with system stats and weather."""
        
        left_panel = ctk.CTkFrame(
            self.root,
            width=240,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["accent_dim"]
        )
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 2), pady=2)
        left_panel.grid_propagate(False)  # Keep fixed width
        
        # Section header
        self._add_section_header(left_panel, "◈ SYSTEM DIAGNOSTICS")
        
        # CPU Usage
        cpu_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        cpu_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            cpu_frame, text="CPU USAGE",
            font=ctk.CTkFont(family="Courier New", size=10),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w")
        
        self.cpu_bar = ctk.CTkProgressBar(
            cpu_frame,
            height=8,
            progress_color=COLORS["accent_cyan"],
            fg_color=COLORS["accent_dim"]
        )
        self.cpu_bar.pack(fill="x", pady=(3, 2))
        self.cpu_bar.set(0)
        
        self.cpu_label = ctk.CTkLabel(
            cpu_frame, text="0%",
            font=ctk.CTkFont(family="Courier New", size=12, weight="bold"),
            text_color=COLORS["accent_cyan"]
        )
        self.cpu_label.pack(anchor="e")
        
        # RAM Usage
        ram_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        ram_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            ram_frame, text="MEMORY (RAM)",
            font=ctk.CTkFont(family="Courier New", size=10),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w")
        
        self.ram_bar = ctk.CTkProgressBar(
            ram_frame,
            height=8,
            progress_color=COLORS["accent_blue"],
            fg_color=COLORS["accent_dim"]
        )
        self.ram_bar.pack(fill="x", pady=(3, 2))
        self.ram_bar.set(0)
        
        self.ram_label = ctk.CTkLabel(
            ram_frame, text="0% (0 GB / 0 GB)",
            font=ctk.CTkFont(family="Courier New", size=10),
            text_color=COLORS["accent_blue"]
        )
        self.ram_label.pack(anchor="e")
        
        # Separator
        ctk.CTkFrame(
            left_panel, height=1,
            fg_color=COLORS["accent_dim"]
        ).pack(fill="x", padx=10, pady=10)
        
        # Weather widget
        self._add_section_header(left_panel, "◈ WEATHER")
        
        self.weather_label = ctk.CTkLabel(
            left_panel,
            text="Fetching weather...",
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color=COLORS["text_primary"],
            wraplength=200,
            justify="left"
        )
        self.weather_label.pack(padx=15, pady=(0, 10), anchor="w")
        
        # Refresh weather button
        ctk.CTkButton(
            left_panel,
            text="↺ Refresh Weather",
            font=ctk.CTkFont(family="Courier New", size=10),
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["accent_blue"],
            text_color=COLORS["accent_cyan"],
            height=28,
            command=self._refresh_weather
        ).pack(padx=15, pady=(0, 10), fill="x")
        
        # Separator
        ctk.CTkFrame(
            left_panel, height=1,
            fg_color=COLORS["accent_dim"]
        ).pack(fill="x", padx=10, pady=10)
        
        # Quick commands section
        self._add_section_header(left_panel, "◈ QUICK ACCESS")
        
        quick_commands = [
            ("📸 Screenshot", "take a screenshot"),
            ("🕐 Time & Date", "what time is it"),
            ("📰 News", "get me the latest news"),
            ("😄 Joke", "tell me a joke"),
            ("🌡️ Weather", "what's the weather"),
        ]
        
        for label_text, command in quick_commands:
            btn = ctk.CTkButton(
                left_panel,
                text=label_text,
                font=ctk.CTkFont(family="Courier New", size=10),
                fg_color=COLORS["accent_dim"],
                hover_color=COLORS["accent_blue"],
                text_color=COLORS["text_primary"],
                height=28,
                anchor="w",
                command=lambda cmd=command: self._send_quick_command(cmd)
            )
            btn.pack(padx=15, pady=2, fill="x")
    
    # -------------------------------------------------------------------------
    def _build_center_panel(self):
        """Build the main center area with the orb and conversation log."""
        
        center_panel = ctk.CTkFrame(
            self.root,
            fg_color=COLORS["bg_primary"],
        )
        center_panel.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)
        center_panel.grid_rowconfigure(1, weight=1)
        center_panel.grid_columnconfigure(0, weight=1)
        
        # --- Orb Area ---
        # The animated circle that reacts to Jarvis's state
        orb_frame = ctk.CTkFrame(
            center_panel,
            height=200,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["accent_dim"]
        )
        orb_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        orb_frame.grid_propagate(False)
        orb_frame.grid_columnconfigure(0, weight=1)
        
        # Canvas for drawing the animated orb
        self.orb_canvas = ctk.CTkCanvas(
            orb_frame,
            height=180,
            bg=COLORS["bg_secondary"],
            highlightthickness=0  # No border around canvas
        )
        self.orb_canvas.pack(fill="x", expand=True, padx=10, pady=5)
        
        # State label below the orb
        self.state_label = ctk.CTkLabel(
            orb_frame,
            text="◈ IDLE ◈",
            font=ctk.CTkFont(family="Courier New", size=14, weight="bold"),
            text_color=COLORS["accent_dim"]
        )
        self.state_label.pack(pady=(0, 5))
        
        # --- Conversation Log ---
        log_frame = ctk.CTkFrame(
            center_panel,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["accent_dim"]
        )
        log_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(2, 0))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self._add_section_header(log_frame, "◈ COMMUNICATION LOG")
        
        # The scrollable text area for conversation history
        self.conversation_text = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Courier New", size=12),
            fg_color=COLORS["bg_primary"],
            text_color=COLORS["text_primary"],
            border_width=0,
            wrap="word",           # Wrap long lines at word boundaries
            state="disabled"       # Read-only — we control what appears here
        )
        self.conversation_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure text colors for different speakers using tags
        # (We'll use these tags when inserting text)
        self.conversation_text.tag_config(
            "user",
            foreground=COLORS["text_user"]
        )
        self.conversation_text.tag_config(
            "jarvis",
            foreground=COLORS["text_jarvis"]
        )
        self.conversation_text.tag_config(
            "timestamp",
            foreground=COLORS["text_timestamp"]
        )
        self.conversation_text.tag_config(
            "system",
            foreground=COLORS["text_secondary"]
        )
        
        # --- Input Area ---
        input_frame = ctk.CTkFrame(
            center_panel,
            height=60,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["accent_dim"]
        )
        input_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(2, 0))
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Text input box
        self.text_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a message or press the microphone button...",
            font=ctk.CTkFont(family="Courier New", size=12),
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["accent_dim"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_secondary"],
            height=40
        )
        self.text_input.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=10)
        
        # Bind Enter key to send the message
        self.text_input.bind("<Return>", lambda e: self._on_send_click())
        
        # Send button
        send_btn = ctk.CTkButton(
            input_frame,
            text="SEND →",
            font=ctk.CTkFont(family="Courier New", size=12, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_cyan"],
            text_color=COLORS["bg_primary"],
            width=100,
            height=40,
            command=self._on_send_click
        )
        send_btn.grid(row=0, column=1, padx=5, pady=10)
        
        # Microphone toggle button
        self.mic_button = ctk.CTkButton(
            input_frame,
            text="🎤 MIC",
            font=ctk.CTkFont(family="Courier New", size=12),
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["accent_blue"],
            text_color=COLORS["accent_cyan"],
            width=80,
            height=40,
            command=self._on_mic_click
        )
        self.mic_button.grid(row=0, column=2, padx=(0, 10), pady=10)
    
    # -------------------------------------------------------------------------
    def _build_right_panel(self):
        """Build the right sidebar with additional info panels."""
        
        right_panel = ctk.CTkFrame(
            self.root,
            width=200,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["accent_dim"]
        )
        right_panel.grid(row=1, column=2, sticky="nsew", padx=(2, 0), pady=2)
        right_panel.grid_propagate(False)
        
        self._add_section_header(right_panel, "◈ INTELLIGENCE")
        
        # Intelligence/status info
        info_items = [
            ("Model", AI_MODEL),
            ("Voice", "en-GB-Ryan"),
            ("STT", "Whisper Base"),
            ("Wake Word", "Hey Jarvis"),
        ]
        
        for label, value in info_items:
            item_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
            item_frame.pack(fill="x", padx=15, pady=2)
            
            ctk.CTkLabel(
                item_frame,
                text=label + ":",
                font=ctk.CTkFont(family="Courier New", size=9),
                text_color=COLORS["text_secondary"]
            ).pack(anchor="w")
            
            ctk.CTkLabel(
                item_frame,
                text=value,
                font=ctk.CTkFont(family="Courier New", size=11, weight="bold"),
                text_color=COLORS["accent_cyan"]
            ).pack(anchor="w")
        
        # Separator
        ctk.CTkFrame(
            right_panel, height=1,
            fg_color=COLORS["accent_dim"]
        ).pack(fill="x", padx=10, pady=10)
        
        # Session info
        self._add_section_header(right_panel, "◈ SESSION")
        
        self.message_count_label = ctk.CTkLabel(
            right_panel,
            text="Messages: 0",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color=COLORS["text_primary"]
        )
        self.message_count_label.pack(padx=15, pady=2, anchor="w")
        
        self.session_time_label = ctk.CTkLabel(
            right_panel,
            text="Session: 00:00",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color=COLORS["text_primary"]
        )
        self.session_time_label.pack(padx=15, pady=2, anchor="w")
        
        # Session start time (for calculating session duration)
        self.session_start = datetime.now()
        self.message_count = 0
        
        # Separator
        ctk.CTkFrame(
            right_panel, height=1,
            fg_color=COLORS["accent_dim"]
        ).pack(fill="x", padx=10, pady=10)
        
        # Clear conversation button
        self._add_section_header(right_panel, "◈ CONTROLS")
        
        ctk.CTkButton(
            right_panel,
            text="Clear Log",
            font=ctk.CTkFont(family="Courier New", size=10),
            fg_color=COLORS["accent_dim"],
            hover_color="#440000",
            text_color=COLORS["error"],
            height=28,
            command=self._clear_conversation
        ).pack(padx=15, pady=3, fill="x")
        
        ctk.CTkButton(
            right_panel,
            text="About J.A.R.V.I.S",
            font=ctk.CTkFont(family="Courier New", size=10),
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["accent_blue"],
            text_color=COLORS["text_primary"],
            height=28,
            command=self._show_about
        ).pack(padx=15, pady=3, fill="x")
    
    # -------------------------------------------------------------------------
    def _build_bottom_bar(self):
        """Build the status bar at the bottom of the dashboard."""
        
        bottom_bar = ctk.CTkFrame(
            self.root,
            height=35,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["accent_dim"]
        )
        bottom_bar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=0, pady=0)
        bottom_bar.grid_columnconfigure(1, weight=1)
        
        # Status indicator dot
        self.status_dot = ctk.CTkLabel(
            bottom_bar,
            text="●",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["accent_dim"]
        )
        self.status_dot.grid(row=0, column=0, padx=(15, 5), pady=8)
        
        # Status text
        self.status_label = ctk.CTkLabel(
            bottom_bar,
            text="SYSTEM IDLE — Awaiting instructions, sir.",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        
        # Version info on the right
        ctk.CTkLabel(
            bottom_bar,
            text=f"J.A.R.V.I.S v{VERSION}  |  © Stark Industries",
            font=ctk.CTkFont(family="Courier New", size=9),
            text_color=COLORS["text_timestamp"]
        ).grid(row=0, column=2, padx=15, pady=8)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _add_section_header(self, parent, text: str):
        """Add a styled section header label to a parent widget."""
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Courier New", size=10, weight="bold"),
            text_color=COLORS["accent_cyan"]
        ).pack(anchor="w", padx=15, pady=(15, 5))
    
    # =========================================================================
    # STARTUP ANIMATION
    # =========================================================================
    
    def _show_startup_animation(self):
        """
        Display the startup animation before showing the main dashboard.
        
        The animation shows:
        1. "J.A.R.V.I.S" typing in character by character
        2. "SYSTEM ONLINE" appears below
        3. A progress bar fills up
        4. Then the main dashboard is revealed
        """
        
        # Create a full-screen overlay frame for the animation
        self.startup_overlay = ctk.CTkFrame(
            self.root,
            fg_color=COLORS["bg_primary"]
        )
        # Place it on top of everything using place geometry manager
        self.startup_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Center content using a frame
        content_frame = ctk.CTkFrame(
            self.startup_overlay,
            fg_color="transparent"
        )
        content_frame.place(relx=0.5, rely=0.4, anchor="center")
        
        # "INITIALIZING" subtitle
        ctk.CTkLabel(
            content_frame,
            text="STARK INDUSTRIES PRESENTS",
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color=COLORS["text_secondary"]
        ).pack(pady=(0, 20))
        
        # Main title — we'll animate this
        self.startup_title = ctk.CTkLabel(
            content_frame,
            text="",
            font=ctk.CTkFont(family="Courier New", size=48, weight="bold"),
            text_color=COLORS["accent_cyan"]
        )
        self.startup_title.pack(pady=10)
        
        # Subtitle
        self.startup_subtitle = ctk.CTkLabel(
            content_frame,
            text="",
            font=ctk.CTkFont(family="Courier New", size=16),
            text_color=COLORS["text_primary"]
        )
        self.startup_subtitle.pack(pady=5)
        
        # Progress bar
        self.startup_progress = ctk.CTkProgressBar(
            content_frame,
            width=400,
            height=6,
            progress_color=COLORS["accent_cyan"],
            fg_color=COLORS["accent_dim"]
        )
        self.startup_progress.pack(pady=20)
        self.startup_progress.set(0)
        
        # Progress label
        self.startup_status = ctk.CTkLabel(
            content_frame,
            text="",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color=COLORS["text_secondary"]
        )
        self.startup_status.pack()
        
        # Start the typing animation
        self._animate_startup_title("J.A.R.V.I.S", 0)
    
    def _animate_startup_title(self, full_text: str, char_index: int):
        """
        Animate the startup title by typing characters one by one.
        
        Args:
            full_text: The complete text to display.
            char_index: Which character we're currently revealing.
        """
        if char_index <= len(full_text):
            # Show the title up to current character
            self.startup_title.configure(text=full_text[:char_index])
            
            if char_index < len(full_text):
                # Schedule the next character reveal after 100ms
                self.root.after(100, self._animate_startup_title, full_text, char_index + 1)
            else:
                # All characters shown — show subtitle and start progress bar
                self.root.after(300, self._show_startup_subtitle)
    
    def _show_startup_subtitle(self):
        """Show the startup subtitle and begin the progress animation."""
        self.startup_subtitle.configure(text="Just A Rather Very Intelligent System")
        self.startup_status.configure(text="Initializing systems...")
        
        # Start the progress bar animation
        self._animate_startup_progress(0)
    
    def _animate_startup_progress(self, progress: float):
        """
        Animate the startup progress bar.
        
        Args:
            progress: Current progress (0.0 to 1.0)
        """
        # Status messages that appear as the progress bar fills
        status_messages = {
            0.1: "Loading AI core modules...",
            0.25: "Initializing voice systems...",
            0.4: "Calibrating sensor array...",
            0.55: "Loading personality matrix...",
            0.7: "Establishing neural connections...",
            0.85: "Running diagnostics...",
            0.95: "All systems nominal.",
            1.0: "SYSTEM ONLINE",
        }
        
        # Update the progress bar
        self.startup_progress.set(progress)
        
        # Update status message if there's one for this progress level
        for threshold, message in status_messages.items():
            if abs(progress - threshold) < 0.02:
                self.startup_status.configure(text=message)
                if progress >= 1.0:
                    self.startup_subtitle.configure(text="✓  SYSTEM ONLINE")
                    self.startup_subtitle.configure(text_color=COLORS["success"])
                break
        
        if progress < 1.0:
            # Continue animating — increase progress by small steps
            next_progress = min(progress + 0.02, 1.0)
            self.root.after(50, self._animate_startup_progress, next_progress)
        else:
            # Progress complete — remove startup overlay after a short delay
            self.root.after(800, self._finish_startup)
    
    def _finish_startup(self):
        """Remove the startup overlay and start the main dashboard."""
        # Fade out the overlay (or just remove it)
        self.startup_overlay.destroy()
        
        # Start all the periodic update loops
        self._start_update_loops()
        
        # Show welcome message in the conversation log
        self.add_system_message(
            "J.A.R.V.I.S is online. All systems operational.\n"
            "Good day, sir. I'm ready to assist you."
        )
        
        # Fetch initial weather
        self._refresh_weather()
    
    # =========================================================================
    # PERIODIC UPDATE LOOPS
    # =========================================================================
    
    def _start_update_loops(self):
        """Start all the periodic update loops."""
        self._update_clock()         # Clock updates every second
        self._update_system_stats()  # System stats update every 2 seconds
        self._update_session_info()  # Session timer updates every 30 seconds
        self._animate_orb()          # Orb animation updates every 50ms
        self._process_update_queue() # Process queued GUI updates every 100ms
    
    def _update_clock(self):
        """Update the clock display. Called every second."""
        now = datetime.now()
        
        # Update the clock label
        self.clock_label.configure(text=now.strftime("%H:%M:%S"))
        
        # Update the date label
        self.date_label.configure(text=now.strftime("%A, %B %d, %Y"))
        
        # Schedule the next update in 1 second (1000ms)
        self.root.after(1000, self._update_clock)
    
    def _update_system_stats(self):
        """Update CPU and RAM stats. Called every 2 seconds."""
        try:
            # Get CPU usage (non-blocking — uses last measured value)
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # Get RAM usage
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            ram_used_gb = ram.used / (1024 ** 3)   # Convert bytes to GB
            ram_total_gb = ram.total / (1024 ** 3)
            
            # Update progress bars (values must be 0.0 to 1.0)
            self.cpu_bar.set(cpu_percent / 100)
            self.ram_bar.set(ram_percent / 100)
            
            # Update labels
            self.cpu_label.configure(text=f"{cpu_percent:.1f}%")
            self.ram_label.configure(
                text=f"{ram_percent:.1f}% ({ram_used_gb:.1f}/{ram_total_gb:.1f} GB)"
            )
            
            # Change color to red if usage is high (warning visual)
            if cpu_percent > 90:
                self.cpu_bar.configure(progress_color=COLORS["error"])
            elif cpu_percent > 70:
                self.cpu_bar.configure(progress_color=COLORS["warning"])
            else:
                self.cpu_bar.configure(progress_color=COLORS["accent_cyan"])
                
        except Exception as e:
            print(f"[Dashboard] Error updating system stats: {e}")
        
        # Schedule next update in 2 seconds
        self.root.after(2000, self._update_system_stats)
    
    def _update_session_info(self):
        """Update session duration and message count."""
        elapsed = datetime.now() - self.session_start
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        
        self.session_time_label.configure(
            text=f"Session: {minutes:02d}:{seconds:02d}"
        )
        self.message_count_label.configure(
            text=f"Messages: {self.message_count}"
        )
        
        # Update every 10 seconds
        self.root.after(10000, self._update_session_info)
    
    def _animate_orb(self):
        """
        Animate the pulsing orb in the center panel.
        
        The orb changes color and size based on Jarvis's current state:
        - Idle: Dim blue, slow gentle pulse
        - Listening: Bright cyan, faster pulse
        - Thinking: Amber/orange, steady glow
        - Speaking: Blue, fast pulse with rings
        """
        try:
            canvas = self.orb_canvas
            canvas.delete("all")  # Clear the canvas before redrawing
            
            # Get canvas dimensions
            width = canvas.winfo_width()
            height = canvas.winfo_height()
            
            if width < 10 or height < 10:
                # Canvas not yet rendered — try again soon
                self.root.after(100, self._animate_orb)
                return
            
            cx = width // 2   # Center X
            cy = height // 2  # Center Y
            
            # Update animation angle (for rotating rings effect)
            self.orb_angle = (self.orb_angle + 2) % 360
            
            # Update pulse (the orb gently grows and shrinks)
            self.orb_pulse += 0.05 * self.orb_pulse_dir
            if self.orb_pulse > 1.0:
                self.orb_pulse_dir = -1
            elif self.orb_pulse < 0.0:
                self.orb_pulse_dir = 1
            
            # Determine colors and behavior based on current state
            state = self.state
            
            if state == "listening":
                base_color = COLORS["orb_listen"]
                ring_color = COLORS["accent_cyan"]
                pulse_speed = 0.1    # Fast pulse
                base_radius = 55
                pulse_radius = 15
                glow_alpha = 0.8
                
            elif state == "thinking":
                base_color = COLORS["orb_think"]
                ring_color = COLORS["warning"]
                pulse_speed = 0.06
                base_radius = 50
                pulse_radius = 10
                glow_alpha = 0.6
                
            elif state == "speaking":
                base_color = COLORS["orb_speak"]
                ring_color = COLORS["accent_blue"]
                pulse_speed = 0.12
                base_radius = 58
                pulse_radius = 18
                glow_alpha = 0.9
                
            else:  # idle
                base_color = COLORS["orb_idle"]
                ring_color = COLORS["accent_dim"]
                pulse_speed = 0.03
                base_radius = 45
                pulse_radius = 8
                glow_alpha = 0.3
            
            # Update pulse speed
            self.orb_pulse += (pulse_speed - 0.05) * self.orb_pulse_dir
            
            # Calculate current radius with pulse effect
            current_radius = base_radius + (self.orb_pulse * pulse_radius)
            
            # Draw outer glow rings (decorative circles)
            for i in range(3, 0, -1):
                ring_radius = current_radius + (i * 15)
                alpha_suffix = f"{max(10, int(40 / i)):02x}"
                # Draw ring using canvas oval
                canvas.create_oval(
                    cx - ring_radius, cy - ring_radius,
                    cx + ring_radius, cy + ring_radius,
                    outline=ring_color,
                    width=1,
                    dash=(4, 8)  # Dashed line for futuristic look
                )
            
            # Draw the main orb (filled circle)
            canvas.create_oval(
                cx - current_radius, cy - current_radius,
                cx + current_radius, cy + current_radius,
                fill=base_color,
                outline=ring_color,
                width=2
            )
            
            # Draw inner highlight (makes it look like a glowing sphere)
            highlight_radius = current_radius * 0.4
            canvas.create_oval(
                cx - highlight_radius + 5, cy - highlight_radius - 5,
                cx + highlight_radius * 0.3 + 5, cy - 5,
                fill="#ffffff",
                outline=""
            )
            
            # If speaking, draw animated sound wave lines
            if state in ["speaking", "listening"]:
                num_bars = 12
                bar_height_max = 25
                for i in range(num_bars):
                    bar_x = cx - 60 + (i * 10)
                    # Each bar has a different height based on angle offset
                    angle_offset = (self.orb_angle + i * 30) % 360
                    bar_height = bar_height_max * abs(math.sin(math.radians(angle_offset)))
                    bar_y1 = cy + current_radius + 5
                    bar_y2 = bar_y1 + bar_height
                    
                    canvas.create_rectangle(
                        bar_x, bar_y1,
                        bar_x + 6, bar_y2,
                        fill=ring_color,
                        outline=""
                    )
            
            # Draw the state text inside the orb
            state_text = {
                "idle": "◈",
                "listening": "◉",
                "thinking": "◌",
                "speaking": "◎"
            }.get(state, "◈")
            
            canvas.create_text(
                cx, cy,
                text=state_text,
                fill=ring_color,
                font=("Courier New", 20, "bold")
            )
            
            # Draw decorative corner elements
            self._draw_hud_corners(canvas, width, height)
            
        except Exception as e:
            pass  # Animation errors shouldn't crash the app
        
        # Schedule next frame (50ms = ~20fps)
        self.root.after(50, self._animate_orb)
    
    def _draw_hud_corners(self, canvas, width: int, height: int):
        """Draw decorative HUD-style corner brackets on the canvas."""
        corner_size = 15
        color = COLORS["accent_dim"]
        
        # Top-left corner
        canvas.create_line(5, 5, 5 + corner_size, 5, fill=color, width=1)
        canvas.create_line(5, 5, 5, 5 + corner_size, fill=color, width=1)
        
        # Top-right corner
        canvas.create_line(width - 5, 5, width - 5 - corner_size, 5, fill=color, width=1)
        canvas.create_line(width - 5, 5, width - 5, 5 + corner_size, fill=color, width=1)
        
        # Bottom-left corner
        canvas.create_line(5, height - 5, 5 + corner_size, height - 5, fill=color, width=1)
        canvas.create_line(5, height - 5, 5, height - 5 - corner_size, fill=color, width=1)
        
        # Bottom-right corner
        canvas.create_line(width - 5, height - 5, width - 5 - corner_size, height - 5, fill=color, width=1)
        canvas.create_line(width - 5, height - 5, width - 5, height - 5 - corner_size, fill=color, width=1)
    
    def _process_update_queue(self):
        """
        Process any pending GUI updates from background threads.
        
        Background threads can't directly modify tkinter widgets (it's not
        thread-safe). Instead, they put update requests in a queue, and this
        function (running on the main thread) applies those updates.
        """
        try:
            # Process up to 10 updates per call to avoid blocking
            for _ in range(10):
                try:
                    # Get an update from the queue (non-blocking)
                    update = self.update_queue.get_nowait()
                    
                    # Each update is a tuple: (function, args)
                    func, args = update
                    func(*args)
                    
                except queue.Empty:
                    break  # No more updates in queue
                    
        except Exception as e:
            print(f"[Dashboard] Error processing update queue: {e}")
        
        # Schedule next check in 100ms
        self.root.after(100, self._process_update_queue)
    
    # =========================================================================
    # WEATHER UPDATE
    # =========================================================================
    
    def _refresh_weather(self):
        """Fetch weather data in a background thread and update the widget."""
        
        self.weather_label.configure(text="Fetching weather...")
        
        def fetch():
            try:
                # Import here to avoid circular imports
                from skills.web_search import get_weather
                weather_text = get_weather("London")
                # Schedule the update on the main thread
                self.update_queue.put((
                    self.weather_label.configure,
                    [{"text": weather_text}]
                ))
            except Exception as e:
                self.update_queue.put((
                    self.weather_label.configure,
                    [{"text": f"Weather unavailable"}]
                ))
        
        # Run in background thread so it doesn't freeze the UI
        threading.Thread(target=fetch, daemon=True).start()
    
    # =========================================================================
    # PUBLIC INTERFACE METHODS (called from main.py)
    # =========================================================================
    
    def set_state(self, new_state: str):
        """
        Update Jarvis's current state (affects orb color and status bar).
        
        Args:
            new_state: One of "idle", "listening", "thinking", "speaking"
        """
        self.state = new_state
        
        # Update the state label below the orb
        state_labels = {
            "idle":      ("◈ IDLE ◈",        COLORS["accent_dim"]),
            "listening": ("◉ LISTENING ◉",   COLORS["accent_cyan"]),
            "thinking":  ("◌ THINKING ◌",    COLORS["warning"]),
            "speaking":  ("◎ SPEAKING ◎",    COLORS["accent_blue"]),
        }
        
        label_text, label_color = state_labels.get(
            new_state,
            ("◈ IDLE ◈", COLORS["accent_dim"])
        )
        
        # Thread-safe update
        self.update_queue.put((
            self.state_label.configure,
            [{"text": label_text, "text_color": label_color}]
        ))
        
        # Update status bar
        status_messages = {
            "idle":      "SYSTEM IDLE — Awaiting instructions, sir.",
            "listening": "LISTENING — Speak your command, sir...",
            "thinking":  "PROCESSING — Please hold, sir...",
            "speaking":  "RESPONDING — J.A.R.V.I.S is speaking...",
        }
        
        status_text = status_messages.get(new_state, "SYSTEM IDLE")
        status_colors = {
            "idle":      COLORS["text_secondary"],
            "listening": COLORS["accent_cyan"],
            "thinking":  COLORS["warning"],
            "speaking":  COLORS["accent_blue"],
        }
        
        self.update_queue.put((
            self.status_label.configure,
            [{"text": status_text, 
              "text_color": status_colors.get(new_state, COLORS["text_secondary"])}]
        ))
        
        # Update status dot color
        dot_colors = {
            "idle":      COLORS["accent_dim"],
            "listening": COLORS["accent_cyan"],
            "thinking":  COLORS["warning"],
            "speaking":  COLORS["accent_blue"],
        }
        self.update_queue.put((
            self.status_dot.configure,
            [{"text_color": dot_colors.get(new_state, COLORS["accent_dim"])}]
        ))
    
    def add_user_message(self, text: str):
        """
        Add a user message to the conversation log.
        
        Args:
            text: The user's message text.
        """
        self.message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        def _add():
            self.conversation_text.configure(state="normal")  # Enable writing
            self.conversation_text.insert("end", f"\n[{timestamp}] ", "timestamp")
            self.conversation_text.insert("end", "YOU:  ", "user")
            self.conversation_text.insert("end", f"{text}\n", "user")
            self.conversation_text.configure(state="disabled")  # Back to read-only
            self.conversation_text.see("end")  # Scroll to bottom
        
        self.update_queue.put((_add, []))
    
    def add_jarvis_message(self, text: str):
        """
        Add a Jarvis response message to the conversation log.
        
        Args:
            text: Jarvis's response text.
        """
        self.message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        def _add():
            self.conversation_text.configure(state="normal")
            self.conversation_text.insert("end", f"\n[{timestamp}] ", "timestamp")
            self.conversation_text.insert("end", "J.A.R.V.I.S:  ", "jarvis")
            self.conversation_text.insert("end", f"{text}\n", "jarvis")
            self.conversation_text.configure(state="disabled")
            self.conversation_text.see("end")
        
        self.update_queue.put((_add, []))
    
    def add_system_message(self, text: str):
        """
        Add a system message to the conversation log.
        
        Used for status updates like "J.A.R.V.I.S is online".
        
        Args:
            text: The system message text.
        """
        def _add():
            self.conversation_text.configure(state="normal")
            self.conversation_text.insert("end", f"\n◈ {text}\n", "system")
            self.conversation_text.configure(state="disabled")
            self.conversation_text.see("end")
        
        self.update_queue.put((_add, []))
    
    def set_voice_active(self, active: bool):
        """
        Update the microphone button state to reflect voice listening status.
        
        Args:
            active: True if voice listening is active, False if not.
        """
        self.voice_active = active
        
        if active:
            self.update_queue.put((
                self.mic_button.configure,
                [{"fg_color": COLORS["accent_cyan"],
                  "text_color": COLORS["bg_primary"],
                  "text": "🎤 ON"}]
            ))
        else:
            self.update_queue.put((
                self.mic_button.configure,
                [{"fg_color": COLORS["accent_dim"],
                  "text_color": COLORS["accent_cyan"],
                  "text": "🎤 MIC"}]
            ))
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_send_click(self):
        """Called when the user clicks Send or presses Enter."""
        text = self.text_input.get().strip()
        
        if text and self.on_send_message:
            # Clear the input box
            self.text_input.delete(0, "end")
            # Call the main message handler
            self.on_send_message(text)
    
    def _on_mic_click(self):
        """Called when the user clicks the microphone button."""
        if self.on_toggle_voice:
            self.on_toggle_voice()
    
    def _send_quick_command(self, command: str):
        """Called when a quick command button is clicked."""
        if self.on_send_message:
            self.on_send_message(command)
    
    def _clear_conversation(self):
        """Clear the conversation log."""
        self.conversation_text.configure(state="normal")
        self.conversation_text.delete("1.0", "end")
        self.conversation_text.configure(state="disabled")
        self.message_count = 0
        self.add_system_message("Conversation log cleared.")
    
    def _show_about(self):
        """Show an about dialog."""
        about_window = ctk.CTkToplevel(self.root)
        about_window.title("About J.A.R.V.I.S")
        about_window.geometry("400x300")
        about_window.configure(fg_color=COLORS["bg_secondary"])
        about_window.grab_set()  # Make it modal
        
        ctk.CTkLabel(
            about_window,
            text="J.A.R.V.I.S",
            font=ctk.CTkFont(family="Courier New", size=32, weight="bold"),
            text_color=COLORS["accent_cyan"]
        ).pack(pady=(30, 5))
        
        ctk.CTkLabel(
            about_window,
            text="Just A Rather Very Intelligent System",
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color=COLORS["text_secondary"]
        ).pack(pady=5)
        
        ctk.CTkLabel(
            about_window,
            text=f"v{VERSION}",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color=COLORS["text_timestamp"]
        ).pack()
        
        ctk.CTkLabel(
            about_window,
            text="Powered by Claude AI · Whisper · Edge TTS",
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color=COLORS["text_primary"]
        ).pack(pady=20)
        
        ctk.CTkButton(
            about_window,
            text="CLOSE",
            font=ctk.CTkFont(family="Courier New", size=12),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_cyan"],
            text_color=COLORS["bg_primary"],
            command=about_window.destroy
        ).pack(pady=10)
    
    # =========================================================================
    # APP LIFECYCLE
    # =========================================================================
    
    def _on_close(self):
        """Handle the window close event — clean up properly."""
        print("[Dashboard] Window closing...")
        # The main.py shutdown handler will be triggered if we set a flag
        # For now, just destroy the window
        self.root.destroy()
    
    def run(self):
        """Start the dashboard main loop. This blocks until the window is closed."""
        self.root.mainloop()
    
    def queue_update(self, func, *args):
        """
        Queue a GUI update from a background thread.
        
        Use this method from background threads to safely update the GUI.
        
        Args:
            func: The GUI function to call.
            *args: Arguments to pass to the function.
        """
        self.update_queue.put((func, args))
