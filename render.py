"""카드뉴스 이미지 렌더링 (1080x1350, 인스타 4:5).

테마는 config.THEME 로 고릅니다.
  hanji  : 한지 바탕 + 띠별 전통색
  navy   : 남색 바탕 + 금색
  ink    : 흰 바탕 + 먹색 헤더 + 붉은 낙관 (매거진형)
"""
from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from fortune import Zodiac

W, H = 1080, 1350
M = 96
ROOT = Path(__file__).parent
FONT_SANS = ROOT / "fonts" / "NotoSansKR-VF.ttf"
FONT_SERIF = ROOT / "fonts" / "NotoSerifKR-VF.ttf"
LOGO = ROOT / "assets" / "logo.png"
ACCOUNT = "@unse_official"
WEEKDAY = "월화수목금토일"

# 띠별 전통색 (채도 낮춘 오방색 계열)
ZCOLOR = {
    "쥐띠": (52, 84, 112), "소띠": (128, 96, 56), "범띠": (156, 78, 44), "토끼띠": (88, 122, 90),
    "용띠": (40, 104, 104), "뱀띠": (132, 52, 52), "말띠": (170, 96, 36), "양띠": (110, 102, 84),
    "원숭이띠": (140, 100, 46), "닭띠": (164, 120, 28), "개띠": (84, 96, 112), "돼지띠": (102, 72, 100),
}

THEMES = {
    "hanji": dict(bg=(245, 240, 230), text=(42, 39, 36), sub=(120, 112, 102), line=(214, 204, 188),
                  accent=(146, 58, 44), band=None, band_text=(250, 246, 238), stripe=(236, 229, 216),
                  zodiac_color=True, logo_bg=None, dark=False),
    "navy": dict(bg=(20, 31, 56), text=(242, 235, 222), sub=(170, 176, 196), line=(64, 78, 108),
                 accent=(206, 168, 96), band=(14, 22, 42), band_text=(206, 168, 96), stripe=(28, 41, 70),
                 zodiac_color=False, logo_bg=(245, 240, 230), dark=True),
    "ink": dict(bg=(250, 249, 245), text=(24, 24, 24), sub=(110, 110, 106), line=(222, 220, 212),
                accent=(178, 42, 36), band=(28, 28, 28), band_text=(250, 249, 245), stripe=(242, 240, 233),
                zodiac_color=False, logo_bg=None, dark=False),
}
T = THEMES["hanji"]


def set_theme(name: str) -> None:
    global T
    T = THEMES[name]


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


def zc(z: Zodiac | None):
    if z is not None and T["zodiac_color"]:
        return ZCOLOR.get(z.name, T["accent"])
    return T["accent"]


# ---------- 공통 그리기 ----------

def wrap(text: str, f, width: int) -> list[str]:
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


def center(d, y, text, f, fill) -> float:
    d.text(((W - f.getlength(text)) / 2, y), text, font=f, fill=fill)
    return y + f.getbbox(text)[3]


def corners(img, color, inset=40, arm=70, gap=10):
    """전통 문살 느낌의 이중 ㄱ자 모서리 장식."""
    d = ImageDraw.Draw(img)
    for k in (0, gap):
        i = inset + k
        a = arm - k
        for (x, y, sx, sy) in ((i, i, 1, 1), (W - i, i, -1, 1), (i, H - i, 1, -1), (W - i, H - i, -1, -1)):
            d.line([(x, y), (x + sx * a, y)], fill=color, width=3 if k == 0 else 1)
            d.line([(x, y), (x, y + sy * a)], fill=color, width=3 if k == 0 else 1)


