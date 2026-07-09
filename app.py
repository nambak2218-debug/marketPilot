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
        # 1. 시장 데이터
        # =========================

        market = MarketService.get_market_data()


        # =========================
        # 2. 한국투자 수급 데이터
        # =========================

        supply_api = SupplyAPIService()

        supply = supply_api.get_supply()


        # 원본 응답 확인용
        print("===== SUPPLY DATA START =====")
        print(supply)
        print("===== SUPPLY DATA END =====")


        # 기본값
        supply_data = {
            "foreign": 0,
            "institution": 0,
            "program": 0
        }


        # API 응답 구조 확인 후 자동 처리
        output = supply.get("output", [])


        if isinstance(output, list) and len(output) > 0:

            data = output[0]

            supply_data["foreign"] = int(
                data.get(
                    "frgn_ntby_qty",
                    0
                )
            )

            supply_data["institution"] = int(
                data.get(
                    "orgn_ntby_qty",
                    0
                )
            )

            supply_data["program"] = int(
                data.get(
                    "prgm_ntby_qty",
                    0
                )
            )


        elif isinstance(output, dict):

            supply_data["foreign"] = int(
                output.get(
                    "frgn_ntby_qty",
                    0
                )
            )

            supply_data["institution"] = int(
                output.get(
                    "orgn_ntby_qty",
                    0
                )
            )

            supply_data["program"] = int(
                output.get(
                    "prgm_ntby_qty",
                    0
                )
            )


        # =========================
        # 3. AI Score
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
        # 4. Telegram
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
