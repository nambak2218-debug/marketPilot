from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from services.kis_service import KISService

logger = logging.getLogger(__name__)


class MarketDataError(RuntimeError):
    pass


class MarketService:
    """시장 데이터를 수집한다.

    - 해외 지수와 환율: Yahoo Finance
    - KOSPI/KOSPI200: KIS 우선, 실패 시 Yahoo Finance 보조
    - KOSPI와 KOSPI200 등락률 차이가 비정상적으로 크면 KOSPI200 차단
    """

    OVERSEAS_SYMBOLS = {
        "NASDAQ": "^IXIC",
        "SP500": "^GSPC",
        "SOX": "^SOX",
        "VIX": "^VIX",
        "USDKRW": "KRW=X",
    }

    # 정보 표시용 선물지수. 스코어 계산(score_service.py)에는 넣지 않는다 -
    # 이미 검증된 가중치를 건드리지 않기 위해 우선 화면 표시만 한다.
    FUTURES_SYMBOLS = {
        "SP500_FUT": "ES=F",
        "NASDAQ_FUT": "NQ=F",
    }

    # ^SOX/^VIX 원본 지수 피드에 구멍이 생겼을 때 대신 쓸 실거래 ETF.
    # SOXX는 SOX를 추적오차 작게 따라가지만, VIXY는 VIX 선물 기반이라
    # 콘탱고로 인해 등락률이 현물 VIX와 정확히 일치하지는 않는다(완벽한 대체는 아님).
    PROXY_SYMBOLS = {
        "SOX_PROXY": "SOXX",
        "VIX_PROXY": "VIXY",
    }

    DOMESTIC_YAHOO_SYMBOLS = {
        "KOSPI": "^KS11",
        "KOSPI200": "^KS200",
    }

    KIS_INDEX_CODES = {
        "KOSPI": "0001",
        "KOSPI200": "2001",
    }

    KIS_INDEX_TR_ID = "FHPUP02100000"
    KIS_INDEX_PATH = "/uapi/domestic-stock/v1/quotations/inquire-index-price"

    KIS_OVERSEAS_PRICE_TR_ID = "HHDFS76200200"
    KIS_OVERSEAS_PRICE_PATH = "/uapi/overseas-price/v1/quotations/price-detail"

    # SOX/VIX를 Yahoo 대신 KIS로 직접 조회할 때 쓸 대체 종목(EXCD, SYMB).
    # VIXY의 정확한 EXCD는 문서만으로 확정하지 못해 NYS로 시도 - 실패 로그로 확인 필요.
    KIS_OVERSEAS_PROXIES = {
        "SOX": ("NAS", "SOXX"),
        "VIX": ("NYS", "VIXY"),
    }

    # 두 지수의 일간 등락률 차이가 이 값 이상이면 KOSPI200을 이상치로 처리한다.
    MAX_DOMESTIC_INDEX_GAP_PCT = 3.0

    @staticmethod
    def _has_weekday_gap(latest_date: date | None, reference_date: date | None) -> bool:
        """latest_date와 reference_date 사이에 평일(영업일)이 하나라도 비어있으면 True.

        주말만 끼어있는 경우(금요일 데이터 vs 월요일 확인)는 정상이므로 False를 반환한다.
        미국 공휴일까지는 반영하지 않아 드물게 오탐이 있을 수 있다.
        """
        if latest_date is None or reference_date is None or reference_date <= latest_date:
            return False
        gap_days = pd.bdate_range(
            start=latest_date + timedelta(days=1),
            end=reference_date - timedelta(days=1),
        )
        return len(gap_days) > 0

    @classmethod
    def _get_kis_overseas_change_with_retry(
        cls,
        kis: KISService,
        name: str,
        excd: str,
        symb: str,
        attempts: int = 2,
    ) -> float | None:
        for attempt in range(1, attempts + 1):
            try:
                return cls._get_kis_overseas_change(kis, excd, symb)
            except Exception as exc:
                logger.warning(
                    "%s(KIS 해외주식 %s:%s) 수집 실패 (%s/%s): %s",
                    name, excd, symb, attempt, attempts, exc,
                )
                if attempt < attempts:
                    time.sleep(attempt * 2)
        return None

    @staticmethod
    def _get_kis_overseas_change(kis: KISService, excd: str, symb: str) -> float:
        url = f"{kis.base_url}{MarketService.KIS_OVERSEAS_PRICE_PATH}"
        headers = kis.get_headers(MarketService.KIS_OVERSEAS_PRICE_TR_ID)
        params = {"AUTH": "", "EXCD": excd, "SYMB": symb}

        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()

        payload = response.json()
        if str(payload.get("rt_cd", "0")) not in {"0", ""}:
            message = payload.get("msg1") or payload.get("msg_cd") or "알 수 없는 오류"
            raise MarketDataError(f"KIS 해외주식 현재가상세 오류: {message}")

        output = payload.get("output")
        if not isinstance(output, dict):
            raise MarketDataError(f"{symb} 응답에 output이 없습니다.")

        last = MarketService._to_float(output.get("last"))
        base = MarketService._to_float(output.get("base"))
        if last is None or base is None or base == 0:
            raise MarketDataError(f"{symb} 현재가/전일종가 파싱 실패")

        return round((last - base) / base * 100, 2)

    @classmethod
    def get_market_data(cls, kis: KISService | None = None) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        dated: dict[str, tuple[float, Any] | None] = {}

        # 선물은 데이터 피드가 가장 신뢰할 수 있어서, 먼저 조회해 "최신 거래일" 기준으로 쓴다.
        for name, symbol in cls.FUTURES_SYMBOLS.items():
            dated[name] = cls._change_with_retry(symbol)
            result[name] = dated[name][0] if dated[name] else None

        # SOX/VIX 원본 피드가 막혔을 때 대신 쓸 ETF 프록시도 미리 조회해둔다.
        for name, symbol in cls.PROXY_SYMBOLS.items():
            dated[name] = cls._change_with_retry(symbol)

        reference_date = max(
            (d for d in (dated.get("SP500_FUT"), dated.get("NASDAQ_FUT")) if d),
            key=lambda d: d[1],
            default=None,
        )
        reference_date = reference_date[1] if reference_date else None

        fallback_map = {
            "NASDAQ": "NASDAQ_FUT",
            "SP500": "SP500_FUT",
            "SOX": "SOX_PROXY",
            "VIX": "VIX_PROXY",
        }

        def is_fresh(dated_tuple: tuple[float, Any, Any] | None) -> bool:
            if dated_tuple is None:
                return False
            _, latest, previous = dated_tuple
            # (1) 최신값 자체가 기준일보다 오래되지 않았는지
            # (2) 등락률 계산에 쓰인 두 날짜(최신/직전) 사이에 평일이 비어있지 않은지
            #     - 둘 다 확인해야 "날짜는 최신인데 비교 대상이 이틀 전"인 경우를 잡아낸다.
            return not cls._has_weekday_gap(latest, reference_date) and not cls._has_weekday_gap(previous, latest)

        for name, symbol in cls.OVERSEAS_SYMBOLS.items():
            # SOX/VIX는 Yahoo(지수/ETF)보다 KIS 해외주식 현재가상세를 먼저 시도한다.
            # KIS는 과거 며칠치를 비교할 필요 없이 현재가 vs 전일종가를 바로 주기 때문에
            # 지금까지 겪은 "며칠치 데이터 중 어디가 최신인지" 문제 자체가 생기지 않는다.
            if kis is not None and name in cls.KIS_OVERSEAS_PROXIES:
                excd, symb = cls.KIS_OVERSEAS_PROXIES[name]
                kis_pct = cls._get_kis_overseas_change_with_retry(kis, name, excd, symb)
                if kis_pct is not None:
                    result[name] = kis_pct
                    continue
                logger.warning("%s KIS 해외주식 조회 실패 - Yahoo 체인으로 대체", name)

            fetched = cls._change_with_retry(symbol)

            if fetched is None:
                result[name] = None
                continue

            pct, latest_date, previous_date = fetched
            if not is_fresh(fetched):
                logger.warning(
                    "%s 데이터 신선도 문제 (최신=%s, 직전=%s, 기준=%s) - 피드 지연 의심",
                    symbol, latest_date, previous_date, reference_date,
                )
                fallback_key = fallback_map.get(name)
                fallback = dated.get(fallback_key) if fallback_key else None
                # 대체 후보(프록시/선물)도 같은 기준으로 신선도를 확인한 후에만 사용한다.
                if fallback and is_fresh(fallback):
                    logger.warning("%s -> %s(으)로 대체", name, fallback_key)
                    result[name] = fallback[0]
                else:
                    # 스코어링에는 안 쓰지만(None), 메시지 표시용으로 마지막 확인값은 남겨둔다.
                    result[name] = None
                    result[f"{name}_stale_value"] = pct
                    result[f"{name}_stale_date"] = latest_date.isoformat()
            else:
                result[name] = pct

        # 국내 지수는 KIS를 우선 사용한다.
        domestic = cls._get_domestic_indices(kis)
        result.update(domestic)

        cls._validate_domestic_indices(result)

        essential = ["NASDAQ", "SP500", "SOX", "VIX", "USDKRW"]
        if all(result.get(key) is None for key in essential):
            raise MarketDataError("필수 해외시장 데이터가 모두 수집되지 않았습니다.")

        return result

    @classmethod
    def _get_domestic_indices(cls, kis: KISService | None = None) -> dict[str, float | None]:
        result: dict[str, float | None] = {}

        # 외부에서 공유 인스턴스를 넘겨받으면 그대로 사용해 토큰 재발급을 피한다.
        if kis is None:
            try:
                kis = KISService()
            except Exception as exc:
                logger.warning("KIS 초기화 실패, 국내 지수는 Yahoo 보조 사용: %s", exc)
                kis = None

        for name, index_code in cls.KIS_INDEX_CODES.items():
            value: float | None = None

            if kis is not None:
                value = cls._get_kis_index_change_with_retry(
                    kis=kis,
                    index_name=name,
                    index_code=index_code,
                )

            if value is None:
                yahoo_symbol = cls.DOMESTIC_YAHOO_SYMBOLS[name]
                logger.warning(
                    "%s KIS 조회 실패, Yahoo 보조값 사용: %s",
                    name,
                    yahoo_symbol,
                )
                fetched = cls._change_with_retry(yahoo_symbol)
                value = fetched[0] if fetched else None

            result[name] = value

        return result


    @classmethod
    def _get_kis_index_change_with_retry(
        cls,
        *,
        kis: KISService,
        index_name: str,
        index_code: str,
        attempts: int = 3,
    ) -> float | None:
        for attempt in range(1, attempts + 1):
            try:
                return cls._get_kis_index_change(kis, index_code)
            except Exception as exc:
                logger.warning(
                    "%s KIS 수집 실패 (%s/%s): %s",
                    index_name,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(attempt * 2)
        return None

    @classmethod
    def _get_kis_index_change(cls, kis: KISService, index_code: str) -> float:
        url = f"{kis.base_url}{cls.KIS_INDEX_PATH}"
        headers = kis.get_headers(cls.KIS_INDEX_TR_ID)
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": index_code,
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20,
        )
        response.raise_for_status()

        payload = response.json()
        if str(payload.get("rt_cd", "0")) not in {"0", ""}:
            message = payload.get("msg1") or payload.get("msg_cd") or "알 수 없는 오류"
            raise MarketDataError(f"KIS 국내지수 API 오류: {message}")

        output = payload.get("output")
        if isinstance(output, list):
            output = output[0] if output else None
        if not isinstance(output, dict):
            raise MarketDataError("KIS 국내지수 응답에 output이 없습니다.")

        # 공식 응답의 전일 대비율 필드를 우선 사용하고, 호환성을 위해 후보를 둔다.
        for field in (
            "bstp_nmix_prdy_ctrt",
            "bstp_nmix_prdy_vrss_rate",
            "prdy_ctrt",
        ):
            value = cls._to_float(output.get(field))
            if value is not None:
                return round(value, 2)

        # 대비율 필드가 없으면 현재가와 전일 대비값으로 역산한다.
        current = cls._to_float(output.get("bstp_nmix_prpr"))
        change = cls._to_float(output.get("bstp_nmix_prdy_vrss"))
        if current is not None and change is not None:
            previous = current - change
            if previous != 0:
                return round(change / previous * 100, 2)

        raise MarketDataError("KIS 국내지수 응답에서 전일 대비율을 찾지 못했습니다.")

    @classmethod
    def _validate_domestic_indices(
        cls,
        result: dict[str, float | None],
    ) -> None:
        kospi = result.get("KOSPI")
        kospi200 = result.get("KOSPI200")

        if kospi is None or kospi200 is None:
            return

        gap = abs(kospi - kospi200)
        if gap >= cls.MAX_DOMESTIC_INDEX_GAP_PCT:
            logger.error(
                "KOSPI200 이상치 차단: KOSPI=%+.2f%%, KOSPI200=%+.2f%%, 차이=%.2f%%p",
                kospi,
                kospi200,
                gap,
            )
            result["KOSPI200"] = None

    @classmethod
    def _change_with_retry(
        cls,
        symbol: str,
        attempts: int = 3,
    ) -> tuple[float, Any] | None:
        for attempt in range(1, attempts + 1):
            try:
                return cls._change(symbol)
            except Exception as exc:
                logger.warning(
                    "%s 수집 실패 (%s/%s): %s",
                    symbol,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(attempt * 2)
        return None

    @staticmethod
    def _change(symbol: str) -> tuple[float, Any, Any]:
        # period="10d"처럼 고정된 문자열은 매일 완전히 동일한 요청이 되어
        # Yahoo/yfinance 쪽 캐시에 걸려 어제 값이 재사용될 위험이 있다.
        # start/end를 오늘 날짜 기준으로 매번 새로 계산해 요청 자체를 달라지게 한다.
        end = datetime.now(timezone.utc) + timedelta(days=1)
        start = end - timedelta(days=15)
        df: Any = yf.Ticker(symbol).history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
        )
        if df is None or df.empty or "Close" not in df:
            raise MarketDataError(f"{symbol} 종가 데이터 없음")

        close = df["Close"].dropna()
        if len(close) < 2:
            raise MarketDataError(f"{symbol} 비교 종가 부족")

        previous = float(close.iloc[-2])
        latest = float(close.iloc[-1])
        latest_date = close.index[-1].date()
        previous_date = close.index[-2].date()
        if previous == 0:
            raise MarketDataError(f"{symbol} 이전 종가 0")

        return round((latest - previous) / previous * 100, 2), latest_date, previous_date

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None

        text = str(value).strip().replace(",", "")
        if not text:
            return None

        try:
            return float(text)
        except (TypeError, ValueError):
            return None
