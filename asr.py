import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer

assert not subprocess.run(
    ["which", "ffmpeg"], stdout=subprocess.DEVNULL).returncode

whisper_normalizer = EnglishTextNormalizer()

class WhisperASR:
    def __init__(self, model="small.en"):
        self.model = whisper.load_model(model)
        self.meta = {"model_name": model, "model_type": "default"}

    def __call__(self, path):
        res = self.model.transcribe(path, word_timestamps=True)
        return {**res, **self.meta}

# can be overly generous
class PromptedWhisperASR:
    def __init__(self, model="base.en"):
        self.model = whisper.load_model(model)
        self.meta = {"model_name": model, "model_type": "prompted"}

    def __call__(self, path, answer):
        res = self.model.transcribe(
                path, word_timestamps=True, initial_prompt=answer)
        return {**res, **self.meta}

