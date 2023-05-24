import speech_recognition as sr
import openai
import pyaudio
import torch
from functools import cache
import sys
MODEL = "gpt-3.5-turbo"
p = pyaudio.PyAudio()

SYSTEM_PROMPTS = {
    "hero": "",
    "sidekick": "",
    "villain": "",
}

class Conversation:
    
    def __init__(self, system_prompt: str) -> None:
        self.messages = [
            {"role": "system", "content": system_prompt}
        ]

    def add_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=self.messages,
        )["choices"][0]["message"]
        self.messages.append(response)
        return response["content"]
        


def recognize_audio(index, model={}, energy=800, pause=0.8, dynamic_energy=True) -> str:
    r = sr.Recognizer()
    r.whisper_model = model
    r.energy_threshold = energy
    r.pause_threshold = pause
    r.non_speaking_duration = 0.2
    if dynamic_energy:
        r.dynamic_energy_threshold = True
    with sr.Microphone(index) as source:
        print("Say something!")
        audio = r.listen(source)
    print("Got it! Now to recognize it...")
    return r.recognize_whisper(audio)

@cache
def get_tts_model(lang, style):
    tts, _ = torch.hub.load(repo_or_dir="snakers4/silero-models",
                                     model="silero_tts",
                                     language="en",
                                     speaker="v3_en_indic")
    tts.to("cpu")
    return tts

def text_to_speech(model, text, speaker, sample_rate):
    audio = model.apply_tts(
        text=text,
        speaker=speaker,
        sample_rate=sample_rate,
    ).numpy().tobytes()
    return audio

def say(text, lang="en", style="v3_en_indic", speaker="tamil_female", sample_rate=48000):
    tts = get_tts_model(lang, style)
    
    audio = text_to_speech(tts, text, speaker, sample_rate)

    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=sample_rate,
                    output=True)
    
    stream.write(audio)

def main():
    # Indian speaker options: 'tamil_female', 'bengali_female', 'malayalam_male', 'manipuri_female', 'assamese_female', 'gujarati_male', 'telugu_male', 'kannada_male', 'hindi_female', 'rajasthani_female', 'kannada_female', 'bengali_male', 'tamil_male', 'gujarati_female', 'assamese_male', 'random'
    conversation = Conversation(SYSTEM_PROMPTS[sys.argv[1]])
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print("Microphone with name \"{1}\" found for `Microphone(device_index={0})`".format(index, name))
    # microphone_index = int(input("Enter microphone index: "))
    input()
    while True:
        input_text = recognize_audio(0, energy=500, pause=0.3).strip()
        if input_text == "":
            print("No input")
            continue
        print(input_text)
        response = conversation.add_message(input_text)
        print(response)
        
        
        say(response)
        input()
    


if __name__ == "__main__":
    main()
