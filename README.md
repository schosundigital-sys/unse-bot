# unse-bot

unsin.co.kr 운세를 카드뉴스로 만들어 인스타그램 @unse_official 에 매일 자동 게시합니다.
GitHub Actions에서 돌아가므로 PC가 꺼져 있어도 동작하며, 모든 구성요소가 무료입니다.

| 시각 (KST) | 내용 | 카드 |
|---|---|---|
| 07:00 | 오늘의 운세 – 출생연도별 | 표지 + 띠 2개씩 6장 + 마무리 = 8장 |
| 17:30 | 내일의 운세 – 띠별 | 표지 + 띠 3개씩 4장 + 마무리 = 6장 |

## 구조
- `fortune.py` 운세 페이지 수집·파싱
- `render.py` 카드 이미지 생성 (1080×1350)
- `config.py` 게시 슬롯·캡션
- `main.py` 카드 생성 실행
- `publish.py` Instagram Graph API 캐러셀 게시
- `.github/workflows/post.yml` 하루 2회 예약 실행
- `.github/workflows/refresh-token.yml` 인스타 토큰 매주 자동 갱신

## 필요한 Secrets (Settings → Secrets and variables → Actions)
| 이름 | 내용 |
|---|---|
| `IG_USER_ID` | 인스타그램 계정 ID (Meta 앱 대시보드에서 확인) |
| `IG_ACCESS_TOKEN` | Instagram API 접근 토큰 |
| `GH_PAT` | 이 저장소의 Secrets 쓰기 권한을 가진 Fine-grained 토큰 (토큰 자동 갱신용) |

## 테스트
Actions → "운세 카드 게시" → Run workflow
- `publish` 끄고 실행하면 카드만 만들어 Artifacts로 받아볼 수 있습니다.
- `publish` 켜면 즉시 인스타그램에 게시합니다.

## 로컬 실행
```bash
pip install -r requirements.txt
python main.py morning --date 2026-11-19
```
폰트(Noto Sans/Serif KR, OFL)는 `fonts/`에 두거나 워크플로처럼 Google Fonts에서 받습니다.
