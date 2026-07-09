import json
from pathlib import Path


class ScoreService:

    def __init__(self):

        path = Path("config/weights.json")

        with open(path, encoding="utf-8") as f:

            self.weights = json.load(f)

    def calculate(self, market):

        score = 50

        detail = {}

        for key, weight in self.weights.items():

            value = market.get(key, 0)

            if key == "VIX":

                # VIX는 하락할수록 시장에는 긍정적
                contribution = -value * (weight / 10)

            else:

                contribution = value * (weight / 10)

            detail[key] = round(contribution, 2)

            score += contribution

        score = max(0, min(100, round(score)))

        if score >= 70:
            signal = "🟢 레버리지"

        elif score >= 40:
            signal = "🟡 관망"

        else:
            signal = "🔴 인버스"

        confidence = min(
            100,
            abs(score - 50) * 2
        )

        return {
            "score": score,
            "signal": signal,
            "confidence": confidence,
            "detail": detail
        }
