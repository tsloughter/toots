#!/usr/bin/env python3
"""Synthesize every sound in the game (pure stdlib, no samples needed).

    python3 tools/make_sounds.py

Writes 16-bit mono WAVs into audio/.
"""
import math
import os
import random
import struct
import wave

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio")


def save(name, samples, sr=SR, peak=0.9):
    m = max(1e-9, max(abs(s) for s in samples))
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s / m * peak)) * 32767)) for s in samples)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data)
    print("wrote %s.wav (%.2fs)" % (name, len(samples) / sr))


def biquad(x, b0, b1, b2, a0, a1, a2):
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, s in enumerate(x):
        v = b0 * s + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, s, y1, v
        y[i] = v
    return y


def lowpass(x, f, q=0.707, sr=SR):
    w = 2 * math.pi * f / sr
    a = math.sin(w) / (2 * q)
    c = math.cos(w)
    return biquad(x, (1 - c) / 2, 1 - c, (1 - c) / 2, 1 + a, -2 * c, 1 - a)


def highpass(x, f, q=0.707, sr=SR):
    w = 2 * math.pi * f / sr
    a = math.sin(w) / (2 * q)
    c = math.cos(w)
    return biquad(x, (1 + c) / 2, -(1 + c), (1 + c) / 2, 1 + a, -2 * c, 1 - a)


def bandpass(x, f, q=1.0, sr=SR):
    w = 2 * math.pi * f / sr
    a = math.sin(w) / (2 * q)
    c = math.cos(w)
    return biquad(x, a, 0, -a, 1 + a, -2 * c, 1 - a)


def env(n, attack, release, sr=SR):
    a, r = int(attack * sr), int(release * sr)
    return [min(1.0, i / max(1, a), (n - i) / max(1, r)) for i in range(n)]


# ---------------------------------------------------------------- the farts
def fart(dur, f0, f1, seed, rasp=0.5, squeak=0.0, sputter=0.08, wobble=0.08):
    """A flappy pulse train: each cycle is one 'flap' (sharp open, soft close),
    with jittery pitch, the odd sputter, and body resonances on top."""
    rng = random.Random(seed)
    n = int(dur * SR)
    out = [0.0] * n
    i = 0
    wob = rng.random() * 6.28
    while i < n:
        u = i / n
        f = f0 + (f1 - f0) * u ** 0.7
        f *= 1 + wobble * math.sin(wob + u * dur * 2 * math.pi * 5.5) + rng.gauss(0, 0.045)
        if squeak and u > 0.78:
            f *= 1 + squeak * ((u - 0.78) / 0.22) ** 2
        period = int(SR / max(28.0, f))
        amp = 1.0 + rng.gauss(0, 0.14)
        if rng.random() < sputter:
            amp *= 0.2
        for k in range(period):
            if i + k >= n:
                break
            x = k / period
            s = math.exp(-x * 7.0) * (1 - math.exp(-x * 60.0))
            s += rasp * (rng.random() * 2 - 1) * math.exp(-x * 4.0) * 0.45
            out[i + k] = amp * s
        i += period
    y = highpass(out, 45)
    lo, b1, b2 = lowpass(y, 1500), bandpass(y, 190, 2.5), bandpass(y, 470, 3.0)
    y = [a + 1.1 * b + 0.6 * c for a, b, c in zip(lo, b1, b2)]
    e = env(n, 0.012, 0.1)
    return [s * g * (0.85 + 0.15 * math.sin(i / SR * 2 * math.pi * 3.1)) for i, (s, g) in enumerate(zip(y, e))]


# ---------------------------------------------------------------- bleeps
def tone(dur, f_from, f_to, shape="sine", attack=0.005, release=0.05, curve=1.0, vib=0.0):
    n = int(dur * SR)
    ph = 0.0
    out = []
    e = env(n, attack, release)
    for i in range(n):
        u = i / n
        f = f_from + (f_to - f_from) * u ** curve
        f *= 1 + vib * math.sin(2 * math.pi * 30 * i / SR)
        ph += f / SR
        x = ph % 1.0
        if shape == "sine":
            s = math.sin(2 * math.pi * x)
        elif shape == "square":
            s = (1.0 if x < 0.5 else -1.0) * 0.6
        elif shape == "saw":
            s = (2 * x - 1) * 0.7
        else:  # triangle
            s = 4 * abs(x - 0.5) - 1
        out.append(s * e[i])
    return out


def decay(x, rate):
    return [s * math.exp(-rate * i / SR) for i, s in enumerate(x)]


def mix(*tracks):
    """tracks: (samples, start_seconds, gain)"""
    n = max(int(t * SR) + len(s) for s, t, g in tracks)
    out = [0.0] * n
    for s, t, g in tracks:
        o = int(t * SR)
        for i, v in enumerate(s):
            out[o + i] += v * g
    return out


def noise(dur, seed=1):
    rng = random.Random(seed)
    return [rng.random() * 2 - 1 for _ in range(int(dur * SR))]


# ---------------------------------------------------------------- music
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(name):
    semis = NOTE[name[0]]
    rest = name[1:]
    if rest[0] == "#":
        semis += 1
        rest = rest[1:]
    return 440.0 * 2 ** ((semis - 9) / 12 + int(rest) - 4)


