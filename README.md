# Indian Market Observatory

**Quantitative Investing Through Behavioral Finance: A Backtest of Momentum
and Mean Reversion in Indian Large-Cap Equities**

This repository contains the complete, reproducible research behind the
Indian Market Observatory project: the data, the backtest engine, the
validation checks, the results, the methodology write-up, and the full
research paper.

This is an educational research backtest. It is **not financial advice**
and **not a prediction of future performance**.

## 1. Project overview

The project tests two simple, rule-based investment strategies — momentum
and mean reversion — against a passive benchmark, using monthly price data
for five Indian large-cap stocks. Everything here is a historical backtest:
a mechanical rule applied consistently to past data, checked for common
errors (especially look-ahead bias), and reported honestly, including
where the results are unflattering for the tested strategies.

## 2. Research question

> Can simple systematic strategies based on momentum and mean reversion
> outperform passive investing in Indian large-cap equities?

## 3. Dataset

- **Source:** Yahoo Finance, via the `yfinance` library
- **Format:** monthly adjusted closing prices (`Date, Ticker, Adjusted_Close`)
- **Stock file:** `data/indian_quant_monthly_data_v2.csv` (175 rows: 35 months x 5 stocks)
- **Benchmark file:** `data/nifty50_monthly_data.csv` (35 monthly rows)

The dataset was checked for missing values, duplicate dates, chronological
ordering, and complete monthly coverage. No issues were found in either
file. Full details are in `results/baseline_results/data_quality_report.csv`.

## 4. Five-stock universe

| Ticker | Company |
|---|---|
| RELIANCE.NS | Reliance Industries |
| TCS.NS | Tata Consultancy Services |
| HDFCBANK.NS | HDFC Bank |
| INFY.NS | Infosys |
| ICICIBANK.NS | ICICI Bank |

This is a small, convenient sample of large, widely followed Indian
companies across energy, IT, and banking. It is **not** claimed to
represent the Indian stock market as a whole.

## 5. Study period

August 2023 – June 2026, monthly frequency. Because both strategies need
one full prior month of return data to generate a signal, **October 2023
is the first active trading month** (see Section 10 below).

## 6. Benchmark

**Nifty 50 Price Index** (`^NSEI`), passive buy-and-hold, ₹100,000 starting
capital. This is the price index, **not** the Total Return Index — it
excludes dividends. It is never referred to as a total-return measure
anywhere in this repository or the paper.

## 7. Momentum methodology

Each month, rank the five stocks by their return over the *previous*
month. Buy the **top 2**, 50% each. Hold for one month. Rebalance monthly.

## 8. Mean-reversion methodology

Uses the exact same previous-month-return signal as momentum, but buys the
**bottom 2** instead of the top 2. This is a simple, return-based rule —
not a z-score, moving-average, or Bollinger-band strategy.

## 9. Portfolio construction

```
R(p,t) = 0.5 * R(1,t) + 0.5 * R(2,t)      # portfolio return
V(t)   = V(t-1) * (1 + R(p,t))            # portfolio value
```

Both strategies start at ₹100,000 and rebalance monthly. Baseline
transaction costs and slippage are both 0; the risk-free rate used for the
Sharpe ratio is 0%. All three are explicit parameters in `src/config.py`.

## 10. Look-ahead-bias prevention

Month *t*'s portfolio is selected using **only** the realized return of
month *t-1*. The return actually earned during month *t* is not known
until month *t* ends, and it is never used in that month's own selection.
This is enforced in code (`src/strategies.py`) and independently re-checked
in `validation/validate.py`, which confirmed **zero look-ahead mismatches**
across the full sample.

## 11. Baseline results

| Metric | Momentum | Mean Reversion | Nifty 50 Price Index |
|---|---|---|---|
| Final Value | ₹105,318.89 | ₹99,876.35 | ₹123,953.45 |
| Total Return | +5.32% | -0.12% | +23.95% |
| CAGR | +1.85% | -0.04% | +7.87% |
| Annualized Volatility | 18.75% | 13.70% | 13.94% |
| Sharpe Ratio (rf=0%) | 0.192 | 0.063 | 0.614 |
| Maximum Drawdown | -22.06% | -19.78% | -14.78% |

