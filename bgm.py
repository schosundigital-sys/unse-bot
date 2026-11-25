"""릴스 배경음 – 코드로 직접 합성하므로 저작권 걱정이 없습니다.

  · 낮은 드론(D·A)   : 은은한 바닥 소리
  · 뜯는 현 소리      : 가야금 느낌의 5음 음계 선율 (날짜마다 다른 선율)
  · 북               : 한 마디에 두 번
  · 풍경(종) 소리     : 순위가 공개되는 순간마다
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 84
# D 단조 5음 음계 (레 파 솔 라 도)
SCALE = [146.83, 174.61, 196.00, 220.00, 261.63, 293.66, 349.23, 392.00, 440.00, 523.25]


def _t(sec: float) -> np.ndarray:
    return np.arange(int(SR * sec)) / SR


def pluck(freq: float, dur: float = 1.6) -> np.ndarray:
    """가야금처럼 튕긴 뒤 살짝 음이 내려앉는 현 소리."""
    t = _t(dur)
    bend = 1 + 0.012 * np.exp(-t * 18)                      # 튕길 때 살짝 높았다가 제자리로
    phase = 2 * np.pi * freq * np.cumsum(bend) / SR
    y = np.zeros_like(t)
    for k, a in ((1, 1.0), (2, 0.5), (3, 0.28), (4, 0.16), (5, 0.08)):
        y += a * np.sin(k * phase) * np.exp(-t * (2.2 + 1.6 * k))
    y *= np.minimum(t / 0.004, 1)
    return y * 0.33


def bell(freq: float = 1318.5, dur: float = 2.4) -> np.ndarray:
    t = _t(dur)
    y = np.zeros_like(t)
    for r, a, dcy in ((1, 1.0, 1.6), (2.76, 0.42, 3.2), (5.40, 0.22, 5.0), (0.5, 0.3, 1.2)):
        y += a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * dcy)
    return y * np.minimum(t / 0.002, 1) * 0.22


def drum(dur: float = 0.7) -> np.ndarray:
    t = _t(dur)
    f = 62 + 70 * np.exp(-t * 28)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    noise = np.random.default_rng(1).normal(0, 1, len(t)) * np.exp(-t * 60) * 0.15
    return (y + noise) * 0.5


def whoosh(dur: float = 0.45) -> np.ndarray:
    t = _t(dur)
    n = np.random.default_rng(3).normal(0, 1, len(t))
    n = np.convolve(n, np.ones(24) / 24, mode="same")      # 부드럽게
    env = np.sin(np.pi * t / dur) ** 2
    return n * env * 0.5


def _add(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    if i >= len(buf):
        return
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def make(path: Path, duration: float, bells: list[float], whooshes: list[float], seed: int = 0) -> Path:
    rng = np.random.default_rng(seed)
    n = int(SR * duration)
    mix = np.zeros(n)

    # 드론
    t = np.arange(n) / SR
    trem = 0.85 + 0.15 * np.sin(2 * np.pi * 0.18 * t)
    mix += (np.sin(2 * np.pi * 73.42 * t) * 0.10 + np.sin(2 * np.pi * 110.0 * t) * 0.06) * trem

    beat = 60 / BPM
    # 북: 마디(4박)의 1, 3박
    k = 0.0
    while k < duration:
        _add(mix, drum(), k, 0.55)
        _add(mix, drum(), k + 2 * beat, 0.35)
        k += 4 * beat

    # 선율: 8분음표 격자에 확률적으로 음을 놓고, 음계 안에서 가까운 음으로 움직임
    idx = 4
    k = 0.0
    step = beat / 2
    while k < duration - 1:
        if rng.random() < 0.55:
            idx = int(np.clip(idx + rng.choice([-2, -1, -1, 1, 1, 2, 0]), 0, len(SCALE) - 1))
            _add(mix, pluck(SCALE[idx]), k, 0.9 if (k / step) % 4 == 0 else 0.6)
        k += step

    for b in bells:
        _add(mix, bell(), b, 1.0)
        _add(mix, bell(1975.5), b + 0.08, 0.5)
    for w in whooshes:
        _add(mix, whoosh(), max(0, w - 0.2), 0.35)

    # 처음·끝 페이드, 정규화
    fade = int(SR * 0.6)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade * 2:] *= np.linspace(1, 0, fade * 2)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.8

    # 아주 살짝 다른 좌우로 스테레오감
    left = mix
    right = np.concatenate([np.zeros(220), mix[:-220]])
    pcm = (np.stack([left, right], axis=1) * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    make(Path("out/bgm_test.wav"), 30, bells=[2.2, 5.6, 9.0], whooshes=[2.2, 5.6, 9.0], seed=5)
    print("out/bgm_test.wav")
