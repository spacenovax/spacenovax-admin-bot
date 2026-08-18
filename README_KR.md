# SpaceNovaX Telegram Community Bot

미션 기능을 포함하지 않는 커뮤니티 관리용 최종 버전입니다.

## 포함 기능
- `/start`, `/rules`, `/about`, `/help`, `/stats`
- 관리자 경고, 경고 취소, 차단, 차단 해제, 음소거, 메시지 고정
- 스팸·피싱 링크 및 금칙어 자동 삭제
- 경고 누적 및 자동 차단
- 신규 사용자 환영 메시지
- 그룹 입장 자동 인사 + 개인 봇 대화로 연결되는 12개국어 선택
- Captain ID·채굴 앱·커뮤니티 사용 가이드 버튼
- 공식 웹사이트·채널·그룹 버튼
- 선택적 SpaceNovaX Mini App 실행 버튼

## Mini App 버튼
Render 환경 변수에 `MINI_APP_URL`을 HTTPS 주소로 등록하면 `/start`에
`🚀 Launch SpaceNovaX` 버튼이 표시됩니다.

## Render 시작 명령
```bash
python bot.py
```

## Render 배포 설정
- 서비스 유형: Web Service
- Python 버전: 3.12.11 (`.python-version`에 고정됨)
- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot.py`
- Render가 제공하는 `PORT`와 `RENDER_EXTERNAL_URL`을 자동으로 사용합니다.
- `WEBHOOK_URL`은 선택 사항입니다. 별도로 지정할 때는
  `https://spacenovax-admin-bot.onrender.com`처럼 서비스의 공개 HTTPS 주소를 입력하세요.

## 환경 변수
`.env.example`을 참고해 Render 환경 변수에 값을 등록하세요.
실제 `.env` 파일이나 봇 토큰은 GitHub에 올리지 마세요.

추가 권장 값:

```text
BOT_USERNAME=SpaceNovaXAdminBot
MINI_APP_URL=https://app.spacenovax.com
COMMUNITY_GUIDE_URL=https://spacenovax.com/getting-started.html
OFFICIAL_GROUP=@spacesnovax
```

## 그룹 자동 환영 설정

1. 봇을 공식 Telegram 그룹에 추가하고 **관리자**로 지정합니다.
2. BotFather → `/setprivacy` → 해당 봇 → **Disable**로 설정합니다.
   - 이것은 스팸 방지·관리 기능에 필요합니다.
3. Render 환경 변수 저장 후 수동 배포(Manual Deploy)를 실행합니다.

신규 입장자는 그룹에서 짧은 환영 메시지를 받고, `Choose Language / 언어 선택`
버튼을 누르면 봇 개인 대화에서 12개국어를 선택합니다. 선택 후 Captain ID,
채굴 앱 및 커뮤니티 가이드 버튼이 표시됩니다. Telegram 정책상 봇은 사용자가
먼저 시작하지 않은 개인 대화에 직접 메시지를 보낼 수 없으므로, 이 방식이
가장 안정적인 공식 입장 흐름입니다.
