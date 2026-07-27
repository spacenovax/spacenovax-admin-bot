# SpaceNovaX Telegram Community Bot

미션 기능을 포함하지 않는 커뮤니티 관리용 최종 버전입니다.

## 포함 기능
- `/start`, `/rules`, `/about`, `/help`, `/stats`
- 관리자 경고, 경고 취소, 차단, 차단 해제, 음소거, 메시지 고정
- 스팸·피싱 링크 및 금칙어 자동 삭제
- 경고 누적 및 자동 차단
- 신규 사용자 환영 메시지
- 공식 웹사이트·채널·그룹 버튼
- 선택적 SpaceNovaX Mini App 실행 버튼

## Mini App 버튼
Render 환경 변수에 `MINI_APP_URL`을 HTTPS 주소로 등록하면 `/start`에
`🚀 Launch SpaceNovaX` 버튼이 표시됩니다.

## Render 시작 명령
```bash
python bot.py
```

## 환경 변수
`.env.example`을 참고해 Render 환경 변수에 값을 등록하세요.
실제 `.env` 파일이나 봇 토큰은 GitHub에 올리지 마세요.
