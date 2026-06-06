#All features in V1.0 plus web search capability. Now with support of Ollama cloud.
import speech_recognition as sr
import pyttsx3
from ollama import chat
import ddgs

engine = pyttsx3.init()
answer = []
while True:
    r = sr.Recognizer()
    engine.say("Hey, I am Churo, your assistant. How can I help?")
    answer.append("Hey, I am Churo, your assistant. How can I help?")
    engine.runAndWait()
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)
    try:
        text = r.recognize_whisper(audio, model="small.en")
        print(f"Transcription: {text}")
    except sr.UnknownValueError:
        print("Could not understand audio")
    web_simplifier = chat(
        model='ministral-3:3b-cloud',
        messages=[
            {'role': 'user', 'content': text},
            {'role': 'system', 'content':f'You are just a simplifier whose job is to use the following text {text} and make a web search query out of it. Make the query as concise as possible and only include the important keywords. Do not include any stop words in the query. Do not include any emojis in the query. SIMPLIFY THE QUERY INTO ONE QUESTION THAT CAN BE USED TO SEARCH THE WEB. In the following format "latest details on (simplify the text:{text}) as of 2026"'} 
            ]
    )
    check = web_simplifier.message.content
    results = ddgs.DDGS().text(check, max_results=2)
    response = chat(
        model='ministral-3:8b-cloud',
        messages=[
            {'role': 'user', 'content': text},
            {'role': 'system', 'content':f'You are Churo, a helpful, professional, smart and precise assistant who follows the instructions carefully, and accuratly. You always answer concisely and use simple language. You are provided the following tools: context {answer} which you will use only when you think the user is talking anything related to the past chats; this is the past query of the user: {text}. You also have the access to the web answers which are {results}: "Search the web for ________" or "Tell the latest news on ________" or "provide the latest details on __________" – These are THE ONLY instances that you will use the web search results. DO NOT USE EMOJIES'}
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