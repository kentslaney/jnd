from typing import Union

import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer

assert not subprocess.run(
    ["which", "ffmpeg"], stdout=subprocess.DEVNULL).returncode

# Whisper documentation at https://github.com/openai/whisper

whisper_normalizer = EnglishTextNormalizer()

class WhisperASR:
    def __init__(self, model_name="small.en"):
        self.model = whisper.load_model(model_name)
        self.meta = {"model_name": model_name, "model_type": "default"}

    def __call__(self, audio_path):
        res = self.model.transcribe(audio_path, word_timestamps=True)
        return {**res, **self.meta}

# can be overly generous
class PromptedWhisperASR:
    def __init__(self, model_name="base.en"):
        self.model = whisper.load_model(model_name)
        self.meta = {"model_name": model_name, "model_type": "prompted"}

    def __call__(self, audio_path, answer):
        res = self.model.transcribe(
                audio_path, word_timestamps=True, initial_prompt=answer)
        return {**res, **self.meta}


WhisperASREngine = Union[WhisperASR, PromptedWhisperASR]
