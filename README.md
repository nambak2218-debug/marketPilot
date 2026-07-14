# MarketPilot V5 Final

## 자동 실행 시간 (KST)

- 평일 08:20: 장전 전략 알림 및 기록
- 평일 09:10: 장초반 알림 및 기록
- 평일 11:30: 오전장 알림 및 기록
- 평일 14:10: 오후 변곡점 알림 및 기록
- 평일 15:15: 마감 직전 알림 및 기록
- 평일 15:40: 당일 KOSPI 종가 기준 성과 평가(CSV 갱신, 기본적으로 텔레그램 알림 없음)
- 매월 1일 16:00: 전월 월간 점검보고서 PDF와 상세 CSV를 텔레그램으로 전송

## 필요한 GitHub Secrets

- BOT_TOKEN
- CHAT_ID
- KIS_APP_KEY
- KIS_APP_SECRET
- KIS_BASE_URL

## 설치

ZIP 내부 파일을 저장소의 동일 경로에 덮어쓰고 커밋/푸시합니다.
GitHub Actions의 `permissions: contents: write`가 적용되어야 신호 이력이 저장소에 누적됩니다.

## 수동 테스트

Actions > MarketPilot V5 Final > Run workflow에서 실행 모드를 선택합니다.

- `alert`: 즉시 알림을 보내고 신호를 기록
- `evaluate`: 당일 기록의 성과를 평가
- `monthly_report`: 전월 보고서를 생성하여 텔레그램 전송

## 주의

- 장전 신호의 진입가는 당일 KOSPI 시가를 사용합니다.
- 장중 신호는 실행 시점에 조회한 5분봉 근사값을 사용합니다.
- 관망은 신호 이후 종가 변동률이 ±0.4% 이내일 때 적중으로 평가합니다.
- 데이터가 최소 30건 이상 쌓이기 전에는 통계 결과를 초기 점검용으로만 해석하세요.
