# V1.7 Speech Agent

A voice-driven AI assistant that listens for spoken queries, performs local actions, optionally captures images for visual requests, and answers using Ollama chat models.

## Features

- Voice input with Whisper speech recognition
- Text-to-speech output using `edge-tts`
- Intelligent command handling with Ollama chat models
- App launching on macOS for `open <app>` voice commands
- Web search query simplification and results retrieval
- Vision-context detection and camera image capture for visual queries
- ANSI-enhanced console output with `rich`

## Requirements

- Install Ollama
- Sign-in to Ollama
- Install ministral-3:3b-cloud, ministral-3:8b-cloud, and gemma4:31b-cloud 
- macOS
- Python 3.11+ (recommended)
- Microphone access
- Camera access for image-based queries
- Installed Python packages:
  - `ollama`
  - `speech_recognition`
  - `edge_tts`
  - `ddgs`
  - `opencv-python`
  - `rich`

## Installation

1. Clone or copy this folder:

```bash
cd /path/to/AI/OSS_speech_model/Phase-1/V1.7
```

2. Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:

```bash
pip install ollama speech_recognition edge_tts ddgs opencv-python rich
```

4. Make sure your environment has access to Ollama.

## Usage

Run the assistant with:

```bash
python main.py
```

The assistant will prompt:

- Choose a voice: `Male` or `Female`
- Speak a query after the prompt
- It will attempt to answer, launch apps, or capture an image if visual context is needed
- When finished, it asks whether you want to continue

## Notes

- The current implementation uses `afplay` to play audio on macOS.
- App launching relies on `mdfind` and the local macOS application metadata.
- If the assistant cannot understand audio, it prompts again.
- Visual queries are captured and saved temporarily as `instant_photo.png` in the current folder.

## Troubleshooting

- If speech recognition fails, verify microphone permissions and `speech_recognition` installation.
- If camera capture fails, verify camera permissions and that `opencv-python` can access the device.
- If audio playback fails, ensure `afplay` is available on macOS.
