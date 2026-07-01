"""Core ChuroVoice assistant implementation."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import shutil
import sys
import tempfile
import time
from functools import lru_cache

import cv2
import edge_tts
import speech_recognition as sr
import torch
from ddgs import DDGS
from diffusers import StableDiffusionPipeline
from ollama import chat
from rich.console import Console
from rich.text import Text

from . import platform_utils as plat


DEFAULT_CHAT_MODEL = os.getenv("CHUROVOICE_CHAT_MODEL", "gemma4:31b-cloud")
DEFAULT_IMAGE_TRIGGER_MODEL = os.getenv("CHUROVOICE_IMAGE_TRIGGER_MODEL", "ministral-3:14b-cloud")
DEFAULT_IMAGE_PROMPT_MODEL = os.getenv("CHUROVOICE_IMAGE_PROMPT_MODEL", "ministral-3:3b-cloud")
DEFAULT_WEB_MODEL = os.getenv("CHUROVOICE_WEB_MODEL", "ministral-3:3b-cloud")
DEFAULT_VISION_MODEL = os.getenv("CHUROVOICE_VISION_MODEL", "ministral-3:14b-cloud")
DEFAULT_IMAGE_ANALYSIS_MODEL = os.getenv("CHUROVOICE_IMAGE_ANALYSIS_MODEL", "ministral-3:8b-cloud")
DEFAULT_STABLE_DIFFUSION_MODEL = os.getenv("CHUROVOICE_SD_MODEL", "nota-ai/bk-sdm-small")

ANSI_BOLD = "\033[1m"
ANSI_ITALIC = "\033[3m"
ANSI_RESET = "\033[0m"


def format_for_terminal(text: str | None) -> str:
    if text is None:
        return ""
    text = re.sub(r"\*\*(.*?)\*\*", f"{ANSI_BOLD}\\1{ANSI_RESET}", text)
    text = re.sub(r"\*(.*?)\*", f"{ANSI_ITALIC}\\1{ANSI_RESET}", text)
    return text


def clean_for_speech(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\*\*|\*", "", text)


def resolve_voice(choice: str) -> str:
    return "en-US-SteffanNeural" if choice.lower().strip() == "male" else "en-US-AvaNeural"


def resolve_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@lru_cache(maxsize=1)
def load_image_pipeline() -> StableDiffusionPipeline:
    device = resolve_device()
    dtype = torch.float16 if device in {"mps", "cuda"} else torch.float32
    pipe = StableDiffusionPipeline.from_pretrained(DEFAULT_STABLE_DIFFUSION_MODEL, torch_dtype=dtype)
    return pipe.to(device)


async def speak_async(text: str, voice: str) -> None:
    clean_text = clean_for_speech(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_path = fp.name

    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(temp_path)
    try:
        plat.play_audio(temp_path)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def speak(text: str, voice: str) -> None:
    asyncio.run(speak_async(text, voice))


def launch_target(target: str) -> bool:
    """Try to launch *target* as a local application; if nothing matches,
    fall back to opening ``https://<target>.com``.

    Works on macOS, Windows and Linux. Returns ``True`` if a launch was
    attempted successfully.
    """

    candidates = plat.find_applications(target)
    if candidates:
        # Prefer the shortest match (usually the canonical "app name" path).
        best = min(candidates, key=len)
        return plat.open_path(best)

    url = f"https://{target.replace(' ', '')}.com"
    return plat.open_url(url)


def simplify_query(text: str) -> str:
    response = chat(
        model=DEFAULT_WEB_MODEL,
        messages=[
            {"role": "user", "content": text},
            {
                "role": "system",
                "content": f'''You are a web-search query simplifier.Your job:Convert the user's message into ONE concise web search query.User message:"{text}"Rules:- Keep only important keywords- Remove filler words and stop words- No emojis- No explanations- Keep the meaning accurate- Make it optimized for a search engine- Output ONLY the final search queryFormat:latest details on <simplified topic> as of 2026''',
            },
        ],
    )
    return response.message.content.strip()


def detect_trigger(text: str, prompt: str, model: str) -> str:
    response = chat(
        model=model,
        messages=[
            {"role": "user", "content": text},
            {"role": "system", "content": prompt.format(text=text)},
        ],
    )
    return response.message.content.strip().lower()


def build_image_prompt(text: str) -> str:
    response = chat(
        model=DEFAULT_IMAGE_PROMPT_MODEL,
        messages=[
            {"role": "user", "content": text},
            {
                "role": "system",
                "content": f'''You are an expert prompt to image prompt generator. Today your goal is to convert "{text}" into a proper prompt for an image model. This is an example you can follow:- User:"Can you generate an image of a sunset over mountains?" this is what you have to do: "Generate a realistic image of a sunset over mountains". You are maximum only allowed to use 10 words, anything higher will not be tollerated.''',
            },
        ],
    )
    return response.message.content.strip()


def analyze_image(text: str, photo_path: str) -> str:
    response = chat(
        model=DEFAULT_IMAGE_ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": text},
            {
                "role": "user",
                "content": f'''Analyze the image based on the user's request.User request:"{text}"Instructions:- Focus mainly on the requested subject- If no subject is specified, analyze the surroundings- Be concise but useful- Be truthful and accurate- Mention important visible details- Do not hallucinate- No emojis- No unnecessary formatting- Make the response natural and clear''',
                "images": [photo_path],
            },
        ],
    )
    return response.message.content.strip()


def answer_with_chat(text: str, memory: list[str], search_results: list[dict[str, str]]) -> str:
    response = chat(
        model=DEFAULT_CHAT_MODEL,
        messages=[
            {"role": "user", "content": text},
            {
                "role": "system",
                "content": f'''You are Churo.Personality:- helpful- professional- intelligent- concise- accurate- natural soundingRules:- Use simple language- Keep responses concise- No emojis- Do not ramble- Answer directly- Be conversational but efficientMemory context:{memory}, use this when you feel that the query lacks context. Current user query:{text}Available web search results:{search_results}Use the web results ONLY if the user explicitly asks for:- latest news- recent updates- current information- newest details- web searchesOtherwise answer normally without relying on web results.If image analysis was already provided,do not repeat the analysis.Simply continue the conversation naturally.Never say:"Analysis provided"Instead continue naturally and intelligently.''',
            },
        ],
    )
    return response.message.content.strip()


def print_block(console: Console, text: str, *, style: str = "cornsilk1 on gray15") -> None:
    console.print(" ")
    console.print(" ", style=style, justify="left")
    console.print(Text.from_ansi(text), style=style, justify="left")
    console.print(" ", style=style, justify="left")
    console.print()


def run_assistant(voice_choice: str | None = None) -> None:
    console = Console()
    terminal_width = shutil.get_terminal_size((100, 20)).columns
    voice = resolve_voice(voice_choice or input("Choose a voice (Male/Female): "))

    answer_history: list[str] = []
    recognizer = sr.Recognizer()
    yes_words = {"y", "yes", "yep", "yeah", "yup", "sure", "ok", "okay", "affirmative", "certainly", "definitely", "absolutely", "indeed", "true", "continue"}

    while True:
        is_app_open = False
        is_recognised = False

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            ask_anything = "*Ask Me Anything...*"
            speak(ask_anything, voice)
            console.print(Text.from_ansi(format_for_terminal(ask_anything)))
            audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_whisper(audio, model="small.en")
            print_block(console, format_for_terminal(text), style="cornsilk1 on gray19")
        except sr.UnknownValueError:
            console.print(Text.from_ansi(format_for_terminal("Could not understand audio")))
            text = ""

        normalized_text = text.strip(".,!?").lower()
        if "open" in normalized_text:
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                target = parts[1].strip()
                console.print(Text.from_ansi(format_for_terminal(f"**Opening {target}**")))
                is_app_open = launch_target(target)

        if text == "":
            console.print(Text.from_ansi(format_for_terminal("No input detected. Please try again.")))
            continue

        web_query = simplify_query(text)
        image_trigger = detect_trigger(
            text,
            '''You are an image generation trigger detector.Determine whether the user's query requires generating an image or not.User query:"{text}"Respond ONLY with:yesornoSay YES only if:- the user explicitly asks for an image- the user requests a visual representation of something- the answer requires generating an imageExamples of YES:- "Generate an image of a sunset over mountains"- "Create a picture of a futuristic city skyline"- "I want to see a visual representation of a dragon"- "Can you make an illustration of a robot?"Examples of NO:- news- coding- facts- explanations- web searches- math- history- general questionsBe accurate.Do not guess.Output ONLY yes or no.No punctuation.No emojis.''',
            DEFAULT_IMAGE_TRIGGER_MODEL,
        )

        if "yes" in image_trigger:
            image_prompt = build_image_prompt(text)
            image = load_image_pipeline()(image_prompt, num_inference_steps=20).images[0]
            image_path = os.path.join(os.getcwd(), "generated_image.png")
            image.save(image_path)

            if not plat.preview_image_in_terminal(image_path, width=60):
                console.print(f"Generated image saved to {image_path}")

        else:
            vision_trigger = detect_trigger(
                text,
                '''You are a vision-context detector.Determine whether answering the user's query requires:- a camera image- surroundings analysis- appearance analysis- object inspection- environmental contextUser query:"{text}"Respond ONLY with:yesornoSay YES only if:- the user refers to themselves- the user refers to their surroundings- the user asks about appearance- the user asks to inspect something visible- the answer requires visual contextExamples of YES:- "How do I look?"- "What's in front of me?"- "Analyze my room"- "What is this object?"- "Does my hair look good?"Examples of NO:- news- coding- facts- explanations- web searches- math- history- general questionsBe accurate.Do not guess.Output ONLY yes or no.No punctuation.No emojis.''',
                DEFAULT_VISION_MODEL,
            )

            if "yes" in vision_trigger:
                is_recognised = True
                console.print(Text.from_ansi(format_for_terminal("**Capturing photo...**")))
                cam = cv2.VideoCapture(0)
                ret, frame = cam.read()
                if ret:
                    photo_path = os.path.join(os.getcwd(), "instant_photo.png")
                    cv2.imwrite(photo_path, frame)
                    console.print(Text.from_ansi(format_for_terminal("**Photo captured successfully!**")))
                else:
                    console.print(Text.from_ansi(format_for_terminal("**Error: Could not access camera.**")))
                    photo_path = ""
                cam.release()

                if photo_path:
                    image_answer = analyze_image(text, photo_path)
                    console.print(Text.from_ansi(format_for_terminal(image_answer)))
                    answer_history.append(image_answer)
                    speak(image_answer, voice)

            if is_recognised and is_app_open:
                continue

            search_results = list(DDGS().text(web_query, max_results=3))
            output = answer_with_chat(text, answer_history, search_results)
            formatted_output = format_for_terminal(output)
            speech_output = clean_for_speech(output)
            aligned = formatted_output.rjust(terminal_width)
            print_block(console, aligned)
            answer_history.append(output)
            speak(speech_output, voice)

            voice_recognizer = sr.Recognizer()
            with sr.Microphone() as source1:
                recognizer.adjust_for_ambient_noise(source1, duration=0.2)
                prompt_text = "*Do you want to continue the conversation? Yes or No?*"
                console.print(Text.from_ansi(format_for_terminal(prompt_text)))
                speak("Do you want to continue the conversation? Yes or No?", voice)
                time.sleep(0.01)
                console.print(Text.from_ansi(format_for_terminal("*Listening for your response...*")))
                audio1 = voice_recognizer.listen(source1)

            try:
                voice_continue = voice_recognizer.recognize_whisper(audio1, model="small.en").strip()
                print_block(console, format_for_terminal(voice_continue), style="cornsilk1 on gray19")
            except sr.UnknownValueError:
                console.print(Text.from_ansi(format_for_terminal("Could not understand audio")))
                voice_continue = ""

            normalized_continue = re.sub(r"[^\w]", "", voice_continue).lower()
            if normalized_continue == "":
                console.print(Text.from_ansi(format_for_terminal("**No input detected.**")))
            elif normalized_continue not in yes_words:
                speak("Bye! Please Visit Again!", voice)
                break


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the ChuroVoice assistant.")
    parser.add_argument("--voice", choices=["male", "female"], help="Choose the spoken voice.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_assistant(args.voice)
