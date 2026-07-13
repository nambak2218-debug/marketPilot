from __future__ import annotations

import logging
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataError(RuntimeError):
    """필수 시장 데이터 수집 실패."""


class MarketService:
    SYMBOLS = {
        "NASDAQ": "^IXIC",
        "SP500": "^GSPC",
        "SOX": "^SOX",
        "VIX": "^VIX",
        "USDKRW": "KRW=X",
    }

    @classmethod
    def get_market_data(cls) -> dict[str, float]:
        result: dict[str, float] = {}
        errors: list[str] = []
        for name, symbol in cls.SYMBOLS.items():
            try:
                result[name] = cls._change(symbol)
            except MarketDataError as exc:
                errors.append(f"{name}: {exc}")
        if errors:
            raise MarketDataError("시장 데이터 수집 실패 - " + "; ".join(errors))
        return result

    @staticmethod
    def _change(symbol: str) -> float:
        try:
            df: Any = yf.Ticker(symbol).history(
                period="10d", interval="1d", auto_adjust=True
            )
        except Exception as exc:
            raise MarketDataError(f"{symbol} 요청 오류: {exc}") from exc
        if df is None or df.empty or "Close" not in df:
            raise MarketDataError(f"{symbol} 종가 데이터 없음")
        close = df["Close"].dropna()
        if len(close) < 2:
            raise MarketDataError(f"{symbol} 비교 가능한 종가 부족")
        previous = float(close.iloc[-2])
        latest = float(close.iloc[-1])
        if previous == 0:
            raise MarketDataError(f"{symbol} 이전 종가가 0")
        change = round((latest - previous) / previous * 100, 2)
        logger.info("%s: previous=%s latest=%s change=%s", symbol, previous, latest, change)
        return change
