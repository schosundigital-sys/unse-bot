"""슬롯 하나를 실행: 운세 수집 → 카드 생성 → (옵션) 인스타그램 게시.

사용법:
  python main.py morning                # 오늘 날짜 기준 생성만
  python main.py evening --date 2026-11-19
  (게시는 publish.py 가 담당)
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config
import fortune
import render

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).parent


def build(slot_name: str, base: date) -> tuple[list[Path], str, date]:
    slot = config.SLOTS[slot_name]
    render.set_theme(slot.get("theme", "hanji"))
    d = base + timedelta(days=slot["day_offset"])
    zs = fortune.fetch(d)
    picked = [zs[i] for i in slot["zodiacs"]]
    names = [z.name for z in picked]
    groups = [picked[i:i + slot["per_card"]] for i in range(0, len(picked), slot["per_card"])]
    total = len(groups) + 2
    if total > 10:
        raise ValueError(f"캐러셀은 최대 10장입니다 (현재 {total}장). per_card를 늘려주세요.")

    out = ROOT / "out" / d.isoformat() / slot_name
    seed = d.toordinal() + sum(map(ord, slot_name))
    label = slot['title']
    files = [render.save(render.cover(d, slot["title"], slot["subtitle"], names, seed), out / "01.jpg")]
    for i, g in enumerate(groups, start=2):
        page = f"{i}/{total}"
        fn = render.yearly_card if slot["kind"] == "yearly" else render.zodiac_card
        files.append(render.save(fn(d, g, label, page, seed + i), out / f"{i:02d}.jpg"))
    files.append(render.save(render.outro(), out / f"{total:02d}.jpg"))

    cap = config.caption(slot, render.date_label(d), names)
    (out / "caption.txt").write_text(cap, encoding="utf-8")
    return files, cap, d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slot", choices=list(config.SLOTS))
    ap.add_argument("--date", help="기준 날짜 YYYY-MM-DD (기본: 오늘 KST)")
    a = ap.parse_args()

    base = date.fromisoformat(a.date) if a.date else datetime.now(KST).date()
    files, cap, d = build(a.slot, base)
    out_dir = files[0].parent.relative_to(ROOT).as_posix()
    print(f"[{a.slot}] {d} 카드 {len(files)}장 생성 → {out_dir}")

    gh_out = os.getenv("GITHUB_OUTPUT")
    if gh_out:  # GitHub Actions 다음 단계로 폴더 경로 전달
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"out={out_dir}\n")


if __name__ == "__main__":
    main()
