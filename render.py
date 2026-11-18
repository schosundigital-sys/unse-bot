"""카드뉴스 이미지 렌더링 (1080x1350, 인스타 4:5) – 한지 톤의 차분한 디자인."""
from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from fortune import Zodiac

W, H = 1080, 1350
M = 96  # 좌우 여백
ROOT = Path(__file__).parent
FONT_SANS = ROOT / "fonts" / "NotoSansKR-VF.ttf"
FONT_SERIF = ROOT / "fonts" / "NotoSerifKR-VF.ttf"

PAPER = (244, 239, 230)
INK = (44, 41, 38)
SUB = (118, 110, 100)
SEAL = (146, 58, 44)      # 도장 붉은색
LINE = (210, 200, 184)

ACCOUNT = "@unse_official"
WEEKDAY = "월화수목금토일"
LOGO = ROOT / "assets" / "logo.png"


def logo(img: Image.Image, cx: float, y: float, height: int) -> None:
    lg = Image.open(LOGO).convert("RGBA")
    w = round(lg.width * height / lg.height)
    lg = lg.resize((w, height), Image.LANCZOS)
    img.paste(lg, (round(cx - w / 2), round(y)), lg)


@lru_cache(maxsize=None)
def font(kind: str, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT_SERIF if kind == "serif" else FONT_SANS), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def date_label(d) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일 {WEEKDAY[d.weekday()]}요일"


def date_dot(d) -> str:
    return f"{d.year}. {d.month:02d}. {d.day:02d}"


# ---------- 공통 ----------

def background() -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    # 아주 옅은 종이결
    rnd = random.Random(3)
    px = img.load()
    for _ in range(26000):
        x, y = rnd.randrange(W), rnd.randrange(H)
        v = rnd.randrange(-7, 4)
        r, g, b = px[x, y]
        px[x, y] = (r + v, g + v, b + v)
    d = ImageDraw.Draw(img)
    d.rectangle([36, 36, W - 37, H - 37], outline=LINE, width=2)
    d.rectangle([46, 46, W - 47, H - 47], outline=LINE, width=1)
    return img


