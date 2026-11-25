"""릴스 배경음 – 코드로 직접 합성하므로 저작권 걱정이 없습니다.

장면에 맞춰 곡이 바뀝니다.
  훅      : 낮은 드론 + 위로 차오르는 바람 소리(라이저)
  3·2위   : 드럼·베이스·화음이 들어오는 본 그루브 + 가야금 선율 + 공개 순간 풍경 소리
  1위     : 직전 북 롤 → 징 + 반짝이는 종소리, 대금 같은 피리 선율이 겹침
  주의    : 드럼이 빠지고 낮은 쿵 + 어두운 화음
  나머지  : 가벼운 그루브 (셰이커 위주)
  마무리  : 으뜸화음으로 풀리며 종소리
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = BEAT * 4

# 음 높이 (Hz)
N = {"D2": 73.42, "F2": 87.31, "G2": 98.00, "A2": 110.0, "Bb2": 116.54, "C3": 130.81, "D3": 146.83,
     "F3": 174.61, "G3": 196.0, "A3": 220.0, "Bb3": 233.08, "C4": 261.63, "D4": 293.66, "E4": 329.63,
     "F4": 349.23, "G4": 392.0, "A4": 440.0, "C5": 523.25, "D5": 587.33, "F5": 698.46, "G5": 783.99,
     "A5": 880.0}
PENTA = ["D4", "F4", "G4", "A4", "C5", "D5", "F5", "G5", "A5"]
# i – VI – VII – i  (Dm – Bb – C – Dm)
PROG = [("D2", ["D3", "F3", "A3"]), ("Bb2", ["Bb2", "D3", "F3"]), ("C3", ["C3", "E4", "G3"]),
        ("D2", ["D3", "F3", "A3"])]
DARK = [("D2", ["D3", "F3", "A3"]), ("Bb2", ["Bb2", "D3", "F3"])]


def _t(sec: float) -> np.ndarray:
    return np.arange(int(SR * sec)) / SR


def _lp(x: np.ndarray, k: int) -> np.ndarray:
    """간단한 저역 통과(이동평균)."""
    if k <= 1:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


RNG = np.random.default_rng(11)
NOISE = RNG.normal(0, 1, SR * 4)


# ---------------- 악기 ----------------

def pluck(f: float, dur: float = 1.4) -> np.ndarray:
    """가야금: 튕긴 뒤 살짝 음이 내려앉고, 끝에 농현(떨림)."""
    t = _t(dur)
    bend = 1 + 0.015 * np.exp(-t * 20) + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t - 0.35, 0, 1)
    ph = 2 * np.pi * f * np.cumsum(bend) / SR
    y = sum(a * np.sin(k * ph) * np.exp(-t * (2.5 + 1.8 * k))
            for k, a in ((1, 1.0), (2, 0.55), (3, 0.32), (4, 0.18), (5, 0.1), (6, 0.05)))
    return y * np.minimum(t / 0.003, 1) * 0.30


def flute(f: float, dur: float) -> np.ndarray:
    """대금 느낌: 부드럽게 들어오는 숨소리 섞인 사인 + 비브라토."""
    t = _t(dur)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.4, 0, 1)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    y = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    breath = _lp(NOISE[:len(t)], 6) * 0.18
    env = np.minimum(t / 0.12, 1) * np.minimum((dur - t) / 0.25, 1).clip(0, 1)
    return (y + breath) * env * 0.16


def pad(notes: list[str], dur: float, dark: bool = False) -> np.ndarray:
    t = _t(dur)
    y = np.zeros_like(t)
    for n in notes:
        f = N[n]
        for det in (-0.35, 0.0, 0.35):  # 살짝 어긋난 3겹 → 풍성하게
            ph = 2 * np.pi * (f + det) * t
            y += np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    env = np.minimum(t / 0.35, 1) * np.minimum((dur - t) / 0.4, 1).clip(0, 1)
    return y * env * (0.020 if not dark else 0.026)


def bass(f: float, dur: float = 0.45) -> np.ndarray:
    t = _t(dur)
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return y * np.exp(-t * 4.5) * np.minimum(t / 0.004, 1) * 0.42


def kick(dur: float = 0.5) -> np.ndarray:
    t = _t(dur)
    f = 52 + 95 * np.exp(-t * 32)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)
    return (y + NOISE[:len(t)] * np.exp(-t * 90) * 0.12) * 0.75


def tak(dur: float = 0.18) -> np.ndarray:
    """장구 '덕' 같은 짧고 마른 소리."""
    t = _t(dur)
    n = np.diff(NOISE[:len(t) + 1]) * 0.5
    tone = np.sin(2 * np.pi * 380 * t) * 0.6
    return (n * np.exp(-t * 45) + tone * np.exp(-t * 30)) * 0.32


def shaker(dur: float = 0.09) -> np.ndarray:
    t = _t(dur)
    n = np.diff(NOISE[1000:1000 + len(t) + 1])
    return n * np.exp(-t * 70) * 0.10


def bell(f: float = 1318.5, dur: float = 2.6) -> np.ndarray:
    t = _t(dur)
    y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d)
            for r, a, d in ((1, 1.0, 1.4), (2.76, 0.42, 3.0), (5.40, 0.2, 5.0), (0.5, 0.3, 1.0)))
    return y * np.minimum(t / 0.002, 1) * 0.20


def gong(dur: float = 4.0) -> np.ndarray:
    """징: 낮게 웅- 하고 오래 울림."""
    t = _t(dur)
    f0 = 98 * (1 - 0.03 * np.exp(-t * 2))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    y = sum(a * np.sin(r * ph) for r, a in ((1, 1), (1.47, 0.5), (2.09, 0.4), (2.56, 0.25), (3.1, 0.15)))
    swell = np.minimum(t / 0.05, 1) * np.exp(-t * 0.9) * (1 + 0.2 * np.sin(2 * np.pi * 3 * t))
    return y * swell * 0.30


def boom(dur: float = 2.0) -> np.ndarray:
    t = _t(dur)
    f = 40 + 60 * np.exp(-t * 6)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2) * 0.9


def riser(dur: float) -> np.ndarray:
    t = _t(dur)
    k = np.linspace(40, 2, len(t)).astype(int)
    n = NOISE[:len(t)].copy()
    out = np.empty_like(n)
    for i in range(0, len(n), 2048):  # 점점 밝아지는 바람 소리
        out[i:i + 2048] = _lp(n[i:i + 2048], int(k[i]))
    sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(200, 900, len(t))) / SR) * 0.15
    return (out * 2.2 + sweep) * (t / dur) ** 2 * 0.35


def roll(dur: float = 1.2) -> np.ndarray:
    """북 롤: 점점 빨라지고 커지는 연타."""
    out = np.zeros(int(SR * dur))
    t, gap = 0.0, 0.16
    while t < dur - 0.05:
        k = kick(0.25) * 0.5 * (0.4 + 0.6 * t / dur)
        i = int(t * SR)
        out[i:i + len(k)] += k[:len(out) - i]
        t += gap
        gap = max(0.045, gap * 0.86)
    return out


def whoosh(dur: float = 0.4) -> np.ndarray:
    t = _t(dur)
    n = _lp(NOISE[5000:5000 + len(t)], 10)
    return n * np.sin(np.pi * t / dur) ** 2 * 0.5


# ---------------- 편곡 ----------------

def _add(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= len(buf):
        return
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def _motif(rng, length: int = 8) -> list[int | None]:
    """8분음표 8개짜리 짧은 선율 동기 (None = 쉼표)."""
    idx, out = 3, []
    for k in range(length):
        if k in (0, 3, 4) or rng.random() < 0.55:
            idx = int(np.clip(idx + rng.choice([-2, -1, 1, 1, 2, -1]), 0, len(PENTA) - 1))
            out.append(idx)
        else:
            out.append(None)
    return out


def make(path: Path, duration: float, sections: list[tuple[float, str]], seed: int = 0) -> Path:
    """sections: [(시작초, 종류)] 종류 = hook | rank3 | rank2 | rank1 | warn | rest | outro"""
    rng = np.random.default_rng(seed)
    n = int(SR * (duration + 0.5))
    drums, music, fx = np.zeros(n), np.zeros(n), np.zeros(n)
    bounds = sections + [(duration, "end")]

    def kind_at(t: float) -> str:
        k = "hook"
        for s, kd in sections:
            if s <= t + 1e-6:
                k = kd
        return k

    groove_from = next((s for s, k in sections if k != "hook"), 2.6)
    motif_a, motif_b = _motif(rng), _motif(rng)

    # 화음·베이스: 본 그루브 시작 시점부터 마디 단위
    t, bar_i = groove_from, 0
    _add(music, pad(PROG[0][1], groove_from + 0.3), 0, 0.6)          # 훅 동안 옅은 화음
    _add(music, pad(["D2", "A2"], groove_from + 0.3), 0, 0.9)
    while t < duration:
        kd = kind_at(t + 0.01)
        chords = DARK if kd == "warn" else PROG
        root, notes = chords[bar_i % len(chords)]
        _add(music, pad(notes, BAR + 0.3, dark=kd == "warn"), t, 1.0)
        if kd not in ("warn", "outro"):
            for b, g in ((0, 1.0), (1.5, 0.7), (2, 0.9), (3.5, 0.6)):  # 쿵-따-쿵 싱코페이션
                _add(music, bass(N[root] * (2 if b == 3.5 else 1)), t + b * BEAT, g)
        elif kd == "warn":
            _add(music, bass(N[root], 1.6), t, 1.0)
        t += BAR
        bar_i += 1

    # 드럼
    t = groove_from
    step = BEAT / 4
    i = 0
    while t < duration:
        kd = kind_at(t + 0.001)
        pos = i % 16
        if kd in ("rank3", "rank2", "rank1"):
            if pos in (0, 8, 10):
                _add(drums, kick(), t, 1.0)
            if pos in (4, 12):
                _add(drums, tak(), t, 1.0)
            if pos in (7, 15) and rng.random() < 0.6:
                _add(drums, tak(), t, 0.45)
            if pos % 2 == 0:
                _add(drums, shaker(), t, 1.0 if pos % 4 == 2 else 0.6)
        elif kd == "rest":
            if pos in (0, 8):
                _add(drums, kick(), t, 0.7)
            if pos in (4, 12):
                _add(drums, tak(), t, 0.6)
            if pos % 2 == 0:
                _add(drums, shaker(), t, 0.8)
        elif kd == "warn":
            if pos == 0:
                _add(drums, kick(), t, 0.5)
        t += step
        i += 1

    # 선율: 가야금 동기 반복 (A A B A), 1위·마무리에서 대금 겹침
    t, k = groove_from, 0
    while t < duration - 0.8:
        kd = kind_at(t + 0.001)
        bar_no = int((t - groove_from) / BAR)
        motif = motif_b if bar_no % 4 == 2 else motif_a
        idx = motif[k % 8]
        if idx is not None and kd not in ("warn",):
            off = -2 if kd == "rest" else 0
            note = PENTA[int(np.clip(idx + off, 0, len(PENTA) - 1))]
            _add(music, pluck(N[note]), t, 0.9 if k % 8 == 0 else 0.65)
        elif idx is not None and kd == "warn" and k % 4 == 0:
            _add(music, pluck(N[PENTA[max(0, idx - 3)]] / 2, 2.0), t, 0.7)
        t += BEAT / 2
        k += 1

    # 장면 전환 효과음
    for s, kd in sections:
        if kd == "hook":
            _add(fx, riser(groove_from), 0, 1.0)
            _add(fx, kick(), 0, 1.0)                       # 첫 1초부터 귀를 잡는 시작음
            _add(fx, bell(1567.98, 2.0), 0.01, 0.8)
            for j, nm in enumerate(("D4", "F4", "A4", "D5", "F5")):  # 가야금 쓸어내리기
                _add(music, pluck(N[nm]), 0.05 + j * 0.09, 0.8)
            for j in range(4):                              # 훅 끝 '둥-둥-둥-둥' 예고
                _add(drums, kick(0.3), groove_from - BEAT * (4 - j) / 2, 0.35 + 0.15 * j)
            continue
        _add(fx, whoosh(), s - 0.25, 0.4)
        if kd in ("rank3", "rank2"):
            _add(fx, bell(), s + 0.05, 1.0)
            _add(fx, bell(1975.5), s + 0.13, 0.45)
        elif kd == "rank1":
            _add(fx, roll(1.1), s - 1.1, 1.0)
            _add(fx, gong(), s, 0.9)
            for j, f in enumerate((1318.5, 1567.98, 1975.5, 2637.0)):  # 반짝 상승 종
                _add(fx, bell(f, 1.8), s + 0.06 + j * 0.07, 0.55)
            for j, nm in enumerate(("A4", "C5", "D5")):
                _add(music, flute(N[nm], BEAT * (2 if j < 2 else 4)), s + 0.3 + j * BEAT * 2, 1.0)
        elif kd == "warn":
            _add(fx, boom(), s, 1.0)
        elif kd == "outro":
            _add(music, pad(["D3", "F3", "A3", "D4"], 3.5), s, 1.2)
            _add(music, flute(N["D5"], 2.4), s + 0.2, 0.9)
            _add(fx, bell(1174.66, 3.0), s + 0.1, 0.9)
            _add(fx, kick(), s, 0.8)

    # 킥이 칠 때 화음을 살짝 눌러 리듬감 (사이드체인)
    env = _lp(np.abs(drums), 900)
    duck = 1 - np.clip(env * 2.2, 0, 0.35)
    mix = music * duck + drums * 0.9 + fx * 0.85

    mix = mix[:int(SR * duration)]
    fade_in, fade_out = int(SR * 0.05), int(SR * 1.2)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    mix = np.tanh(mix / (np.max(np.abs(mix)) + 1e-9) * 1.6) / np.tanh(1.6) * 0.92  # 부드러운 리미터

    left = mix
    right = np.concatenate([np.zeros(180), mix[:-180]])  # 살짝 넓은 스테레오
    pcm = (np.stack([left, right], axis=1) * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    secs = [(0, "hook"), (2.6, "rank3"), (6.0, "rank2"), (9.4, "rank1"), (12.8, "warn"),
            (16.0, "rest"), (26.4, "outro")]
    make(Path("out/bgm_test.wav"), 29.4, secs, seed=5)
    print("out/bgm_test.wav")