Within this sample, the Nifty 50 Price Index accumulated more value than
either tested strategy. Momentum finished above its starting capital;
mean reversion finished approximately flat. Full results, best/worst
months, win rates, and the monthly selection tables are in `results/` and
in the research paper.

## 12. Robustness tests

- **Common active-period check:** all three series rebased to ₹100,000 at
  October 2023 (the first month all three are genuinely comparable). The
  same relative pattern holds.
- **Transaction-cost sensitivity:** round-trip costs of 0, 10, 25, and 50
  basis points applied to the active strategies on rebalance months (never
  to the passive benchmark). At 25 bps, momentum's small gain is nearly
  erased; at 50 bps, both strategies show a net loss. No cost level is
  claimed to be "realistic" — these are illustrative stress points.

See `results/robustness_results/` and Section 7 of the paper.

## 13. Limitations

Small universe (5 stocks), short sample (~3 years), a concentrated 2-of-5
portfolio construction, zero baseline transaction costs and slippage, a
dividend-excluding benchmark, no direct investor-psychology data, no
out-of-sample testing, and a single one-month signal. None of these
weaknesses are hidden — they are discussed in full in Section 9 of the
research paper and in `methodology/METHODOLOGY.md`.

## 14. Repository structure

```
Indian-Market-Observatory/
├── README.md                     - this file
├── paper/
│   └── Indian_Market_Observatory_Research_Paper.pdf
├── data/
│   ├── indian_quant_monthly_data_v2.csv    (5-stock universe, monthly)
│   └── nifty50_monthly_data.csv            (benchmark, monthly)
├── src/
│   ├── config.py                 - universe, dates, weights, costs, rf rate
│   ├── data_loader.py            - loads + validates the monthly CSVs
│   ├── strategies.py             - momentum / mean-reversion ranking (no look-ahead)
│   ├── portfolio.py              - return compounding, benchmark, drawdown
│   ├── metrics.py                - CAGR, volatility, Sharpe, drawdown, win rate
│   └── backtest_engine.py        - orchestrates the full pipeline
├── validation/
│   └── validate.py               - sanity checks + manual one-month worked example
├── scripts/
│   ├── run_real_backtest.py      - reproduces the baseline results
│   └── run_robustness.py         - reproduces the two robustness checks
├── results/
│   ├── baseline_results/         - performance metrics, portfolio histories, drawdowns
│   ├── monthly_selections/       - month-by-month stock selections for both strategies
│   └── robustness_results/       - common active-period + transaction-cost sensitivity
├── methodology/
│   └── METHODOLOGY.md            - full methodology, matching the code exactly
└── dashboard/
    └── README.md                 - link to the published interactive dashboard
```

## 15. How to reproduce the backtest

You do not need advanced programming experience to run this. You need
Python 3 and two packages: `pandas` and `numpy`.

**Step 1 — install dependencies**

```bash
pip install pandas numpy
```

**Step 2 — check the data is in place**

The two required files are already included in this repository, at:

```
data/indian_quant_monthly_data_v2.csv
data/nifty50_monthly_data.csv
```

You do not need to download anything else.

**Step 3 — run the backtest**

From the repository's root folder:

```bash
python scripts/run_real_backtest.py
```

This prints the sanity-check results and the final metrics table to your
screen, and writes the full result files into `results/baseline_results/`
and `results/monthly_selections/`.

**Step 4 — run the robustness checks (optional)**

```bash
python scripts/run_robustness.py
```

This writes the common active-period and transaction-cost sensitivity
results into `results/robustness_results/`.

**Step 5 — find your results**

Every generated file lands under `results/`. Open any `.csv` file in Excel,
Google Sheets, or a text editor to inspect it. `manual_calculation_example.txt`
in `results/baseline_results/` walks through one month's momentum
calculation by hand, so you can independently verify the arithmetic
without trusting the code.

If your numbers do not match Section 11 above exactly, something in your
environment differs from the one this project was built in — please do
not adjust the code to force a match; check your Python/pandas version and
confirm the data files were not modified.