def wrap(text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if f.getlength(cand) <= width:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = ""
        for ch in word:
            if f.getlength(cur + ch) > width and cur:
                lines.append(cur)
                cur = ""
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def center(d: ImageDraw.ImageDraw, y: float, text: str, f, fill) -> float:
    d.text(((W - f.getlength(text)) / 2, y), text, font=f, fill=fill)
    return y + f.getbbox(text)[3]


def header(img: Image.Image, left: str, right: str) -> None:
    d = ImageDraw.Draw(img)
    f = font("serif", 28, 600)
    d.text((M, 92), left, font=f, fill=INK)
    d.text((W - M - f.getlength(right), 92), right, font=font("serif", 28, 400), fill=SUB)
    d.line([(M, 146), (W - M, 146)], fill=INK, width=2)


def footer(img: Image.Image, page: str | None) -> None:
    d = ImageDraw.Draw(img)
    f = font("sans", 24, 400)
    d.line([(M, H - 140), (W - M, H - 140)], fill=LINE, width=1)
    d.text((M, H - 120), ACCOUNT, font=f, fill=SUB)
    logo(img, W / 2, H - 126, 42)
    if page:
        d.text((W - M - f.getlength(page), H - 120), page, font=f, fill=SUB)


def seal(img: Image.Image, x: float, y: float, size: int, ch: str) -> None:
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + size, y + size], radius=max(4, size // 14), fill=SEAL)
    f = font("serif", int(size * 0.62), 700)
    bb = f.getbbox(ch)
    d.text((x + (size - (bb[2] - bb[0])) / 2 - bb[0], y + (size - (bb[3] - bb[1])) / 2 - bb[1]), ch, font=f, fill=PAPER)


# ---------- 표지 ----------

def cover(d, title: str, subtitle: str, names: list[str], seed: int = 0) -> Image.Image:
    img = background()
    dr = ImageDraw.Draw(img)
    logo(img, W / 2, 290, 92)
    y = 500
    y = center(dr, y, date_label(d), font("serif", 40, 400), SUB) + 40
    y = center(dr, y, title, font("serif", 120, 700), INK) + 52
    dr.line([(W / 2 - 40, y), (W / 2 + 40, y)], fill=INK, width=2)
    y += 50
    y = center(dr, y, subtitle, font("serif", 40, 500), SEAL) + 70

    f = font("sans", 30, 400)
    line, rows = "", []
    for n in names:
        cand = n if not line else line + "   ·   " + n
        if f.getlength(cand) > W - 2 * M - 40 and line:
            rows.append(line)
            line = n
        else:
            line = cand
    rows.append(line)
    for r in rows:
        y = center(dr, y, r, f, SUB) + 22
    footer(img, None)
    return img


# ---------- 연도별 카드 ----------

def _yearly_block(img, z: Zodiac, y: float, s: float, draw: bool) -> float:
    d = ImageDraw.Draw(img)
    ss = int(72 * s)
    fn = font("serif", int(52 * s), 700)
    if draw:
        seal(img, M, y, ss, z.hanja)
        d.text((M + ss + int(26 * s), y + ss / 2), z.name, font=fn, fill=INK, anchor="lm")
    y += ss + int(24 * s)

    fs = font("serif", int(33 * s), 500)
    lh = int(50 * s)
    for ln in wrap(z.summary, fs, W - 2 * M):
        if draw:
            d.text((M, y), ln, font=fs, fill=INK)
        y += lh
    y += int(16 * s)

    fy = font("sans", int(28 * s), 600)
    ft = font("sans", int(30 * s), 400)
    col = int(150 * s)
    lh = int(46 * s)
    for yr, txt in z.years:
        if draw:
            d.line([(M, y), (W - M, y)], fill=LINE, width=1)
        y += int(16 * s)
        lines = wrap(txt, ft, W - 2 * M - col)
        if draw:
            d.text((M, y + int(2 * s)), yr, font=fy, fill=SEAL)
            ty = y
            for ln in lines:
                d.text((M + col, ty), ln, font=ft, fill=INK)
                ty += lh
        y += len(lines) * lh + int(4 * s)
    return y


def yearly_card(d, zs: list[Zodiac], label: str, page: str, seed: int = 0) -> Image.Image:
    img = background()
    top, bottom, gap = 200, H - 180, 64
    s = 1.4
    while s > 0.6:
        y = top
        for z in zs:
            y = _yearly_block(img, z, y, s, False) + gap
        if y - gap <= bottom:
            break
        s -= 0.03
    y = top + max(0, (bottom - (y - gap)) / 2)
    for i, z in enumerate(zs):
        y = _yearly_block(img, z, y, s, True)
        y += gap
    header(img, label, date_dot(d))
    footer(img, page)
    return img


# ---------- 띠별 카드 ----------

def _zodiac_block(img, z: Zodiac, y: float, s: float, draw: bool) -> float:
    d = ImageDraw.Draw(img)
    ss = int(80 * s)
    tx = M + ss + int(36 * s)
    fn = font("serif", int(44 * s), 700)
    fs = font("serif", int(34 * s), 400)
    lines = wrap(z.summary, fs, W - M - tx)
    lh = int(54 * s)
    h = max(ss, int(68 * s) + len(lines) * lh)
    if draw:
        seal(img, M, y + int(4 * s), ss, z.hanja)
        d.text((tx, y), z.name, font=fn, fill=SEAL)
        ty = y + int(68 * s)
        for ln in lines:
            d.text((tx, ty), ln, font=fs, fill=INK)
            ty += lh
    return y + h


def zodiac_card(d, zs: list[Zodiac], label: str, page: str, seed: int = 0) -> Image.Image:
    img = background()
    top, bottom = 210, H - 190
    s = 1.3
    while s > 0.6:
        hs = [_zodiac_block(img, z, 0, s, False) for z in zs]
        if sum(hs) + 80 * (len(zs) - 1) <= bottom - top:
            break
        s -= 0.03
    gap = min(((bottom - top) - sum(hs)) / max(1, len(zs) - 1), 140)
    y = top + max(0, ((bottom - top) - sum(hs) - gap * (len(zs) - 1)) / 2)
    dr = ImageDraw.Draw(img)
    for i, z in enumerate(zs):
        y = _zodiac_block(img, z, y, s, True)
        if i < len(zs) - 1:
            dr.line([(M, y + gap / 2), (W - M, y + gap / 2)], fill=LINE, width=1)
            y += gap
    header(img, label, date_dot(d))
    footer(img, page)
    return img


# ---------- 마무리 ----------

def outro(seed: int = 0) -> Image.Image:
    img = background()
    dr = ImageDraw.Draw(img)
    logo(img, W / 2, 440, 92)
    y = 600
    y = center(dr, y, "오늘도 평안한 하루 보내세요", font("serif", 56, 600), INK) + 50
    dr.line([(W / 2 - 40, y), (W / 2 + 40, y)], fill=INK, width=2)
    y += 56
    y = center(dr, y, ACCOUNT, font("serif", 40, 600), SEAL) + 24
    center(dr, y, "팔로우하고 매일의 운세를 받아보세요", font("sans", 28, 400), SUB)
    return img


def save(img: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=92, optimize=True)
    return path
