class SupplyService:

    def calculate_score(self, foreign, institution, program):

        score = 0
        reasons = []

        # 외국인 수급
        if foreign > 0:
            score += 15
            reasons.append("✅ 외국인 순매수")
        else:
            score -= 15
            reasons.append("⚠️ 외국인 순매도")


        # 기관 수급
        if institution > 0:
            score += 10
            reasons.append("✅ 기관 순매수")
        else:
            score -= 10
            reasons.append("⚠️ 기관 순매도")


        # 프로그램
        if program > 0:
            score += 10
            reasons.append("✅ 프로그램 매수")
        else:
            score -= 10
            reasons.append("⚠️ 프로그램 매도")


        return {
            "score": score,
            "reasons": reasons
        }
