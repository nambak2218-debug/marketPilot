import os
from telegram import Bot
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

now = datetime.now().strftime("%Y-%m-%d %H:%M")

message = f"""
🚦 MarketPilot

✅ GitHub Actions 정상 실행

🕒 실행시간
{now}

다음 단계:
📈 미국시장 데이터 수집
🧠 AI 점수 계산
🚦 매매 신호 생성
"""

bot.send_message(
    chat_id=CHAT_ID,
    text=message
)

print("Telegram message sent.")
