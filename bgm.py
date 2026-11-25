"""릴스 배경음 – 코드로 직접 합성하므로 저작권 걱정이 없습니다.

스타일 (reel.py 의 BGM_STYLE 로 선택)
  trap : 요즘 릴스에서 많이 쓰는 다크 팝-트랩. 808 베이스, 빠른 하이햇 롤, 클랩, 신스 플럭
  lofi : 로파이 힙합. 재즈 코드 일렉피아노, 느슨한 스윙 비트, LP 잡음 (강조 효과음 없음, 기본)

장면에 맞춰 곡이 움직입니다.
  훅     : 필터로 막힌 코드 + 차오르는 라이저 → 드롭
  3·2위  : 비트 전체 + 공개 순간 반짝 효과음
  1위    : 직전 스네어 빌드업 → 임팩트, 리드 신스가 겹침
  주의   : 소리가 먹먹해지고(로우패스) 808만 낮게
  나머지 : 리드 없이 가벼운 비트
  마무리 : 코드 한 번 치고 리버브로 사라짐
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
RNG = np.random.default_rng(11)
NOISE = RNG.normal(0, 1, SR * 6)


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _t(sec: float) -> np.ndarray:
    return np.arange(max(1, int(SR * sec))) / SR


def _lp(x: np.ndarray, k: int) -> np.ndarray:
    if k <= 1:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


def _hp(x: np.ndarray, k: int = 8) -> np.ndarray:
    return x - _lp(x, k)


def _add(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= len(buf) or len(sig) == 0:
        return
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


# ---------------- 드럼 ----------------

def kick(punch: float = 1.0) -> np.ndarray:
    t = _t(0.45)
    f = 48 + 140 * np.exp(-t * 38)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    click = _hp(NOISE[:len(t)], 4) * np.exp(-t * 400) * 0.5
    return np.tanh((y + click) * 1.6 * punch) * 0.62


def clap() -> np.ndarray:
    t = _t(0.3)
    n = _hp(_lp(NOISE[2000:2000 + len(t)], 3), 12)
    env = np.zeros_like(t)
    for d in (0.0, 0.011, 0.022):  # 손뼉 여러 번 겹친 느낌
        env += np.where(t >= d, np.exp(-(t - d) * 60), 0)
    env += np.exp(-t * 14) * 0.35
    return n * env * 0.55


def snare() -> np.ndarray:
    t = _t(0.25)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    n = _hp(NOISE[3000:3000 + len(t)], 6) * np.exp(-t * 22)
    return (tone * 0.5 + n * 0.6) * 0.6


def hat(open_: bool = False) -> np.ndarray:
    t = _t(0.25 if open_ else 0.05)
    n = _hp(_hp(NOISE[4000:4000 + len(t)], 3), 3)
    return n * np.exp(-t * (14 if open_ else 110)) * 0.22


def b808(midi: float, dur: float, glide_from: float | None = None) -> np.ndarray:
    t = _t(dur)
    f = np.full_like(t, hz(midi))
    if glide_from is not None:
        f = hz(midi) + (hz(glide_from) - hz(midi)) * np.exp(-t * 18)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = np.minimum(t / 0.005, 1) * np.exp(-t * 1.1) * np.minimum((dur - t) / 0.04, 1).clip(0, 1)
    y = y + 0.35 * np.sin(2 * np.pi * 2 * np.cumsum(f) / SR)   # 휴대폰 스피커에서도 들리게 2배음
    return np.tanh(y * 2.6) * env * 0.36


# ---------------- 신스·피아노 ----------------

def supersaw(midi: float, dur: float) -> np.ndarray:
    """요즘 팝의 넓은 패드: 살짝 어긋난 톱니파 5겹 (배음 제한)."""
    t = _t(dur)
    y = np.zeros_like(t)
    f0 = hz(midi)
    for det in (-0.12, -0.05, 0.0, 0.05, 0.12):
        f = f0 * 2 ** (det / 12)
        ph = 2 * np.pi * f * t + RNG.uniform(0, 6.28)
        for k in range(1, 9):
            y += np.sin(k * ph) / k
    env = np.minimum(t / 0.08, 1) * np.minimum((dur - t) / 0.15, 1).clip(0, 1)
    return y * env * 0.017


def pluck_synth(midi: float, dur: float = 0.6) -> np.ndarray:
    """신스 플럭: 처음엔 밝고 빠르게 어두워짐."""
    t = _t(dur)
    ph = 2 * np.pi * hz(midi) * t
    y = sum(np.sin(k * ph) / k * np.exp(-t * (6 + 5 * k)) for k in range(1, 12))
    return y * np.minimum(t / 0.002, 1) * 0.22


def epiano(midi: float, dur: float) -> np.ndarray:
    """로파이 일렉피아노(로즈 느낌): FM으로 종소리 섞인 부드러운 음."""
    t = _t(dur)
    ph = 2 * np.pi * hz(midi) * t
    y = np.sin(ph + 1.2 * np.exp(-t * 3) * np.sin(ph)) + 0.2 * np.sin(2 * ph) * np.exp(-t * 2)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    env = np.minimum(t / 0.004, 1) * np.exp(-t * 0.9) * np.minimum((dur - t) / 0.1, 1).clip(0, 1)
    return y * trem * env * 0.09


def sparkle(base_midi: float = 84) -> np.ndarray:
    """순위 공개 순간 '띠리링' 반짝음."""
    out = np.zeros(int(SR * 1.2))
    for j, iv in enumerate((0, 7, 12, 16, 19)):
        t = _t(0.9)
        s = np.sin(2 * np.pi * hz(base_midi + iv) * t) * np.exp(-t * 5)
        _add(out, s, j * 0.045, 0.16)
    return out


def swoosh(dur: float = 0.45, rev: bool = False) -> np.ndarray:
    t = _t(dur)
    n = _hp(NOISE[5000:5000 + len(t)], 4)
    env = (t / dur) ** 2.5 if rev else np.sin(np.pi * t / dur) ** 2
    return n * env * 0.5


def riser(dur: float) -> np.ndarray:
    t = _t(dur)
    out = np.empty_like(t)
    n = NOISE[:len(t)]
    ks = np.linspace(48, 2, len(t)).astype(int)
    for i in range(0, len(n), 2048):
        out[i:i + 2048] = _lp(n[i:i + 2048], int(ks[i]))
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(220, 1400, len(t))) / SR) * 0.12
    return (out * 2.0 + tone) * (t / dur) ** 2.2 * 0.4


def impact() -> np.ndarray:
    t = _t(2.2)
    sub = np.sin(2 * np.pi * np.cumsum(35 + 80 * np.exp(-t * 9)) / SR) * np.exp(-t * 2.5)
    n = _lp(NOISE[:len(t)], 3) * np.exp(-t * 6) * 0.3
    return np.tanh((sub + n) * 1.5) * 0.8


def crackle(n: int) -> np.ndarray:
    """LP 판 잡음."""
    hiss = _hp(NOISE[:n] if n <= len(NOISE) else np.resize(NOISE, n), 3) * 0.006
    pops = np.zeros(n)
    idx = RNG.integers(0, n, n // 2500)
    pops[idx] = RNG.uniform(-0.25, 0.25, len(idx))
    return hiss + _lp(pops, 2)


def reverb(x: np.ndarray, sec: float = 1.6, wet: float = 0.25) -> np.ndarray:
    t = _t(sec)
    ir = NOISE[:len(t)] * np.exp(-t * (6.9 / sec))
    ir = _lp(ir, 4)
    ir /= np.sqrt((ir ** 2).sum())
    n = len(x) + len(ir)
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
    return x + y * wet


def _scene_fx(fx: np.ndarray, sections, drop: float, style: str) -> None:
    """장면 강조 효과음 (라이저·임팩트·반짝음·빌드업)."""
    _add(fx, riser(drop), 0, 1.0)
    _add(fx, kick(1.2), 0, 0.9)                       # 첫 프레임부터 '쿵'
    _add(fx, sparkle(79), 0.02, 1.0)
    for s, kd in sections:
        if kd == "hook":
            continue
        _add(fx, swoosh(0.4, rev=True), s - 0.4, 0.5)
        if kd in ("rank3", "rank2"):
            _add(fx, sparkle(84 if kd == "rank3" else 86), s + 0.04, 1.0)
        if kd == "rank3":
            _add(fx, impact(), s, 0.8)                    # 첫 드롭
        if kd == "rank1":
            # 직전 스네어 빌드업 (점점 빨라짐)
            tt, g = s - 1.2, 0.15
            while tt < s - 0.03:
                _add(fx, snare() if style == "lofi" else clap(), tt, 0.25 + 0.5 * (1 - (s - tt) / 1.2))
                tt += g
                g = max(0.04, g * 0.8)
            _add(fx, impact(), s, 1.0)
            _add(fx, sparkle(88), s + 0.04, 1.3)
        if kd == "warn":
            _add(fx, impact(), s, 0.7)
        if kd == "outro":
            _add(fx, sparkle(81), s + 0.05, 1.0)


# ---------------- 곡 구성 ----------------

STYLES = {
    # 마디별 코드 (MIDI)와 808 근음
    "trap": dict(bpm=140, half=True, swing=0.0,
                 prog=[([57, 60, 64], 45), ([53, 57, 60], 41), ([48, 52, 55], 36), ([55, 59, 62], 43)],
                 dark=[([57, 60, 63], 45), ([53, 56, 60], 41)],
                 lead=[69, 72, 74, 76, 79, 81, 84]),
    "lofi": dict(bpm=84, half=False, swing=0.18, fx=False,   # 강조 효과음 없이 부드럽게
                 prog=[([53, 57, 60, 64], 41), ([52, 55, 59, 62], 40), ([50, 53, 57, 60, 64], 38),
                       ([48, 52, 55, 59], 36)],
                 dark=[([50, 53, 56, 60], 38), ([49, 52, 56, 59], 37)],
                 lead=[72, 74, 76, 79, 81, 84]),
}


def make(path: Path, duration: float, sections: list[tuple[float, str]], seed: int = 0,
         style: str = "trap") -> Path:
    S = STYLES[style]
    rng = np.random.default_rng(seed)
    beat = 60 / S["bpm"]
    bar = beat * 4 * (2 if S["half"] else 1)          # 트랩은 반박자 느낌(하프타임)으로 2배 길게
    step = beat / 4                                     # 16분음표
    n = int(SR * (duration + 0.5))
    drums, music, lead, fx = (np.zeros(n) for _ in range(4))

    def kind_at(t: float) -> str:
        k = "hook"
        for s, kd in sections:
            if s <= t + 1e-6:
                k = kd
        return k

    drop = next((s for s, k in sections if k != "hook"), 2.6)
    starts = {kd: s for s, kd in sections}

    # 코드 + 808 (드롭 시점 기준 마디 정렬)
    t0 = drop - np.ceil(drop / bar) * bar
    t, i = t0, 0
    while t < duration:
        kd = kind_at(max(t, 0) + 0.01)
        prog = S["dark"] if kd == "warn" else S["prog"]
        notes, root = prog[i % len(prog)]
        if style == "trap":
            for m in notes:
                _add(music, supersaw(m, bar + 0.1), t, 1.0)
                _add(music, supersaw(m + 12, bar + 0.1), t, 0.35)
        else:
            for j, m in enumerate(notes):  # 살짝 흘려 치는 코드
                _add(music, epiano(m, bar * 0.98), t + j * 0.018, 1.0)
            _add(music, epiano(notes[0] + 12, beat * 1.5), t + beat * 2.5, 0.6)
        if t >= drop - 0.01 and kd != "outro":
            if style == "trap":
                _add(music, b808(root, bar * 0.55), t, 1.0)
                _add(music, b808(root, bar * 0.4, glide_from=root + 5), t + bar * 0.625, 0.9)
            else:
                _add(music, b808(root, beat * 1.8), t, 0.7)
                _add(music, b808(root + 7, beat * 0.9), t + beat * 2.5, 0.5)
        t += bar
        i += 1

    # 드럼 (16분음표 격자)
    t, k = drop, 0
    sw = S["swing"] * step
    while t < duration:
        kd = kind_at(t + 0.001)
        pos = k % (32 if S["half"] else 16)
        tt = t + (sw if k % 2 else 0)
        full = kd in ("rank3", "rank2", "rank1")
        light = kd == "rest"
        if style == "trap":
            if kd != "warn" and kd != "outro":
                if pos in (0, 10, 19) or (full and pos == 22):
                    _add(drums, kick(), tt, 1.0)
                if pos in (8, 24):
                    _add(drums, clap(), tt, 1.0)
                # 하이햇: 8분 기본 + 1위에서 32분 롤
                if pos % 2 == 0 or (full and pos in (13, 29)):
                    _add(drums, hat(), tt, 0.9 if pos % 4 == 0 else 0.6)
                if kd == "rank1" and pos in (28, 29, 30, 31):
                    for r in range(2):
                        _add(drums, hat(), tt + r * step / 2, 0.5)
                if full and pos == 30:
                    _add(drums, hat(True), tt, 0.6)
            elif kd == "warn" and pos == 0:
                _add(drums, kick(0.7), tt, 0.7)
        else:  # lofi
            if kd not in ("warn", "outro"):
                if pos in (0, 7, 10):
                    _add(drums, kick(0.8), tt, 0.85)
                if pos in (4, 12):
                    _add(drums, snare(), tt, 0.9)
                if pos % 2 == 0:
                    _add(drums, hat(), tt, 0.55 if light else 0.7)
            elif kd == "warn" and pos == 0:
                _add(drums, kick(0.6), tt, 0.6)
        t += step
        k += 1

    # 리드: 짧은 동기 반복 (순위 구간), 1위에서 한 옥타브 위 겹침
    motif = [rng.choice(len(S["lead"])) if (j in (0, 3, 6) or rng.random() < 0.4) else None for j in range(8)]
    t, k = drop, 0
    while t < duration - 1:
        kd = kind_at(t + 0.001)
        idx = motif[k % 8]
        if idx is not None and kd in ("rank3", "rank2", "rank1"):
            m = S["lead"][idx]
            fn = pluck_synth if style == "trap" else epiano
            _add(lead, fn(m, 0.5) if style == "trap" else fn(m, 0.6), t + (sw if k % 2 else 0), 1.0 if style == "trap" else 1.6)
            if kd == "rank1":
                _add(lead, fn(m + 12, 0.4), t, 0.45)
        t += beat / 2
        k += 1

    # 장면 효과음 (lofi는 사용 안 함)
    if S.get("fx", True):
        _scene_fx(fx, sections, drop, style)

    # 훅·주의 구간은 먹먹하게 (로우패스)
    muffled = _lp(music, 28)
    mask = np.zeros(n)
    for s, kd in sections:
        if kd in ("hook", "warn"):
            e = next((x for x, _ in sections if x > s), duration)
            a, b = int(s * SR), int(e * SR)
            mask[a:b] = 1
    mask = _lp(mask, int(SR * (0.15 if S.get("fx", True) else 0.8)))  # lofi는 천천히 열림
    music = music * (1 - mask) + muffled * mask * 1.3

    # 킥에 맞춰 패드가 출렁이는 사이드체인
    kenv = _lp(np.abs(drums), 1500)
    pump = 1 - np.clip(kenv * 3.0, 0, 0.5)
    bus = reverb(music * pump + lead * 1.25, 1.8, 0.28)
    mix = bus + drums * 0.95 + reverb(fx, 1.2, 0.2) * 0.9
    if style == "lofi":
        mix = _lp(mix, 2) + crackle(n) * 1.0         # 살짝 둥근 소리 + LP 잡음

    mix = mix[:int(SR * duration)]
    if not S.get("fx", True):
        fi = int(SR * 0.5)
        mix[:fi] *= np.linspace(0, 1, fi)
    fo = int(SR * 1.0)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = np.tanh(mix / (np.max(np.abs(mix)) + 1e-9) * 1.4) / np.tanh(1.4)
    rms = np.sqrt((mix ** 2).mean()) + 1e-9
    mix = np.clip(mix * (10 ** (-16.5 / 20) / rms), -0.95, 0.95)   # 인스타 권장 음량(약 -14 LUFS)에 맞춤

    left = mix
    right = np.concatenate([np.zeros(150), mix[:-150]])
    pcm = (np.stack([left, right], axis=1) * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    import sys

    secs = [(0, "hook"), (2.6, "rank3"), (6.0, "rank2"), (9.4, "rank1"), (12.8, "warn"),
            (16.0, "rest"), (26.4, "outro")]
    st = sys.argv[1] if len(sys.argv) > 1 else "trap"
    make(Path(f"out/bgm_{st}.wav"), 29.4, secs, seed=5, style=st)
    print(f"out/bgm_{st}.wav")
