from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from services.market_service import MarketService
from services.score_service import ScoreService
from services.supply_api_service import SupplyAPIError, SupplyAPIService
from services.telegram_service import TelegramService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("marketpilot")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"필수 환경변수 {name}가 설정되지 않았습니다.")
    return value


def format_number(value: int | None) -> str:
    return "미집계" if value is None else f"{value:+,}"


def build_message(
    market: dict[str, float],
    supply: dict[str, Any],
    result: dict[str, Any],
) -> str:
    reasons = list(result.get("reasons", []))

    if not supply.get("program_available"):
        reasons = [
            reason
            for reason in reasons
            if "프로그램" not in reason
        ]
        reasons.append("⚪ 프로그램 수급 미집계")

    supply_date = str(supply.get("date", ""))
    if len(supply_date) == 8 and supply_date.isdigit():
        supply_date = f"{supply_date[:4]}-{supply_date[4:6]}-{supply_date[6:]}"

    reason_text = "\n".join(reasons) or "⚪ 판단 근거 없음"

    return f"""🚦 MarketPilot V2

━━━━━━━━━━━━━━

🇺🇸 미국시장

NASDAQ : {market['NASDAQ']:+.2f}%
S&P500 : {market['SP500']:+.2f}%
SOX : {market['SOX']:+.2f}%
VIX : {market['VIX']:+.2f}%

💵 환율

USD/KRW : {market['USDKRW']:+.2f}%

━━━━━━━━━━━━━━

📊 국내 수급 · KOSPI
기준일 : {supply_date or '확인 불가'}

외국인 : {format_number(supply.get('foreign'))}
기관 : {format_number(supply.get('institution'))}
프로그램 : {format_number(supply.get('program'))}

━━━━━━━━━━━━━━

🧠 AI SCORE

{result['score']} / 100

{result['signal']}

신뢰도 : {result['confidence']}%

━━━━━━━━━━━━━━

📌 판단 근거

{reason_text}

━━━━━━━━━━━━━━"""


async def main() -> None:
    bot_token = require_env("BOT_TOKEN")
    chat_id = require_env("CHAT_ID")
    telegram = TelegramService(bot_token)

    try:
        market = MarketService.get_market_data()
        logger.info("시장 데이터 수집 완료: %s", market)

        supply_service = SupplyAPIService()
        supply = supply_service.get_supply()
        logger.info("국내 수급 수집 완료: %s", supply)

        # 미집계(None)는 점수에서 중립으로 처리하고 메시지에는 그대로 표시한다.
        score_supply = {
            "foreign": supply.get("foreign"),
            "institution": supply.get("institution"),
            "program": supply.get("program"),
        }

        result = ScoreService().calculate(market, score_supply)
        message = build_message(market, supply, result)

    except SupplyAPIError as exc:
        logger.exception("KIS 수급 API 오류")
        message = f"❌ MarketPilot 수급 API 오류\n\n{exc}"
    except Exception as exc:
        logger.exception("MarketPilot 실행 오류")
        message = f"❌ MarketPilot 오류\n\n{type(exc).__name__}: {exc}"

    await telegram.send(chat_id, message)


if __name__ == "__main__":
    asyncio.run(main())
