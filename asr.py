import whisper
from whisper.normalizers import EnglishTextNormalizer

model = whisper.load_model("base.en")
normalizer = EnglishTextNormalizer()

def asr(path):
    return normalizer(model.transcribe(path)["text"])
