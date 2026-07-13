from __future__ import annotations

from typing import Any


class ScoreService:
    """미국시장, 환율, 국내 수급을 이용해 0~100 점수를 계산한다."""

    @staticmethod
    def _supply_score(value: int | None, label: str) -> tuple[int, str]:
        if value is None:
            return 0, f"⚪ {label} 수급 미집계"
        if value > 0:
            return 5, f"✅ {label} 순매수"
        if value < 0:
            return -5, f"⚠️ {label} 순매도"
        return 0, f"⚪ {label} 수급 중립"

    def calculate(
        self,
        market: dict[str, float],
        supply_data: dict[str, int | None] | None = None,
    ) -> dict[str, Any]:
        required = {"NASDAQ", "SP500", "SOX", "VIX", "USDKRW"}
        missing = sorted(required - market.keys())
        if missing:
            raise ValueError(f"시장 데이터 누락: {', '.join(missing)}")

        score = 50
        reasons: list[str] = []

        if market["NASDAQ"] > 0:
            score += 8
            reasons.append("✅ 나스닥 상승")
        elif market["NASDAQ"] < 0:
            score -= 8
            reasons.append("⚠️ 나스닥 하락")
        else:
            reasons.append("⚪ 나스닥 보합")

        if market["SP500"] > 0:
            score += 5
            reasons.append("✅ S&P500 상승")
        elif market["SP500"] < 0:
            score -= 5
            reasons.append("⚠️ S&P500 하락")
        else:
            reasons.append("⚪ S&P500 보합")

        if market["SOX"] >= 2:
            score += 15
            reasons.append("✅ 반도체 강세")
        elif market["SOX"] > 0:
            score += 10
            reasons.append("✅ 반도체 상승")
        elif market["SOX"] < 0:
            score -= 12
            reasons.append("⚠️ 반도체 약세")
        else:
            reasons.append("⚪ 반도체 보합")

        if market["VIX"] < 0:
            score += 8
            reasons.append("✅ 변동성 안정")
        elif market["VIX"] > 0:
            score -= 8
            reasons.append("⚠️ 변동성 증가")
        else:
            reasons.append("⚪ 변동성 보합")

        if market["USDKRW"] < 0:
            score += 5
            reasons.append("✅ 환율 안정")
        elif market["USDKRW"] > 0:
            score -= 5
            reasons.append("⚠️ 원화 약세")
        else:
            reasons.append("⚪ 환율 보합")

        if supply_data is not None:
            for key, label in (
                ("foreign", "외국인"),
                ("institution", "기관"),
                ("program", "프로그램"),
            ):
                delta, reason = self._supply_score(supply_data.get(key), label)
                score += delta
                reasons.append(reason)

        score = max(0, min(100, int(round(score))))

        if score >= 75:
            signal = "🟢 레버리지 우세"
        elif score <= 40:
            signal = "🔴 인버스 우세"
        else:
            signal = "🟡 관망"

        confidence = min(100, abs(score - 50) * 2)

        return {
            "score": score,
            "signal": signal,
            "confidence": confidence,
            "reasons": reasons,
        }
