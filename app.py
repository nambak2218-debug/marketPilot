import os
import asyncio
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

async def main():
    bot = Bot(token=BOT_TOKEN)

    await bot.send_message(
        chat_id=CHAT_ID,
        text="🚀 MarketPilot 연결 성공!\n\nGitHub Actions에서 보낸 첫 번째 메시지입니다."
    )

    print("SUCCESS")

asyncio.run(main())
