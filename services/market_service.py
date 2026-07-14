from __future__ import annotations
import logging, time
from typing import Any
import yfinance as yf

logger = logging.getLogger(__name__)

class MarketDataError(RuntimeError):
    pass

class MarketService:
    SYMBOLS = {
        "NASDAQ": "^IXIC", "SP500": "^GSPC", "SOX": "^SOX", "VIX": "^VIX",
        "USDKRW": "KRW=X", "KOSPI": "^KS11", "KOSPI200": "^KS200",
    }

    @classmethod
    def get_market_data(cls) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for name, symbol in cls.SYMBOLS.items():
            result[name] = cls._change_with_retry(symbol)
        essential = ["NASDAQ", "SP500", "SOX", "VIX", "USDKRW"]
        if all(result.get(k) is None for k in essential):
            raise MarketDataError("필수 해외시장 데이터가 모두 수집되지 않았습니다.")
        return result

    @classmethod
    def _change_with_retry(cls, symbol: str, attempts: int = 3) -> float | None:
        for attempt in range(1, attempts + 1):
            try:
                return cls._change(symbol)
            except Exception as exc:
                logger.warning("%s 수집 실패 (%s/%s): %s", symbol, attempt, attempts, exc)
                if attempt < attempts:
                    time.sleep(attempt * 2)
        return None

    @staticmethod
    def _change(symbol: str) -> float:
        df: Any = yf.Ticker(symbol).history(period="10d", interval="1d", auto_adjust=True)
        if df is None or df.empty or "Close" not in df:
            raise MarketDataError(f"{symbol} 종가 데이터 없음")
        close = df["Close"].dropna()
        if len(close) < 2:
            raise MarketDataError(f"{symbol} 비교 종가 부족")
        previous, latest = float(close.iloc[-2]), float(close.iloc[-1])
        if previous == 0:
            raise MarketDataError(f"{symbol} 이전 종가 0")
        return round((latest - previous) / previous * 100, 2)
