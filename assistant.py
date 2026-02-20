# -*- coding: utf-8 -*-

import queue
import json
import sounddevice as sd
import vosk
import subprocess
import threading
from datetime import datetime

# ---------------- CONFIG ----------------
MODEL_PATH = "vosk-model-hi"
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024   # smaller = faster response

# ---------------- LOAD ASR MODEL ----------------
model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

audio_queue = queue.Queue()

# ---------------- LOAD PIPER ONCE (VERY IMPORTANT) ----------------
piper_process = subprocess.Popen(
    [
        "piper",
        "--model", "hi_IN-rohan-medium.onnx",
        "--output-raw"
    ],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL
)

# ---------------- AUDIO CALLBACK ----------------
def callback(indata, frames, time, status):
    if status:
        print(status)
    audio_queue.put(bytes(indata))

# ---------------- FAST TTS FUNCTION ----------------
def speak(text):
    if not text:
        return

    # Send text to piper
    piper_process.stdin.write((text + "\n").encode("utf-8"))
    piper_process.stdin.flush()

    # Read generated audio (approx 2 seconds buffer)
    audio_data = piper_process.stdout.read(22050 * 2)

    # Play immediately
    subprocess.run(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
        input=audio_data,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# ---------------- INTENT LOGIC ----------------
INTENTS = {
    "time": ["समय", "कितने बजे"],
    "date": ["तारीख"],
    "city": ["शहर"],
    "state": ["राज्य"],
    "add": ["जोड़", "प्लस"],
    "exit": ["बंद", "अलविदा"]
}

def detect_intent(text):
    for intent, words in INTENTS.items():
        if any(word in text for word in words):
            return intent
    return "unknown"

def handle_intent(intent):
    if intent == "time":
        return f"अभी {datetime.now().strftime('%I:%M')} बजे हैं"
    elif intent == "date":
        return f"आज {datetime.now().strftime('%d/%m/%Y')}"
    elif intent == "city":
        return "आप चेन्नई शहर में हैं"
    elif intent == "state":
        return "आप तमिलनाडु राज्य में हैं"
    elif intent == "add":
        return "20 जोड़ 10 बराबर 30"
    elif intent == "exit":
        return "नमस्ते"
    else:
        return "समझा नहीं"

# ---------------- MAIN LOOP ----------------
print("🔥 Offline Hindi Assistant Ready")
print("🎤 बोलिए...")

with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype='int16',
        channels=1,
        callback=callback):

    while True:
        data = audio_queue.get()

        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "")

            if text:
                print("📝:", text)

                intent = detect_intent(text)
                response = handle_intent(intent)

                print("🤖:", response)
                speak(response)

                if intent == "exit":
                    break
