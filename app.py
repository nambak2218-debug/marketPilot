import os
import asyncio
import yfinance as yf
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


def pct(symbol):
    df = yf.download(symbol, period="5d", progress=False, auto_adjust=True)

    close = df["Close"].dropna()

    today = float(close.iloc[-1])
    yesterday = float(close.iloc[-2])

    return round((today - yesterday) / yesterday * 100, 2)


def score(nasdaq, sox, nvda, mu):

    score = 50

    score += nasdaq * 5
    score += sox * 3
    score += nvda * 2
    score += mu * 2

    score = max(0, min(100, round(score)))

    if score >= 70:
        signal = "🟢 레버리지 우세"

    elif score >= 40:
        signal = "🟡 관망"

    else:
        signal = "🔴 인버스 우세"

    return score, signal


async def main():

    nasdaq = pct("^IXIC")
    sox = pct("^SOX")
    nvda = pct("NVDA")
    mu = pct("MU")

    s, signal = score(nasdaq, sox, nvda, mu)

    text = f"""
🚦 MarketPilot

🇺🇸 미국시장

NASDAQ {nasdaq:+.2f}%

SOX {sox:+.2f}%

NVIDIA {nvda:+.2f}%

MICRON {mu:+.2f}%

━━━━━━━━━━━━━━

🧠 AI SCORE : {s}

{signal}

━━━━━━━━━━━━━━
"""

    bot = Bot(BOT_TOKEN)

    await bot.send_message(
        chat_id=CHAT_ID,
        text=text
    )


asyncio.run(main())
