<img width="1707" height="960" alt="Screenshot 2026-06-28 at 14 14 09" src="https://github.com/user-attachments/assets/05eb1e4e-0675-4aa2-8707-291e059c54cf" />

## Star History

<a href="https://www.star-history.com/?repos=MathObsession%2FChuro-assistant&type=timeline&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=MathObsession/Churo-assistant&type=timeline&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=MathObsession/Churo-assistant&type=timeline&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=MathObsession/Churo-assistant&type=timeline&legend=top-left" />
 </picture>
</a>

# V1.8 Speech Agent

V1.8 is an experimental voice-first AI assistant. It listens to spoken prompts, responds out loud, can launch apps on macOS, can search the web for current context, can inspect images from a webcam, and can generate images when the user asks for a visual result.

## Preview


https://github.com/user-attachments/assets/a4ca60a9-3868-4cab-acdb-4ddd5323cd20


<hr>

## What It Does

This project combines several assistant behaviors into one loop:

- Speech-to-text using Whisper through `speech_recognition`
- Text-to-speech using `edge-tts`
- App launching on macOS for commands such as `open Safari`
- Web query simplification and search retrieval through DDGS
- Webcam-based vision analysis for appearance or environment questions
- Image generation with Stable Diffusion
- Terminal-friendly output formatting with `rich`

## Who This Is For

This repository is intended for developers and hobbyists who want to explore a local voice assistant workflow. It is especially useful if you are interested in:

- voice interfaces
- multimodal AI interactions
- local automation on macOS
- image generation pipelines
- combining web search, vision, and speech in a single assistant

## Requirements

- macOS
- Python 3.11 or newer is recommended
- A microphone with system permission enabled
- A camera with system permission enabled if you want vision features
- Ollama installed and available on the machine running the script
- `chafa` installed if you want terminal previews for generated images
- Hardware that can run the configured Stable Diffusion pipeline on `mps`, or code changes to target a different device

## Python Dependencies

The script uses the following Python packages:

- `torch`
- `ollama`
- `speech_recognition`
- `edge_tts`
- `ddgs`
- `opencv-python`
- `rich`
- `diffusers`
- `term-image`

## Installation

1. Clone the repository and open the `V1.8` folder.

2. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the dependencies:

```bash
pip install torch ollama SpeechRecognition edge-tts ddgs opencv-python rich diffusers term-image
```

4. Make sure Ollama can access the models referenced in `main.py`.

## Usage

Run the assistant with:

```bash
python main.py
```

On startup, the program asks you to choose a voice:

- `Male` selects `en-US-SteffanNeural`
- Any other input selects `en-US-AvaNeural`

Then the assistant will:

1. Prompt you to speak
2. Transcribe your speech
3. Decide whether the request is for app launching, image generation, vision analysis, or a normal answer
4. Speak the response back to you
5. Ask whether you want to continue the conversation

## How It Works

### App Launching

If the transcription includes `open`, the assistant tries to find a matching application on macOS. If no local app is found, it falls back to opening a website based on the target name.

### Web Answers

For general questions, the assistant first simplifies the query and fetches recent search results. The response model can use those results when the request is about news, current events, or recent information.

### Vision Mode

If the prompt seems to require visual context, the assistant captures a frame from the webcam, saves it locally, and sends it to a vision-capable model for analysis.

### Image Generation

If the prompt is recognized as an image request, the assistant converts it into a short image prompt, generates an image with Stable Diffusion, saves the result as `generated_image.png`, and displays it in the terminal.

## Limitations

- The current implementation is macOS-focused.
- The assistant depends on several external models and services.
- The Stable Diffusion pipeline is loaded at startup, which may be slow on lower-powered machines.
- The current code stores generated and captured images in the working directory.
- The app-launching behavior is intentionally simple and may not match every app name perfectly.
- The image preview in the terminal is pixelated and low quality.

## Future Opportunities

This version leaves room for several improvements:

- Add cross-platform support beyond macOS
- Make the model names and device selection configurable through environment variables or a config file
- Add a proper command parser for app launching instead of relying on keyword matching
- Add a conversation history file or database
- Add streaming responses so users hear partial answers sooner
- Add a richer UI for desktop or web use
- Add safer image handling and cleanup for generated files
- Add a setup script or dependency file for easier installation

## Troubleshooting

- If microphone input fails, check system permissions and verify `speech_recognition` is installed correctly.
- If camera capture fails, check camera permissions and confirm OpenCV can access the device.
- If image generation fails, verify that your hardware supports the configured device target or update the pipeline configuration.
- If terminal image preview fails, install `chafa` and confirm it is available in your PATH.

## License

The MIT licence has been added for maximum freedom
