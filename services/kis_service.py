from __future__ import annotations

import os
from typing import Any

import requests


class KISServiceError(RuntimeError):
    """KIS 인증 또는 공통 설정 오류."""


class KISService:
    def __init__(self, timeout: int = 20) -> None:
        self.base_url = self._require_env("KIS_BASE_URL").rstrip("/")
        self.app_key = self._require_env("KIS_APP_KEY")
        self.app_secret = self._require_env("KIS_APP_SECRET")
        self.timeout = timeout
        self.access_token: str | None = None

    @staticmethod
    def _require_env(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise KISServiceError(f"필수 환경변수 {name}가 설정되지 않았습니다.")
        return value

    def get_access_token(self) -> str:
        url = f"{self.base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        try:
            response = requests.post(
                url,
                headers={"content-type": "application/json"},
                json=body,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise KISServiceError(f"KIS 토큰 요청 실패: {exc}") from exc

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise KISServiceError(
                f"KIS 토큰 응답이 JSON이 아닙니다: {response.text[:300]}"
            ) from exc

        token = payload.get("access_token")
        if not token:
            message = payload.get("error_description") or payload.get("msg1") or payload
            raise KISServiceError(f"KIS access_token 발급 실패: {message}")
        self.access_token = str(token)
        return self.access_token

    def get_headers(self, tr_id: str) -> dict[str, str]:
        if not self.access_token:
            self.get_access_token()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
