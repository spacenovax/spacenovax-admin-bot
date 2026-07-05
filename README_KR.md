# SpaceNovaX Mining Points Bot

## 포함 링크
- YouTube: https://youtube.com/@spacenovaxteam?si=EYRw26QnrhXUkov8
- X: https://x.com/spacenovaxteam
- Telegram Group: https://t.me/spacesnovax
- Telegram Channel: https://t.me/spacenovaxteam
- Discord: https://discord.gg/rxVNWMC8e8
- Website: http://www.spacenovax.com

## 기능
- /mine : 24시간마다 100 SNP 적립
- /mission : 미션 목록
- /done youtube : 유튜브 구독 완료 기록
- /done x : X 팔로우 완료 기록
- /done telegram_group : 텔레그램 그룹 완료 기록
- /done telegram_channel : 텔레그램 채널 완료 기록
- /done discord : 디스코드 완료 기록
- /done website : 웹사이트 방문 완료 기록
- /points : 내 포인트 확인
- /ref : 추천 링크
- /rank : 랭킹
- /wallet : Solana 지갑 등록
- /export : 관리자 CSV 다운로드

## 설치
```cmd
python -m pip install -r requirements.txt
```

## 설정
.env.example 파일 이름을 .env로 바꾼 뒤 아래 값을 수정하세요.

```text
BOT_TOKEN=BotFather 토큰
ADMIN_IDS=내 텔레그램 숫자 ID
```

## 실행
```cmd
python bot.py
```

성공 메시지:
```text
SpaceNovaX Mining Points Bot is running...
```

## 중요
초기 버전은 사용자가 /done 명령으로 미션 완료를 직접 기록하는 방식입니다.
최종 SPNX 전환 전에는 /export 파일을 기준으로 중복/부정 계정을 검토하는 것을 추천합니다.
