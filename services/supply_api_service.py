from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests

from services.kis_service import KISService


class SupplyAPIError(RuntimeError):
    """한국투자증권 수급 API 호출 또는 응답 처리 오류."""


class SupplyAPIService:
    """KOSPI 시장 수급과 프로그램매매 수급을 조회한다."""

    MARKET_PATH = "/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market"
    MARKET_TR_ID = "FHPTJ04040000"

    PROGRAM_PATH = "/uapi/domestic-stock/v1/quotations/investor-program-trade-today"
    PROGRAM_TR_ID = "HHPPG046600C1"

    def __init__(self, timeout: int = 30) -> None:
        self.kis = KISService()
        self.timeout = timeout

    @staticmethod
    def _to_int(value: Any) -> int:
        if value in (None, "", "-"):
            return 0
        return int(str(value).replace(",", "").strip())

    def _get(self, path: str, tr_id: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self.kis.base_url.rstrip('/')}{path}"
        headers = self.kis.get_headers(tr_id)

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SupplyAPIError(f"KIS HTTP 요청 실패: {exc}") from exc

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

    def _get_market_supply(self) -> dict[str, Any]:
        # 휴장일에도 동작하도록 최근 10일을 역순으로 조회한다.
        today = datetime.now().date()
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

            output = payload.get("output") or []
            if isinstance(output, dict):
                rows = [output]
            elif isinstance(output, list):
                rows = output
            else:
                rows = []

            if not rows:
                continue

            row = rows[0]
            return {
                "foreign": self._to_int(row.get("frgn_ntby_qty")),
                "institution": self._to_int(row.get("orgn_ntby_qty")),
                "date": row.get("stck_bsop_date") or target_date,
            }

        if last_error:
            raise SupplyAPIError(f"시장 수급 조회 실패: {last_error}")
        raise SupplyAPIError("최근 10일 내 KOSPI 시장 수급 데이터가 없습니다.")

    def _get_program_supply(self) -> int | None:
        params = {"MRKT_DIV_CLS_CODE": "1"}  # 1: 코스피
        payload = self._get(self.PROGRAM_PATH, self.PROGRAM_TR_ID, params)
        output = payload.get("output1") or []

        if isinstance(output, dict):
            rows = [output]
        elif isinstance(output, list):
            rows = output
        else:
            rows = []

        if not rows:
            return None

        # 응답에 전체/합계 행이 있으면 그 값을 우선 사용한다.
        for row in rows:
            name = str(row.get("invr_cls_name", "")).strip()
            code = str(row.get("invr_cls_code", "")).strip()
            if name in {"전체", "합계", "총계"} or code in {"0", "00"}:
                return self._to_int(row.get("all_ntby_qty"))

        # 전체 행이 없으면 프로그램 전체값을 임의 합산하지 않는다.
        return None

    def get_supply(self) -> dict[str, Any]:
        market = self._get_market_supply()

        program: int | None = None
        program_error: str | None = None
        try:
            program = self._get_program_supply()
        except SupplyAPIError as exc:
            # 외국인/기관 데이터는 살리고 프로그램 데이터만 미집계 처리한다.
            program_error = str(exc)

        return {
            "foreign": market["foreign"],
            "institution": market["institution"],
            "program": program,
            "date": market["date"],
            "available": True,
            "program_available": program is not None,
            "program_error": program_error,
        }
