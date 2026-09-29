"""
backtest_engine.py
===================
Orchestrates the full, locked pipeline: load data -> build the no-look-
-ahead ranking table -> build the Momentum, Mean Reversion, and Nifty 50
Price Index portfolios -> compute performance metrics and drawdown.

This module contains no CLI parsing; it exposes run_baseline(), which is
called by scripts/run_real_backtest.py. Nothing in this file changes the
locked methodology - it is the same logic already validated and reported
in the research paper, reorganized for reproducibility.
"""

from __future__ import annotations
import pandas as pd

import config
import data_loader
import strategies
import portfolio as port
import metrics


def run_baseline(prices_csv: str, benchmark_csv: str):
    """
    Runs the full baseline backtest and returns a dict of DataFrames and
    the data-quality report. Raises no exception on data-quality findings;
    issues are recorded in the report, not silently fixed.
    """
    monthly, bench_monthly, dqr = data_loader.load_and_prepare(prices_csv, benchmark_csv)

    ranking_table, incomplete_months = strategies.build_ranking_table(monthly)
    if incomplete_months:
        dqr.add(
            "INFO", "ALL",
            f"Month(s) with fewer than {config.N_SELECT} valid signals "
            f"(no trade possible / undefined selection): {incomplete_months}",
        )

    mom_portfolio = port.build_strategy_portfolio(ranking_table, monthly, "momentum")
    mr_portfolio = port.build_strategy_portfolio(ranking_table, monthly, "mean_reversion")

    bench_input = bench_monthly.rename(columns={"MonthlyReturn": "MonthlyReturn"})[["Month", "MonthlyReturn"]]
    bench_portfolio = port.build_benchmark_portfolio(bench_input)

    # Drop the one hypothetical holding month the ranking table always
    # generates one step beyond the last real price observation (it has a
    # signal but, correctly, no realized return because no further price
    # exists). This is not a data problem; it is simply not a real,
    # evaluable month.
    last_real_month = monthly["Month"].max()
    mom_portfolio = mom_portfolio[mom_portfolio["Month"] <= last_real_month].reset_index(drop=True)
    mr_portfolio = mr_portfolio[mr_portfolio["Month"] <= last_real_month].reset_index(drop=True)

    mom_dd = port.compute_drawdown(mom_portfolio.set_index("Month")["PortfolioValue"])
    mr_dd = port.compute_drawdown(mr_portfolio.set_index("Month")["PortfolioValue"])
    bench_dd = port.compute_drawdown(bench_portfolio.set_index("Month")["PortfolioValue"])

    metrics_table = pd.DataFrame([
        metrics.full_metrics_row("Momentum", mom_portfolio["PortfolioValue"], mom_portfolio["PortfolioReturn"]),
        metrics.full_metrics_row("Mean Reversion", mr_portfolio["PortfolioValue"], mr_portfolio["PortfolioReturn"]),
        metrics.full_metrics_row("Nifty 50 Price Index", bench_portfolio["PortfolioValue"], bench_portfolio["PortfolioReturn"]),
    ])

    return {
        "monthly": monthly,
        "bench_monthly": bench_monthly,
        "ranking_table": ranking_table,
        "mom_portfolio": mom_portfolio,
        "mr_portfolio": mr_portfolio,
        "bench_portfolio": bench_portfolio,
        "mom_drawdown": mom_dd,
        "mr_drawdown": mr_dd,
        "bench_drawdown": bench_dd,
        "metrics_table": metrics_table,
        "data_quality_report": dqr,
    }


def run_common_active_period(prices_csv: str, benchmark_csv: str, start_month: str = "2023-10"):
    """
    Robustness Test 1: rebase all three series to Rs 100,000 at
    `start_month` (the first month all three are genuinely comparable)
    and recompute metrics over that shorter window. Uses the exact same
    underlying monthly returns as run_baseline(); only the starting point
    and compounding base change.
    """
    base = run_baseline(prices_csv, benchmark_csv)

    def rebase(df):
        idx = df[df["Month"] == start_month].index[0]
        sub = df.loc[idx:].reset_index(drop=True)
        values = [config.INITIAL_CAPITAL]
        for i in range(1, len(sub)):
            r = sub.loc[i, "PortfolioReturn"]
            values.append(values[-1] if pd.isna(r) else values[-1] * (1 + r))
        sub["RebasedValue"] = values
        sub["RebasedReturn"] = sub["PortfolioReturn"]
        sub.loc[0, "RebasedReturn"] = float("nan")
        return sub[["Month", "RebasedReturn", "RebasedValue"]]

    mom_r = rebase(base["mom_portfolio"])
    mr_r = rebase(base["mr_portfolio"])
    bench_r = rebase(base["bench_portfolio"])

    table = pd.DataFrame([
        metrics.full_metrics_row("Momentum", mom_r["RebasedValue"], mom_r["RebasedReturn"]),
        metrics.full_metrics_row("Mean Reversion", mr_r["RebasedValue"], mr_r["RebasedReturn"]),
        metrics.full_metrics_row("Nifty 50 Price Index", bench_r["RebasedValue"], bench_r["RebasedReturn"]),
    ])
    return table, {"momentum": mom_r, "mean_reversion": mr_r, "nifty50": bench_r}


def run_transaction_cost_sensitivity(prices_csv: str, benchmark_csv: str, bps_levels=(0, 10, 25, 50)):
    """
    Robustness Test 2: re-run the active strategies' portfolio construction
    under different round-trip transaction-cost assumptions (basis points),
    applied only on rebalance months. The benchmark is never given a cost,
    since it never trades. Uses the same ranking table / signals as the
    baseline; only config.TRANSACTION_COST changes between runs.
    """
    monthly, bench_monthly, dqr = data_loader.load_and_prepare(prices_csv, benchmark_csv)
    ranking_table, _ = strategies.build_ranking_table(monthly)
    last_real_month = monthly["Month"].max()

    rows = []
    for bps in bps_levels:
        config.TRANSACTION_COST = bps / 10_000.0
        config.SLIPPAGE = 0.0
        mom_p = port.build_strategy_portfolio(ranking_table, monthly, "momentum")
        mr_p = port.build_strategy_portfolio(ranking_table, monthly, "mean_reversion")
        mom_p = mom_p[mom_p["Month"] <= last_real_month]
        mr_p = mr_p[mr_p["Month"] <= last_real_month]
        rows.append({
            "round_trip_bps": bps,
            "momentum_final_value": mom_p["PortfolioValue"].iloc[-1],
            "mean_reversion_final_value": mr_p["PortfolioValue"].iloc[-1],
            "momentum_rebalances": int(mom_p["Rebalanced"].sum()),
            "mean_reversion_rebalances": int(mr_p["Rebalanced"].sum()),
        })
    config.TRANSACTION_COST = 0.0  # reset to baseline for any subsequent calls
    return pd.DataFrame(rows)
