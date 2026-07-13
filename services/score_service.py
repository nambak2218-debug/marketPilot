from __future__ import annotations

from typing import Any


class ScoreService:
    """미국시장, 환율, 국내 수급으로 0~100 점수를 계산한다."""

    @staticmethod
    def _direction_score(
        value: float,
        *,
        positive_points: int,
        negative_points: int,
        strong_threshold: float,
        positive_reason: str,
        strong_positive_reason: str,
        negative_reason: str,
        strong_negative_reason: str,
        neutral_reason: str,
    ) -> tuple[int, str]:
        if value >= strong_threshold:
            return positive_points, strong_positive_reason
        if value > 0:
            return max(1, round(positive_points * 0.65)), positive_reason
        if value <= -strong_threshold:
            return -negative_points, strong_negative_reason
        if value < 0:
            return -max(1, round(negative_points * 0.65)), negative_reason
        return 0, neutral_reason

    @staticmethod
    def _inverse_score(
        value: float,
        *,
        positive_points: int,
        negative_points: int,
        strong_threshold: float,
        positive_reason: str,
        strong_positive_reason: str,
        negative_reason: str,
        strong_negative_reason: str,
        neutral_reason: str,
    ) -> tuple[int, str]:
        if value <= -strong_threshold:
            return positive_points, strong_positive_reason
        if value < 0:
            return max(1, round(positive_points * 0.65)), positive_reason
        if value >= strong_threshold:
            return -negative_points, strong_negative_reason
        if value > 0:
            return -max(1, round(negative_points * 0.65)), negative_reason
        return 0, neutral_reason

    @staticmethod
    def _supply_score(
        value: int | None,
        label: str,
        *,
        normal_points: int,
        strong_points: int,
        strong_threshold: int,
    ) -> tuple[int, str, bool]:
        if value is None:
            return 0, f"⚪ {label} 수급 미집계", False
        if value >= strong_threshold:
            return strong_points, f"✅ {label} 강한 순매수", True
        if value > 0:
            return normal_points, f"✅ {label} 순매수", True
        if value <= -strong_threshold:
            return -strong_points, f"⚠️ {label} 강한 순매도", True
        if value < 0:
            return -normal_points, f"⚠️ {label} 순매도", True
        return 0, f"⚪ {label} 수급 중립", True

    @staticmethod
    def _signal_and_action(score: int, session: str) -> tuple[str, str]:
        if score >= 80:
            signal = "🟢 레버리지 우세"
            action = "상승 흐름 확인 후 분할 접근"
        elif score >= 65:
            signal = "🟢 상승 우세"
            action = "무리한 추격보다 눌림목 중심 대응"
        elif score <= 30:
            signal = "🔴 인버스 우세"
            action = "반등 추격을 피하고 위험 노출 축소"
        elif score <= 45:
            signal = "🔴 하락 우세"
            action = "신규 진입을 줄이고 방어적으로 대응"
        else:
            signal = "🟡 관망"
            action = "방향 확인 전까지 포지션 확대 자제"

        if session == "pre_market":
            action += " · 개장 후 수급 재확인"
        elif session == "market_open":
            action += " · 현재 수급 지속 여부 확인"

        return signal, action

    def calculate(
        self,
        market: dict[str, float],
        supply_data: dict[str, int | None] | None = None,
        *,
        session: str = "market_open",
    ) -> dict[str, Any]:
        required = {"NASDAQ", "SP500", "SOX", "VIX", "USDKRW"}
        missing = sorted(required - market.keys())
        if missing:
            raise ValueError(f"시장 데이터 누락: {', '.join(missing)}")

        score = 50
        reasons: list[str] = []

        market_rules = [
            self._direction_score(
                market["NASDAQ"], positive_points=9, negative_points=9,
                strong_threshold=1.0, positive_reason="✅ 나스닥 상승",
                strong_positive_reason="✅ 나스닥 강세",
                negative_reason="⚠️ 나스닥 하락",
                strong_negative_reason="⚠️ 나스닥 급락",
                neutral_reason="⚪ 나스닥 보합",
            ),
            self._direction_score(
                market["SP500"], positive_points=7, negative_points=7,
                strong_threshold=0.8, positive_reason="✅ S&P500 상승",
                strong_positive_reason="✅ S&P500 강세",
                negative_reason="⚠️ S&P500 하락",
                strong_negative_reason="⚠️ S&P500 급락",
                neutral_reason="⚪ S&P500 보합",
            ),
            self._direction_score(
                market["SOX"], positive_points=14, negative_points=14,
                strong_threshold=2.0, positive_reason="✅ 반도체 상승",
                strong_positive_reason="✅ 반도체 강세",
                negative_reason="⚠️ 반도체 하락",
                strong_negative_reason="⚠️ 반도체 급락",
                neutral_reason="⚪ 반도체 보합",
            ),
            self._inverse_score(
                market["VIX"], positive_points=9, negative_points=9,
                strong_threshold=4.0, positive_reason="✅ 변동성 안정",
                strong_positive_reason="✅ 변동성 크게 안정",
                negative_reason="⚠️ 변동성 증가",
                strong_negative_reason="⚠️ 변동성 급등",
                neutral_reason="⚪ 변동성 보합",
            ),
            self._inverse_score(
                market["USDKRW"], positive_points=7, negative_points=7,
                strong_threshold=0.7, positive_reason="✅ 환율 안정",
                strong_positive_reason="✅ 원화 강세",
                negative_reason="⚠️ 원화 약세",
                strong_negative_reason="⚠️ 환율 급등",
                neutral_reason="⚪ 환율 보합",
            ),
        ]

        for delta, reason in market_rules:
            score += delta
            reasons.append(reason)

        available_items = 5
        total_items = 8

        if supply_data is not None:
            # 장전에는 전일 외국인·기관은 반영하되 당일 프로그램 미집계는 중립 처리한다.
            supply_rules = (
                ("foreign", "외국인", 6, 10, 1000),
                ("institution", "기관", 5, 8, 1000),
                ("program", "외국인 프로그램", 4, 6, 500),
            )
            for key, label, normal, strong, threshold in supply_rules:
                delta, reason, available = self._supply_score(
                    supply_data.get(key), label,
                    normal_points=normal, strong_points=strong,
                    strong_threshold=threshold,
                )
                score += delta
                reasons.append(reason)
                if available:
                    available_items += 1

        score = max(0, min(100, int(round(score))))
        signal, action = self._signal_and_action(score, session)

        directional_confidence = min(100, abs(score - 50) * 2)
        completeness = available_items / total_items
        confidence = int(round(directional_confidence * (0.65 + 0.35 * completeness)))
        confidence = max(10, min(100, confidence))

        return {
            "score": score,
            "signal": signal,
            "action": action,
            "confidence": confidence,
            "reasons": reasons,
            "data_completeness": round(completeness * 100),
        }
