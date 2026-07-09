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

        msg = f"""
✅ 한국투자 OpenAPI 연결 성공

토큰 길이 : {len(token)}

앞 20자리

{token[:20]}...
"""

    except Exception as e:

        msg = f"""
❌ 한국투자 OpenAPI 연결 실패

{e}
"""

    await telegram.send(
        CHAT_ID,
        msg
    )


if __name__ == "__main__":
    asyncio.run(main())
