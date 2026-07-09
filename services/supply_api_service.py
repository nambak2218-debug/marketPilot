import requests

from services.kis_service import KISService


class SupplyAPIService:

    def __init__(self):

        self.kis = KISService()


    def get_supply(self):

        url = (
            f"{self.kis.base_url}"
            "/uapi/domestic-stock/v1/quotations/inquire-investor"
        )


        headers = self.kis.get_headers(
            "FHPTJ04040000"
        )


        params = {

            # 코스피
            "FID_COND_MRKT_DIV_CODE": "J",

            # 삼성전자 테스트
            "FID_INPUT_ISCD": "005930",

        }


        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )


        print("KIS STATUS:", response.status_code)

        print("KIS BODY:", response.text)


        return response.json()
