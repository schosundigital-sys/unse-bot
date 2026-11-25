"""릴스 훅용 띠 순위 – 운세 문장 속 좋은 말/나쁜 말을 세어 점수를 매깁니다 (무료, API 없음).

  TOP 3   : 점수가 가장 높은 띠 3개 (3위 → 2위 → 1위 순서로 공개)
  주의 띠 : 점수가 가장 낮은 띠 1개
  나머지  : 그 외 8개 띠 (띠 순서대로)
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass

from fortune import Zodiac

GOOD = {
    "재물": 2, "재수": 2, "복": 2, "횡재": 3, "대길": 3, "길하": 2, "행운": 3, "귀인": 2, "경사": 2, "성공": 2,
    "이루": 2, "얻": 2, "기쁨": 2, "기쁜": 2, "기분좋": 2, "즐거": 2, "순조": 2, "순항": 2, "양호": 2,
    "평온": 1, "편안": 1, "좋은 소식": 3, "좋은": 1, "좋습니다": 1, "상승": 2, "도움": 2, "형통": 3,
    "이익": 2, "합격": 2, "승진": 2, "인기": 1, "사랑": 1, "신뢰": 1, "생동": 2, "풍족": 2, "번창": 3,
    "순풍": 3, "희망": 2, "해소": 1, "감사": 1, "행복": 2, "성사": 2, "보람": 2, "만족": 2, "빛나": 2,
    "만사": 2, "기분 좋": 2, "성과": 2, "금전운": 2, "활기": 1, "반겨": 1,
}
BAD = {
    "손해": 2, "잃": 2, "망신": 3, "다툼": 2, "다투": 2, "구설": 2, "실수": 2, "흉": 3, "근심": 2,
    "걱정": 1, "조심": 1, "주의": 1, "유의": 1, "막히": 2, "고생": 2, "곤란": 2, "괴로": 2, "실패": 3,
    "불안": 2, "어려": 1, "지쳐": 1, "피로": 1, "상해": 2, "나쁜": 2, "놓치": 1, "가벼워": 1, "지출": 1,
    "건강운이 안좋": 3, "흠": 1, "경솔": 2, "어수선": 1, "가라앉": 1, "돈을 좀 써야": 2,
    "탐내": 1, "헛된": 1, "스트레스": 1, "끝이 없": 1, "분명치": 1, "어렵": 2,
}

# 날마다 바뀌는 훅 문구 (같은 문구 반복으로 식상해지지 않게)
HOOKS = [
    ("오늘 운 터지는 띠", "TOP 3"),
    ("오늘 대박 나는 띠", "TOP 3"),
    ("오늘 웃게 될 띠", "TOP 3"),
    ("오늘 일 풀리는 띠", "TOP 3"),
]


@dataclass
class Ranked:
    z: Zodiac
    score: float
    best: tuple[str, str] | None   # 가장 좋은 출생연도 한 줄
    worst: tuple[str, str] | None  # 가장 조심할 출생연도 한 줄


def _score(text: str) -> float:
    s = 0.0
    for w, v in GOOD.items():
        s += v * len(re.findall(w, text))
    for w, v in BAD.items():
        s -= v * len(re.findall(w, text))
    return s


def rank(zs: list[Zodiac], seed: int = 0) -> list[Ranked]:
    rnd = random.Random(seed)
    out = []
    for z in zs:
        ys = [(y, t, _score(t)) for y, t in z.years]
        total = _score(z.summary) * 2 + sum(s for *_, s in ys) + rnd.random() * 0.01  # 동점은 날짜별로 섞기
        best = max(ys, key=lambda r: r[2], default=None)
        worst = min(ys, key=lambda r: r[2], default=None)
        out.append(Ranked(z, total, best[:2] if best else None, worst[:2] if worst else None))
    return sorted(out, key=lambda r: r.score, reverse=True)


def pick(zs: list[Zodiac], seed: int = 0):
    """(훅 문구, TOP3[1위,2위,3위], 주의 띠, 나머지 8띠[띠 순서])"""
    r = rank(zs, seed)
    top, warn = r[:3], r[-1]
    used = {x.z.name for x in top} | {warn.z.name}
    rest = [x for x in sorted(r, key=lambda x: [z.name for z in zs].index(x.z.name)) if x.z.name not in used]
    hook = HOOKS[seed % len(HOOKS)]
    return hook, top, warn, rest


if __name__ == "__main__":
    import sys
    from datetime import date

    import fortune

    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    for x in rank(fortune.fetch(d), d.toordinal()):
        print(f"{x.score:6.1f} {x.z.name:5} | {x.z.summary[:40]} | best={x.best}")
