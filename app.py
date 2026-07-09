import os
from telegram import Bot

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

bot.send_message(
    chat_id=CHAT_ID,
    text="🚀 MarketPilot v1.0\n\nGitHub Actions 연결 성공!"
)

print("Done")
