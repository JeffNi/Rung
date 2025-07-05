# audio_listener.py

import collections
import os
import sys
import time
import glob
import wave
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
import webrtcvad
import asyncio
import speech_recognition as sr
from diurize import transcribe_and_diarize

# Config
SAMPLE_RATE = 16000
FRAME_DURATION = 30  # ms
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)  # samples per frame
VAD_MODE = 3  # 0: aggressive, 3: very aggressive
BUFFER_DURATION = 1.5  # seconds max ring buffer
MIN_SPEECH_SECONDS = 1.0
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio") 

load_dotenv()
HF_TOKEN = os.environ.get("HF_TOKEN")

vad = webrtcvad.Vad(VAD_MODE)

def delete_all_files(folder_path):
    """Delete all files in the given folder"""
    files = glob.glob(os.path.join(folder_path, "*"))
    for file in files:
        if os.path.isfile(file):
            try:
                os.remove(file)
            except Exception as e:
                print(f"Could not delete {file}: {e}")

def save_chunk_to_wav(chunk, filename):
    filepath = os.path.join(AUDIO_DIR, filename)
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 2 bytes for int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(chunk.tobytes())

def frame_generator(stream):
    """Yields audio frames from the microphone"""
    while True:
        audio, overflow = stream.read(FRAME_SIZE)
        if overflow:
            print("⚠️ Overflow detected")
        yield audio

def vad_collector(stream):
    pre_speech_buffer = collections.deque(maxlen=int(0.3 * 1000 / FRAME_DURATION))  # 300ms pre-roll
    silence_buffer = collections.deque(maxlen=int(0.8 * 1000 / FRAME_DURATION))     # 800ms of silence padding
    voiced_frames = []
    triggered = False

    for frame in frame_generator(stream):
        is_speech = vad.is_speech(frame.tobytes(), SAMPLE_RATE)

        if not triggered:
            pre_speech_buffer.append(frame)
            if is_speech:
                triggered = True
                voiced_frames = list(pre_speech_buffer) + [frame]
                silence_buffer.clear()
        else:
            voiced_frames.append(frame)
            if is_speech:
                silence_buffer.clear()
            else:
                silence_buffer.append(frame)
                if len(silence_buffer) >= silence_buffer.maxlen:
                    # Enough silence -> end speech
                    triggered = False
                    yield np.concatenate(voiced_frames)
                    pre_speech_buffer.clear()
                    silence_buffer.clear()
                    voiced_frames = []


def listen_for_chunk():
    """Start mic and yield chunks of speech"""
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=FRAME_SIZE) as stream:
        print("🎙️ Listening for speech...")
        for chunk in vad_collector(stream):
            yield chunk

def transcribe_simple(audio_path, transcript_index=0):
    TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), "transcript") 
    r = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = r.record(source)
    try:
        text = r.recognize_google(audio)
        # Ensure transcript directory exists
        os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
        output_path = os.path.join(TRANSCRIPT_DIR, f"transcript{transcript_index}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved transcription to {output_path}")
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results; {e}")


def main():
    try:
        delete_all_files(AUDIO_DIR)
        delete_all_files("transcript")

        i = 0
        for chunk in listen_for_chunk():  # make sure this is async iterable or wrap it
            path = f"chunk_{i}.wav"
            filename = os.path.join(AUDIO_DIR, path)
            print(f"🔊 Got chunk of {len(chunk)} samples")
            save_chunk_to_wav(chunk, filename)
            transcribe_simple(filename, i)

    except Exception as e:
        print(f"❌ Error during listening: {e}")

if __name__ == "__main__":
    asyncio.run(main())