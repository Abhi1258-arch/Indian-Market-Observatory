"""
strategies.py
=============
Implements the momentum and mean-reversion selection rules exactly as
specified, with the timing convention documented in config.TIMING_CONVENTION:

    Selection for month t is based ONLY on each stock's return during
    month t-1 (i.e. the return that was already fully realized and known
    by the close of month t-1). The chosen two stocks are then HELD during
    month t, and the portfolio's return for month t is month t's own
    close-to-close return - which cannot be known until month t itself
    has ended.

No function in this file is allowed to see monthly_panel rows for month t
when deciding the month-t portfolio; the join enforces this by shifting
the ranking signal forward by one month before it is ever compared to the
holding-period return.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import config


def build_ranking_table(monthly: pd.DataFrame) -> pd.DataFrame:
    """
    For every (Month, Stock), compute:
      - MonthlyReturn (already in `monthly`, i.e. the stock's own realized return for that month)
      - MomentumRank: rank of the PRIOR month's return (1 = best), used to pick month t's momentum portfolio
      - MeanReversionRank: rank of the PRIOR month's return (1 = worst), used to pick month t's MR portfolio
      - MomentumSelected / MeanReversionSelected: booleans

    The "prior month's return" is monthly['MonthlyReturn'] shifted forward by
    one month per stock - i.e. the signal available at the START of month t
    is the realized return of month t-1. This is the mechanical enforcement
    of the no-look-ahead rule.
    """
    df = monthly.copy().sort_values(["LogicalStock", "Month"])
    df["SignalMonth"] = df["Month"]  # the month whose return is the signal
    df["HoldingMonth"] = df["Month"] + 1  # the month this signal will be used to trade

    signal = df[["LogicalStock", "HoldingMonth", "MonthlyReturn"]].rename(
        columns={"MonthlyReturn": "SignalReturn", "HoldingMonth": "Month"}
    )

    # Realized return actually earned during the holding month (only knowable after month end)
    realized = df[["LogicalStock", "Month", "MonthlyReturn"]].rename(
        columns={"MonthlyReturn": "RealizedReturn"}
    )

    ranking = pd.merge(signal, realized, on=["LogicalStock", "Month"], how="outer")
    ranking = ranking.dropna(subset=["Month"])
    ranking = ranking.sort_values(["Month", "LogicalStock"]).reset_index(drop=True)

    # Rank within each Month across the 5 stocks, using ONLY SignalReturn.
    # Months where a stock's SignalReturn is NaN (e.g. very first month of
    # sample, no prior month available) are excluded from ranking for that
    # stock-month rather than assigning it an arbitrary rank.
    valid = ranking["SignalReturn"].notna()
    ranking["MomentumRank"] = np.nan
    ranking["MeanReversionRank"] = np.nan
    ranking.loc[valid, "MomentumRank"] = (
        ranking.loc[valid].groupby("Month")["SignalReturn"].rank(ascending=False, method="first")
    )
    ranking.loc[valid, "MeanReversionRank"] = (
        ranking.loc[valid].groupby("Month")["SignalReturn"].rank(ascending=True, method="first")
    )
    n_valid_per_month = ranking.loc[valid].groupby("Month")["SignalReturn"].transform("count")
    ranking["_n_valid_this_month"] = 0
    ranking.loc[valid, "_n_valid_this_month"] = n_valid_per_month

    ranking["MomentumSelected"] = ranking["MomentumRank"] <= config.N_SELECT
    ranking["MeanReversionSelected"] = ranking["MeanReversionRank"] <= config.N_SELECT

    # If fewer than N_SELECT stocks have a valid signal in a month (e.g. the
    # very first tradeable month), selection for that month is undefined -
    # flag it rather than silently trading with too few names.
    incomplete_months = sorted(
        ranking.loc[ranking["_n_valid_this_month"] < config.N_SELECT, "Month"].unique()
    )

    ranking = ranking.drop(columns=["_n_valid_this_month"])
    return ranking, incomplete_months


def select_portfolio(ranking_table: pd.DataFrame, strategy: str, month) -> list:
    """Return the list of (stock, signal_return) tuples selected for `strategy` in `month`."""
    col = "MomentumSelected" if strategy == "momentum" else "MeanReversionSelected"
    rows = ranking_table[(ranking_table["Month"] == month) & (ranking_table[col])]
    return list(zip(rows["LogicalStock"], rows["SignalReturn"]))
