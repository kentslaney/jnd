import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer
from matplotlib import pyplot as plt

assert not subprocess.run(
    ["which", "ffmpeg"], stdout=subprocess.PIPE).returncode

model = whisper.load_model("base.en")
normalizer = EnglishTextNormalizer()

def asr(path):
    return normalizer(model.transcribe(path)["text"])

