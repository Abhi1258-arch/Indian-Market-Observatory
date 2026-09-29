"""
portfolio.py
============
Turns a per-month list of selected (stock, realized_return) pairs into a
compounding portfolio value series. Two equally-weighted stocks per the
spec: R_p = 0.5*R_1 + 0.5*R_2. Also builds the passive benchmark series
and computes drawdown for any of the three series using the same formula.

Transaction costs / slippage are wired in as explicit parameters (from
config.py) applied to the traded value at each rebalance, defaulting to
zero for the baseline run per the spec.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import config


def build_strategy_portfolio(ranking_table: pd.DataFrame, monthly: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """
    Build the month-by-month portfolio history for 'momentum' or 'mean_reversion'.
    Returns a DataFrame: Month, Stock1, Stock2, Score1, Score2, RealizedReturn1,
    RealizedReturn2, PortfolioReturn, PortfolioValue.

    PortfolioReturn for month t = 0.5 * RealizedReturn(Stock1, t) + 0.5 * RealizedReturn(Stock2, t)
    where RealizedReturn is the stock's OWN close-to-close return for month t
    (the SAME thing that was used, one month lagged, as the selection signal
    for a DIFFERENT month - never for the month being scored).

    Transaction costs (config.TRANSACTION_COST + config.SLIPPAGE) are charged
    on the portion of the portfolio that turns over at each rebalance (i.e.
    when a selected stock changes from the prior month), applied to the
    return of that month before compounding. At the baseline (both = 0) this
    has no effect.
    """
    col_sel = "MomentumSelected" if strategy == "momentum" else "MeanReversionSelected"
    col_rank = "MomentumRank" if strategy == "momentum" else "MeanReversionRank"

    months = sorted(ranking_table["Month"].unique())
    records = []
    prev_holdings = set()
    value = config.INITIAL_CAPITAL

    for m in months:
        sel = ranking_table[(ranking_table["Month"] == m) & (ranking_table[col_sel])]
        sel = sel.sort_values(col_rank)

        if len(sel) != config.N_SELECT:
            # Undefined month (e.g. no valid signal yet) - record NaN, do not
            # advance the portfolio arbitrarily.
            records.append({
                "Month": m, "Stock1": None, "Stock2": None,
                "Score1": np.nan, "Score2": np.nan,
                "PortfolioReturn": np.nan, "PortfolioValue": value,
                "Rebalanced": False,
            })
            continue

        stocks = sel["LogicalStock"].tolist()
        scores = sel["SignalReturn"].tolist()
        realized = sel["RealizedReturn"].tolist()

        if any(pd.isna(r) for r in realized):
            records.append({
                "Month": m, "Stock1": stocks[0], "Stock2": stocks[1],
                "Score1": scores[0], "Score2": scores[1],
                "PortfolioReturn": np.nan, "PortfolioValue": value,
                "Rebalanced": set(stocks) != prev_holdings,
            })
            continue

        gross_return = config.WEIGHT_PER_STOCK * realized[0] + config.WEIGHT_PER_STOCK * realized[1]

        new_holdings = set(stocks)
        turnover_fraction = len(new_holdings - prev_holdings) / config.N_SELECT if prev_holdings else 1.0
        cost = turnover_fraction * (config.TRANSACTION_COST + config.SLIPPAGE)
        net_return = gross_return - cost

        value = value * (1 + net_return)
        records.append({
            "Month": m, "Stock1": stocks[0], "Stock2": stocks[1],
            "Score1": scores[0], "Score2": scores[1],
            "PortfolioReturn": net_return, "PortfolioValue": value,
            "Rebalanced": new_holdings != prev_holdings,
        })
        prev_holdings = new_holdings

    return pd.DataFrame(records)


def build_benchmark_portfolio(benchmark_monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Passive Nifty 50 portfolio: buy-and-hold from the first month of the study
    window, compounding the index's own monthly return with no rebalancing.
    """
    df = benchmark_monthly.sort_values("Month").copy()
    value = config.INITIAL_CAPITAL
    records = []
    for _, row in df.iterrows():
        ret = row["MonthlyReturn"]
        if pd.isna(ret):
            records.append({"Month": row["Month"], "PortfolioReturn": np.nan, "PortfolioValue": value})
            continue
        value = value * (1 + ret)
        records.append({"Month": row["Month"], "PortfolioReturn": ret, "PortfolioValue": value})
    return pd.DataFrame(records)


def compute_drawdown(portfolio_values: pd.Series) -> pd.DataFrame:
    """
    RunningMax_t = max(V_1..V_t); Drawdown_t = (V_t - RunningMax_t) / RunningMax_t.
    Returns a DataFrame aligned to the input index with RunningMax and Drawdown.
    """
    running_max = portfolio_values.cummax()
    drawdown = (portfolio_values - running_max) / running_max
    return pd.DataFrame({"PortfolioValue": portfolio_values, "RunningMax": running_max, "Drawdown": drawdown})
