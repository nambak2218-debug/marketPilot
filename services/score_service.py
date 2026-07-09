class ScoreService:

    @staticmethod
    def calculate(data):

        score = 50

        score += data["NASDAQ"]*5
        score += data["SOX"]*3
        score += data["NVDA"]*2
        score += data["MU"]*2

        score = round(score)

        score = max(0, min(100, score))

        if score >= 70:

            signal = "🟢 레버리지"

        elif score >= 40:

            signal = "🟡 관망"

        else:

            signal = "🔴 인버스"

        return score, signal
