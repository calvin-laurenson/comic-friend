import json
from typing import Callable
import numpy as np
import speech_recognition as sr
import openai
import pyaudio
import torch
from functools import cache
import sys
import serial
import whisper
whisper_model = whisper.load_model("base")

MODEL = "gpt-3.5-turbo"
p = pyaudio.PyAudio()

CHARACTERS = {
    "hero": (
        "",
        "tamil_female",
    ),
    "sidekick": (
        "",
        "rajasthani_female",
    ),
    "villain": (
        "",
        "tamil_male",
    ),
}

CHARACTER_MAP = {1: "hero", 2: "sidekick", 3: "villain"}

def record_async(sample_rate=16000, chunk_size=1024) -> Callable[[], np.ndarray]:
    """
    This function will start recording audio in a separate thread.
    It uses pyaudio to record audio and returns a numpy array of the audio.
    """
    audio = pyaudio.PyAudio()
    frames = []

    def cb(in_data, frame_count, time_info, status):
        frames.append(np.frombuffer(in_data, dtype=np.int16))
        return (in_data, pyaudio.paContinue)

    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size,
        stream_callback=cb,
    )

    stream.start_stream()

    def stop():
        stream.stop_stream()
        stream.close()
        audio.terminate()
        if frames:
            return np.concatenate(frames)
        else:
            return None

    return stop


class Conversation:
    def __init__(self, system_prompt: str) -> None:
        self.messages = [{"role": "system", "content": system_prompt}]

    def add_message(self, content: str) -> str:
        self.messages.append({"role": "user", "content": content})
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=self.messages,
        )[
            "choices"
        ][0]["message"]
        self.messages.append(response)
        return response["content"]

@cache
def get_tts_model(lang, style):
    tts, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="en",
        speaker="v3_en_indic",
    )
    tts.to("cpu")
    return tts


def text_to_speech(model, text, speaker, sample_rate):
    audio = (
        model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=sample_rate,
        )
        .numpy()
        .tobytes()
    )
    return audio


def say(
    text, lang="en", style="v3_en_indic", speaker="tamil_female", sample_rate=48000
):
    tts = get_tts_model(lang, style)

    audio = text_to_speech(tts, text, speaker, sample_rate)

    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=sample_rate, output=True)

    stream.write(audio)

class PanelManager:
    conversation: Conversation | None = None
    character: int | None = None
    arduino: serial.Serial
    recording: Callable[[], np.ndarray] | None = None
    def __init__(self) -> None:
        self.arduino = serial.Serial("/dev/ttyACM0", 9600)

    def loop(self):
        """
        This function continuously listens for json messages from the arduino
        """
        data: str = self.arduino.readline().decode("utf-8")

        data = json.loads(data)

        button_number: int = data["button"]
        button_state: bool = bool(data["state"])
        
        if button_number in {1, 2, 3}:
            # Button press is for the character change
            self.conversation = Conversation(CHARACTERS[CHARACTER_MAP[button_number]][0])
            self.character = button_number
            print(f"Changed character to {CHARACTER_MAP[button_number]}")
        elif button_number == 4:
            if self.character is None or self.conversation is None:
                print("Character not selected")
                return
            # Button press is for start recording0
            if button_state:
                # Start recording
                self.recording = record_async()
                print("Started recording")
            else:
                print("Stopped recording")
                # Stop recording
                audio = self.recording()
                self.recording = None
                if audio is not None:
                    # Disable buttons
                    self.set_disabled(True)
                    # print(audio)
                    # print(audio.shape)
                    # Recognize audio
                    text: str = whisper_model.transcribe(audio.astype(np.float32) / 32768.0, task="transcribe", language="en")["text"]
                    text = str(text).strip()
                    print(f"Recognized text: {text}")
                    if text == "" or text == "you":
                        self.set_disabled(False)
                        return
                    # Add message to conversation
                    response = self.conversation.add_message(text)
                    print(f"Response: {response}")
                    # Say response
                    say(response, speaker=CHARACTERS[CHARACTER_MAP[self.character]][1])

                    # Enable buttons
                    self.set_disabled(False)
                print("Done")

    def set_disabled(self, disabled: bool):
        """
        Sends a JSON message to the arduino to disable or enable the buttons
        E.g. {"disabled": true}
        """

        self.arduino.write(json.dumps({"disabled": disabled}).encode("utf-8"))




def main():
    # Indian speaker options: "tamil_female", "bengali_female", "malayalam_male", "manipuri_female", "assamese_female", "gujarati_male", "telugu_male", "kannada_male", "hindi_female", "rajasthani_female", "kannada_female", "bengali_male", "tamil_male", "gujarati_female", "assamese_male", "random"

    # Start conversation
    panel_manager = PanelManager()

    while True:
        panel_manager.loop()


if __name__ == "__main__":
    main()
