# All features in V1.7.1 plus image generation capablities.
import torch
import ollama
import speech_recognition as sr
import edge_tts
import asyncio
import tempfile
from ollama import chat
import ddgs
import os
import cv2
import re
import shutil
import time
import subprocess
from rich.console import Console
from rich.text import Text
from diffusers import StableDiffusionPipeline
from term_image.image import from_file

pipe = StableDiffusionPipeline.from_pretrained("nota-ai/bk-sdm-small", torch_dtype=torch.float16)
pipe = pipe.to("mps")

console = Console()
terminal_width = os.get_terminal_size().columns
columns, _ = shutil.get_terminal_size()

voice_selector = input("Choose a voice (Male/Female): ").lower().strip()
if voice_selector == "male":
    VOICE = "en-US-SteffanNeural"
else:
    VOICE = "en-US-AvaNeural"

ANSI_BOLD = "\033[1m"
ANSI_ITALIC = "\033[3m"
ANSI_RESET = "\033[0m"

def format_for_terminal(text):
    if text is None:
        return ""
    text = re.sub(r'\*\*(.*?)\*\*', f"{ANSI_BOLD}\\1{ANSI_RESET}", text)
    text = re.sub(r'\*(.*?)\*', f"{ANSI_ITALIC}\\1{ANSI_RESET}", text)
    return text
def clean_for_speech(text):
    if text is None:
        return ""
    return re.sub(r'\*\*|\*', '', text)

