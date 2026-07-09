class SignalService:

    @staticmethod
    def decide(score):

        if score >= 80:

            return "🟢 강한 레버리지"

        if score >= 65:

            return "🟢 레버리지"

        if score >= 45:

            return "🟡 관망"

        if score >= 25:

            return "🔴 인버스"

        return "🔴 강한 인버스"
