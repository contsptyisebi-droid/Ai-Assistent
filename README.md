```
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝

  Just A Rather Very Intelligent System
  ◈ SYSTEM ONLINE ◈
```

# J.A.R.V.I.S — Iron Man-Inspired AI Assistant

> *"At your service, sir."*

A fully-functional AI assistant inspired by J.A.R.V.I.S from the Iron Man films. Built with Python, powered by Claude AI (Anthropic), and featuring a futuristic HUD-style desktop dashboard.

---

## 📸 Screenshots

> *Launch the app and experience the HUD dashboard live!*

---

## ✨ Features

- 🧠 **AI Brain** — Powered by Anthropic's Claude Opus model with Jarvis's distinctive personality
- 🎤 **Voice Input** — Offline speech-to-text using OpenAI Whisper + wake word detection ("Hey Jarvis")
- 🔊 **Voice Output** — High-quality British TTS using Microsoft Edge TTS (`en-GB-RyanNeural`)
- 💻 **PC Control** — Launch apps, take screenshots, control volume, manage power
- 🌐 **Web Search** — DuckDuckGo search (no API key needed), weather, jokes, news
- 🏠 **Smart Home** — Home Assistant integration for controlling smart devices
- 🖥️ **HUD Dashboard** — Futuristic Iron Man-style GUI with animated orb, live stats, and more
- 🧠 **Conversation Memory** — Jarvis remembers the full session history
- 🎯 **Intent Detection** — Claude automatically understands what you want to do

---

## 📋 Prerequisites

- **Python 3.9 or newer** (Download from [python.org](https://www.python.org/downloads/))
- **Git** (Download from [git-scm.com](https://git-scm.com/))
- **FFmpeg** — Required by Whisper for audio processing
- **A microphone** — For voice input
- **Anthropic API key** — Get one free at [console.anthropic.com](https://console.anthropic.com/)

---

## 🚀 Step-by-Step Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/Ai-Assistent.git
cd Ai-Assistent
```

### Step 2: Create a Virtual Environment

A virtual environment keeps the project's dependencies isolated from your system Python.

```bash
# Create the virtual environment
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ This may take a few minutes — Whisper is a large model!

### Step 4: Install FFmpeg (Required for Whisper)

**Windows:**
```bash
# Using winget (Windows 10/11):
winget install ffmpeg

# Or download from: https://ffmpeg.org/download.html
# Add to PATH after installing
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install ffmpeg
```

### Step 5: Set Up Your .env File

Copy the example file:
```bash
cp .env.example .env
```

Then open `.env` and fill in your API key:
```
ANTHROPIC_API_KEY=your_actual_api_key_here
```

Get your Anthropic API key at: https://console.anthropic.com/

**Optional — Smart Home (Home Assistant):**
```
HA_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_token_here
```

**Optional — Wake Word (Picovoice Porcupine):**
```
PORCUPINE_API_KEY=your_porcupine_key_here
```
Get a free key at: https://picovoice.ai/ (required for accurate wake word detection)

### Step 6: Run J.A.R.V.I.S

```bash
cd jarvis
python main.py
```

The HUD dashboard will open. Say "Hey Jarvis" (with the mic enabled) or type in the text box!

---

## 🗣️ Example Commands

| What you say | What happens |
|---|---|
| "Hey Jarvis, open Spotify" | Opens the Spotify app |
| "What time is it?" | Tells you the current time |
| "Take a screenshot" | Captures and saves your screen |
| "What's the weather in New York?" | Shows weather for New York |
| "Search the web for Python tutorials" | Searches DuckDuckGo |
| "Turn on the living room lights" | Controls your smart home devices |
| "Tell me a joke" | Tells a random joke |
| "Volume up" | Increases system volume |
| "Shutdown the computer" | Initiates a 30-second countdown shutdown |
| "What's in the news?" | Fetches latest headlines |

---

## ⚙️ Configuration Guide

### Whisper Model Size

Edit `jarvis/voice_input.py` and change `WHISPER_MODEL_SIZE`:

| Model | Speed | Accuracy | Size |
|-------|-------|----------|------|
| `tiny` | Fastest | Lower | ~75 MB |
| `base` | Fast | Good | ~145 MB |
| `small` | Moderate | Better | ~466 MB |
| `medium` | Slow | Best (CPU) | ~1.5 GB |

### Wake Word Detection

- **With Porcupine API key**: Very accurate, low CPU usage. Set `PORCUPINE_API_KEY` in `.env`
- **Without API key**: Uses Whisper to check short clips for "jarvis" — works but uses more CPU

### Voice Language

Edit `jarvis/voice_output.py` to change the TTS voice:
```python
JARVIS_VOICE = "en-GB-RyanNeural"  # British male (default, sounds like Jarvis)
# Other options:
# "en-US-GuyNeural"    — American male
# "en-AU-WilliamNeural" — Australian male
```

---

## 🔧 Troubleshooting

**"No module named X"**
> Make sure you activated the virtual environment and ran `pip install -r requirements.txt`

**Whisper model download takes forever**
> This is normal on first run — the model is ~145MB. It's cached after the first download.

**"ANTHROPIC_API_KEY not found"**
> Make sure you created a `.env` file (not just `.env.example`) with your actual API key.

**Microphone not working**
> Check your system's microphone permissions. On Windows, go to Settings → Privacy → Microphone.

**"PortAudio not found" or sounddevice error**
> On Linux, install: `sudo apt install portaudio19-dev python3-pyaudio`
> On Windows, try: `pip install pipwin && pipwin install pyaudio`

**Dashboard appears but nothing works**
> Check the terminal for error messages. Most issues are API key or dependency related.

**Edge TTS fails**
> Check your internet connection — Edge TTS requires an internet connection to generate speech.

---

## 📁 Project Structure

```
Ai-Assistent/
├── requirements.txt          # Python dependencies
├── .env.example              # API key template (safe to commit)
├── .env                      # Your actual API keys (DO NOT commit)
├── .gitignore                # Git ignore rules
├── README.md                 # This file
└── jarvis/
    ├── main.py               # Entry point — starts everything
    ├── brain.py              # Claude AI integration + personality + intent detection
    ├── voice_input.py        # Whisper speech-to-text + wake word detection
    ├── voice_output.py       # Edge TTS text-to-speech
    ├── skills/
    │   ├── __init__.py       # Package marker
    │   ├── pc_control.py     # App launching, screenshots, volume, power
    │   ├── web_search.py     # DuckDuckGo search, weather, jokes, news
    │   └── smart_home.py     # Home Assistant integration
    └── dashboard/
        ├── __init__.py       # Package marker
        └── ui.py             # HUD dashboard GUI (customtkinter)
```

---

## 🔒 Security Notes

- Never commit your `.env` file — it's in `.gitignore` for this reason
- Your Anthropic API key is sensitive — treat it like a password
- The `.env.example` file shows the format without real values — this is safe to commit

---

## 📜 License

MIT License — feel free to use, modify, and distribute.

---

## 🙏 Credits

- **Anthropic Claude** — AI intelligence
- **OpenAI Whisper** — Offline speech recognition
- **Microsoft Edge TTS** — Text to speech
- **CustomTkinter** — Modern GUI framework
- **pvporcupine** — Wake word detection
- Inspired by J.A.R.V.I.S from the Iron Man / Marvel Cinematic Universe