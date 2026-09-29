"""
config.py
=========
Single source of truth for the backtest engine's parameters and universe.
Every number here matches the locked, published results in
paper/Indian_Market_Observatory_Research_Paper.pdf and dashboard/.

Note on history: an earlier iteration of this project used a five-stock
universe that included Tata Motors (ticker TMPV.NS, post-demerger). That
universe was discarded because the October 2025 Tata Motors demerger made
the stock's price-only return difficult to interpret (see METHODOLOGY.md).
The FINAL, LOCKED universe below replaces Tata Motors with Infosys and
ICICI Bank and is the only universe this repository reproduces.
"""

from datetime import date

# ----------------------------------------------------------------------
# STUDY WINDOW
# ----------------------------------------------------------------------
STUDY_START = date(2023, 8, 1)    # first month in the sample
STUDY_END = date(2026, 6, 30)     # last month in the sample
INITIAL_CAPITAL = 100_000.0       # INR

# ----------------------------------------------------------------------
# STOCK UNIVERSE (FINAL / LOCKED)
# ----------------------------------------------------------------------
# Ticker -> logical name used throughout the engine and in every output
# file. All five tickers are continuously listed for the full study
# window with no renames or demergers to handle.
UNIVERSE = {
    "RELIANCE.NS": "RELIANCE",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFCBANK",
    "INFY.NS": "INFY",
    "ICICIBANK.NS": "ICICIBANK",
}

BENCHMARK_TICKER = "^NSEI"          # Nifty 50 PRICE INDEX (not TRI)

# ----------------------------------------------------------------------
# STRATEGY PARAMETERS
# ----------------------------------------------------------------------
N_SELECT = 2             # stocks selected each month, per strategy
WEIGHT_PER_STOCK = 0.5   # equal weight

# ----------------------------------------------------------------------
# COSTS (baseline = zero; wired as parameters for the transaction-cost
# sensitivity test, never silently assumed elsewhere)
# ----------------------------------------------------------------------
TRANSACTION_COST = 0.0   # fraction of traded value, round-trip, per rebalance
SLIPPAGE = 0.0

# ----------------------------------------------------------------------
# RISK / METRICS
# ----------------------------------------------------------------------
RISK_FREE_RATE_ANNUAL = 0.0   # baseline assumption, not the true INR risk-free rate
PERIODS_PER_YEAR = 12

# ----------------------------------------------------------------------
# TIMING CONVENTION
# ----------------------------------------------------------------------
# Month t's portfolio is selected using the realized return of month t-1
# (close of t-2 to close of t-1). The selected portfolio is held through
# month t; its return is month t's own close-to-close return, which is
# not known until month t has ended. August 2023 has no prior month, so
# it and the following month (September 2023) have no valid signal.
# October 2023 is the first active trading month.
TIMING_CONVENTION = (
    "Selection for month t uses only the realized return of month t-1. "
    "The selected portfolio is held through month t, and its return is "
    "month t's own close-to-close return, observed only after month t "
    "ends. First active trading month: October 2023."
)
