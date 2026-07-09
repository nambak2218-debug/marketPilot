from services.supply_service import SupplyService


class ScoreService:

    def __init__(self):
        self.supply = SupplyService()


    def calculate(self, market, supply_data=None):

        score = 50
        reasons = []


        # 미국시장
        if market["NASDAQ"] > 0:
            score += 10
            reasons.append("✅ 나스닥 상승")
        else:
            score -= 10
            reasons.append("⚠️ 나스닥 약세")


        # 반도체
        if market["SOX"] > 0:
            score += 15
            reasons.append("✅ 반도체 강세")
        else:
            score -= 15
            reasons.append("⚠️ 반도체 약세")


        # VIX
        if market["VIX"] < 0:
            score += 10
            reasons.append("✅ 변동성 안정")
        else:
            score -= 10
            reasons.append("⚠️ 변동성 증가")


        # 환율
        if market["USDKRW"] < 0:
            score += 5
            reasons.append("✅ 환율 안정")
        else:
            score -= 5
            reasons.append("⚠️ 원화 약세")


        # 수급 추가
        if supply_data:

            supply_result = self.supply.calculate_score(
                supply_data["foreign"],
                supply_data["institution"],
                supply_data["program"]
            )

            score += supply_result["score"]

            reasons.extend(
                supply_result["reasons"]
            )


        # 점수 제한
        score = max(0, min(100, score))


        if score >= 75:
            signal = "🟢 레버리지 우세"

        elif score <= 40:
            signal = "🔴 인버스 우세"

        else:
            signal = "🟡 관망"


        confidence = abs(score - 50) * 2


        return {
            "score": score,
            "signal": signal,
            "confidence": confidence,
            "reasons": reasons
        }
