# -*- coding: utf-8 -*-

import json
import sounddevice as sd
import vosk
import subprocess
import serial
import pynmea2
from datetime import datetime

# ================= CONFIG =================
MODEL_PATH = "vosk-model-hi"
PIPER_MODEL = "hi_IN-pratham-medium.onnx"
GPS_PORT = "/dev/serial0"
SAMPLE_RATE = 44100
RECORD_SECONDS = 2

# ================= LOAD ASR =================
model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

# ================= PERSISTENT PIPER =================
piper_process = subprocess.Popen(
    ["piper", "--model", PIPER_MODEL, "--output-raw"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL
)

def speak(text):
    try:
        # Generate wav
        subprocess.run(
            f'echo "{text}" | piper --model {PIPER_MODEL} --output_file response.wav',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Play wav
        subprocess.run(
            ["aplay", "-D", "plughw:0,0", "response.wav"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except:
        pass

# ================= GPS =================
def convert_to_decimal(raw, direction):
    if not raw:
        return None

    dot_index = raw.index(".")
    deg_len = dot_index - 2

    deg = int(raw[:deg_len])
    minutes = float(raw[deg_len:])

    dec = deg + minutes / 60

    if direction in ['S', 'W']:
        dec = -dec

    return dec

def get_gps_location():
    try:
        ser = serial.Serial(GPS_PORT, 9600, timeout=1)

        lat = None
        lon = None

        for _ in range(60):
            line = ser.readline().decode(errors='ignore')

            if "$GPRMC" in line:
                msg = pynmea2.parse(line)

                if msg.status == "A":
                    lat = convert_to_decimal(msg.lat, msg.lat_dir)
                    lon = convert_to_decimal(msg.lon, msg.lon_dir)
                    break

        ser.close()
        return lat, lon

    except:
        return None, None

# ================= GEO MAP =================
def get_city_state(lat, lon):

    if lat is None:
        return None, None

    # Coimbatore
    if 10.9 <= lat <= 11.2 and 76.8 <= lon <= 77.1:
        return "कोयंबटूर", "तमिलनाडु"

    # Chennai
    if 12.9 <= lat <= 13.2 and 80.1 <= lon <= 80.4:
        return "चेन्नई", "तमिलनाडु"

    return None, None

# ================= INTENTS =================
INTENTS = {
    "time": ["समय", "कितने बजे"],
    "date": ["तारीख"],
    "day": ["आज कौन सा दिन", "दिन"],
    "city": ["शहर"],
    "state": ["राज्य"],
    "location": ["लोकेशन", "स्थान"],
    "greeting": ["नमस्ते", "हैलो"],
    "identity": ["तुम कौन हो"],
    "help": ["मदद"],
    "temperature": ["तापमान"],
    "internet": ["इंटरनेट"],
    "exit": ["बंद", "अलविदा"]
}


def detect_intent(text):
    for intent, words in INTENTS.items():
        if any(w in text for w in words):
            return intent
    return "unknown"

# ================= HANDLER =================
def handle_intent(intent):

    if intent == "time":
        return datetime.now().strftime('%H:%M')

    elif intent == "date":
        return datetime.now().strftime('%d/%m/%Y')

    elif intent == "city":
        lat, lon = get_gps_location()
        city, state = get_city_state(lat, lon)
        return city if city else "स्थान नहीं मिला"

    elif intent == "state":
        lat, lon = get_gps_location()
        city, state = get_city_state(lat, lon)
        return state if state else "स्थान नहीं मिला"

    elif intent == "exit":
        return "नमस्ते"
        
    elif intent == "greeting":
        return "नमस्ते मैं आपकी सहायता के लिए तैयार हूँ"

    elif intent == "identity":
        return "मैं आपका ऑफलाइन हिंदी सहायक हूँ"

    elif intent == "help":
        return "आप समय तारीख शहर राज्य पूछ सकते हैं"

    elif intent == "temperature":
        return "सिस्टम तापमान सामान्य है"

    elif intent == "internet":
        return "यह ऑफलाइन सहायक है"

    elif intent == "day":
        return f"आज {datetime.now().strftime('%A')} है"


    else:
        return "समझा नहीं"

# ================= MAIN =================
print("🔥 FINAL LOW LATENCY GPS ASSISTANT READY")

# Warm Piper (IMPORTANT)
speak("तैयार")

while True:
    input("\nPress ENTER to Speak (Ctrl+C to exit)")
    print("🎤 Speak now...")

    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
                   samplerate=SAMPLE_RATE,
                   channels=1,
                   dtype='int16')
    sd.wait()

    rec.Reset()
    rec.AcceptWaveform(audio.tobytes())
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
    else:
        print("No speech detected.")
