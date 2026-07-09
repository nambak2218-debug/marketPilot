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

        # =========================
        # 1. 시장 데이터 수집
        # =========================

        market = MarketService.get_market_data()


        # =========================
        # 2. 한국투자 수급 데이터
        # =========================

        supply_api = SupplyAPIService()

        supply = supply_api.get_supply()


        output = supply.get(
            "output",
            []
        )


        if output:

            today_supply = output[0]

            supply_data = {

                "foreign": int(
                    today_supply.get(
                        "frgn_ntby_qty",
                        0
                    )
                ),

                "institution": int(
                    today_supply.get(
                        "orgn_ntby_qty",
                        0
                    )
                ),

                "program": int(
                    today_supply.get(
                        "prgm_ntby_qty",
                        0
                    )
                )
            }

        else:

            supply_data = {

                "foreign": 0,

                "institution": 0,

                "program": 0
            }


        # =========================
        # 3. AI Score 계산
        # =========================

        engine = ScoreService()

        result = engine.calculate(
            market,
            supply_data
        )


        reasons = "\n".join(
            result["reasons"]
        )


        # =========================
        # 4. Telegram 메시지
        # =========================

        message = f"""
🚦 MarketPilot V2

━━━━━━━━━━━━━━

🇺🇸 미국시장

NASDAQ : {market['NASDAQ']:+.2f}%

S&P500 : {market['SP500']:+.2f}%

SOX : {market['SOX']:+.2f}%

VIX : {market['VIX']:+.2f}%


💵 환율

USD/KRW : {market['USDKRW']:+.2f}%


━━━━━━━━━━━━━━

📊 국내 수급

외국인 : {supply_data['foreign']:,}

기관 : {supply_data['institution']:,}

프로그램 : {supply_data['program']:,}


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

{str(e)}
"""


    await telegram.send(
        CHAT_ID,
        message
    )


if __name__ == "__main__":
    asyncio.run(main())