def pluck(freq, dur, sr, seed, bright=0.5, damp=0.996):
    """Karplus-Strong string: close enough to a banjo for a mountain tune."""
    rng = random.Random(seed)
    n = max(2, int(sr / freq))
    buf = [rng.random() * 2 - 1 for _ in range(n)]
    out = []
    j = 0
    prev = 0.0
    for _ in range(int(dur * sr)):
        v = buf[j]
        nxt = buf[(j + 1) % n]
        buf[j] = damp * (bright * v + (1 - bright) * 0.5 * (v + nxt))
        out.append(v - 0.6 * prev)
        prev = v
        j = (j + 1) % n
    return out


def music():
    sr = 22050
    eighth = 60.0 / 116 / 2
    chords = {
        "G": ["G3", "B3", "D4", "G4", "B4"],
        "C": ["G3", "C4", "E4", "G4", "C5"],
        "Em": ["G3", "B3", "E4", "G4", "B4"],
        "D": ["A3", "D4", "F#4", "A4", "D5"],
    }
    bass = {"G": ("G2", "D3"), "C": ("C3", "G2"), "Em": ("E2", "B2"), "D": ("D3", "A2")}
    bars = ["G", "G", "C", "G", "G", "Em", "D", "G"]
    tune = ["D5 B4 G4 B4", "D5 E5 D5 B4", "E5 G5 E5 C5", "D5 B4 G4 -",
            "B4 D5 G5 D5", "E5 G5 E5 B4", "F#5 E5 D5 A4", "G4 B4 G4 -"]
    roll = [1, 2, 4, 1, 2, 4, 1, 2]
    total = int(len(bars) * 8 * eighth * sr)
    out = [0.0] * total
    seed = 0

    def put(samples, t, gain):
        o = int(t * sr)
        for i, v in enumerate(samples):
            out[(o + i) % total] += v * gain      # wrap the tail so the loop is seamless

    for b, chord in enumerate(bars):
        t0 = b * 8 * eighth
        for e in range(8):
            seed += 1
            put(pluck(hz(chords[chord][roll[e]]), 0.5, sr, seed, bright=0.6, damp=0.992), t0 + e * eighth, 0.32)
        for beat, nm in ((0, bass[chord][0]), (4, bass[chord][1])):
            seed += 1
            put(pluck(hz(nm), 0.9, sr, seed, bright=0.2, damp=0.997), t0 + beat * eighth, 0.75)
        for q, nm in enumerate(tune[b].split()):
            if nm == "-":
                continue
            seed += 1
            put(pluck(hz(nm), 0.8, sr, seed, bright=0.75, damp=0.995), t0 + q * 2 * eighth, 0.6)
    save("music", lowpass(out, 5000, sr=sr), sr=sr, peak=0.8)


def main():
    save("fart_a", fart(1.6, 92, 66, seed=1, rasp=0.5, sputter=0.06))
    save("fart_b", fart(1.6, 118, 78, seed=2, rasp=0.35, squeak=0.5, wobble=0.12))
    save("fart_c", fart(1.6, 74, 52, seed=3, rasp=0.7, sputter=0.12))
    save("toot", fart(0.22, 150, 210, seed=4, rasp=0.2, sputter=0.0, wobble=0.02), peak=0.6)
    save("fart_win", fart(2.4, 130, 48, seed=5, rasp=0.5, squeak=0.9, sputter=0.1, wobble=0.15))

    save("jump", tone(0.17, 280, 640, "triangle", release=0.08, curve=0.7), peak=0.5)
    save("stomp", mix((decay(tone(0.16, 190, 55, "sine", release=0.04), 14), 0, 1.0),
                      (tone(0.09, 950, 520, "square", release=0.04), 0.01, 0.25),
                      (decay(lowpass(noise(0.08), 2500), 40), 0, 0.5)), peak=0.75)
    save("berry", mix((decay(tone(0.09, 1318, 1318, "triangle"), 18), 0, 1.0),
                      (decay(tone(0.22, 1976, 1976, "triangle", release=0.1), 12), 0.07, 1.0)), peak=0.45)
    save("beans", mix((tone(0.12, 330, 160, "sine", release=0.03), 0, 1.0),
                      (tone(0.16, 170, 520, "sine", release=0.05, curve=2.0), 0.11, 1.0),
                      (fart(0.2, 160, 230, seed=9, rasp=0.2, sputter=0.0), 0.26, 0.5)), peak=0.7)
    save("hurt", tone(0.32, 420, 140, "saw", release=0.1, vib=0.08), peak=0.55)
    save("land", decay(lowpass(noise(0.1, 3), 500), 45), peak=0.5)
    save("checkpoint", mix(*[(decay(tone(0.3, hz(n), hz(n), "triangle", release=0.1), 9), i * 0.09, 1.0)
                             for i, n in enumerate(("C5", "E5", "G5", "C6"))]), peak=0.5)
    save("lose", mix(*[(tone(0.26, hz(n), hz(n) * 0.94, "square", release=0.08), i * 0.24, 1.0)
                       for i, n in enumerate(("E4", "C4", "A3", "F3"))]), peak=0.45)
    fan = [("G4", 0.0, 0.16), ("C5", 0.16, 0.16), ("E5", 0.32, 0.16), ("G5", 0.48, 0.34),
           ("E5", 0.84, 0.16), ("G5", 1.0, 0.9)]
    save("win", mix(*([(tone(d + 0.08, hz(n), hz(n), "square", release=0.08), t, 1.0) for n, t, d in fan] +
                      [(tone(d + 0.08, hz(n) / 2, hz(n) / 2, "triangle", release=0.08), t, 0.9) for n, t, d in fan])),
         peak=0.5)
    music()


if __name__ == "__main__":
    main()
