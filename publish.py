"""인스타그램 캐러셀(카드뉴스)·릴스 게시 – Instagram Graph API (무료).

사용법: python publish.py <카드 폴더> <이미지 공개 URL 접두어>
        python publish.py --reel out/<날짜>/reel <공개 URL 접두어>   (릴스)
  예) python publish.py out/2026-11-19/evening https://raw.githubusercontent.com/OWNER/REPO/SHA/

필요한 환경변수
  IG_USER_ID       (선택) 없으면 토큰으로 @unse_official 계정 ID를 자동 조회
  IG_ACCESS_TOKEN  시스템 사용자 토큰 (만료 없음)
  GRAPH_HOST       (선택) 기본 graph.facebook.com
  GRAPH_VERSION    (선택) 비우면 앱 기본 버전 사용
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent


class AuthError(RuntimeError):
    """토큰 문제 – 재시도해도 소용없음."""


def _base() -> str:
    # 버전을 지정하지 않으면 앱 기본 버전을 쓰고, 오래된 버전 만료 시에도 자동으로 올라갑니다.
    host = os.getenv("GRAPH_HOST") or "graph.facebook.com"
    ver = os.getenv("GRAPH_VERSION")
    return f"https://{host}/{ver}" if ver else f"https://{host}"


def _call(method: str, path: str, tries: int = 4, **data) -> dict:
    """네트워크 오류·일시적 서버 오류는 재시도, 토큰 오류는 즉시 실패."""
    data["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    last = ""
    for i in range(tries):
        try:
            if method == "GET":
                r = requests.get(f"{_base()}/{path}", params=data, timeout=60)
            else:
                r = requests.post(f"{_base()}/{path}", data=data, timeout=60)
            body = r.json() if r.content else {}
            if r.ok and "error" not in body:
                return body
            err = body.get("error", {})
            if err.get("code") == 190 or r.status_code in (401, 403) and err.get("type") == "OAuthException" and err.get("code") in (190, 102):
                raise AuthError(f"토큰이 만료됐거나 권한이 없습니다: {err.get('message')}")
            last = f"{method} {path} {r.status_code}: {err or r.text[:300]}"
        except AuthError:
            raise
        except (requests.RequestException, ValueError) as e:
            last = f"{method} {path} 네트워크 오류: {e}"
        print("  재시도 대기 –", last)
        time.sleep(15 * (i + 1))
    raise RuntimeError(last)


def _wait(container_id: str, timeout: int = 300) -> None:
    end = time.time() + timeout
    while time.time() < end:
        st = _call("GET", container_id, fields="status_code").get("status_code")
        if st in ("FINISHED", "PUBLISHED"):
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"컨테이너 {container_id} 처리 실패({st})")
        time.sleep(5)
    raise TimeoutError(f"컨테이너 {container_id} 처리 시간 초과")


def find_ig_user_id(username: str = "unse_official") -> str:
    """IG_USER_ID가 없으면 토큰으로 연결된 페이지에서 인스타 계정 ID를 찾습니다."""
    r = _call("GET", "me/accounts", fields="name,instagram_business_account{id,username}")
    found = [p["instagram_business_account"] for p in r.get("data", []) if p.get("instagram_business_account")]
    for a in found:
        if a.get("username") == username:
            return a["id"]
    raise RuntimeError(f"@{username} 계정을 찾지 못했습니다. 토큰에 연결된 계정: {[a.get('username') for a in found]}")


def publish_carousel(image_urls: list[str], caption: str) -> str:
    uid = os.getenv("IG_USER_ID") or find_ig_user_id()
    print("  인스타 계정 ID:", uid)

    # 1) 컨테이너 준비 – 이미지 처리 실패 시 컨테이너를 새로 만들어 최대 3번 시도 (아직 게시 전이라 중복 위험 없음)
    parent = None
    for attempt in range(3):
        try:
            children = []
            for u in image_urls:
                cid = _call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
                children.append(cid)
                print("  이미지 업로드:", u.rsplit("/", 1)[-1], cid)
            for cid in children:
                _wait(cid)
            parent = _call("POST", f"{uid}/media", media_type="CAROUSEL",
                           children=",".join(children), caption=caption)["id"]
            _wait(parent)
            break
        except AuthError:
            raise
        except Exception as e:
            print(f"  컨테이너 준비 실패({attempt + 1}/3): {e}")
            if attempt == 2:
                raise
            time.sleep(60)

    return _publish(uid, parent)


def _publish(uid: str, parent: str) -> str:
    """게시 – 응답이 끊겨도 실제로 게시됐는지 확인한 뒤에만 다시 시도 (중복 게시 방지)."""
    for attempt in range(3):
        try:
            return _call("POST", f"{uid}/media_publish", tries=1, creation_id=parent)["id"]
        except AuthError:
            raise
        except Exception as e:
            print(f"  게시 요청 오류({attempt + 1}/3): {e}")
            time.sleep(20)
            try:
                st = _call("GET", parent, fields="status_code").get("status_code")
            except Exception:
                st = None
            if st == "PUBLISHED":
                print("  확인 결과 이미 게시됨")
                return f"published:{parent}"
            if attempt == 2:
                raise


def video_urls(base_url: str, path: str) -> list[str]:
    """영상 주소 후보: jsDelivr(영상 형식 헤더가 정확함) → raw.githubusercontent 순서."""
    urls = []
    if base_url.startswith("https://raw.githubusercontent.com/"):
        owner, repo, sha = base_url.split("/")[3:6]
        urls.append(f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@{sha}/{path}")
    urls.append(base_url + path)
    return urls


def publish_reel(video_urls_: list[str], caption: str, cover_url: str | None = None) -> str:
    uid = os.getenv("IG_USER_ID") or find_ig_user_id()
    print("  인스타 계정 ID:", uid)
    parent, last = None, None
    for url in video_urls_:
        for attempt in range(2):
            try:
                data = dict(media_type="REELS", video_url=url, caption=caption, share_to_feed="true")
                if cover_url:
                    data["cover_url"] = cover_url
                parent = _call("POST", f"{uid}/media", **data)["id"]
                print("  릴스 업로드:", url, parent)
                _wait(parent, timeout=900)  # 영상은 처리에 1~5분 걸림
                break
            except AuthError:
                raise
            except Exception as e:
                last = e
                parent = None
                print(f"  릴스 컨테이너 실패({url}, {attempt + 1}/2): {e}")
                time.sleep(30)
        if parent:
            break
    if not parent:
        raise RuntimeError(f"릴스 영상 처리 실패: {last}")
    return _publish(uid, parent)


def main() -> None:
    if sys.argv[1:] == ["--check"]:  # 게시 없이 토큰·계정 연결만 확인
        uid = os.getenv("IG_USER_ID") or find_ig_user_id()
        info = _call("GET", uid, fields="username,media_count")
        print(f"토큰 정상 – @{info.get('username')} (게시물 {info.get('media_count')}개)")
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    folder, base_url = Path(args[0]), args[1].rstrip("/") + "/"
    if "--reel" in sys.argv:
        return main_reel(folder, base_url, force)
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


def main_reel(folder: Path, base_url: str, force: bool) -> None:
    """python publish.py --reel out/<날짜>/reel <공개 URL 접두어>"""
    date_s = folder.parts[-2]
    marker = ROOT / "posted" / f"{date_s}-reel.json"
    if marker.exists() and not force:
        print(f"이미 게시됨({marker.name}) – 중복 게시 방지로 건너뜁니다.")
        return
    caption = (folder / "caption.txt").read_text(encoding="utf-8")
    cover = folder / "cover.jpg"
    cover_url = base_url + cover.as_posix() if cover.exists() else None
    print(f"[reel] {date_s} 릴스 게시 시작")
    media_id = publish_reel(video_urls(base_url, (folder / "reel.mp4").as_posix()), caption, cover_url)
    marker.parent.mkdir(exist_ok=True)
    marker.write_text(json.dumps({"date": date_s, "slot": "reel", "media_id": media_id}), encoding="utf-8")
    print("릴스 게시 완료 media_id =", media_id)


if __name__ == "__main__":
    main()
