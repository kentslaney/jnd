import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer
from matplotlib import pyplot as plt

assert not subprocess.run(
    ["which", "ffmpeg"], stdout=subprocess.PIPE).returncode

model = whisper.load_model("small.en")
normalizer = EnglishTextNormalizer()

def asr(path):
    return model.transcribe(path)["text"]

