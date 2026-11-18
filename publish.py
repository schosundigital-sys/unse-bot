"""인스타그램 캐러셀(카드뉴스) 게시 – Instagram Graph API (무료).

사용법: python publish.py <카드 폴더> <이미지 공개 URL 접두어>
  예) python publish.py out/2026-11-19/evening https://raw.githubusercontent.com/OWNER/REPO/SHA/

필요한 환경변수
  IG_USER_ID       인스타그램 비즈니스 계정 ID
  IG_ACCESS_TOKEN  접근 토큰
  GRAPH_HOST       (선택) 기본 graph.instagram.com  /  페이스북 로그인 방식이면 graph.facebook.com
  GRAPH_VERSION    (선택) 기본 v21.0
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent


def _base() -> str:
    return f"https://{os.getenv('GRAPH_HOST', 'graph.instagram.com')}/{os.getenv('GRAPH_VERSION', 'v21.0')}"


def _post(path: str, **data) -> dict:
    data["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{_base()}/{path}", data=data, timeout=60)
    if not r.ok:
        raise RuntimeError(f"POST {path} 실패 {r.status_code}: {r.text}")
    return r.json()


def _wait(container_id: str, timeout: int = 300) -> None:
    end = time.time() + timeout
    while time.time() < end:
        r = requests.get(
            f"{_base()}/{container_id}",
            params={"fields": "status_code", "access_token": os.environ["IG_ACCESS_TOKEN"]},
            timeout=30,
        ).json()
        st = r.get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"컨테이너 {container_id} 처리 실패: {r}")
        time.sleep(5)
    raise TimeoutError(f"컨테이너 {container_id} 처리 시간 초과")


def publish_carousel(image_urls: list[str], caption: str) -> str:
    uid = os.environ["IG_USER_ID"]
    children = []
    for u in image_urls:
        cid = _post(f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
        children.append(cid)
        print("  이미지 업로드:", u.rsplit("/", 1)[-1], cid)
    for cid in children:
        _wait(cid)
    parent = _post(f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
    _wait(parent)
    return _post(f"{uid}/media_publish", creation_id=parent)["id"]


def main() -> None:
    folder, base_url = Path(sys.argv[1]), sys.argv[2].rstrip("/") + "/"
    force = "--force" in sys.argv
    date_s, slot = folder.parts[-2], folder.parts[-1]
    marker = ROOT / "posted" / f"{date_s}-{slot}.json"
    if marker.exists() and not force:
        print(f"이미 게시됨({marker.name}) – 중복 게시 방지로 건너뜁니다.")
        return

    files = sorted(folder.glob("*.jpg"))
    urls = [base_url + f.as_posix() for f in files]
    caption = (folder / "caption.txt").read_text(encoding="utf-8")
    print(f"[{slot}] {date_s} 캐러셀 {len(urls)}장 게시 시작")
    media_id = publish_carousel(urls, caption)

    marker.parent.mkdir(exist_ok=True)
    marker.write_text(json.dumps({"date": date_s, "slot": slot, "media_id": media_id}), encoding="utf-8")
    print("게시 완료 media_id =", media_id)


if __name__ == "__main__":
    main()
