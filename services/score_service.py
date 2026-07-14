from __future__ import annotations

import os
from typing import Any


class ScoreService:
    """미국시장, 환율, 국내 수급으로 0~100 점수를 계산한다."""

    @staticmethod
    def _direction_score(
        value: float | None,
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
        if value is None:
            return 0, neutral_reason.replace("보합", "데이터 없음")
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
        value: float | None,
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
        if value is None:
            return 0, neutral_reason.replace("보합", "데이터 없음")
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
    def _signal_and_actions(score: int, session: str) -> tuple[str, list[str]]:
        if score >= 80:
            signal = "🟢 레버리지 우세"
            actions = [
                "상승 흐름 확인 후 분할 접근",
                "급등 추격보다 눌림목 중심 대응",
                "손절 기준을 정하고 비중 관리",
            ]
        elif score >= 65:
            signal = "🟢 상승 우세"
            actions = [
                "무리한 추격보다 눌림목 중심 대응",
                "수급이 유지되는 종목 위주로 선별",
                "포지션은 단계적으로 확대",
            ]
        elif score <= 30:
            signal = "🔴 인버스 우세"
            actions = [
                "신규 레버리지 진입 자제",
                "반등 추격을 피하고 위험 노출 축소",
                "장중 수급 반전 여부 재확인",
            ]
        elif score <= 45:
            signal = "🔴 하락 우세"
            actions = [
                "신규 진입을 줄이고 방어적으로 대응",
                "약한 반등에서 비중 확대 자제",
                "외국인·프로그램 수급 확인",
            ]
        else:
            signal = "🟡 관망"
            actions = [
                "방향 확인 전까지 포지션 확대 자제",
                "장중 돌파·이탈 확인 후 대응",
                "현금 비중을 유지하며 관찰",
            ]

        if session == "pre_market":
            actions[-1] = "개장 후 외국인·프로그램 수급 재확인"
        elif session == "market_open":
            actions[-1] = "현재 수급이 이어지는지 지속 확인"
        elif session == "after_market":
            actions[-1] = "마감 수급을 바탕으로 다음 거래일 준비"

        return signal, actions

    @staticmethod
    def _risk_level(score: int, market: dict[str, float]) -> tuple[int, str]:
        downside = max(0, 50 - score)
        vix_penalty = max(0.0, market.get("VIX") or 0.0) * 2.0
        sox_penalty = max(0.0, -(market.get("SOX") or 0.0)) * 3.0
        risk_value = downside + vix_penalty + sox_penalty

        if risk_value >= 60:
            return 5, "매우 높음"
        if risk_value >= 42:
            return 4, "높음"
        if risk_value >= 25:
            return 3, "보통"
        if risk_value >= 12:
            return 2, "낮음"
        return 1, "매우 낮음"

    @staticmethod
    def _volatility_level(market: dict[str, float]) -> tuple[int, str]:
        pressure = abs(market.get("NASDAQ") or 0.0) + abs(market.get("SOX") or 0.0) * 0.8 + max(0.0, market.get("VIX") or 0.0) * 0.45
        if pressure >= 7.0:
            return 5, "매우 높음"
        if pressure >= 4.5:
            return 4, "높음"
        if pressure >= 2.5:
            return 3, "보통"
        if pressure >= 1.2:
            return 2, "낮음"
        return 1, "매우 낮음"

    @staticmethod
    def _tomorrow_outlook(score: int, confidence: int) -> str:
        if confidence < 35:
            return "방향성 불확실 · 다음 거래일 장전 데이터 재확인"
        if score >= 75:
            return "긍정 흐름 지속 가능성 우세"
        if score >= 60:
            return "완만한 긍정 우세 · 수급 확인 필요"
        if score <= 25:
            return "부정 흐름 지속 가능성 우세"
        if score <= 40:
            return "약세 지속 가능성 · 반등 강도 확인 필요"
        return "중립 구간 · 해외시장과 환율 변화 확인"

    def calculate(
        self,
        market: dict[str, float | None],
        supply_data: dict[str, int | None] | None = None,
        *,
        session: str = "market_open",
        futures_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

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

        market_keys = ("NASDAQ", "SP500", "SOX", "VIX", "USDKRW")
        available_items = sum(1 for key in market_keys if market.get(key) is not None)
        total_items = 8

        if supply_data is not None:
            supply_rules = (
                ("foreign", "외국인", 6, 10, int(os.getenv("SUPPLY_STRONG_THRESHOLD_MKRW", "100000"))),
                ("institution", "기관", 5, 8, int(os.getenv("SUPPLY_STRONG_THRESHOLD_MKRW", "100000"))),
                ("program", "외국인 프로그램", 4, 6, int(os.getenv("PROGRAM_STRONG_THRESHOLD_SHARES", "100000"))),
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

        if futures_data and futures_data.get("available"):
            chosen = futures_data.get("day") or futures_data.get("night") or {}
            disparity = chosen.get("disparity")
            basis = chosen.get("basis")
            if disparity is not None:
                if disparity >= 0.3: score += 7; reasons.append("✅ 선물 괴리율 강한 플러스")
                elif disparity > 0: score += 4; reasons.append("✅ 선물 괴리율 플러스")
                elif disparity <= -0.3: score -= 7; reasons.append("⚠️ 선물 괴리율 강한 마이너스")
                elif disparity < 0: score -= 4; reasons.append("⚠️ 선물 괴리율 마이너스")
                available_items += 1; total_items += 1
            elif basis is not None:
                if basis > 0: score += 3; reasons.append("✅ 선물 시장 베이시스 플러스")
                elif basis < 0: score -= 3; reasons.append("⚠️ 선물 시장 베이시스 마이너스")
                available_items += 1; total_items += 1

        score = max(0, min(100, int(round(score))))
        signal, actions = self._signal_and_actions(score, session)

        directional_confidence = min(100, abs(score - 50) * 2)
        completeness = available_items / total_items
        confidence = int(round(directional_confidence * (0.65 + 0.35 * completeness)))
        confidence = max(10, min(100, confidence))

        risk_stars, risk_label = self._risk_level(score, market)
        volatility_stars, volatility_label = self._volatility_level(market)

        return {
            "score": score,
            "signal": signal,
            "actions": actions,
            "confidence": confidence,
            "reasons": reasons,
            "data_completeness": round(completeness * 100),
            "risk_stars": risk_stars,
            "risk_label": risk_label,
            "volatility_stars": volatility_stars,
            "volatility_label": volatility_label,
            "tomorrow_outlook": self._tomorrow_outlook(score, confidence),
        }
