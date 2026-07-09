import os
import asyncio

from services.market_service import MarketService
from services.score_service import ScoreService
from services.telegram_service import TelegramService
from services.signal_service import SignalService
from services.history_service import HistoryService


BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


async def main():

    # 시장 데이터 수집
    market = MarketService.get_market_data()

    # AI 점수 계산
    engine = ScoreService()
    result = engine.calculate(market)

    # 매매 신호 생성
    signal = SignalService.decide(result["score"])

    # 기록 저장
    HistoryService.save(
        result["score"],
        signal,
        market
    )

    # 텔레그램 메시지
    message = f"""
🚦 MarketPilot V1

━━━━━━━━━━━━━━━━━━

🇺🇸 미국시장

NASDAQ : {market['NASDAQ']:+.2f}%

S&P500 : {market['SP500']:+.2f}%

SOX : {market['SOX']:+.2f}%

VIX : {market['VIX']:+.2f}%

━━━━━━━━━━━━━━━━━━

💻 반도체

NVIDIA : {market['NVDA']:+.2f}%

MICRON : {market['MU']:+.2f}%

━━━━━━━━━━━━━━━━━━

💵 환율

USD/KRW : {market['USDKRW']:+.2f}%

━━━━━━━━━━━━━━━━━━

🧠 AI SCORE

{result['score']}점

{signal}

신뢰도 : {result['confidence']}%

━━━━━━━━━━━━━━━━━━
"""

    telegram = TelegramService(BOT_TOKEN)

    await telegram.send(
        CHAT_ID,
        message
    )


if __name__ == "__main__":
    asyncio.run(main())
