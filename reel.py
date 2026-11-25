"""오늘의 운세 릴스 (1080×1920, 약 30초) – 카드뉴스를 옮긴 게 아니라 훅 중심으로 새로 구성.

  0.0s  훅      "오늘 운 터지는 띠 TOP 3" + "끝까지 보면 조심할 띠도 공개"
  2.6s  3위 → 2위 → 1위  (띠 낙관 + 총평 + '특히 ○○년생')
 12.8s  오늘 조심할 띠
 16.0s  나머지 8띠 한 줄 운세 (2띠씩, 멈춰서 확인하도록 빠르게)
 26.4s  마무리   "내 출생연도 운세는 ▶ 피드 게시물에서" + 팔로우

사용법: python reel.py [--date 2026-11-26]   → out/<날짜>/reel/{reel.mp4, cover.jpg, caption.txt}
"""
from __future__ import annotations

import argparse
import math
import os
import random
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import bgm
import fortune
import hook
from render import ACCOUNT, LOGO, WEEKDAY, ZCOLOR, font, wrap

W, H, FPS = 1080, 1920, 30
ROOT = Path(__file__).parent
KST = timezone(timedelta(hours=9))

# 인스타 화면 위·아래·오른쪽 버튼에 가리지 않는 안전 영역
SAFE_TOP, SAFE_BOTTOM = 260, 1580
CX = 520  # 오른쪽 버튼(좋아요·댓글) 쪽을 피해 살짝 왼쪽이 중심
TEXT_W = 840

BG_TOP, BG_BOTTOM = (12, 18, 42), (34, 16, 44)
GOLD = (226, 186, 110)
CREAM = (246, 238, 222)
SUB = (178, 176, 196)
RED = (214, 64, 56)
MEDAL = {1: (232, 192, 96), 2: (196, 204, 216), 3: (204, 140, 92)}

# 장면 길이(초)
T_HOOK, T_RANK, T_WARN, T_PAGE, T_OUTRO = 2.6, 3.4, 3.2, 2.6, 3.0

# 배경음 스타일: trap(다크 팝-트랩) | lofi(로파이 힙합)
BGM_STYLE = os.getenv("BGM_STYLE", "trap")


# ---------------- 그리기 도구 ----------------

def text_img(text: str, size: int, weight: int = 700, color=CREAM, kind: str = "sans", shadow: bool = True) -> Image.Image:
    f = font(kind, size, weight)
    l, t, r, b = f.getbbox(text)
    pad = max(12, size // 5)
    im = Image.new("RGBA", (int(r - l) + pad * 2, int(b - t) + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l, pad - t + size * 0.04), text, font=f, fill=(0, 0, 0, 170))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(size / 14)))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=color)
    return im


