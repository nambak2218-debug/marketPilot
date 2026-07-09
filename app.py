import os
import asyncio

from services.market_service import MarketService
from services.score_service import ScoreService
from services.telegram_service import TelegramService

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


async def main():

    # 시장 데이터 수집
    market = MarketService.get_market_data()

    # AI 점수 계산
    engine = ScoreService()

    result = engine.calculate(market)

    # 메시지 생성
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

{result['signal']}

신뢰도 : {result['confidence']}%

━━━━━━━━━━━━━━━━━━
"""

    telegram = TelegramService(BOT_TOKEN)

    await telegram.send_message(
        CHAT_ID,
        message
    )


asyncio.run(main())
