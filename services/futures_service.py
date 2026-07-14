from __future__ import annotations
import logging, os
from typing import Any
import requests
from services.kis_service import KISService

logger = logging.getLogger(__name__)

class FuturesService:
    """KOSPI200 선물 베이시스/괴리율 조회. 종목코드는 환경변수로 주입한다."""
    PATH = "/uapi/domestic-futureoption/v1/quotations/inquire-price"
    TR_ID = "FHMIF10000000"

    def __init__(self, timeout: int = 20):
        self.kis = KISService(); self.timeout = timeout

    @staticmethod
    def _num(v: Any) -> float | None:
        try: return float(str(v).replace(',', '').strip())
        except (TypeError, ValueError): return None

    def _fetch(self, code: str) -> dict[str, float | None]:
        r=requests.get(f"{self.kis.base_url}{self.PATH}", headers=self.kis.get_headers(self.TR_ID),
            params={"FID_COND_MRKT_DIV_CODE":"F", "FID_INPUT_ISCD":code}, timeout=self.timeout)
        r.raise_for_status(); payload=r.json()
        if str(payload.get('rt_cd','0'))!='0': raise RuntimeError(payload.get('msg1','선물 API 오류'))
        row=payload.get('output') or {}; row=row[0] if isinstance(row,list) and row else row
        return {"price":self._num(row.get('futs_prpr')), "theoretical":self._num(row.get('hts_thpr')),
                "basis":self._num(row.get('mrkt_basis')), "disparity":self._num(row.get('dprt'))}

    def get_data(self) -> dict[str, Any]:
        result={"day":None,"night":None,"available":False}
        day=os.getenv('KIS_FUTURES_CODE','').strip(); night=os.getenv('KIS_NIGHT_FUTURES_CODE','').strip()
        for key,code in (("day",day),("night",night)):
            if not code: continue
            try: result[key]=self._fetch(code); result['available']=True
            except Exception as exc: logger.warning('%s 선물 조회 실패: %s', key, exc)
        return result
