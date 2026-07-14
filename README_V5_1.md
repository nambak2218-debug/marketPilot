# MarketPilot V5.1 Final

주요 변경: reportlab 설치 검증, KRX 휴장일 처리, yfinance 재시도/부분 누락 중립처리, KOSPI/KOSPI200 표시, 외국인·기관 수급을 순매수 대금(백만원)으로 변경, 전체/외국인 프로그램 수량 병기, 선택적 KOSPI200 선물 괴리율 반영.

## 선택 Secrets
- KIS_FUTURES_CODE: 최근월물 KOSPI200 선물 단축코드
- KIS_NIGHT_FUTURES_CODE: 야간선물 코드(사용 계정/API 지원 시)

선물 코드를 설정하지 않아도 기존 기능은 정상 작동합니다. 월물 교체 시 코드를 갱신해야 합니다.
