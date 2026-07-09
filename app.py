import os
import asyncio

from services.market_service import MarketService
from services.score_service import ScoreService
from services.telegram_service import TelegramService
from services.supply_api_service import SupplyAPIService


BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


async def main():

    telegram = TelegramService(BOT_TOKEN)


    try:

        # 시장 데이터
        market = MarketService.get_market_data()


        # 실제 수급 데이터
        supply_api = SupplyAPIService()

supply = supply_api.get_supply()

print(supply)

        # 임시 변환
        # API 응답 구조 확인 후 정확한 필드 연결 예정
        supply_data = {

            "foreign": 0,

            "institution": 0,

            "program": 0
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
