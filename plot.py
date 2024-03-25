# https://stackoverflow.com/a/50728936/3476782
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

def fig_bytes(fig):
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return output.getvalue()

def scatter_fig(x, y):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.scatter(x, y)
    return fig

def scatter_png(x, y):
    return fig_bytes(scatter_fig(x, y))

# https://github.com/MalcolmSlaney/GoogleSIN/blob/main/google_asr_sin.py
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt

def logistic_curve(x: np.ndarray,
                   a: float, b: float, c:float, d: float) -> float:
  """
  Logistic function with parameters a, b, c, d
  a is the curve's maximum value (top asymptote)
  b is the curve's minimum value (bottom asymptote)
  c is the logistic growth rate or steepness of the curve
  d is the x value of the sigmoid's midpoint
  """
  return ((a-b) / (1 + np.exp(-c * (x - d)))) + b

def psychometric_curve(x, c, d):
  """Like the logistic curve above, but the output is always >= 0.0 and <= 1.0.
  """
  return logistic_curve(x, 1, 0, c, d)

figsize = (6.4, 4.8) # (10, 6)

def logistic_results(spin_snrs, scores):
    # pylint: disable=unbalanced-tuple-unpacking
    logistic_params, _ = curve_fit(psychometric_curve,
                                   spin_snrs,
                                   scores,
                                   ftol=1e-4)
    detailed_snr = np.arange(0, 25, 0.1)
    fig = plt.figure(figsize=figsize)  # reset to default size
    plt.plot(spin_snrs, scores, 'x', label='Experimental Data')
    plt.plot(detailed_snr,
             psychometric_curve(detailed_snr,
                                logistic_params[0],
                                logistic_params[1]),
             label='Logistic Fit')
    plt.plot([0, 25], [0.5, 0.5], '--', label='50% Theshold')
    plt.plot([logistic_params[1], logistic_params[1]], [0, 0.5], ':')
    plt.legend()
    plt.xlabel('SNR (dB)')
    plt.ylabel('Fraction recognized correctly')
    plt.title('Logistic Regression for QuickSIN Data')
    return fig

def logistic_png(x, y):
    return fig_bytes(logistic_results(x, y))