def background() -> Image.Image:
    img = Image.new("RGB", (W, H), T["bg"])
    rnd = random.Random(3)
    px = img.load()
    amp = 5 if T["dark"] else 7
    for _ in range(24000):  # 옅은 종이결
        x, y = rnd.randrange(W), rnd.randrange(H)
        v = rnd.randrange(-amp, amp // 2 + 1)
        r, g, b = px[x, y]
        px[x, y] = (max(0, r + v), max(0, g + v), max(0, b + v))
    return img


def watermark(img, ch: str, x: float, y: float, size: int, color, alpha: int):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((x, y), ch, font=font("serif", size, 700), fill=(*color, alpha))
    base = img.convert("RGBA")
    base.alpha_composite(ov)
    img.paste(base.convert("RGB"))


def seal(img, x, y, size, ch, color, fg=None):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + size, y + size], radius=max(4, size // 12), fill=color)
    d.rounded_rectangle([x + 5, y + 5, x + size - 5, y + size - 5], radius=max(3, size // 14),
                        outline=fg or T["bg"], width=1)
    f = font("serif", int(size * 0.58), 700)
    bb = f.getbbox(ch)
    d.text((x + (size - (bb[2] - bb[0])) / 2 - bb[0], y + (size - (bb[3] - bb[1])) / 2 - bb[1]),
           ch, font=f, fill=fg or T["bg"])


def logo(img, cx, y, height):
    lg = Image.open(LOGO).convert("RGBA")
    w = round(lg.width * height / lg.height)
    lg = lg.resize((w, height), Image.LANCZOS)
    if T["logo_bg"]:  # 어두운 배경에서는 밝은 바탕 위에 로고
        d = ImageDraw.Draw(img)
        pad = height // 4
        d.rounded_rectangle([cx - w / 2 - pad, y - pad / 2, cx + w / 2 + pad, y + height + pad / 2],
                            radius=height // 3, fill=T["logo_bg"])
    img.paste(lg, (round(cx - w / 2), round(y)), lg)


def header(img, label, d_text, color):
    d = ImageDraw.Draw(img)
    band = T["band"] or color
    d.rectangle([0, 0, W, 132], fill=band)
    d.rectangle([0, 132, W, 138], fill=T["accent"] if T["band"] else T["bg"])
    f = font("serif", 34, 700)
    d.text((M, 46), label, font=f, fill=T["band_text"])
    f2 = font("serif", 28, 400)
    d.text((W - M - f2.getlength(d_text), 52), d_text, font=f2, fill=T["band_text"])


def footer(img, page):
    d = ImageDraw.Draw(img)
    f = font("sans", 24, 400)
    d.line([(M, H - 120), (W - M, H - 120)], fill=T["line"], width=1)
    d.text((M, H - 96), ACCOUNT, font=f, fill=T["sub"])
    logo(img, W / 2, H - 102, 40)
    if page:
        d.text((W - M - f.getlength(page), H - 96), page, font=f, fill=T["sub"])


# ---------- 표지 ----------

def cover(d, title, subtitle, names, seed=0):
    img = background()
    watermark(img, "運", W - 560, 260, 640, T["accent"], 16 if T["dark"] else 14)
    corners(img, T["accent"])
    dr = ImageDraw.Draw(img)
    logo(img, W / 2, 190, 96)

    y = 420
    y = center(dr, y, date_label(d), font("serif", 38, 500), T["sub"]) + 34
    y = center(dr, y, title, font("serif", 132, 800), T["text"]) + 46
    # 부제: 색 띠 위 글자
    f = font("serif", 40, 600)
    tw = f.getlength(subtitle)
    dr.rectangle([(W - tw) / 2 - 36, y, (W + tw) / 2 + 36, y + 72], fill=T["accent"])
    dr.text(((W - tw) / 2, y + 10), subtitle, font=f, fill=T["bg"])
    y += 130

    # 띠 목록: 한자 낙관 6개씩 두 줄
    size, gap = 92, 34
    per = 6
    for r in range(0, len(names), per):
        row = names[r:r + per]
        total = len(row) * size + (len(row) - 1) * gap
        x = (W - total) / 2
        for n in row:
            z_color = ZCOLOR.get(n, T["accent"]) if T["zodiac_color"] else T["accent"]
            from fortune import HANJA
            seal(img, x, y, size, HANJA.get(n, ""), z_color)
            fn = font("sans", 24, 500)
            dr.text((x + (size - fn.getlength(n)) / 2, y + size + 10), n, font=fn, fill=T["sub"])
            x += size + gap
        y += size + 70

    center(dr, H - 150, "옆으로 넘겨 확인하세요", font("sans", 26, 400), T["sub"])
    return img


# ---------- 출생연도별 카드 ----------

def _yearly_block(img, z, y, s, draw):
    d = ImageDraw.Draw(img)
    col = zc(z)
    ss = int(76 * s)
    if draw:
        watermark(img, z.hanja, W - M - int(250 * s), y - int(40 * s), int(300 * s), col, 20 if T["dark"] else 18)
        seal(img, M, y, ss, z.hanja, col)
        d = ImageDraw.Draw(img)
        d.text((M + ss + int(24 * s), y + ss / 2), z.name, font=font("serif", int(54 * s), 800), fill=T["text"], anchor="lm")
    y += ss + int(22 * s)

    # 총평: 왼쪽 색 막대 + 본문
    fs = font("serif", int(33 * s), 600)
    lines = wrap(z.summary, fs, W - 2 * M - int(34 * s))
    lh = int(50 * s)
    h = len(lines) * lh + int(8 * s)
    if draw:
        d.rectangle([M, y + int(4 * s), M + int(8 * s), y + h - int(4 * s)], fill=col)
        ty = y
        for ln in lines:
            d.text((M + int(30 * s), ty), ln, font=fs, fill=T["text"])
            ty += lh
    y += h + int(18 * s)

    fy = font("sans", int(27 * s), 700)
    ft = font("sans", int(30 * s), 400)
    colw = int(150 * s)
    lh = int(45 * s)
    for i, (yr, txt) in enumerate(z.years):
        lines = wrap(txt, ft, W - 2 * M - colw - int(20 * s))
        rh = len(lines) * lh + int(22 * s)
        if draw:
            if i % 2 == 0:
                d.rectangle([M, y, W - M, y + rh], fill=T["stripe"])
            d.text((M + int(18 * s), y + int(13 * s)), yr, font=fy, fill=col)
            ty = y + int(10 * s)
            for ln in lines:
                d.text((M + colw, ty), ln, font=ft, fill=T["text"])
                ty += lh
        y += rh
    return y


def yearly_card(d, zs, label, page, seed=0):
    img = background()
    top, bottom, gap = 190, H - 160, 56
    s = 1.35
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
        if i < len(zs) - 1:
            ImageDraw.Draw(img).line([(M, y + gap / 2), (W - M, y + gap / 2)], fill=T["line"], width=2)
        y += gap
    header(img, label, date_dot(d), zc(zs[0]))
    footer(img, page)
    return img


# ---------- 띠별 카드 ----------

def _zodiac_block(img, z, y, s, draw):
    d = ImageDraw.Draw(img)
    col = zc(z)
    ss = int(104 * s)
    tx = M + ss + int(36 * s)
    fn = font("serif", int(46 * s), 800)
    fs = font("serif", int(34 * s), 500)
    lines = wrap(z.summary, fs, W - M - tx)
    lh = int(54 * s)
    h = max(ss, int(70 * s) + len(lines) * lh)
    if draw:
        watermark(img, z.hanja, W - M - int(200 * s), y - int(30 * s), int(230 * s), col, 18 if T["dark"] else 16)
        seal(img, M, y, ss, z.hanja, col)
        d = ImageDraw.Draw(img)
        d.text((tx, y), z.name, font=fn, fill=col if not T["dark"] else T["accent"])
        ty = y + int(70 * s)
        for ln in lines:
            d.text((tx, ty), ln, font=fs, fill=T["text"])
            ty += lh
    return y + h


def zodiac_card(d, zs, label, page, seed=0):
    img = background()
    top, bottom = 200, H - 170
    s = 1.3
    while s > 0.6:
        hs = [_zodiac_block(img, z, 0, s, False) for z in zs]
        if sum(hs) + 80 * (len(zs) - 1) <= bottom - top:
            break
        s -= 0.03
    gap = min(((bottom - top) - sum(hs)) / max(1, len(zs) - 1), 140)
    y = top + max(0, ((bottom - top) - sum(hs) - gap * (len(zs) - 1)) / 2)
    for i, z in enumerate(zs):
        y = _zodiac_block(img, z, y, s, True)
        if i < len(zs) - 1:
            ImageDraw.Draw(img).line([(M, y + gap / 2), (W - M, y + gap / 2)], fill=T["line"], width=1)
            y += gap
    header(img, label, date_dot(d), zc(zs[0]))
    footer(img, page)
    return img


# ---------- 마무리 ----------

def outro(seed=0):
    img = background()
    watermark(img, "福", (W - 600) / 2, 330, 600, T["accent"], 14)
    corners(img, T["accent"])
    dr = ImageDraw.Draw(img)
    logo(img, W / 2, 420, 100)
    y = 600
    y = center(dr, y, "오늘도 평안한 하루 보내세요", font("serif", 58, 700), T["text"]) + 50
    dr.line([(W / 2 - 40, y), (W / 2 + 40, y)], fill=T["accent"], width=3)
    y += 56
    y = center(dr, y, ACCOUNT, font("serif", 42, 700), T["accent"]) + 24
    center(dr, y, "팔로우하고 매일의 운세를 받아보세요", font("sans", 28, 400), T["sub"])
    return img


def save(img, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=92, optimize=True)
    return path
