import requests
from services.kis_service import KISService


class SupplyAPIService:


    def __init__(self):

        self.kis = KISService()



    def get_supply(self):

        # 현재는 코스피 대표값 기준
        # 다음 단계에서 종목/ETF별 확장

        url = (
            f"{self.kis.base_url}"
            "/uapi/domestic-stock/v1/quotations/"
            "inquire-investor"
        )


        headers = self.kis.get_headers(
            "FHPTJ04040000"
        )


        params = {

            "FID_COND_MRKT_DIV_CODE": "J",

            "FID_INPUT_ISCD": "0001"

        }


        response = requests.get(
            url,
            headers=headers,
            params=params
        )


        data = response.json()


        return data