def para_img(text: str, size: int, width: int, weight: int = 500, color=CREAM, kind: str = "serif",
             lh: float = 1.5, max_lines: int = 4) -> Image.Image:
    f = font(kind, size, weight)
    lines = wrap(text, f, width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "…"
    step = int(size * lh)
    pad = 14
    im = Image.new("RGBA", (width + pad * 2, step * len(lines) + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ds, d = ImageDraw.Draw(sh), ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        x = pad + (width - f.getlength(ln)) / 2
        ds.text((x, pad + i * step + 2), ln, font=f, fill=(0, 0, 0, 190))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((pad + (width - f.getlength(ln)) / 2, pad + i * step), ln, font=f, fill=color)
    return im


def seal_img(ch: str, size: int, color, fg=CREAM) -> Image.Image:
    pad = size // 6
    im = Image.new("RGBA", (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([pad, pad + size // 30, pad + size, pad + size + size // 30],
                                         radius=size // 9, fill=(0, 0, 0, 160))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(size // 18)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad, pad, pad + size, pad + size], radius=size // 9, fill=(*color, 255))
    i = max(4, size // 18)
    d.rounded_rectangle([pad + i, pad + i, pad + size - i, pad + size - i], radius=size // 11,
                        outline=(*fg, 200), width=max(1, size // 60))
    f = font("serif", int(size * 0.6), 800)
    l, t, r, b = f.getbbox(ch)
    d.text((pad + (size - (r - l)) / 2 - l, pad + (size - (b - t)) / 2 - t), ch, font=f, fill=fg)
    return im


def pill_img(text: str, size: int, bg, fg, weight: int = 800) -> Image.Image:
    f = font("sans", size, weight)
    l, t, r, b = f.getbbox(text)
    px, py = int(size * 0.7), int(size * 0.38)
    w, h = int(r - l) + px * 2, int(b - t) + py * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=(*bg, 255))
    d.text((px - l, py - t), text, font=f, fill=fg)
    return im


def logo_img(height: int) -> Image.Image:
    lg = Image.open(LOGO).convert("RGBA")
    w = round(lg.width * height / lg.height)
    lg = lg.resize((w, height), Image.LANCZOS)
    pad = height // 4
    im = Image.new("RGBA", (w + pad * 2, height + pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=height // 3,
                                         fill=(245, 240, 230, 255))
    im.alpha_composite(lg, (pad, pad // 2))
    return im


def rays_img(size: int, color) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    for k in range(16):
        a0 = k * math.pi / 8
        a1 = a0 + math.pi / 22
        d.polygon([(c, c), (c + c * math.cos(a0), c + c * math.sin(a0)), (c + c * math.cos(a1), c + c * math.sin(a1))],
                  fill=(*color, 46))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(size / 6))
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), mask))
    return im


# ---------------- 장면·요소 ----------------

@dataclass
class El:
    img: Image.Image
    cx: float          # 가로 중심
    y: float           # 위쪽 y
    t0: float          # 등장 시작 (장면 기준)
    anim: str = "pop"  # pop | fade | up | stamp | spin
    dur: float = 0.32


@dataclass
class Scene:
    length: float
    els: list[El] = field(default_factory=list)
    mark: str = ""             # 배경에 크게 깔리는 한자
    mark_color: tuple = GOLD
    tint: tuple | None = None  # 배경 색조 (주의 장면 붉은빛)
    bell: bool = False
    kind: str = ""             # 배경음 구간 (hook·rank3·rank2·rank1·warn·rest·outro)


def ease_out_back(x: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x: float) -> float:
    return 1 - (1 - x) ** 3


class Frames:
    def __init__(self, seed: int):
        self.rnd = random.Random(seed)
        g = Image.new("RGB", (1, H))
        for y in range(H):
            k = y / (H - 1)
            g.putpixel((0, y), tuple(int(a + (b - a) * k) for a, b in zip(BG_TOP, BG_BOTTOM)))
        self.base = g.resize((W, H)).convert("RGBA")
        vig = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vig).ellipse([-260, 120, W + 260, H - 120], fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(180))
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 150))
        dark.putalpha(Image.eval(vig, lambda v: int((255 - v) * 0.6)))
        self.base.alpha_composite(dark)
        self.dots = [(self.rnd.uniform(0, W), self.rnd.uniform(0, H), self.rnd.uniform(1.5, 4.2),
                      self.rnd.uniform(18, 60), self.rnd.uniform(0, 6.28)) for _ in range(70)]
        self.marks: dict = {}
        self.tints: dict = {}

    def mark(self, ch: str, color) -> Image.Image:
        key = (ch, color)
        if key not in self.marks:
            f = font("serif", 900, 800)
            im = Image.new("RGBA", (1100, 1150), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((550, 575), ch, font=f, fill=(*color, 22), anchor="mm")
            self.marks[key] = im
        return self.marks[key]

    def tint(self, color) -> Image.Image:
        if color not in self.tints:
            t = Image.new("RGBA", (W, H), (*color, 0))
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).ellipse([-200, 300, W + 200, H - 200], fill=70)
            t.putalpha(m.filter(ImageFilter.GaussianBlur(160)))
            self.tints[color] = t
        return self.tints[color]

    def background(self, t: float, sc: Scene, st: float) -> Image.Image:
        im = self.base.copy()
        if sc.tint:
            im.alpha_composite(self.tint(sc.tint))
        if sc.mark:
            mk = self.mark(sc.mark, sc.mark_color)
            a = min(1.0, st / 0.4) * min(1.0, (sc.length - st) / 0.3)
            if a < 1:
                mk = mk.copy()
                mk.putalpha(mk.getchannel("A").point(lambda v: int(v * a)))
            im.alpha_composite(mk, (int(W / 2 - 550 + 40 - st * 14), int(H / 2 - 600 - 60 + st * 10)))
        d = ImageDraw.Draw(im)
        for x, y, r, sp, ph in self.dots:  # 위로 떠오르는 금빛 가루
            yy = (y - t * sp) % H
            xx = x + math.sin(t * 0.8 + ph) * 12
            a = int(70 + 60 * math.sin(t * 2 + ph))
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(*GOLD, a))
        return im


def place(frame: Image.Image, e: El, st: float, out_a: float) -> None:
    p = (st - e.t0) / e.dur
    if p <= 0:
        return
    p = min(p, 1.0)
    img, a, dy, s = e.img, 1.0, 0.0, 1.0
    if e.anim == "pop":
        s = 0.6 + 0.4 * ease_out_back(p)
        a = min(1.0, p * 2.2)
    elif e.anim == "stamp":
        s = 1.0 + 0.7 * (1 - ease_out(p))
        a = min(1.0, p * 2.5)
    elif e.anim == "up":
        dy = 46 * (1 - ease_out(p))
        a = ease_out(p)
    elif e.anim == "spin":
        a = min(1.0, p * 1.5)
        img = img.rotate(-st * 22, resample=Image.BICUBIC)
    else:  # fade
        a = p
    a *= out_a
    if a <= 0.01:
        return
    if abs(s - 1) > 0.005:
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)
    if a < 0.999:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    cy = e.y + e.img.height / 2 + dy
    frame.alpha_composite(img, (int(e.cx - img.width / 2), int(cy - img.height / 2)))


# ---------------- 장면 구성 ----------------

def _stack(items: list[tuple[Image.Image, float, str, float]], top: float, bottom: float, cx: float = CX) -> list[El]:
    """(이미지, 등장시각, 애니, 아래 간격)을 세로로 쌓아 가운데 정렬."""
    total = sum(im.height + gap for im, _, _, gap in items) - items[-1][3]
    y = top + max(0, (bottom - top - total) / 2)
    out = []
    for im, t0, anim, gap in items:
        out.append(El(im, cx, y, t0, anim))
        y += im.height + gap
    return out


def build_scenes(d: date, seed: int):
    zs = fortune.fetch(d)
    (h1, h2), top, warn, rest = hook.pick(zs, seed)
    date_txt = f"{d.month}월 {d.day}일 {WEEKDAY[d.weekday()]}요일"
    scenes: list[Scene] = []

    # 0) 훅
    seals = Image.new("RGBA", (6 * 150 - 20, 2 * 160 + 10), (0, 0, 0, 0))
    for i, z in enumerate(zs):
        s = seal_img(z.hanja, 120, ZCOLOR.get(z.name, GOLD))
        seals.alpha_composite(s, ((i % 6) * 150 - 20, (i // 6) * 160 - 20))
    items = [
        (pill_img(date_txt, 46, (40, 46, 84), CREAM, 600), -1.0, "fade", 48),
        (text_img(h1, 116, 900, CREAM), -1.0, "up", 6),  # 첫 프레임부터 보이게
        (text_img(h2, 250, 900, GOLD, kind="sans"), 0.4, "stamp", 64),
        (seals, 0.95, "fade", 64),
        (text_img("끝까지 보면 '조심할 띠'도 공개", 48, 700, SUB, shadow=False), 1.35, "up", 0),
    ]
    scenes.append(Scene(T_HOOK, _stack(items, SAFE_TOP, SAFE_BOTTOM), mark="運", kind="hook"))

    # 1~3) 3위 → 2위 → 1위
    for rank_no, r in ((3, top[2]), (2, top[1]), (1, top[0])):
        z, col = r.z, ZCOLOR.get(r.z.name, GOLD)
        items = [
            (pill_img(f"{rank_no}위", 76, MEDAL[rank_no], (24, 20, 36)), 0.0, "pop", 40),
            (seal_img(z.hanja, 300, col), 0.12, "pop", 18),
            (text_img(z.name, 136, 900, GOLD if rank_no == 1 else CREAM, kind="serif"), 0.28, "up", 26),
            (para_img(z.summary, 56, TEXT_W, 600), 0.55, "up", 40),
        ]
        if r.best:
            yr, txt = r.best
            items.append((text_img(f"★ 특히 {yr}", 50, 800, GOLD, shadow=False), 1.15, "up", 8))
            items.append((para_img(txt, 42, TEXT_W - 40, 400, SUB, kind="sans", max_lines=2), 1.3, "up", 0))
        els = _stack(items, SAFE_TOP, SAFE_BOTTOM)
        if rank_no == 1:  # 1위는 낙관 뒤로 회전하는 금빛 후광
            sealel = els[1]
            ray = rays_img(880, GOLD)
            els.insert(0, El(ray, CX, sealel.y + sealel.img.height / 2 - 440, 0.1, "spin", 0.5))
        scenes.append(Scene(T_RANK, els, mark=z.hanja, mark_color=col, bell=True, kind=f"rank{rank_no}"))

    # 4) 조심할 띠
    z = warn.z
    items = [
        (pill_img("오늘 조심할 띠", 68, RED, CREAM), 0.0, "stamp", 40),
        (seal_img(z.hanja, 280, (120, 40, 40)), 0.15, "pop", 18),
        (text_img(z.name, 130, 900, CREAM, kind="serif"), 0.3, "up", 26),
        (para_img(z.summary, 56, TEXT_W, 600), 0.55, "up", 36),
    ]
    if warn.worst:
        yr, txt = warn.worst
        items.append((text_img(f"특히 {yr}", 50, 800, (240, 130, 120), shadow=False), 1.1, "up", 8))
        items.append((para_img(txt, 42, TEXT_W - 40, 400, SUB, kind="sans", max_lines=2), 1.25, "up", 0))
    scenes.append(Scene(T_WARN, _stack(items, SAFE_TOP, SAFE_BOTTOM), mark=z.hanja, mark_color=RED,
                        tint=(150, 30, 30), bell=True, kind="warn"))

    # 5) 나머지 8띠: 2띠씩 4화면
    for i in range(0, len(rest), 2):
        pair = rest[i:i + 2]
        els = [El(pill_img("나머지 띠 한 줄 운세", 48, (40, 46, 84), GOLD, 700), CX, SAFE_TOP, 0.0, "fade", 0.2)]
        y = SAFE_TOP + 170
        for j, r in enumerate(pair):
            z = r.z
            col = ZCOLOR.get(z.name, GOLD)
            t0 = 0.05 + j * 0.35
            row = Image.new("RGBA", (TEXT_W + 40, 600), (0, 0, 0, 0))
            row.alpha_composite(seal_img(z.hanja, 160, col), (0, 0))
            nm = text_img(z.name, 84, 900, GOLD, kind="serif")
            row.alpha_composite(nm, (220, 30))
            yrs = ", ".join(yr.replace("년생", "") for yr, _ in z.years) + "년생"
            row.alpha_composite(text_img(yrs, 36, 500, SUB, shadow=False), (232, 142))
            body = para_img(z.summary, 50, TEXT_W, 500, max_lines=3)
            row.alpha_composite(body, (0, 230))
            row = row.crop((0, 0, row.width, 230 + body.height))
            els.append(El(row, CX, y, t0, "up", 0.35))
            y += row.height + 90
        sc = Scene(T_PAGE, els, mark=pair[0].z.hanja, mark_color=GOLD, kind="rest")
        scenes.append(sc)

    # 6) 마무리
    items = [
        (logo_img(130), 0.0, "pop", 80),
        (text_img("내 출생연도 운세는?", 92, 900, CREAM), 0.15, "up", 30),
        (pill_img("▶  피드 게시물에서 확인", 60, GOLD, (24, 20, 36)), 0.45, "pop", 70),
        (text_img(ACCOUNT, 64, 800, GOLD, kind="serif"), 0.8, "up", 14),
        (text_img("팔로우하면 매일 아침 7시 운세 도착", 46, 500, SUB, shadow=False), 0.95, "up", 0),
    ]
    scenes.append(Scene(T_OUTRO, _stack(items, SAFE_TOP, SAFE_BOTTOM), mark="福", kind="outro"))

    info = dict(hook=f"{h1} {h2}", top=top, warn=warn, date_txt=date_txt)
    return scenes, info


# ---------------- 영상 만들기 ----------------

def find_ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if not p:
        raise RuntimeError("ffmpeg를 찾지 못했습니다.")
    return p


def caption(d: date, info) -> str:
    top, warn = info["top"], info["warn"]
    lines = [
        f"{info['date_txt']} {info['hook']} 🔮",
        "",
        *[f"{i}위 {r.z.name} – {r.z.summary}" for i, r in enumerate(top, 1)],
        "",
        f"오늘 조심할 띠: {warn.z.name}",
        "",
        "내 출생연도 운세는 피드 게시물에서 확인하세요.",
        "저장해 두고 내일 아침에도 확인하세요 🙏",
        "",
        "#오늘의운세 #띠별운세 #운세 #오늘운세 #띠운세 #출생연도별운세 #운세릴스 #행운",
    ]
    return "\n".join(lines)


def build(d: date, style: str = BGM_STYLE) -> Path:
    seed = d.toordinal()
    scenes, info = build_scenes(d, seed)
    out = ROOT / "out" / d.isoformat() / "reel"
    out.mkdir(parents=True, exist_ok=True)

    starts, t = [], 0.0
    for sc in scenes:
        starts.append(t)
        t += sc.length
    total = t
    wav = bgm.make(out / "bgm.wav", total + 0.2,
                   sections=[(s, sc.kind) for s, sc in zip(starts, scenes)], seed=seed, style=style)

    mp4 = out / "reel.mp4"
    cmd = [find_ffmpeg(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "5M", "-bufsize", "10M",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(FPS), "-g", str(FPS * 2),
           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
           "-shortest", "-movflags", "+faststart", str(mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    fr = Frames(seed)
    n = int(total * FPS)
    cover_at = (0, 2.0)  # 훅 화면이 다 나타난 순간
    for i in range(n):
        t = i / FPS
        k = max(j for j, s in enumerate(starts) if s <= t + 1e-9)
        sc, st = scenes[k], t - starts[k]
        out_a = min(1.0, max(0.0, (sc.length - st) / 0.22)) if k < len(scenes) - 1 else 1.0
        frame = fr.background(t, sc, st)
        for e in sc.els:
            place(frame, e, st, out_a)
        # 진행 바
        dr = ImageDraw.Draw(frame)
        dr.rectangle([0, 0, W, 10], fill=(255, 255, 255, 40))
        dr.rectangle([0, 0, int(W * (t + 1 / FPS) / total), 10], fill=(*GOLD, 255))
        rgb = frame.convert("RGB")
        if k == cover_at[0] and abs(st - cover_at[1]) < 0.5 / FPS:
            rgb.save(out / "cover.jpg", "JPEG", quality=92)
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 인코딩 실패")
    wav.unlink(missing_ok=True)

    (out / "caption.txt").write_text(caption(d, info), encoding="utf-8")
    mb = mp4.stat().st_size / 1e6
    print(f"[reel] {d} {total:.1f}초 {mb:.1f}MB → {out.relative_to(ROOT).as_posix()}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="운세 날짜 YYYY-MM-DD (기본: 오늘 KST)")
    ap.add_argument("--style", default=BGM_STYLE, choices=list(bgm.STYLES), help="배경음 스타일")
    a = ap.parse_args()
    d = date.fromisoformat(a.date) if a.date else datetime.now(KST).date()
    out = build(d, a.style)
    gh_out = os.getenv("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"reel={out.relative_to(ROOT).as_posix()}\n")


if __name__ == "__main__":
    main()
