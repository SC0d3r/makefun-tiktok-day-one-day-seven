"""Beat for Frog Run: a small 120 BPM pond loop with soft fly-catch blips."""

import math
import os
import subprocess
import wave

import numpy as np

SR = 48000
DURATION = 16.5
N = int(round(SR * DURATION))
BEAT = 0.5  # 120 BPM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "beat.wav")

CATCHES = [2.2, 4.6, 5.3, 6.0, 6.7, 7.4, 8.1, 8.8]
BASS_NOTES = [55.0, 55.0, 82.41, 73.42, 55.0, 65.41, 82.41, 49.0]


def add(buf, start, sig, pan=0.0):
    i = int(round(start * SR))
    if i >= N:
        return
    sig = sig[: N - i]
    gl = math.sqrt(0.5 * (1.0 - pan))
    gr = math.sqrt(0.5 * (1.0 + pan))
    buf[0, i:i + len(sig)] += sig * gl
    buf[1, i:i + len(sig)] += sig * gr


def kick(dur=0.24):
    t = np.arange(int(dur * SR)) / SR
    f = 148.0 * np.exp(-t * 22.0) + 46.0
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = np.exp(-t * 26.0)
    click = np.exp(-t * 240.0) * 0.25
    return (np.sin(phase) * env + click) * 0.72


def hat(dur=0.055, open_hat=False):
    rng = np.random.default_rng(4400 if not open_hat else 4401)
    t = np.arange(int(dur * SR)) / SR
    noise = rng.standard_normal(len(t))
    noise = np.diff(noise, prepend=0.0)
    env = np.exp(-t * (58.0 if open_hat else 130.0))
    return noise * env * (0.16 if open_hat else 0.13)


def bass(freq, dur=0.24):
    t = np.arange(int(dur * SR)) / SR
    env = (1.0 - np.exp(-t * 220.0)) * np.exp(-t * 9.0)
    tone = np.sin(2 * np.pi * freq * t)
    tone += 0.32 * np.sin(2 * np.pi * freq * 2 * t)
    tone += 0.12 * np.sin(2 * np.pi * freq * 3 * t)
    return tone * env * 0.30


def blip(freq, dur=0.22):
    t = np.arange(int(dur * SR)) / SR
    env = (1.0 - np.exp(-t * 300.0)) * np.exp(-t * 20.0)
    tone = np.sin(2 * np.pi * freq * t)
    tone += 0.25 * np.sin(2 * np.pi * freq * 2.01 * t)
    return tone * env * 0.17


def main():
    buf = np.zeros((2, N), dtype=np.float64)

    print("beat: 120 BPM, 16.5 s, 48 kHz stereo")
    for bar in range(8):
        bar_t = bar * 2.0
        for beat_i in range(4):
            t = bar_t + beat_i * BEAT
            add(buf, t, kick(), 0.0)
            if beat_i == 2:
                add(buf, t, hat(open_hat=True), 0.2)
            else:
                add(buf, t + 0.25, hat(), -0.25 if beat_i % 2 else 0.25)
                add(buf, t, hat(), 0.15)
            add(buf, t + 0.25, hat(), -0.3)
        for step in range(8):
            freq = BASS_NOTES[(bar * 8 + step) % len(BASS_NOTES)]
            if step == 3:
                freq *= 2.0
            add(buf, bar_t + step * 0.25, bass(freq), -0.05)

    for i, ct in enumerate(CATCHES):
        add(buf, ct, blip(1568.0 if i % 2 else 2093.0), -0.35 + 0.1 * i)

    fade = np.ones(N)
    fi = int(0.04 * SR)
    fade[:fi] = np.linspace(0.0, 1.0, fi)
    fo = int(0.25 * SR)
    fade[-fo:] = np.linspace(1.0, 0.0, fo)
    buf *= fade

    peak = float(np.max(np.abs(buf)))
    print("  raw peak %.4f" % peak)
    target = 0.85
    if peak > 0:
        buf *= target / peak
    buf = np.tanh(buf * 1.05)
    peak = float(np.max(np.abs(buf)))
    if peak > 0:
        buf *= 0.88 / peak
    peak = float(np.max(np.abs(buf)))
    print("  final peak %.4f (limit 0.90)" % peak)

    pcm = np.clip(buf.T * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(OUT, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("  wrote %s (%.2f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
    print("  ffprobe beat.wav")
    subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=codec_name,sample_rate,channels",
        "-of", "default=nw=1", OUT,
    ], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
