"""하루 게시 슬롯 설정.
실제 실행 시각은 .github/workflows/post.yml 의 cron(UTC)이 정합니다.
  morning : 매일 07:00 KST  오늘의 운세 (출생연도별)
  evening : 매일 17:30 KST  내일의 운세 (띠별)
"""

SLOTS = {
    "morning": dict(
        day_offset=0, kind="yearly", zodiacs=range(0, 12), per_card=2,
        title="오늘의 운세", subtitle="출생연도별 운세",
        theme="hanji",   # 아침: 한지 바탕 + 띠별 전통색
    ),
    "evening": dict(
        day_offset=1, kind="zodiac", zodiacs=range(0, 12), per_card=3,
        title="내일의 운세", subtitle="띠별 운세",
        theme="navy",    # 저녁: 남색 바탕 + 금색
    ),
}

TAGS = "#오늘의운세 #내일의운세 #띠별운세 #운세"


def caption(slot: dict, date_label: str, names: list[str]) -> str:
    guide = "태어난 해를 찾아 확인해 보세요." if slot["kind"] == "yearly" else "내 띠의 운세를 확인해 보세요."
    return "\n".join([
        f"{date_label} {slot['title']}",
        guide,
        "",
        TAGS,
    ])
