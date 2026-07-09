import os
import requests


class KISService:

    def __init__(self):

        self.base_url = os.getenv("KIS_BASE_URL")

        self.app_key = os.getenv("KIS_APP_KEY")

        self.app_secret = os.getenv("KIS_APP_SECRET")

        if not self.base_url:
            raise Exception("KIS_BASE_URL Secret이 없습니다.")

        if not self.app_key:
            raise Exception("KIS_APP_KEY Secret이 없습니다.")

        if not self.app_secret:
            raise Exception("KIS_APP_SECRET Secret이 없습니다.")

    def get_access_token(self):

        url = f"{self.base_url}/oauth2/tokenP"

        headers = {
            "content-type": "application/json"
        }

        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=30
        )

        response.raise_for_status()

        return response.json()["access_token"]
