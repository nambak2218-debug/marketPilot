import os
import asyncio

from services.market_service import MarketService
from services.score_service import ScoreService
from services.telegram_service import TelegramService


BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


async def main():

    telegram = TelegramService(BOT_TOKEN)


    try:

        # 시장 데이터
        market = MarketService.get_market_data()


        # 수급 데이터
        # (현재는 테스트 값, 다음 단계에서 OpenAPI 연결)
        supply_data = {
            "foreign": 1000,
            "institution": 500,
            "program": 700
        }


        # AI Score
        engine = ScoreService()

        result = engine.calculate(
            market,
            supply_data
        )


        reasons = "\n".join(
            result["reasons"]
        )


        message = f"""
🚦 MarketPilot V2

━━━━━━━━━━━━━━

🇺🇸 미국시장

NASDAQ : {market['NASDAQ']:+.2f}%

SOX : {market['SOX']:+.2f}%

VIX : {market['VIX']:+.2f}%


💵 환율

USD/KRW : {market['USDKRW']:+.2f}%


━━━━━━━━━━━━━━

🧠 AI SCORE

{result['score']} / 100

{result['signal']}

신뢰도 : {result['confidence']}%


━━━━━━━━━━━━━━

📌 판단 근거

{reasons}

━━━━━━━━━━━━━━
"""


    except Exception as e:

        message = f"""
❌ MarketPilot 오류

{e}
"""


    await telegram.send(
        CHAT_ID,
        message
    )



if __name__ == "__main__":
    asyncio.run(main())
