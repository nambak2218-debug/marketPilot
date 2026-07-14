# -*- coding: utf-8 -*-
"""
해외시장 서브스코어 백테스트

score_service.py의 ScoreService를 그대로 import해서 쓰기 때문에,
실제 MarketPilot 봇이 쓰는 로직과 100% 동일한 계산으로 검증한다.
(수급/선물 데이터는 과거 이력이 없으므로 이 백테스트에서는 제외 -
 순수하게 "해외시장 5개 지표"만으로 계산한 점수의 예측력을 본다.)

사용법:
    python backtest_overseas_score.py --years 2
    python backtest_overseas_score.py --start 2023-01-01 --end 2026-07-01

결과:
    - 콘솔에 전체 정확도 / 신호 구간별 정확도 출력
    - backtest_result.csv 에 일별 상세 데이터 저장
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, ".")  # services/ 패키지를 프로젝트 루트 기준으로 import
from services.score_service import ScoreService  # noqa: E402

TICKERS = {
    "NASDAQ": "^IXIC",
    "SP500": "^GSPC",
    "SOX": "^SOX",
    "VIX": "^VIX",
    "USDKRW": "KRW=X",
    "KOSPI": "^KS11",
}


def fetch_pct_change(ticker: str, start: str, end: str) -> pd.Series:
    """일별 종가 기준 전일 대비 등락률(%)을 반환한다."""
    df = yf.Ticker(ticker).history(start=start, end=end, interval="1d", auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"{ticker} 데이터를 받아오지 못했습니다.")
    close = df["Close"].dropna()
    pct = close.pct_change() * 100
    pct.index = pd.to_datetime(pct.index).tz_localize(None).normalize()
    return pct.rename(ticker)


def build_dataset(start: str, end: str) -> pd.DataFrame:
    series = {name: fetch_pct_change(symbol, start, end) for name, symbol in TICKERS.items()}

    # 미국/환율 지표는 KOSPI 개장 전날 밤에 마감한 데이터이므로,
    # 하루를 앞으로 밀어서 "그 다음 KOSPI 거래일"과 짝지어준다.
    overseas_cols = ["NASDAQ", "SP500", "SOX", "VIX", "USDKRW"]
    shifted = {}
    for name in overseas_cols:
        s = series[name].copy()
        s.index = s.index + pd.Timedelta(days=1)
        shifted[name] = s

    kospi = series["KOSPI"]

    df = pd.DataFrame(shifted)
    df["KOSPI_return"] = kospi
    df = df.dropna(how="all", subset=overseas_cols)
    df = df.dropna(subset=["KOSPI_return"])
    return df.sort_index()


def score_row(row: pd.Series) -> int:
    market = {
        "NASDAQ": None if pd.isna(row["NASDAQ"]) else row["NASDAQ"],
        "SP500": None if pd.isna(row["SP500"]) else row["SP500"],
        "SOX": None if pd.isna(row["SOX"]) else row["SOX"],
        "VIX": None if pd.isna(row["VIX"]) else row["VIX"],
        "USDKRW": None if pd.isna(row["USDKRW"]) else row["USDKRW"],
    }
    # supply_data=None, futures_data=None → 해외시장 서브스코어만 계산됨
    result = ScoreService().calculate(market, supply_data=None, futures_data=None)
    return result["score"]


SIGNAL_BANDS = [
    (80, 101, "레버리지 우세(80+)"),
    (65, 80, "상승 우세(65-79)"),
    (46, 65, "관망(46-64)"),
    (31, 46, "하락 우세(31-45)"),
    (0, 31, "인버스 우세(0-30)"),
]


def band_label(score: int) -> str:
    for lo, hi, label in SIGNAL_BANDS:
        if lo <= score < hi:
            return label
    return "미분류"


def run_backtest(start: str, end: str) -> pd.DataFrame:
    df = build_dataset(start, end)
    df["score"] = df.apply(score_row, axis=1)
    df["predicted_up"] = df["score"] > 50
    df["actual_up"] = df["KOSPI_return"] > 0
    df["hit"] = df["predicted_up"] == df["actual_up"]
    df["band"] = df["score"].apply(band_label)
    return df


def summarize(df: pd.DataFrame) -> None:
    total = len(df)
    hit_rate = df["hit"].mean() * 100
    corr = df["score"].sub(50).corr(df["KOSPI_return"])

    print(f"\n=== 전체 결과 ({df.index.min().date()} ~ {df.index.max().date()}, n={total}) ===")
    print(f"방향 적중률: {hit_rate:.1f}%")
    print(f"(score-50)과 KOSPI 다음날 수익률의 상관계수: {corr:.3f}")

    print("\n=== 신호 구간별 결과 ===")
    band_order = [label for _, _, label in SIGNAL_BANDS]
    grouped = df.groupby("band").agg(
        건수=("hit", "size"),
        적중률=("hit", "mean"),
        평균수익률=("KOSPI_return", "mean"),
    )
    grouped["적중률"] = (grouped["적중률"] * 100).round(1)
    grouped["평균수익률"] = grouped["평균수익률"].round(2)
    grouped = grouped.reindex(band_order).dropna(how="all")
    print(grouped.to_string())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument("--years", type=int, default=2, help="--start 미지정시 최근 N년")
    parser.add_argument("--out", type=str, default="backtest_result.csv")
    args = parser.parse_args()

    end = args.end or date.today().isoformat()
    start = args.start or (date.today() - timedelta(days=365 * args.years)).isoformat()

    print(f"백테스트 기간: {start} ~ {end}")
    df = run_backtest(start, end)
    summarize(df)

    df.to_csv(args.out, encoding="utf-8-sig")
    print(f"\n일별 상세 데이터 저장: {args.out}")


if __name__ == "__main__":
    main()
