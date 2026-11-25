# unse-bot

unsin.co.kr 운세를 카드뉴스로 만들어 인스타그램 @unse_official 에 매일 자동 게시합니다.
GitHub Actions에서 돌아가므로 PC가 꺼져 있어도 동작하며, 모든 구성요소가 무료입니다.

| 시각 (KST) | 내용 | 카드 |
|---|---|---|
| 07:00 | 오늘의 운세 – 출생연도별 | 표지 + 띠 2개씩 6장 + 마무리 = 8장 |
| 07:00 직후 | 오늘의 운세 릴스 | 훅(운 좋은 띠 TOP 3) → 3·2·1위 → 조심할 띠 → 나머지 띠 → 피드 유도, 약 30초 |
| 17:30 | 내일의 운세 – 띠별 | 표지 + 띠 3개씩 4장 + 마무리 = 6장 |

## 구조
- `fortune.py` 운세 페이지 수집·파싱
- `render.py` 카드 이미지 생성 (1080×1350)
- `hook.py` 운세 문장의 좋은 말·나쁜 말로 띠 순위 매기기 (릴스 훅)
- `reel.py` 릴스 영상 생성 (1080×1920, ffmpeg)
- `bgm.py` 릴스 배경음 합성 (코드로 생성, 저작권 없음)
- `config.py` 게시 슬롯·캡션
- `main.py` 카드 생성 실행
- `publish.py` Instagram Graph API 캐러셀 게시
- `.github/workflows/post.yml` 하루 2회 예약 실행

## 필요한 Secrets (Settings → Secrets and variables → Actions)
| 이름 | 내용 |
|---|---|
| `IG_ACCESS_TOKEN` | 비즈니스 설정 → 시스템 사용자에서 발급한 토큰 (만료 없음) |
| `IG_USER_ID` | (선택) 비워 두면 토큰으로 @unse_official 계정 ID를 자동으로 찾습니다 |

## 테스트
Actions → "운세 카드 게시" → Run workflow
- `publish` 끄고 실행하면 카드만 만들어 Artifacts로 받아볼 수 있습니다.
- `publish` 켜면 즉시 인스타그램에 게시합니다.

## 로컬 실행
```bash
pip install -r requirements.txt
python main.py morning --date 2026-11-19
python reel.py --date 2026-11-19      # 릴스 (ffmpeg 필요)
```

릴스만 따로 시험하려면 Actions → Run workflow 에서 slot을 `reel`로 고르세요.
릴스가 실패해도 카드뉴스는 게시되고, 08:10 백업 실행이 릴스만 다시 시도합니다.
폰트(Noto Sans/Serif KR, OFL)는 `fonts/`에 두거나 워크플로처럼 Google Fonts에서 받습니다.
