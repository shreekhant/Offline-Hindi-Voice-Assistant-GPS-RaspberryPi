# -*- coding: utf-8 -*-

import json
import sounddevice as sd
import vosk
import subprocess
import numpy as np
from datetime import datetime

# ---------------- CONFIG ----------------
MODEL_PATH = "vosk-model-hi"
SAMPLE_RATE = 44100
DEVICE_ID = 2              # USB mic from your device list
RECORD_SECONDS = 4

# Piper model
PIPER_MODEL = "hi_IN-pratham-medium.onnx"

# ----------------------------------------

# Load Vosk
model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

# ---------------- SPEAK FUNCTION ----------------
def speak(text):
    print("TTS TEXT:", text)
    subprocess.run(
        f'echo "{text}" | piper --model {PIPER_MODEL} --output-raw | aplay -D hw:0,0 -r 22050 -f S16_LE -t raw -',
        shell=True
    )

# ---------------- INTENTS ----------------
INTENTS = {
    "date": ["तारीख", "आज की तारीख"],
    "time": ["समय", "कितने बजे"],
    "city": ["शहर"],
    "state": ["राज्य"],
    "add": ["जोड़", "प्लस"],
    "multiply": ["गुणा"],
    "divide": ["भाग"],
    "alarm": ["अलार्म"],
    "joke": ["जोक"],
    "exit": ["बंद", "अलविदा"]
}

# ---------------- INTENT DETECTION ----------------
def detect_intent(text):

    # IMPORTANT: DATE first to avoid overlap
    if any(word in text for word in INTENTS["date"]):
        return "date"

    if any(word in text for word in INTENTS["time"]):
        return "time"

    for intent, words in INTENTS.items():
        if intent in ["date", "time"]:
            continue
        if any(word in text for word in words):
            return intent

    return "unknown"

# ---------------- RESPONSE HANDLER ----------------
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

    elif intent == "multiply":
        return "5 गुणा 6 बराबर 30"

    elif intent == "divide":
        return "100 भाग 4 बराबर 25"

    elif intent == "alarm":
        return "सुबह 7 बजे अलार्म सेट"

    elif intent == "joke":
        return "डॉक्टर बोला कब से? मरीज बोला क्या?"

    elif intent == "exit":
        return "नमस्ते"

    else:
        return "समझा नहीं"

# ---------------- MAIN LOOP ----------------
print("🔥 Stable Offline Assistant Running")

while True:

    print("🎤 Speak...")

    # Record audio
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
                   samplerate=SAMPLE_RATE,
                   channels=1,
                   dtype='int16',
                   device=DEVICE_ID)

    sd.wait()

    data = audio.tobytes()

    if rec.AcceptWaveform(data):

        result = json.loads(rec.Result())
        text = result.get("text", "").strip()

        if text:
            print("📝:", text)

            intent = detect_intent(text)
            response = handle_intent(intent)

            print("🤖:", response)
            speak(response)

            if intent == "exit":
                break

        else:
            print("No speech detected.")
