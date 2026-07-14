from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

from services.kis_service import KISService, KISServiceError

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")


class SupplyAPIError(RuntimeError):
    """KIS 국내 수급 조회 오류."""


class SupplyAPIService:
    MARKET_PATH = "/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market"
    MARKET_TR_ID = "FHPTJ04040000"
    PROGRAM_PATH = "/uapi/domestic-stock/v1/quotations/investor-program-trade-today"
    PROGRAM_TR_ID = "HHPPG046600C1"

    def __init__(self, kis: KISService | None = None, timeout: int = 30) -> None:
        if kis is not None:
            self.kis = kis
        else:
            try:
                self.kis = KISService()
            except KISServiceError as exc:
                raise SupplyAPIError(str(exc)) from exc
        self.timeout = timeout

    @staticmethod
    def _to_int_or_none(value: Any) -> int | None:
        if value in (None, "", "-"):
            return None
        try:
            return int(float(str(value).replace(",", "").strip()))
        except (TypeError, ValueError):
            return None

    def _get(self, path: str, tr_id: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self.kis.base_url}{path}"
        try:
            response = requests.get(
                url,
                headers=self.kis.get_headers(tr_id),
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except (requests.RequestException, KISServiceError) as exc:
            raise SupplyAPIError(f"KIS 요청 실패: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise SupplyAPIError(
                f"KIS 응답이 JSON이 아닙니다: {response.text[:300]}"
            ) from exc
        if str(payload.get("rt_cd", "0")) != "0":
            raise SupplyAPIError(
                f"KIS API 오류 [{payload.get('msg_cd', 'UNKNOWN')}]: "
                f"{payload.get('msg1', '알 수 없는 오류')}"
            )
        return payload

    @staticmethod
    def _rows(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        return []

    def _get_market_supply(self) -> dict[str, Any]:
        today = datetime.now(KST).date()
        last_error: Exception | None = None
        for days_ago in range(10):
            target_date = (today - timedelta(days=days_ago)).strftime("%Y%m%d")
            params = {
                "FID_COND_MRKT_DIV_CODE": "U",
                "FID_INPUT_ISCD": "0001",
                "FID_INPUT_DATE_1": target_date,
                "FID_INPUT_ISCD_1": "KSP",
                "FID_INPUT_DATE_2": target_date,
                "FID_INPUT_ISCD_2": "0001",
            }
            try:
                payload = self._get(self.MARKET_PATH, self.MARKET_TR_ID, params)
            except SupplyAPIError as exc:
                last_error = exc
                continue
            rows = self._rows(payload.get("output"))
            if not rows:
                continue
            row = rows[0]
            foreign = self._to_int_or_none(row.get("frgn_ntby_tr_pbmn"))
            institution = self._to_int_or_none(row.get("orgn_ntby_tr_pbmn"))
            foreign_qty = self._to_int_or_none(row.get("frgn_ntby_qty"))
            institution_qty = self._to_int_or_none(row.get("orgn_ntby_qty"))
            if foreign is None and institution is None:
                continue
            return {
                "foreign": foreign,
                "institution": institution,
                "foreign_qty": foreign_qty,
                "institution_qty": institution_qty,
                "supply_unit": "백만원",
                "date": row.get("stck_bsop_date") or target_date,
            }
        if last_error:
            raise SupplyAPIError(f"시장 수급 조회 실패: {last_error}")
        raise SupplyAPIError("최근 10일 내 KOSPI 시장 수급 데이터가 없습니다.")

    # 문서(프로그램매매 투자자매매동향(당일), 국내주식-116) 기준 최상위 투자자 코드.
    # 응답엔 "전체/합계" 행이 따로 없고, 개인·외국인·기관(하위구분 소계) 3개로 시장 전체가 구성됨.
    TOP_LEVEL_CODES = {"8000": "개인", "9100": "외국인", "8888": "기관"}
    FOREIGN_CODE = "9100"

    def _get_program_supply(self) -> tuple[int | None, int | None]:
        params = {
            "MRKT_DIV_CLS_CODE": "1",
            # J: KRX, NX: NXT, UN: 통합 (KIS 문서 "프로그램매매 투자자매매동향(당일)" 기준)
            "EXCH_DIV_CLS_CODE": os.getenv("KIS_PROGRAM_EXCH_DIV_CLS_CODE", "UN"),
        }
        payload = self._get(self.PROGRAM_PATH, self.PROGRAM_TR_ID, params)
        rows = self._rows(payload.get("output1"))
        if not rows:
            return None, None

        foreign = None
        top_level_values: dict[str, int] = {}
        for row in rows:
            code = str(row.get("invr_cls_code", "")).strip()
            value = self._to_int_or_none(row.get("all_ntby_qty"))
            if value is None:
                continue
            if code == self.FOREIGN_CODE:
                foreign = value
            if code in self.TOP_LEVEL_CODES:
                top_level_values[code] = value

        # 개인+외국인+기관(소계) 세 최상위 카테고리를 더하면 시장 전체 순매수가 된다.
        total = sum(top_level_values.values()) if len(top_level_values) == len(self.TOP_LEVEL_CODES) else None

        return foreign, total

    def get_supply(self, *, session: str = "market_open") -> dict[str, Any]:
        market = self._get_market_supply()
        program: int | None = None
        program_total: int | None = None
        program_error: str | None = None

        # 장전에는 당일 프로그램 값이 아직 의미가 없으므로 호출하지 않는다.
        if session not in {"pre_market", "closed"}:
            try:
                program, program_total = self._get_program_supply()
            except SupplyAPIError as exc:
                program_error = str(exc)
                logger.warning("프로그램 수급 조회 실패: %s", exc)

        return {
            "foreign": market["foreign"],
            "institution": market["institution"],
            "foreign_qty": market.get("foreign_qty"),
            "institution_qty": market.get("institution_qty"),
            "supply_unit": market.get("supply_unit", "백만원"),
            "program": program,
            "program_total": program_total,
            "program_unit": "주",
            "date": market["date"],
            "available": True,
            "program_available": program is not None,
            "program_total_available": program_total is not None,
            "program_error": program_error,
            "error": None,
        }
