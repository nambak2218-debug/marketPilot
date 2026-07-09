import os
import requests


class KISService:

    def __init__(self):

        self.base_url = os.environ["KIS_BASE_URL"]
        self.app_key = os.environ["KIS_APP_KEY"]
        self.app_secret = os.environ["KIS_APP_SECRET"]

        self.access_token = None


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
            json=body
        )

        response.raise_for_status()

        self.access_token = response.json()["access_token"]

        return self.access_token



    def get_headers(self, tr_id):

        if not self.access_token:
            self.get_access_token()


        return {

            "content-type":
                "application/json; charset=utf-8",

            "authorization":
                f"Bearer {self.access_token}",

            "appkey":
                self.app_key,

            "appsecret":
                self.app_secret,

            "tr_id":
                tr_id
        }
