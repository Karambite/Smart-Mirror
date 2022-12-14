#ultrasonic sensor
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
# This example uses the sounddevice library to get an audio stream from the
# microphone. It's not a dependency of the project but can be installed with
# `python -m pip install amazon-transcribe aiofile`
# `pip install sounddevice`.
import sounddevice
from googlesearch import search


from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

TRIG = 16
ECHO = 18

print("Distance Measurement In Progess")
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

GPIO.output(TRIG, False)

print("Waiting For sensor to Settle")

time.sleep(2)

#Initialize 'currentname' to trigger only when a new person is identified.
#currentname = "unknown"
#Determine faces from encodings.pickle file model created from train_model.py
encodingsP = "encodings.pickle"

# load the known faces and embeddings along with OpenCV's Haar
# cascade for face detection
print("[INFO] loading encodings + face detector...")
data = pickle.loads(open(encodingsP, "rb").read())

def recFace():
    # initialize the video stream and allow the camera sensor to warm up
    # Set the ser to the followng
    # src = 0 : for the build in single web cam, could be your laptop webcam
    # src = 2 : I had to set it to 2 inorder to use the USB webcam attached to my laptop
    # vs = VideoStream(src=2,framerate=10).start()
    vid = cv2.VideoCapture(0)
    #vs = VideoStream(usePiCamera=True).start()
    time.sleep(2.0)
    continueLoop = True

    # start the FPS counter
    #fps = FPS().start()

    # loop over frames from the video file stream
    t_end = time.time() + 2
    while continueLoop:
        # grab the frame from the threaded video stream and resize it
        rec, frame = vid.read()
        # to 500px (to speedup processing)
        #frame = vs.read()
        frame = imutils.resize(frame, width=400)
        # Detect the fce boxes
        boxes = face_recognition.face_locations(frame)
        # compute the facial embeddings for each face bounding box
        encodings = face_recognition.face_encodings(frame, boxes)
        names = []

        # loop over the facial embeddings
        for encoding in encodings:
            # attempt to match each face in the input image to our known
            # encodings
            matches = face_recognition.compare_faces(data["encodings"],
                encoding)
            name = "Unknown" #if face is not recognized, then print Unknown

            # check to see if we have found a match
            if True in matches:
                # find the indexes of all matched faces then initialize a
                # dictionary to count the total number of times each face
                # was matched
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}

                # loop over the matched indexes and maintain a count for
                # each recognized face face
                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                # determine the recognized face with the largest number
                # of votes (note: in the event of an unlikely tie Python
                # will select first entry in the dictionary)
                name = max(counts, key=counts.get)

                #If someone in your dataset is identified, print their name on the screen
                #if currentname != name:
                    #currentname = name
                print("HI", name)
                continue_loop = False

            # update the list of names
            names.append(name)
            
        # loop over the recognized faces
        #for ((top, right, bottom, left), name) in zip(boxes, names):
            # draw the predicted face name on the image - color is in BGR
            #cv2.rectangle(frame, (left, top), (right, bottom),
                #(0, 255, 225), 2)
            #y = top - 15 if top - 15 > 15 else top + 15
            #cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                #.8, (0, 255, 255), 2)

        # display the image to our screen
        #cv2.imshow("Facial Recognition is Running", frame)
        #key = cv2.waitKey(1) & 0xFF

        # quit when 'q' key is pressed
        #if key == ord("q"):
            #break

        # update the FPS counter
        #fps.update()

    # stop the timer and display FPS information
    #fps.stop()
    #print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
    #print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

    # do a bit of cleanup
    cv2.destroyAllWindows()
    #vs.stop()

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

    print("Distance: ", distance, "cm")
    return distance

class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # This handler can be implemented to handle transcriptions as needed.
        # Here's an example to get started.
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:                 
                # to search
                query = alt.transcript
                print("Statement: ", query)
                if query == "Quit." or query == "Quit":
                    exit(0)
                for j in search(query, tld="co.in", num=1, stop=1, pause=2):
                    print("link: ", j)
                


async def mic_stream():
    # This function wraps the raw input stream from the microphone forwarding
    # the blocks to an asyncio.Queue.
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

    # Be sure to use the correct parameters for the audio stream that matches
    # the audio formats described for the source language you'll be using:
    # https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html
    stream = sounddevice.RawInputStream(
        channels=1,
        samplerate=16000,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16",
    )
    # Initiate the audio stream and asynchronously yield the audio chunks
    # as they become available.
    with stream:
        while True:
            indata, status = await input_queue.get()
            yield indata, status


async def write_chunks(stream):
    # This connects the raw audio chunks generator coming from the microphone
    # and passes them along to the transcription stream.
    async for chunk, status in mic_stream():
        await stream.input_stream.send_audio_event(audio_chunk=chunk)
    await stream.input_stream.end_stream()


async def basic_transcribe():
    # Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region="us-east-1")

    # Start transcription to generate our async stream
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm"
    )

    # Instantiate our handler and start processing events
    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(write_chunks(stream), handler.handle_events())

while True:
    distance = readSensor()
    if distance > 10:
        print("recognizing face")
        recFace()
        print("Any Commands?")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(basic_transcribe())
        loop.close()
    else:
        print("Not close enough")
    time.sleep(1)
GPIO.cleanup()


