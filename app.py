from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from services.market_service import MarketService
from services.score_service import ScoreService
from services.supply_api_service import SupplyAPIError, SupplyAPIService
from services.telegram_service import TelegramService

KST = ZoneInfo("Asia/Seoul")

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


def get_market_session(now: datetime | None = None) -> str:
    current = now or datetime.now(KST)
    if current.weekday() >= 5:
        return "closed"
    if current.time() < time(9, 0):
        return "pre_market"
    if current.time() <= time(15, 30):
        return "market_open"
    return "after_market"


def get_report_slot(now: datetime | None = None) -> tuple[str, str, str]:
    current = now or datetime.now(KST)
    current_time = current.time()
    if current_time < time(9, 0):
        return "pre_market", "🌅 장전 전략", "미국시장과 최근 국내 수급 기반 1차 방향 판단"
    if current_time < time(10, 30):
        return "opening", "🚀 장초반 확인", "장전 시나리오와 실제 수급이 일치하는지 점검"
    if current_time < time(13, 0):
        return "midday", "☀️ 오전장 점검", "오전 추세의 지속성과 수급 방향 점검"
    if current_time < time(15, 0):
        return "afternoon", "🌤 오후 변곡점", "오후 수급 변화와 추세 전환 가능성 점검"
    return "closing", "🔔 마감 직전", "종가 전 최종 수급과 다음 거래일 준비"


def market_session_label(session: str) -> str:
    return {
        "pre_market": "장 개시 전",
        "market_open": "장중",
        "after_market": "장 마감 후",
        "closed": "휴장일",
    }.get(session, "상태 확인 불가")


def format_supply_value(value: int | None, *, kind: str, session: str) -> str:
    if value is not None:
        return f"{value:+,}"
    if kind == "program":
        if session == "pre_market":
            return "장 개시 전"
        if session == "market_open":
            return "장중 미집계"
        if session == "closed":
            return "휴장일"
    return "미집계"


def format_date(value: Any) -> str:
    raw = str(value or "")
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw or "확인 불가"


def star_gauge(level: int) -> str:
    safe_level = max(1, min(5, int(level)))
    return "★" * safe_level + "☆" * (5 - safe_level)


def build_message(
    market: dict[str, float],
    supply: dict[str, Any],
    result: dict[str, Any],
    now: datetime,
) -> str:
    session = get_market_session(now)
    slot, report_title, report_purpose = get_report_slot(now)
    reasons = list(result.get("reasons", []))

    if not supply.get("program_available"):
        reasons = [reason for reason in reasons if "프로그램" not in reason]
        if session == "pre_market":
            reasons.append("⚪ 외국인 프로그램 수급 장 개시 전")
        elif session == "market_open":
            reasons.append("⚪ 외국인 프로그램 수급 장중 미집계")
        elif session == "closed":
            reasons.append("⚪ 외국인 프로그램 수급 휴장일")
        else:
            reasons.append("⚪ 외국인 프로그램 수급 미집계")

    if supply.get("error"):
        reasons.append("⚠️ 국내 수급 API 일부 또는 전체 조회 실패")

    reason_text = "\n".join(reasons) or "⚪ 판단 근거 없음"
    timestamp = now.strftime("%Y-%m-%d %H:%M KST")
    action_text = "\n".join(f"• {item}" for item in result.get("actions", []))

    tomorrow_section = ""
    if slot == "closing":
        tomorrow_section = f"""

━━━━━━━━━━━━━━

🔭 다음 거래일 전망

{result['tomorrow_outlook']}"""

    return f"""🚦 MarketPilot V4
{report_title}
{report_purpose}
기준 시각 : {timestamp}

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
시장 상태 : {market_session_label(session)}
수급 기준일 : {format_date(supply.get('date'))}

외국인 : {format_supply_value(supply.get('foreign'), kind='general', session=session)}
기관 : {format_supply_value(supply.get('institution'), kind='general', session=session)}
프로그램(외국인) : {format_supply_value(supply.get('program'), kind='program', session=session)}

━━━━━━━━━━━━━━

🧠 AI SCORE

{result['score']} / 100

{result['signal']}

🎯 행동 가이드
{action_text}

신뢰도 : {result['confidence']}%
데이터 완전도 : {result['data_completeness']}%

━━━━━━━━━━━━━━

🚨 시장 위험도
{star_gauge(result['risk_stars'])} · {result['risk_label']}

🌊 예상 변동성
{star_gauge(result['volatility_stars'])} · {result['volatility_label']}

━━━━━━━━━━━━━━

📌 판단 근거

{reason_text}{tomorrow_section}

━━━━━━━━━━━━━━

※ 본 신호는 시장 대응을 돕는 참고 지표이며 투자 성과를 보장하지 않습니다."""


async def main() -> None:
    bot_token = require_env("BOT_TOKEN")
    chat_id = require_env("CHAT_ID")
    telegram = TelegramService(bot_token)
    now = datetime.now(KST)

    try:
        market = MarketService.get_market_data()
        logger.info("시장 데이터 수집 완료: %s", market)

        try:
            supply = SupplyAPIService().get_supply(session=get_market_session(now))
            logger.info("국내 수급 수집 완료: %s", supply)
        except SupplyAPIError as exc:
            logger.exception("KIS 수급 API 오류 - 시장 점수만으로 계속 실행")
            supply = {
                "foreign": None,
                "institution": None,
                "program": None,
                "date": None,
                "available": False,
                "program_available": False,
                "error": str(exc),
            }

        score_supply = {
            "foreign": supply.get("foreign"),
            "institution": supply.get("institution"),
            "program": supply.get("program"),
        }
        result = ScoreService().calculate(
            market,
            score_supply,
            session=get_market_session(now),
        )
        message = build_message(market, supply, result, now)

    except Exception as exc:
        logger.exception("MarketPilot 실행 오류")
        message = f"❌ MarketPilot 오류\n\n{type(exc).__name__}: {exc}"

    await telegram.send(chat_id, message)


if __name__ == "__main__":
    asyncio.run(main())
