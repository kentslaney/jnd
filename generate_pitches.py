import os, subprocess, sys
import numpy as np
import scipy.io.wavfile

try:
    proc = subprocess.Popen(("ffmpeg", "-codecs"), stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    subprocess.check_output(("grep", r"\bpcm_s16le\b"), stdin=proc.stdout)
    proc.wait()
except subprocess.CalledProcessError as e:
    raise Exception("missing required audio codec pcm_s16le")
except FileNotFoundError:
    raise Exception("ffmpeg not installed on PATH")

def raised_cosine_mask(signal_length: float,
                       transition_time: float = 0.20,
                       fs: float = 22050) -> np.ndarray:
    """Generate a mask with raised-cosine transitions at the start and end."""
    if 2 * transition_time > signal_length:
        raise ValueError(f'Transition time {transition_time} is bigger than '
                         f'half total time {signal_length}')
    t = np.arange(0, signal_length, 1.0 / fs)
    tt = np.arange(0, transition_time, 1.0 / fs)
    transition = (1 - np.cos(tt / transition_time * np.pi)) / 2
    mask = np.concatenate([transition,
                           np.ones(len(t) - len(tt) - len(tt)),
                           np.flipud(transition)])
    return mask

def generate_trial(f0: float, delta: float,
                   signal_length:float = 1.0, fs = 22050) -> np.ndarray:
    """Generate one A-B trial for a pitch JND experiment."""
    mask = raised_cosine_mask(signal_length, transition_time=0.1, fs=fs)
    t = np.arange(0, signal_length, 1.0 / fs)
    f0 += np.random.randn(1) * delta * f0
    sign = 2 * np.random.randint(2) - 1
    f1 = f0 + sign * delta * f0
    # print(f'f0 {f0[0]}Hz -> {f1[0]}Hz')
    t = np.arange(0, signal_length, 1.0 / fs)
    s0 = mask * np.sin(f0 * 2 * np.pi * t)
    s1 = mask * np.sin(f1 * 2 * np.pi * t)

    signal = np.concatenate((s0, s1))
    return signal, sign

fs = 22050
sounds_per_trial = 2
levels = np.array([16, 8.0, 4.0, 2.0, 1.0, 0.4, 0.2, 0.1]) / 100.0
f0_list = [220, 440, 880, 2760]

# import tempfile
# metadir = basedir = tempfile.mkdtemp()
# print(basedir)
from utils import relpath
metadir, basedir = relpath("metadata"), relpath("static", "pitches")

metadata = 'pitch_jnd_files.csv'
metapath = os.path.join(metadir, metadata)
if os.path.exists(metapath):
    while True:
        ans = input(f'The file "{metadata}" already exists. '
                    "Are you sure you want to overwrite it? [y/N] ")
        if ans.lower() in ('y', 'yes'):
            break
        elif ans.lower() in ('', 'n', 'no'):
            print("No files were generated or changed.")
            exit(1)
        print('Please answer with either "yes" or "no".')

exitcode = 0
with open(metapath, 'w') as fp:
    for f0 in f0_list:
        for i, level in enumerate(levels):
            for t in range(sounds_per_trial):
                signal, sign = generate_trial(f0, level, fs=fs)
                tmpname = f'pitch_jnd_{f0}_{i}_{t}.tmp.wav'
                tmppath = os.path.join(basedir, tmpname)
                scipy.io.wavfile.write(tmppath, fs, signal)

                filename = f'pitch_jnd_{f0}_{i}_{t}.wav'
                path = os.path.join(basedir, filename)
                fp.write(', '.join(map(str, (f0, i, t, filename, sign))) + '\n')
                # wav files written by scipy break web audio playback
                try:
                    subprocess.run(
                        ("ffmpeg", "-i", tmppath, "-f", "wav", "-acodec",
                         "pcm_s16le", "-ar", str(fs), "-ac", "1", path),
                        check=True, stderr=subprocess.DEVNULL)
                    os.remove(tmppath)
                except subprocess.CalledProcessError as e:
                    print(f"Failed to process {tmpname}", file=sys.stderr)
                    exitcode = 1
exit(exitcode)

