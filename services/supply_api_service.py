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
            "FHPTJ04030000"
        )


        params = {

            "FID_COND_MRKT_DIV_CODE": "J",

            "FID_INPUT_ISCD": "005930",

            "FID_INPUT_ISCD_2": "005930"

        }


        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )


        print("KIS RESPONSE")
        print(response.text)


        return response.json()
