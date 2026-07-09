import os
import asyncio

from services.kis_service import KISService
from services.telegram_service import TelegramService


BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


async def main():

    telegram = TelegramService(BOT_TOKEN)

    try:

        kis = KISService()

        token = kis.get_access_token()

        message = f"""
✅ MarketPilot V2

한국투자 OpenAPI 연결 성공

토큰 길이 : {len(token)}

토큰 앞 20자리

{token[:20]}...
"""

    except Exception as e:

        message = f"""
❌ MarketPilot V2

한국투자 OpenAPI 연결 실패

오류 :

{str(e)}
"""

    await telegram.send(
        CHAT_ID,
        message
    )


if __name__ == "__main__":
    asyncio.run(main())
