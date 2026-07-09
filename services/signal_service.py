class SignalService:

    @staticmethod
    def decide(score):

        if score >= 80:
            return {
                "emoji": "🟢",
                "action": "강한 레버리지",
                "color": "GREEN"
            }

        if score >= 65:
            return {
                "emoji": "🟢",
                "action": "레버리지",
                "color": "GREEN"
            }

        if score >= 45:
            return {
                "emoji": "🟡",
                "action": "관망",
                "color": "YELLOW"
            }

        if score >= 25:
            return {
                "emoji": "🔴",
                "action": "인버스",
                "color": "RED"
            }

        return {
            "emoji": "🔴",
            "action": "강한 인버스",
            "color": "RED"
        }
