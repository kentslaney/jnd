# https://stackoverflow.com/a/50728936/3476782
import io, functools
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

def fig_png(f):
    def decorator(*a, **kw):
        fig = f(*a, **kw)
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        return output.getvalue()
    return functools.wraps(f)(decorator)

def quick_labeled(fig, axis):
    axis.legend()
    axis.set_xlabel('SNR (dB)')
    axis.set_ylabel('Fraction recognized correctly')
    fig.suptitle('Logistic Regression for QuickSIN Data')
    return fig

@fig_png
def scatter_results(x, y):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.scatter(x, y, marker='x', label='Experimental Data')
    return quick_labeled(fig, axis)

# https://github.com/MalcolmSlaney/GoogleSIN/blob/main/google_asr_sin.py
import numpy as np
from scipy.optimize import curve_fit

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

@fig_png
def logistic_results(spin_snrs, scores):
    # pylint: disable=unbalanced-tuple-unpacking
    logistic_params, _ = curve_fit(
            psychometric_curve, spin_snrs, scores, ftol=1e-4)
    detailed_snr = np.arange(0, 25, 0.1)
    fig = Figure(figsize=figsize)  # reset to default size
    axis = fig.add_subplot(1, 1, 1)
    axis.plot(spin_snrs, scores, 'x', label='Experimental Data')
    axis.plot(detailed_snr,
        psychometric_curve(
            detailed_snr, logistic_params[0], logistic_params[1]),
        label='Logistic Fit')
    axis.plot([0, 25], [0.5, 0.5], '--', label='50% Theshold')
    axis.plot([logistic_params[1], logistic_params[1]], [0, 0.5], ':')
    return quick_labeled(fig, axis)

