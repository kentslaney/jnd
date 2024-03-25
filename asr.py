import whisper, subprocess
from whisper.normalizers import EnglishTextNormalizer
from matplotlib import pyplot as plt

assert not subprocess.run(
    ["which", "ffmpeg"], stdout=subprocess.PIPE).returncode

model = whisper.load_model("base.en")
normalizer = EnglishTextNormalizer()

def asr(path):
    return normalizer(model.transcribe(path)["text"])

import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

# https://stackoverflow.com/a/50728936/3476782
def fig_bytes(fig) -> bytes:
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return output.getvalue()

def scatter_fig(x, y):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.scatter(x, y)
    return fig

def results_png(x, y):
    return fig_bytes(scatter_fig(x, y))

