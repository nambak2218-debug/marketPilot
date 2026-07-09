import os
import requests


class KISService:

    def __init__(self):

        self.base_url = os.environ["KIS_BASE_URL"]

        self.app_key = os.environ["KIS_APP_KEY"]

        self.app_secret = os.environ["KIS_APP_SECRET"]

    def get_access_token(self):

        url = f"{self.base_url}/oauth2/tokenP"

        body = {

            "grant_type": "client_credentials",

            "appkey": self.app_key,

            "appsecret": self.app_secret

        }

        response = requests.post(url, json=body)

        response.raise_for_status()

        token = response.json()["access_token"]

        return token
