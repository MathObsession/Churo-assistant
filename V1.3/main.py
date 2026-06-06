#All features in V1.2 plus vision capablities.
import ollama
import speech_recognition as sr
import pyttsx3
from ollama import chat
import ddgs
import os
import cv2
engine = pyttsx3.init()
answer = []
is_app_open = 0
r = sr.Recognizer()
while True:
    is_app_open = 0
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening...")
        audio = r.listen(source)
    try:
        text = r.recognize_whisper(audio, model="small.en")
        print(f"Transcription: {text}")
    except sr.UnknownValueError:
        print("Could not understand audio")

    if "open" in text.strip(".").strip(",").strip("!").strip("?"):
        converted_text = text.lower().split()
        if len(converted_text) > 1:
            next_word = converted_text[1]
            print(f"Opening {next_word}")
            os.system(f"open -a {next_word}")
            is_app_open+=1
    if text == "":
        print("No input detected. Please try again.")
        pass
    else:
        if is_app_open == 0:
            web_simplifier = chat(
                model='ministral-3:3b-cloud',
                messages=[
                    {'role': 'user', 'content': text},
                    {'role': 'system', 'content':f'You are just a simplifier whose job is to use the following text {text} and make a web search query out of it. Make the query as concise as possible and only include the important keywords. Do not include any stop words in the query. Do not include any emojis in the query. SIMPLIFY THE QUERY INTO ONE QUESTION THAT CAN BE USED TO SEARCH THE WEB. In the following format "latest details on (simplify the text:{text}) as of 2026"'} 
                    ]
            )
            trigger = chat(
                model='gemma4:31b-cloud',
                messages=[
                    {'role': 'user', 'content': text},
                    {'role': 'system', 'content':f'You are a trigger word detector for the following text: {text}.You are basically a flagger for weather answer the question, does it need a context, yes or no, if it does then say yes or else say no. YOU MUST NOT FLAG THE WRONG QUERIES THAT DO NOT REQUIRE CONTEXT. YOU MUST ANSWER IN ONLY YES OR NO DO NOT LEAVE THE ANSWER BLANK OR ELSE YOU WILL BE PUNISHED(yes/no)–make the classification fast, Check carefully for specific word combinations like my, I, look, is my, and any oher triggers that might mean that the user is talking about their surroundings(i.e.environment, room, school, hall or any other setting) or their self(hair, over all looks, etc.) etc... IT IS MAINLY ABOUT DOES IT NEED ACCESS TO A FOOTAGE FOR ANSWERING? IT MUST ME ACCURATE, IF THE USER IS TALKING ABOUT THE THE ROOM THEN SAY YES, IF THE USER IS TALKING ABOUT THEMSELVES THEN ALSO SAY YES, IF THE USER IS TALKING ABOUT ANYTHING ELSE THAT DOES NOT NEED A REFERENCE TO AN IMAGE THEN SAY NO. DO NOT USE EMOJIES. drz'} 
                    ]
            )
            if "yes" in trigger.message.content.lower():
                print("Capturing photo...")
                cam = cv2.VideoCapture(0)
                ret = cam.read()
                frame = cam.read()[1]
                if ret:
                    cv2.imwrite("instant_photo.png", frame)
                    print("Photo captured successfully!")
                else:
                    print("Error: Could not access camera.")
                cam.release()
                image_analysis = ollama.chat(
                    model='ministral-3:3b-cloud',
                    messages=[
                        {'role': 'system', 'content': text},
                        {
                            'role': 'user', 
                            'content': f'Your main goal is to just analyze the surroundings (or the thing they tell you to analyse, you can check for this based on {text} IN THAT CASE MAINLY ONLY FOCUS ON THE SUBJECT NOT THE SURROUNDINGS) of the image and provide a concise, but useful discription of the surroundings. NO EMOJIES. YOU MUST TELL THE TRUTH, ELSE YOU WILL BE PUNISHED', 
                            'images': ['/Users/lakshyaprajapati/Documents/Repositories/instant_photo.png']
                        }
                    ]
                )
                print(image_analysis.message.content)
                answer.append(image_analysis.message.content)
                engine.setProperty('rate', 155)
                engine.say(image_analysis.message.content)
                engine.runAndWait()
            else:
                pass
            check = web_simplifier.message.content
            results = ddgs.DDGS().text(check, max_results=2)
            response = chat(
                model='ministral-3:8b-cloud',
                messages=[
                    {'role': 'user', 'content': text},
                    {'role': 'system', 'content':f'You are Churo, a helpful, professional, smart and precise assistant who follows the instructions carefully, and accuratly. You always answer concisely and use simple language. You are provided the following tools: context {answer} which you will use only when you think the user is talking anything related to the past chats; this is the past query of the user: {text}. You also have the access to the web answers which are {results}: "Search the web for ________" or "Tell the latest news on ________" or "provide the latest details on __________"  or "Tell the newest _________ details on __________" or "update me on the latest __________"– These are THE ONLY instances that you will use the web search results. DO NOT USE EMOJIES. If you recieve any inputs related to taking a photo or analyzing the surroundings, you MUST NOT RESPOND WITH THE FOLLOWING ELSE YOU WILL BE PUNISHED JUST SAY "Analysis provided" '}
                    ]
            )
            print(response.message.content)
            answer.append(response.message.content)
            engine.setProperty('rate', 155)
            engine.say(response.message.content)
            engine.runAndWait()
            continue_chat=input("Do you want to continue talking to me? ").lower().strip()
            if continue_chat != "yes":
                print("Bye!")
                break
            else:
                continue
        else:
            continue