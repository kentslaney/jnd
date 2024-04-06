import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer

assert not subprocess.run(
    ["which", "ffmpeg"], stdout=subprocess.DEVNULL).returncode

whisper_normalizer = EnglishTextNormalizer()

class WhisperASR:
    def __init__(self):
        self.model = whisper.load_model("small.en")

    def __call__(self, path):
        return self.model.transcribe(path)

# can be overly generous
class PromptedWhisperASR:
    def __init__(self):
        self.model = whisper.load_model("base.en")

    def __call__(self, path, answer):
        return self.model.transcribe(path, initial_prompt=answer)

