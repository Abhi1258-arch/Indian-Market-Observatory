# Methodology

This document describes the exact, locked methodology implemented in `src/`
and reported in `paper/Indian_Market_Observatory_Research_Paper.pdf`. It
does not introduce anything new; it documents what the code in this
repository actually does.

**Note on project history:** an earlier iteration of this project used a
five-stock universe that included Tata Motors (ticker `TMPV.NS`, the
post-demerger passenger-vehicle entity). That universe was discarded
because the October 2025 Tata Motors demerger caused a large, single-month
price move (roughly -40%) that made the stock's price-only return
difficult to interpret without also accounting for the value of shares
distributed in the demerger. The final, locked universe below replaces
Tata Motors with Infosys and ICICI Bank. This repository reproduces only
the final universe.

## Universe (final, locked)

| Ticker | Company |
|---|---|
| RELIANCE.NS | Reliance Industries |
| TCS.NS | Tata Consultancy Services |
| HDFCBANK.NS | HDFC Bank |
| INFY.NS | Infosys |
| ICICIBANK.NS | ICICI Bank |

**Benchmark:** Nifty 50 **Price Index** (`^NSEI`). This is the price
index, not the Total Return Index (TRI) — it excludes dividends. It is
never relabeled as a total-return measure anywhere in this project.

## Study window

- **Period:** August 2023 – June 2026
- **Frequency:** Monthly (35 monthly observations per stock, 35 for the benchmark)
- **Initial capital:** ₹100,000 for each of the three portfolios (Momentum, Mean Reversion, Nifty 50 Price Index)

## Signal: previous-month return

For every stock, the signal used to select month *t*'s portfolio is that
stock's own realized return during month *t-1*:

```
M(i,t) = (P(i,t-1) - P(i,t-2)) / P(i,t-2)
```

This is the only signal used by either strategy. It is calculated from
adjusted closing prices, so stock splits and bonus issues do not create
artificial return spikes.

## Momentum

1. Rank the five stocks by their previous-month return, highest to lowest.
2. Select the **top 2**.
3. Allocate 50% / 50%.
4. Hold for month *t*.
5. Rebalance monthly, repeating steps 1–4.

## Mean reversion

Uses the exact same signal as momentum. The only difference is direction:

1. Rank the five stocks by their previous-month return, lowest to highest.
2. Select the **bottom 2**.
3. Allocate 50% / 50%.
4. Hold for month *t*.
5. Rebalance monthly, repeating steps 1–4.

This is a **simple, return-based** mean-reversion rule. It is not a
z-score model, a moving-average model, a Bollinger-band model, or any
other statistical distance-from-mean model.

## Portfolio construction

```
R(p,t) = 0.5 * R(1,t) + 0.5 * R(2,t)      # portfolio return
V(t)   = V(t-1) * (1 + R(p,t))            # portfolio value
```

Both strategies always hold exactly 2 of the 5 stocks (a concentrated
construction — see the Limitations section of the paper).

## Benchmark construction

The Nifty 50 Price Index benchmark is a passive, buy-and-hold portfolio:
₹100,000 compounded forward using the index's own monthly returns, with
no rebalancing and no interaction with either active strategy.

## Baseline assumptions

| Assumption | Baseline value |
|---|---|
| Transaction costs | 0 bps |
| Slippage | 0 |
| Risk-free rate (for Sharpe ratio) | 0% |

These are wired as explicit parameters in `src/config.py`
(`TRANSACTION_COST`, `SLIPPAGE`, `RISK_FREE_RATE_ANNUAL`), never hidden
inside a calculation, so the transaction-cost sensitivity test (Section
7.2 of the paper) is a parameter change, not a rewrite.

## Look-ahead bias prevention

Selection for month *t* uses **only** the realized return of month *t-1*.
The return actually earned during month *t* is not known until month *t*
has ended, and it is never used to make month *t*'s selection.

August 2023 has no prior month, so it has no valid signal. September 2023
would need August's return as its signal, which is also unavailable.
**October 2023 is therefore the first active trading month** for both
strategies.

This is enforced mechanically in `src/strategies.py` (the ranking signal
is built by shifting each stock's monthly return forward by one month
*before* any ranking occurs) and independently re-checked in
`validation/validate.py`, which re-derives each month's signal from the
output and confirms it equals the prior month's realized return. Running
`scripts/run_real_backtest.py` reproduces this check and prints:

```
[PASS] No look-ahead: each month's signal equals the PRIOR month's realized return
```

with **zero mismatches** across the full sample.

## Risk metrics

- **Annualized volatility:** standard deviation of monthly returns × √12
- **Sharpe ratio:** (mean monthly excess return / monthly return std. dev.) × √12, using a 0% annual risk-free rate
- **Maximum drawdown:** the most negative value of `(V(t) - RunningMax(t)) / RunningMax(t)` observed over the sample

## Locked baseline results

| Metric | Momentum | Mean Reversion | Nifty 50 Price Index |
|---|---|---|---|
| Final Value | ₹105,318.89 | ₹99,876.35 | ₹123,953.45 |
| Total Return | +5.32% | -0.12% | +23.95% |
| CAGR | +1.85% | -0.04% | +7.87% |
| Annualized Volatility | 18.75% | 13.70% | 13.94% |
| Sharpe Ratio (rf=0%) | 0.192 | 0.063 | 0.614 |
| Maximum Drawdown | -22.06% | -19.78% | -14.78% |

These numbers are reproduced exactly by running `scripts/run_real_backtest.py`
against the data in `data/`. See `paper/Indian_Market_Observatory_Research_Paper.pdf`
for full results, robustness checks, behavioral-finance discussion, and limitations.
