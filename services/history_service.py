from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yfinance as yf

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class KospiSnapshot:
    price: float
    source: str


class HistoryService:
    FIELDNAMES = [
        "run_at", "trade_date", "slot", "session", "score", "signal_code",
        "signal_text", "confidence", "data_completeness", "nasdaq", "sp500",
        "sox", "vix", "usdkrw", "foreign", "institution", "program",
        "kospi_at_signal", "kospi_entry_price", "kospi_close",
        "return_after_signal", "result", "evaluated_at",
    ]

    def __init__(self, path: str | Path = "data/signal_history.csv") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_rows([])

    @staticmethod
    def signal_code(score: int) -> str:
        if score >= 65:
            return "LEVERAGE"
        if score <= 45:
            return "INVERSE"
        return "HOLD"

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, "", "None"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _today_daily_ohlc(target: date | None = None) -> tuple[float | None, float | None]:
        target = target or datetime.now(KST).date()
        start = target.isoformat()
        end = (target + timedelta(days=1)).isoformat()
        try:
            df = yf.download("^KS11", start=start, end=end, progress=False, auto_adjust=False)
        except Exception as exc:
            logger.warning("KOSPI 일봉 조회 실패: %s", exc)
            return None, None
        if df is None or df.empty:
            return None, None
        try:
            open_price = float(df["Open"].iloc[-1].item())
            close_price = float(df["Close"].iloc[-1].item())
            return open_price, close_price
        except Exception as exc:
            logger.warning("KOSPI 일봉 파싱 실패: %s", exc)
            return None, None

    @classmethod
    def get_kospi_snapshot(cls, session: str) -> KospiSnapshot | None:
        if session == "pre_market":
            try:
                df = yf.Ticker("^KS11").history(period="10d", interval="1d", auto_adjust=False)
                close = df["Close"].dropna()
                if not close.empty:
                    return KospiSnapshot(float(close.iloc[-1]), "previous_close")
            except Exception as exc:
                logger.warning("KOSPI 전일 종가 조회 실패: %s", exc)
            return None

        try:
            df = yf.Ticker("^KS11").history(period="1d", interval="5m", auto_adjust=False)
            close = df["Close"].dropna()
            if not close.empty:
                return KospiSnapshot(float(close.iloc[-1]), "intraday_5m")
        except Exception as exc:
            logger.warning("KOSPI 장중 스냅숏 조회 실패: %s", exc)

        _, close_price = cls._today_daily_ohlc()
        if close_price is not None:
            return KospiSnapshot(close_price, "daily_close")
        return None

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _write_rows(self, rows: list[dict[str, Any]]) -> None:
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in self.FIELDNAMES})
        temp.replace(self.path)

    def record_signal(
        self,
        *,
        now: datetime,
        slot: str,
        session: str,
        market: dict[str, float],
        supply: dict[str, Any],
        result: dict[str, Any],
    ) -> bool:
        rows = self._read_rows()
        run_at = now.strftime("%Y-%m-%d %H:%M:%S")
        duplicate = any(row.get("run_at", "")[:16] == run_at[:16] and row.get("slot") == slot for row in rows)
        if duplicate:
            logger.info("동일 시각 신호가 이미 기록되어 건너뜁니다: %s %s", run_at, slot)
            return False

        snapshot = self.get_kospi_snapshot(session)
        signal_price = snapshot.price if snapshot else ""
        rows.append({
            "run_at": run_at,
            "trade_date": now.strftime("%Y-%m-%d"),
            "slot": slot,
            "session": session,
            "score": result["score"],
            "signal_code": self.signal_code(int(result["score"])),
            "signal_text": result["signal"],
            "confidence": result["confidence"],
            "data_completeness": result["data_completeness"],
            "nasdaq": market["NASDAQ"],
            "sp500": market["SP500"],
            "sox": market["SOX"],
            "vix": market["VIX"],
            "usdkrw": market["USDKRW"],
            "foreign": supply.get("foreign") if supply.get("foreign") is not None else "",
            "institution": supply.get("institution") if supply.get("institution") is not None else "",
            "program": supply.get("program") if supply.get("program") is not None else "",
            "kospi_at_signal": signal_price,
            "kospi_entry_price": "",
            "kospi_close": "",
            "return_after_signal": "",
            "result": "",
            "evaluated_at": "",
        })
        self._write_rows(rows)
        logger.info("신호 기록 완료: %s", self.path)
        return True

    @staticmethod
    def _judge(signal_code: str, return_pct: float, hold_band: float = 0.4) -> str:
        if signal_code == "LEVERAGE":
            return "HIT" if return_pct > 0 else "MISS"
        if signal_code == "INVERSE":
            return "HIT" if return_pct < 0 else "MISS"
        return "HIT" if abs(return_pct) <= hold_band else "MISS"

    def evaluate_today(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(KST)
        rows = self._read_rows()
        trade_date = now.strftime("%Y-%m-%d")
        open_price, close_price = self._today_daily_ohlc(now.date())
        if close_price is None:
            raise RuntimeError("당일 KOSPI 종가를 조회하지 못했습니다.")

        updated = 0
        for row in rows:
            if row.get("trade_date") != trade_date or row.get("result"):
                continue
            signal_price = self._to_float(row.get("kospi_at_signal"))
            entry_price = open_price if row.get("slot") == "pre_market" else signal_price
            if entry_price in (None, 0):
                continue
            return_pct = (close_price - float(entry_price)) / float(entry_price) * 100
            row["kospi_entry_price"] = f"{float(entry_price):.4f}"
            row["kospi_close"] = f"{close_price:.4f}"
            row["return_after_signal"] = f"{return_pct:.4f}"
            row["result"] = self._judge(row.get("signal_code", "HOLD"), return_pct)
            row["evaluated_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
            updated += 1

        self._write_rows(rows)
        return {"trade_date": trade_date, "updated": updated, "open": open_price, "close": close_price}

    def rows_for_period(self, start: date, end: date) -> list[dict[str, str]]:
        result = []
        for row in self._read_rows():
            raw = row.get("trade_date", "")
            try:
                current = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                continue
            if start <= current <= end and row.get("result") in {"HIT", "MISS"}:
                result.append(row)
        return result
