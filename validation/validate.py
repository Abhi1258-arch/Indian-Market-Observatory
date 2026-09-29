"""
validate.py
===========
Runs the sanity checks required before any results are trusted, and
produces one fully worked manual calculation for a single month so a human
can independently re-derive the numbers by hand.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import config


def run_sanity_checks(mom_portfolio: pd.DataFrame, mr_portfolio: pd.DataFrame,
                       bench_portfolio: pd.DataFrame, ranking_table: pd.DataFrame) -> list:
    """Returns a list of {check, passed, detail} dicts."""
    results = []

    def check(name, condition, detail=""):
        results.append({"check": name, "passed": bool(condition), "detail": detail})

    # 1. Every portfolio starts at INITIAL_CAPITAL (first non-NaN value's *prior* base is
    # INITIAL_CAPITAL by construction; verify the first computed value is consistent with it)
    for name, df in [("Momentum", mom_portfolio), ("Mean Reversion", mr_portfolio), ("Nifty 50", bench_portfolio)]:
        first_valid = df["PortfolioReturn"].first_valid_index()
        if first_valid is None:
            check(f"{name} starts at ₹{config.INITIAL_CAPITAL:,.0f}", False, "No valid return observations at all.")
            continue
        pre_value = config.INITIAL_CAPITAL
        for i in range(first_valid):
            pre_value = df.loc[i, "PortfolioValue"]  # unchanged rows before first trade
        implied_start = df.loc[first_valid, "PortfolioValue"] / (1 + df.loc[first_valid, "PortfolioReturn"])
        check(
            f"{name} starts at ₹{config.INITIAL_CAPITAL:,.0f}",
            np.isclose(implied_start, config.INITIAL_CAPITAL, rtol=1e-6),
            f"Implied starting value = {implied_start:,.4f}",
        )

    # 2. Exactly two stocks selected each defined month
    for name, col in [("Momentum", "MomentumSelected"), ("Mean Reversion", "MeanReversionSelected")]:
        counts = ranking_table.groupby("Month")[col].sum()
        bad_months = counts[(counts != 0) & (counts != config.N_SELECT)]
        check(
            f"{name}: exactly {config.N_SELECT} stocks selected in every active month",
            len(bad_months) == 0,
            f"Offending months: {list(bad_months.index)}" if len(bad_months) else "OK",
        )

    # 3. Weights sum to 100% (structural - always true given WEIGHT_PER_STOCK*2, but verify config)
    check(
        "Portfolio weights sum to 100%",
        np.isclose(config.WEIGHT_PER_STOCK * config.N_SELECT, 1.0),
        f"{config.WEIGHT_PER_STOCK} x {config.N_SELECT} = {config.WEIGHT_PER_STOCK * config.N_SELECT}",
    )

    # 4. No future information used: SignalReturn for holding month t must equal
    # RealizedReturn for month t-1 (i.e., the signal is always one full month old)
    rt = ranking_table.dropna(subset=["SignalReturn"])
    shifted_check = []
    for stock, g in rt.groupby("LogicalStock"):
        g = g.sort_values("Month")
        prior_realized = g["RealizedReturn"].shift(1)
        mismatch = ~np.isclose(g["SignalReturn"].values[1:], prior_realized.values[1:], equal_nan=True)
        shifted_check.append(mismatch.sum() if len(mismatch) else 0)
    check(
        "No look-ahead: each month's signal equals the PRIOR month's realized return",
        sum(shifted_check) == 0,
        f"Mismatches found: {sum(shifted_check)}",
    )

    # 5. Portfolio value compounds correctly (spot check: recompute cumulative product)
    for name, df in [("Momentum", mom_portfolio), ("Mean Reversion", mr_portfolio), ("Nifty 50", bench_portfolio)]:
        clean = df.dropna(subset=["PortfolioReturn"]).reset_index(drop=True)
        if len(clean) == 0:
            check(f"{name}: portfolio value compounds correctly", False, "No valid rows.")
            continue
        recomputed = config.INITIAL_CAPITAL * (1 + clean["PortfolioReturn"]).cumprod()
        ok = np.allclose(recomputed.values, clean["PortfolioValue"].values, rtol=1e-6)
        check(f"{name}: portfolio value compounds correctly", ok,
              "Recomputed cumulative product matches stored PortfolioValue" if ok else "MISMATCH")

    return results


def manual_calculation_example(ranking_table: pd.DataFrame, mom_portfolio: pd.DataFrame,
                                monthly: pd.DataFrame) -> str:
    """
    Produce a fully worked, human-checkable example: pick the first month with
    a complete, valid momentum portfolio and show every arithmetic step.
    """
    valid_months = mom_portfolio.dropna(subset=["PortfolioReturn"])
    if valid_months.empty:
        return "No month has a complete valid momentum portfolio yet - supply real price data to generate this example."

    row = valid_months.iloc[0]
    m = row["Month"]
    signal_month = m - 1

    sig_rows = ranking_table[ranking_table["Month"] == m].sort_values("MomentumRank")
    lines = []
    lines.append(f"MANUAL VERIFICATION - Momentum strategy, holding month {m}")
    lines.append(f"Signal month (prior month whose returns determine selection): {signal_month}")
    lines.append("")
    lines.append("Step 1 - Signal-month returns for all 5 stocks (this is the momentum score):")
    for _, r in sig_rows.iterrows():
        lines.append(f"  {r['LogicalStock']:<10} SignalReturn (return in {signal_month}) = {r['SignalReturn']:+.4%}"
                      f"   -> MomentumRank = {int(r['MomentumRank']) if pd.notna(r['MomentumRank']) else 'NA'}")
    lines.append("")
    top2 = sig_rows[sig_rows["MomentumSelected"]]
    s1, s2 = top2.iloc[0], top2.iloc[1]
    lines.append(f"Step 2 - Select top {config.N_SELECT} by MomentumRank: {s1['LogicalStock']} and {s2['LogicalStock']}")
    lines.append("")
    lines.append(f"Step 3 - Realized return of each selected stock DURING the holding month {m} "
                  f"(this is what actually gets earned, and was NOT known at selection time):")
    lines.append(f"  {s1['LogicalStock']}: RealizedReturn({m}) = {s1['RealizedReturn']:+.4%}")
    lines.append(f"  {s2['LogicalStock']}: RealizedReturn({m}) = {s2['RealizedReturn']:+.4%}")
    lines.append("")
    port_ret = 0.5 * s1["RealizedReturn"] + 0.5 * s2["RealizedReturn"]
    lines.append(f"Step 4 - Portfolio return = 0.5 x {s1['RealizedReturn']:+.4%} + 0.5 x {s2['RealizedReturn']:+.4%} "
                  f"= {port_ret:+.4%}")
    lines.append(f"         (Engine computed: {row['PortfolioReturn']:+.4%} -- should match to rounding)")
    lines.append("")
    prior_value = row["PortfolioValue"] / (1 + row["PortfolioReturn"])
    lines.append(f"Step 5 - Portfolio value: V(t) = V(t-1) x (1 + R_p) = ₹{prior_value:,.2f} x (1 + {port_ret:+.4%}) "
                  f"= ₹{row['PortfolioValue']:,.2f}")
    return "\n".join(lines)
