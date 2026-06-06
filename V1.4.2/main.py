#All features in V1.4.1 plus more Terminal formatting. 
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
    text = re.sub(r'\*\*(.*?)\*\*', f"{ANSI_BOLD}\\1{ANSI_RESET}", text)
    text = re.sub(r'\*(.*?)\*', f"{ANSI_ITALIC}\\1{ANSI_RESET}", text)
    return text

def clean_for_speech(text):
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
r = sr.Recognizer()

while True:
    is_app_open = 0
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.2)
        print(format_for_terminal("*Ask Me Anything...*"))
        audio = r.listen(source)
    try:
        text = r.recognize_whisper(audio, model="small.en")
        print("-" * columns)
        print(format_for_terminal(f"**You:** {text}"))
        print("-" * columns)
    except sr.UnknownValueError:
        print(format_for_terminal("Could not understand audio"))

    if "open" in text.strip(".").strip(",").strip("!").strip("?").lower():
        converted_text = text.lower().split()
        if len(converted_text) > 1:
            next_word = converted_text[1]
            print(format_for_terminal(f"**Opening {next_word}**"))
            os.system(f"open -a {next_word}")
            is_app_open += 1
            
    if text == "":
        print(format_for_terminal("No input detected. Please try again."))
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
            trigger = chat(
                model='gemma4:31b-cloud',
                messages=[
                    {'role': 'user','content': text},
                    {'role': 'system','content': f'''You are a vision-context detector.Determine whether answering the user's query requires:- a camera image- surroundings analysis- appearance analysis- object inspection- environmental contextUser query:"{text}"Respond ONLY with:yesornoSay YES only if:- the user refers to themselves- the user refers to their surroundings- the user asks about appearance- the user asks to inspect something visible- the answer requires visual contextExamples of YES:- "How do I look?"- "What's in front of me?"- "Analyze my room"- "What is this object?"- "Does my hair look good?"Examples of NO:- news- coding- facts- explanations- web searches- math- history- general questionsBe accurate.Do not guess.Output ONLY yes or no.No punctuation.No emojis.'''}
                ]
            )
            if "yes" in trigger.message.content.lower():
                print(format_for_terminal("**Capturing photo...**"))
                cam = cv2.VideoCapture(0)
                ret, frame = cam.read()
                if ret:
                    cv2.imwrite("instant_photo.png",frame)
                    print(format_for_terminal("**Photo captured successfully!**"))
                else:
                    print(format_for_terminal("**Error: Could not access camera.**"))
                cam.release()
                image_analysis = ollama.chat(
                    model='ministral-3:3b-cloud',
                    messages=[
                        {'role': 'system','content': text},
                        {'role': 'user','content': f'''Analyze the image based on the user's request.User request:"{text}"Instructions:- Focus mainly on the requested subject- If no subject is specified, analyze the surroundings- Be concise but useful- Be truthful and accurate- Mention important visible details- Do not hallucinate- No emojis- No unnecessary formatting- Keep the response natural and clear''',
                            'images': ['/Users/lakshyaprajapati/Documents/Repositories/instant_photo.png']
                        }
                    ] 
                )
                print(format_for_terminal(image_analysis.message.content))
                answer.append(image_analysis.message.content)
                speak(image_analysis.message.content)
            else:
                pass
            check = web_simplifier.message.content
            results = ddgs.DDGS().text(
                check,
                max_results=2
            )
            response = chat(
                model='ministral-3:8b-cloud',
                messages=[
                    {'role': 'user','content': text },

                    {'role': 'system','content': f'''You are Churo.Personality:- helpful- professional- intelligent- concise- accurate- natural soundingRules:- Use simple language- Keep responses concise- No emojis- Do not ramble- Answer directly- Be conversational but efficientMemory context:{answer}Current user query:{text}Available web search results:{results}Use the web results ONLY if the user explicitly asks for:- latest news- recent updates- current information- newest details- web searchesOtherwise answer normally without relying on web results.If image analysis was already provided,do not repeat the analysis.Simply continue the conversation naturally.Never say:"Analysis provided"Instead continue naturally and intelligently.'''}
                ]
            )

            output = response.message.content
            print("-" * columns)
            print(format_for_terminal(f"{output:>{terminal_width}}"))
            print("-" * columns)
            print()
            answer.append(response.message.content)
            speak(response.message.content)
            continue_chat = input(format_for_terminal("**Do you want to continue talking to me? **")).lower().strip()
            print()
            if continue_chat != "yes":
                print("Bye!")
                break
            else:
                continue
        else:
            continue
