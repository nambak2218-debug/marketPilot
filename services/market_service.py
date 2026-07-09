import yfinance as yf


class MarketService:

    @staticmethod
    def get_change(symbol):

        ticker = yf.Ticker(symbol)

        hist = ticker.history(
            period="5d",
            auto_adjust=True
        )

        close = hist["Close"].dropna()

        if len(close) < 2:
            return 0.0

        yesterday = close.iloc[-2]
        today = close.iloc[-1]

        return round(
            (today-yesterday)/yesterday*100,
            2
        )

    @classmethod
    def get_market_data(cls):

        return {

            "NASDAQ": cls.get_change("^IXIC"),

            "SOX": cls.get_change("^SOX"),

            "NVDA": cls.get_change("NVDA"),

            "MU": cls.get_change("MU")

        }
