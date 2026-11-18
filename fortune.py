"""unsin.co.kr 오늘의 운세 페이지를 가져와 띠별/연도별 데이터로 파싱."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import date

import requests

URL = "https://unsin.co.kr/unse/free/todaylinesc2/result?setDate={d}"
UA = "Mozilla/5.0 (compatible; unse-card-bot/1.0)"

# 띠 순서와 한자(카드 배지용)
ZODIAC = [
    ("쥐띠", "子"), ("소띠", "丑"), ("범띠", "寅"), ("토끼띠", "卯"),
    ("용띠", "辰"), ("뱀띠", "巳"), ("말띠", "午"), ("양띠", "未"),
    ("원숭이띠", "申"), ("닭띠", "酉"), ("개띠", "戌"), ("돼지띠", "亥"),
]
HANJA = dict(ZODIAC)


@dataclass
class Zodiac:
    name: str          # 쥐띠
    hanja: str         # 子
    summary: str       # 띠 총평
    years: list[tuple[str, str]] = field(default_factory=list)  # [("60년생", "...")]


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse(page: str) -> list[Zodiac]:
    body = page.split("<!--date-->", 1)[-1]
    out: list[Zodiac] = []
    for m in re.finditer(r"([가-힣]+띠)\s*:\s*(.*?)<table>(.*?)</table>", body, re.S):
        name, summary, table = m.group(1), _clean(m.group(2)), m.group(3)
        years = [
            (f"{y}년생", _clean(t))
            for y, t in re.findall(r"<td>\s*(\d{2})년생\s*:\s*(.*?)</td>", table, re.S)
        ]
        out.append(Zodiac(name, HANJA.get(name, ""), summary, years))
    names = [z.name for z in out]
    if names != [n for n, _ in ZODIAC]:
        raise ValueError(f"페이지 구조가 예상과 다릅니다. 파싱된 띠: {names}")
    return out


def fetch(d: date) -> list[Zodiac]:
    r = requests.get(URL.format(d=d.isoformat()), headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    page = r.content.decode("utf-8", "ignore")
    return parse(page)


if __name__ == "__main__":
    import sys
    from datetime import datetime, timedelta, timezone

    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(timezone(timedelta(hours=9))).date()
    for z in fetch(d):
        print(z.name, z.hanja, "|", z.summary)
        for y, t in z.years:
            print("   ", y, t)
