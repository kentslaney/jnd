import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer

assert not subprocess.run(
    ["which", "ffmpeg"], stdout=subprocess.DEVNULL).returncode

whisper_normalizer = EnglishTextNormalizer()

class WhisperASR:
    def __init__(self, model="small.en"):
        self.model = whisper.load_model(model)

    def __call__(self, path):
        return self.model.transcribe(path)

# can be overly generous
class PromptedWhisperASR:
    def __init__(self, model="base.en"):
        self.model = whisper.load_model(model)

    def __call__(self, path, answer):
        return self.model.transcribe(path, initial_prompt=answer)

