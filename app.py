import asyncio
import os

from services.market_service import MarketService
from services.score_service import ScoreService
from services.telegram_service import TelegramService

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


async def main():

    market = MarketService.get_market_data()

    score, signal = ScoreService.calculate(market)

    message = f"""
🚦 MarketPilot

NASDAQ : {market['NASDAQ']:+.2f}%

SOX : {market['SOX']:+.2f}%

NVIDIA : {market['NVDA']:+.2f}%

MICRON : {market['MU']:+.2f}%

━━━━━━━━━━━━━━

AI SCORE : {score}

{signal}
"""

    telegram = TelegramService(BOT_TOKEN)

    await telegram.send(
        CHAT_ID,
        message
    )


asyncio.run(main())
