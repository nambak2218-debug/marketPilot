import yfinance as yf


class MarketService:

    SYMBOLS = {

        "NASDAQ": "^IXIC",
        "SP500": "^GSPC",
        "SOX": "^SOX",
        "VIX": "^VIX",

        "NVDA": "NVDA",
        "MU": "MU",

        "USDKRW": "KRW=X"

    }

    @classmethod
    def get_market_data(cls):

        result = {}

        for name, symbol in cls.SYMBOLS.items():

            result[name] = cls._change(symbol)

        return result

    @staticmethod
    def _change(symbol):

        try:

            ticker = yf.Ticker(symbol)

            df = ticker.history(
                period="5d",
                auto_adjust=True
            )

            close = df["Close"].dropna()

            if len(close) < 2:
                return 0.0

            yesterday = float(close.iloc[-2])

            today = float(close.iloc[-1])

            return round(
                (today-yesterday)/yesterday*100,
                2
            )

        except:

            return 0.0
