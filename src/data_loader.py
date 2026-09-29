"""
data_loader.py
===============
Loads the project's actual monthly price files (Date, Ticker,
Adjusted_Close) and builds the validated monthly panel used by every
downstream calculation. This is the loader that actually produced the
locked results; it matches the plain monthly-Adjusted_Close schema of
data/indian_quant_monthly_data_v2.csv and data/nifty50_monthly_data.csv,
not a full daily-OHLCV feed.

It never invents a price, never silently bridges a gap, and never treats
a missing return as zero. Every issue it finds is recorded in a
DataQualityReport and returned alongside the data, not corrected in
place.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

import config


@dataclass
class DataQualityReport:
    issues: list = field(default_factory=list)

    def add(self, severity: str, subject: str, description: str):
        self.issues.append({"severity": severity, "subject": subject, "issue": description})

    def to_dataframe(self) -> pd.DataFrame:
        if not self.issues:
            return pd.DataFrame([{"severity": "INFO", "subject": "ALL", "issue": "No data-quality issues detected."}])
        return pd.DataFrame(self.issues)


def _load_monthly_csv(csv_path: str, ticker_map: dict, dqr: DataQualityReport, label: str) -> pd.DataFrame:
    """
    Shared loader for both the stock file and the benchmark file. Expects
    columns Date, Ticker, Adjusted_Close. Maps raw tickers to logical
    names via ticker_map (identity map of {ticker: ticker} for the
    benchmark, which has only one series).
    """
    raw = pd.read_csv(csv_path)
    expected_cols = {"Date", "Ticker", "Adjusted_Close"}
    if not expected_cols.issubset(raw.columns):
        raise ValueError(f"{csv_path}: expected columns {expected_cols}, got {list(raw.columns)}")

    raw["Date"] = pd.to_datetime(raw["Date"])
    raw["Month"] = raw["Date"].dt.to_period("M")

    unmapped = sorted(set(raw["Ticker"]) - set(ticker_map))
    if unmapped:
        dqr.add("ERROR", str(unmapped), f"{label}: ticker(s) with no declared mapping in config.UNIVERSE. Excluded.")
        raw = raw[raw["Ticker"].isin(ticker_map)]

    raw["LogicalStock"] = raw["Ticker"].map(ticker_map)

    # Duplicate (stock, month) rows
    dup_mask = raw.duplicated(subset=["LogicalStock", "Month"], keep="first")
    if dup_mask.any():
        for stock, cnt in raw[dup_mask].groupby("LogicalStock").size().items():
            dqr.add("WARNING", stock, f"{label}: {cnt} duplicate (stock, month) row(s); kept first, dropped rest.")
        raw = raw[~dup_mask]

    # Missing / non-positive prices
    bad = raw[raw["Adjusted_Close"].isna() | (raw["Adjusted_Close"] <= 0)]
    if len(bad):
        for stock, cnt in bad.groupby("LogicalStock").size().items():
            dqr.add("WARNING", stock, f"{label}: {cnt} row(s) with missing/non-positive Adjusted_Close.")
        raw = raw[~(raw["Adjusted_Close"].isna() | (raw["Adjusted_Close"] <= 0))]

    # Gaps in monthly coverage
    for stock, g in raw.groupby("LogicalStock"):
        months = sorted(g["Month"].unique())
        expected = pd.period_range(months[0], months[-1], freq="M")
        missing = sorted(set(expected) - set(months))
        if missing:
            dqr.add("ERROR", stock, f"{label}: missing month(s) {[str(m) for m in missing]}.")

    monthly = (
        raw.sort_values(["LogicalStock", "Month"])
        .rename(columns={"Adjusted_Close": "MonthEndPrice", "Date": "MonthEndDate"})
        [["LogicalStock", "Month", "MonthEndPrice", "MonthEndDate"]]
        .reset_index(drop=True)
    )
    monthly["PrevMonthEndPrice"] = monthly.groupby("LogicalStock")["MonthEndPrice"].shift(1)
    monthly["MonthlyReturn"] = monthly["MonthEndPrice"] / monthly["PrevMonthEndPrice"] - 1.0

    # Abnormal single-month moves (>30%): flagged, never altered
    abnormal = monthly[monthly["MonthlyReturn"].abs() > 0.30]
    for _, r in abnormal.iterrows():
        dqr.add(
            "WARNING", r["LogicalStock"],
            f"{label}: abnormal monthly move of {r['MonthlyReturn']:+.1%} in {r['Month']} "
            f"({r['PrevMonthEndPrice']:.2f} -> {r['MonthEndPrice']:.2f}). Value used as supplied; "
            f"not altered.",
        )
    return monthly


def load_stock_universe(csv_path: str, dqr: DataQualityReport) -> pd.DataFrame:
    """Load the five-stock monthly panel using config.UNIVERSE's ticker mapping."""
    return _load_monthly_csv(csv_path, config.UNIVERSE, dqr, label="stock universe")


def load_benchmark(csv_path: str, dqr: DataQualityReport) -> pd.DataFrame:
    """Load the Nifty 50 Price Index monthly panel."""
    ticker_map = {config.BENCHMARK_TICKER: config.BENCHMARK_TICKER}
    return _load_monthly_csv(csv_path, ticker_map, dqr, label="benchmark")


def validate_study_window(monthly: pd.DataFrame, dqr: DataQualityReport):
    """Confirm every logical stock's data spans the declared study window."""
    start_period = pd.Period(config.STUDY_START, freq="M")
    end_period = pd.Period(config.STUDY_END, freq="M")
    for stock in set(config.UNIVERSE.values()):
        g = monthly[monthly["LogicalStock"] == stock]
        if g.empty:
            dqr.add("ERROR", stock, "No data found for this stock.")
            continue
        actual_start, actual_end = g["Month"].min(), g["Month"].max()
        if actual_start > start_period:
            dqr.add("ERROR", stock, f"Data starts at {actual_start}, after declared study start {start_period}.")
        if actual_end < end_period:
            dqr.add("ERROR", stock, f"Data ends at {actual_end}, before declared study end {end_period}.")


def load_and_prepare(prices_csv: str, benchmark_csv: str):
    """
    Full pipeline: two raw monthly CSVs -> validated stock monthly panel,
    validated benchmark monthly panel, and one combined DataQualityReport.
    """
    dqr = DataQualityReport()
    monthly = load_stock_universe(prices_csv, dqr)
    bench_monthly = load_benchmark(benchmark_csv, dqr)
    validate_study_window(monthly, dqr)
    return monthly, bench_monthly, dqr
