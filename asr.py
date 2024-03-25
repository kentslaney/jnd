import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer

assert not subprocess.run(["which", "ffmpeg"]).returncode

model = whisper.load_model("base.en")
normalizer = EnglishTextNormalizer()

def asr(path):
    return normalizer(model.transcribe(path)["text"])