async def speak_async(text):
    clean_text = clean_for_speech(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_path = fp.name
    communicate = edge_tts.Communicate(clean_text, VOICE)
    await communicate.save(temp_path)
    os.system(f'afplay "{temp_path}"')
    os.remove(temp_path)
def speak(text):
    asyncio.run(speak_async(text))

answer = []
is_app_open = 0
is_recognised = 0
r = sr.Recognizer()

while True:
    is_app_open = 0
    is_recognised = 0

    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.2)
        Ask_anything = "*Ask Me Anything...*"
        speak(Ask_anything)
        console.print(Text.from_ansi(format_for_terminal(Ask_anything)))
        audio = r.listen(source)
    try:
        text = r.recognize_whisper(audio, model="small.en")
        console.print(" ", style="cornsilk1 on gray19", justify="left")
        console.print(Text.from_ansi(format_for_terminal(text)), style="cornsilk1 on gray19", justify="left")
        console.print(" ", style="cornsilk1 on gray19", justify="left")
    except sr.UnknownValueError:
        console.print(Text.from_ansi(format_for_terminal("Could not understand audio")))
        text = ""

    if "open" in text.strip(".").strip(",").strip("!").strip("?").lower():
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            target = parts[1].strip()
            console.print(Text.from_ansi(format_for_terminal(f"**Opening {target}**")))
            app = os.popen(
                f'mdfind \'kMDItemKind == "Application"\' | grep -i "{target}" | head -n 1'
            ).read().strip()
            if app:
                os.system(f'open "{app}"')
            else:
                os.system(f'open "https://{target.replace(" ", "")}.com"')
            is_app_open += 1

    if text == "":
        console.print(Text.from_ansi(format_for_terminal("No input detected. Please try again.")))
        pass
    else:
        if is_app_open == 0:
            web_simplifier = chat(
                model='ministral-3:3b-cloud',
                messages=[
                    {'role': 'user','content': text},
                    {'role': 'system','content': f'''You are a web-search query simplifier.Your job:Convert the user's message into ONE concise web search query.User message:"{text}"Rules:- Keep only important keywords- Remove filler words and stop words- No emojis- No explanations- Keep the meaning accurate- Make it optimized for a search engine- Output ONLY the final search queryFormat:latest details on <simplified topic> as of 2026'''}
                ]
            )

            image_generation_trigger = chat(
                model='ministral-3:14b-cloud',
                messages=[
                    {'role': 'user','content': text},
                    {'role': 'system','content': f'''You are an image generation trigger detector.Determine whether the user's query requires generating an image or not.User query:"{text}"Respond ONLY with:yesornoSay YES only if:- the user explicitly asks for an image- the user requests a visual representation of something- the answer requires generating an imageExamples of YES:- "Generate an image of a sunset over mountains"- "Create a picture of a futuristic city skyline"- "I want to see a visual representation of a dragon"- "Can you make an illustration of a robot?"Examples of NO:- news- coding- facts- explanations- web searches- math- history- general questionsBe accurate.Do not guess.Output ONLY yes or no.No punctuation.No emojis.'''}
                ]
            )

            if "yes" in image_generation_trigger.message.content.lower():
                image_generation_filter = chat(
                model='ministral-3:3b-cloud',
                messages=[
                        {'role': 'user','content': text},
                        {'role': 'system','content': f"""You are an expert prompt to image prompt generator. Today your goal is to convert "{text}" into a proper prompt for an image model. This is an example you can follow:- User:"Can you generate an image of a sunset over mountains?" this is what you have to do: "Generate a realistic image of a sunset over mountains". You are maximum only allowed to use 10 words, anything higher will not be tollerated."""}
                    ]
                )

                prompt = image_generation_filter.message.content
                image = pipe(prompt, num_inference_steps=20).images[0]
                image.save("generated_image.png")
                small_width = 60
                subprocess.run([
                    "chafa",
                    "/Users/lakshyaprajapati/Documents/Repositories/generated_image.png",
                    "--symbols", "block",
                    f"--size={small_width}"
                ])
                
            else:

                vision_trigger = chat(
                    model='ministral-3:14b-cloud',
                    messages=[
                        {'role': 'user','content': text},
                        {'role': 'system','content': f'''You are a vision-context detector.Determine whether answering the user's query requires:- a camera image- surroundings analysis- appearance analysis- object inspection- environmental contextUser query:"{text}"Respond ONLY with:yesornoSay YES only if:- the user refers to themselves- the user refers to their surroundings- the user asks about appearance- the user asks to inspect something visible- the answer requires visual contextExamples of YES:- "How do I look?"- "What's in front of me?"- "Analyze my room"- "What is this object?"- "Does my hair look good?"Examples of NO:- news- coding- facts- explanations- web searches- math- history- general questionsBe accurate.Do not guess.Output ONLY yes or no.No punctuation.No emojis.'''}
                    ]
                )
                if "yes" in vision_trigger.message.content.lower():
                    is_recognised = 1
                    console.print(Text.from_ansi(format_for_terminal("**Capturing photo...**")))
                    cam = cv2.VideoCapture(0)
                    ret, frame = cam.read()
                    if ret:
                        photo_path = os.path.join(os.getcwd(), "instant_photo.png")
                        cv2.imwrite(photo_path, frame)
                        console.print(Text.from_ansi(format_for_terminal("**Photo captured successfully!**")))
                    else:
                        console.print(Text.from_ansi(format_for_terminal("**Error: Could not access camera.**")))
                        photo_path = None
                    cam.release()
                    if photo_path:
                        image_analysis = ollama.chat(
                            model='ministral-3:8b-cloud',
                            messages=[
                                {'role': 'system','content': text},
                                {'role': 'user','content': f'''Analyze the image based on the user's request.User request:"{text}"Instructions:- Focus mainly on the requested subject- If no subject is specified, analyze the surroundings- Be concise but useful- Be truthful and accurate- Mention important visible details- Do not hallucinate- No emojis- No unnecessary formatting- Keep the response natural and clear''',
                                    'images': [photo_path]
                                }
                            ]
                        )
                        img_out = image_analysis.message.content
                        console.print(Text.from_ansi(format_for_terminal(img_out)))
                        answer.append(img_out)
                        speak(img_out)
                else:
                    pass

                if is_recognised == 1 and is_app_open == 1:
                    pass
                else:
                    check = web_simplifier.message.content
                    results = ddgs.DDGS().text(
                        check,
                        max_results=3
                    )
                    
                    response = chat(
                        model='gemma4:31b-cloud',
                        messages=[
                            {'role': 'user','content': text },
                            {'role': 'system','content': f'''You are Churo.Personality:- helpful- professional- intelligent- concise- accurate- natural soundingRules:- Use simple language- Keep responses concise- No emojis- Do not ramble- Answer directly- Be conversational but efficientMemory context:{answer}, use this when you feel that the query lacks context. Current user query:{text}Available web search results:{results}Use the web results ONLY if the user explicitly asks for:- latest news- recent updates- current information- newest details- web searchesOtherwise answer normally without relying on web results.If image analysis was already provided,do not repeat the analysis.Simply continue the conversation naturally.Never say:"Analysis provided"Instead continue naturally and intelligently.'''}
                        ]
                    )
                    output = response.message.content
                    formatted_output = format_for_terminal(output)
                    speech_output = clean_for_speech(output)
                    aligned = formatted_output.rjust(terminal_width)
                    console.print(" ")
                    console.print(" ", style="cornsilk1 on gray15", justify="left")
                    console.print(Text.from_ansi(aligned), style="cornsilk1 on gray15", justify="left")
                    console.print(" ", style="cornsilk1 on gray15", justify="left")
                    console.print()
                    answer.append(output)
                    speak(speech_output)

                voice_recogniser = sr.Recognizer()
                with sr.Microphone() as source1:
                    r.adjust_for_ambient_noise(source1, duration=0.2)
                    prompt_text = "*Do you want to continue the conversation? Yes or No?*"
                    console.print(Text.from_ansi(format_for_terminal(prompt_text)))
                    speak("Do you want to continue the conversation? Yes or No?")
                    time.sleep(0.01)
                    console.print(Text.from_ansi(format_for_terminal("*Listening for your response...*")))
                    audio1 = voice_recogniser.listen(source1)
                try:
                    voice_continue_recogniser = voice_recogniser.recognize_whisper(audio1, model="small.en")
                    voice_continue_recogniser = voice_continue_recogniser.strip()
                    console.print(" ", style="cornsilk1 on gray19", justify="left")
                    console.print(Text.from_ansi(format_for_terminal(voice_continue_recogniser)), style="cornsilk1 on gray19", justify="left")
                    console.print(" ", style="cornsilk1 on gray19", justify="left")
                except sr.UnknownValueError:
                    console.print(Text.from_ansi(format_for_terminal("Could not understand audio")))
                print()

                norm = re.sub(r'[^\w]', '', voice_continue_recogniser).lower()
                positive_patterns = positive_patterns = {"y", "Y", "yes", "Yes", "YES", "yep", "Yep", "yeah", "Yeah", "yup", "Yup", "sure", "Sure", "ok", "OK", "okay", "Okay", "affirmative", "Affirmative", "certainly", "Certainly", "definitely", "Definitely", "absolutely", "Absolutely", "indeed", "Indeed", "true", "True", "continue"}
                if norm == "":
                    console.print(Text.from_ansi(format_for_terminal("**No input detected.**")))
                    pass
                elif norm not in positive_patterns:
                    speak("Bye! Please Visit Again!")
                    break
                else:
                    continue

        else:
            continue