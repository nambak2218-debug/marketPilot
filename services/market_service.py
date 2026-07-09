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

    @staticmethod
    def get_change(symbol):

        ticker = yf.Ticker(symbol)

        hist = ticker.history(
            period="5d",
            auto_adjust=True
        )

        if hist.empty:
            return 0.0

        close = hist["Close"].dropna()

        if len(close) < 2:
            return 0.0

        yesterday = float(close.iloc[-2])
        today = float(close.iloc[-1])

        return round(
            (today - yesterday) / yesterday * 100,
            2
        )

    @classmethod
    def get_market_data(cls):

        result = {}

        for name, symbol in cls.SYMBOLS.items():

            try:

                result[name] = cls.get_change(symbol)

            except Exception:

                result[name] = 0.0

        return result
