from __future__ import annotations
from datetime import date, datetime
from zoneinfo import ZoneInfo
import exchange_calendars as xcals

KST = ZoneInfo("Asia/Seoul")

class CalendarService:
    """KRX 정규 거래일 여부를 판단한다."""
    _calendar = xcals.get_calendar("XKRX")

    @classmethod
    def is_trading_day(cls, value: date | datetime | None = None) -> bool:
        if value is None:
            target = datetime.now(KST).date()
        elif isinstance(value, datetime):
            target = value.astimezone(KST).date() if value.tzinfo else value.date()
        else:
            target = value
        return bool(cls._calendar.is_session(target.isoformat()))
