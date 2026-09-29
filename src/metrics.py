"""
metrics.py
==========
Standard performance-metric formulas applied to a monthly portfolio-return
series. Every function returns the string "Insufficient data" instead of a
number when the input doesn't support a valid calculation (e.g. fewer than
2 non-NaN monthly returns for volatility), per the spec's explicit
instruction never to invent a value.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import config

INSUFFICIENT = "Insufficient data"


def _clean(returns: pd.Series) -> pd.Series:
    return returns.dropna()


def total_return(values: pd.Series):
    v = values.dropna()
    if len(v) < 1:
        return INSUFFICIENT
    return v.iloc[-1] / v.iloc[0] - 1.0


def cagr(values: pd.Series, n_months: int):
    v = values.dropna()
    if len(v) < 2 or n_months <= 0:
        return INSUFFICIENT
    total = v.iloc[-1] / v.iloc[0]
    years = n_months / config.PERIODS_PER_YEAR
    if years <= 0 or total <= 0:
        return INSUFFICIENT
    return total ** (1 / years) - 1.0


def annualized_volatility(returns: pd.Series):
    r = _clean(returns)
    if len(r) < 2:
        return INSUFFICIENT
    return r.std(ddof=1) * np.sqrt(config.PERIODS_PER_YEAR)


def sharpe_ratio(returns: pd.Series, risk_free_annual: float = None):
    r = _clean(returns)
    if len(r) < 2:
        return INSUFFICIENT
    rf_annual = config.RISK_FREE_RATE_ANNUAL if risk_free_annual is None else risk_free_annual
    rf_monthly = (1 + rf_annual) ** (1 / config.PERIODS_PER_YEAR) - 1
    excess = r - rf_monthly
    vol = excess.std(ddof=1)
    if vol == 0 or np.isnan(vol):
        return INSUFFICIENT
    return (excess.mean() / vol) * np.sqrt(config.PERIODS_PER_YEAR)


def max_drawdown(values: pd.Series):
    v = values.dropna()
    if len(v) < 2:
        return INSUFFICIENT
    running_max = v.cummax()
    dd = (v - running_max) / running_max
    return dd.min()


def best_month(returns: pd.Series):
    r = _clean(returns)
    return r.max() if len(r) >= 1 else INSUFFICIENT


def worst_month(returns: pd.Series):
    r = _clean(returns)
    return r.min() if len(r) >= 1 else INSUFFICIENT


def positive_negative_counts(returns: pd.Series):
    r = _clean(returns)
    if len(r) < 1:
        return INSUFFICIENT, INSUFFICIENT
    return int((r > 0).sum()), int((r < 0).sum())


def win_rate(returns: pd.Series):
    r = _clean(returns)
    if len(r) < 1:
        return INSUFFICIENT
    return (r > 0).sum() / len(r)


def full_metrics_row(label: str, values: pd.Series, returns: pd.Series) -> dict:
    n_months = values.dropna().shape[0] - 1 if values.dropna().shape[0] > 0 else 0
    pos, neg = positive_negative_counts(returns)
    v_clean = values.dropna()
    return {
        "Strategy": label,
        "Initial Value": v_clean.iloc[0] if len(v_clean) else INSUFFICIENT,
        "Final Value": v_clean.iloc[-1] if len(v_clean) else INSUFFICIENT,
        "Total Return": total_return(values),
        "CAGR": cagr(values, n_months),
        "Annualized Volatility": annualized_volatility(returns),
        "Sharpe Ratio (rf=0%)": sharpe_ratio(returns),
        "Maximum Drawdown": max_drawdown(values),
        "Best Month": best_month(returns),
        "Worst Month": worst_month(returns),
        "Positive Months": pos,
        "Negative Months": neg,
        "Win Rate": win_rate(returns),
    }
