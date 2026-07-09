import csv
from datetime import datetime
from pathlib import Path


class HistoryService:

    FILE = Path("data/history.csv")

    @classmethod
    def save(
        cls,
        score,
        signal,
        market
    ):

        with open(
            cls.FILE,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                score,
                signal,
                market["NASDAQ"],
                market["SOX"],
                market["NVDA"],
                market["MU"],
                market["VIX"],
                market["USDKRW"]
            ])
