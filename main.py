import RPi.GPIO as GPIO
import time
import os
from imutils.video import VideoStream
from imutils.video import FPS
import face_recognition
import imutils
import pickle
import time
import cv2
import asyncio
import sounddevice
from googlesearch import search
import tkinter as tk
import random
import database
from database import window
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import asyncio
import time
import sounddevice
import os
import json
from gtts import gTTS
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

TRIG = 16
ECHO = 18

question_words = ["Who", "What", "Where", "When", "Why","How"]
weather_commands = ["temperature","weather","rain","whether"]

times = ["one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty","twenty one","twenty two","twenty three","twenty four","twenty five","twenty six","twenty seven","twenty eight","twenty nine","thirty","thirty one","thirty two","thirty three","thirty four","thirty five","thirty six","thirty seven","thirty eight","thirty nine","fourty","fourty one","fourty two","fourty three","fourty four","fourty five","fourty six","fourty seven","fourty eight","fourty nine","fifty","fifty one","fifty two","fifty three","fifty four","fifty five","fifty six","fifty seven","fifty eight","fifty nine","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","27","28","29","30","31","32","33","34","35","36","37","38","39","40","41","42","43","44","45","46","47","48","49","50","51","52","53","54","55","56","57","58","59"]
times_one_to_twelve = ["one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","1","2","3","4","5","6","7","8","9","10","11","12"]

reminder_commands = ["remind","reminder","set", "senate", "reminds"]

def recFace():
    vid = cv2.VideoCapture(0)
    time.sleep(2.0)
    while True:
        rec, frame = vid.read()
        frame = imutils.resize(frame, width=400)
        boxes = face_recognition.face_locations(frame)
        encodings = face_recognition.face_encodings(frame, boxes)
        names = []

        for encoding in encodings:
            matches = face_recognition.compare_faces(data["encodings"],
                encoding)
            name = "Unknown"

            if True in matches:
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}
                
                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                name = max(counts, key=counts.get)
                return name
            
            names.append(name)
    cv2.destroyAllWindows()

def readSensor():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)
    return distance



class MyEventHandler(TranscriptResultStreamHandler):

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        global prev_query
        results = transcript_event.transcript.results
        if len(results) == 0:
            query = ""
        for result in results:
            for alt in result.alternatives:
                query = alt.transcript

        with open("prev_query.txt","r") as fr:
            try:
                prev_query = fr.readlines()[0]
            except IndexError as e:
                print(e)
                prev_query = ""

        if len(results) != 0:
            with open("prev_query.txt","w") as fw:
                fw.write(query)
                fw.close()

        if query != prev_query:
            print(query)
            if isWeatherCommand(query):
                weather(query)

            if isReminderCommand(query) and "Setting a reminder" not in query and "Center reminder" not in query and "Reminder at" not in query and len(query.split()) < 10:
                remind(query)
            if query == "Quit." or query == "Quit":
                exit(0)

async def mic_stream():
    
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))
        
    stream = sounddevice.RawInputStream(
        channels=1,
        samplerate=16000,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16",

    )

    with stream:
        while True:
            indata, status = await input_queue.get()
            yield indata, status


async def write_chunks(stream):

    async for chunk, status in mic_stream():
        await stream.input_stream.send_audio_event(audio_chunk=chunk)
    await stream.input_stream.end_stream()


async def basic_transcribe():

    client = TranscribeStreamingClient(region="us-east-1")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm"

    )
    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(write_chunks(stream), handler.handle_events())


def isWeatherCommand(query):
    for command in query.split():
        if command.lower() in weather_commands or command.lower()[:-1] in weather_commands:
            if any(question_word in query.split() for question_word in question_words):
                return True
    return False


def weather(query):

    weather_data = os.popen("curl -s 'http://api.openweathermap.org/data/2.5/weather?q=Dallas,US&units=metric&appid=10a62430af617a949055a46fa6dec32f'").read()
    weather_data = json.loads(weather_data)
    city = str(weather_data["name"])
    current_temperature = str(round(float(weather_data['main']['temp'])*1.8+32,1))
    max_temperature = str(round(float(weather_data['main']['temp_max'])*1.8+32,1))
    min_temperature = str(round(float(weather_data['main']['temp_min'])*1.8+32,1))
    weather_description = weather_data["weather"][0]["description"].lower()

    if 'temperature' in query.lower():
        speech = "The temperature is " + current_temperature + " degrees fahrenheit."
        
    if 'weather' in query.lower() or 'whether' in query.lower() or 'rain' in query.lower():
        speech = city + " has a " + weather_description + " and is currently " + current_temperature + " degrees fahrenheit; The temperature ranges from " + min_temperature + " degrees fahrenheit to " + max_temperature + " degrees fahrenheit."

    audio = gTTS(text=speech, lang="en", slow=False)
    audio.save("weather.mp3")
    os.system("omxplayer --no-keys weather.mp3")
    time.sleep(4)
    query = ""

def isReminderCommand(query):

    for command in query.split():

        if command.lower() in reminder_commands:

            return True

    return False


def remind(query):

    current_time = ""
    words = query.split()
    for word in words:
        if word in times or word[:-1] in times:
            if '.' == word[-1]:
                word = word[:-1]
            current_time += word + " "

    prev_words = prev_query.split()
    prev_time = ""
    for prev_word in prev_words:
        if prev_word in times or prev_word[:-1] in times:
            if '.' == prev_word[-1]:
                prev_word = prev_word[:-1]
            prev_time += prev_word + " "
            
    if len(current_time.split()) >= len(prev_time.split()) and len(prev_time.split()) >= 1 and current_time.split()[0] in times_one_to_twelve and current_time != prev_time:

        speech = "Setting a reminder at" + current_time + "."
        audio = gTTS(text=speech, lang="en", slow=False)
        audio.save("reminder.mp3")
        time.sleep(5)


def main():
    while True:
        distance = readSensor()
        if distance < 50:
            name = recFace()
            window.attributes('-fullscreen', True)
            if name == "Ajay":
               user = database.Ajay
            else:
               user = database.Sudesh
            label = tk.Label(window,text="Hi " + user["name"], background=user["backgroundcolor"], foreground="white", font=("Helvetica", 100))
            label.pack()
            window.configure(bg=user["backgroundcolor"])
            window.after(3000, lambda: window.destroy()) # Destroy the widget after 30 seconds
            window.mainloop()
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(basic_transcribe())
                loop.close()
            except Exception as e:
                print(e)
        else:
            print("Not close enough")
        time.sleep(1)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False)
time.sleep(2)
encodingsP = "encodings.pickle"
data = pickle.loads(open(encodingsP, "rb").read())
main()
GPIO.cleanup()



