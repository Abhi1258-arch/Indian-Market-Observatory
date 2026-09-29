"""
run_robustness.py
==================
Regenerates the two robustness checks reported in the research paper
(Section 7): the common active-period comparison and the transaction-cost
sensitivity test. Uses the exact same signals and returns as the baseline
backtest - no new calculation method is introduced.

Usage (from the repository root):
    python scripts/run_robustness.py
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

import backtest_engine  # noqa: E402

PRICES_CSV = os.path.join(REPO_ROOT, "data", "indian_quant_monthly_data_v2.csv")
BENCHMARK_CSV = os.path.join(REPO_ROOT, "data", "nifty50_monthly_data.csv")
OUT_DIR = os.path.join(REPO_ROOT, "results", "robustness_results")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Test 1: common active-period comparison, rebased to October 2023
    table1, series1 = backtest_engine.run_common_active_period(PRICES_CSV, BENCHMARK_CSV, start_month="2023-10")
    table1.to_csv(os.path.join(OUT_DIR, "common_active_period_metrics.csv"), index=False)
    for name, df in series1.items():
        df.to_csv(os.path.join(OUT_DIR, f"common_active_period_{name}_values.csv"), index=False)

    print("Common active-period robustness check (rebased to Rs 100,000 at October 2023):")
    print(table1[["Strategy", "Final Value", "Total Return", "CAGR", "Sharpe Ratio (rf=0%)", "Maximum Drawdown"]]
          .to_string(index=False))
    print()

    # Test 2: transaction-cost sensitivity
    table2 = backtest_engine.run_transaction_cost_sensitivity(PRICES_CSV, BENCHMARK_CSV, bps_levels=(0, 10, 25, 50))
    table2.to_csv(os.path.join(OUT_DIR, "transaction_cost_sensitivity.csv"), index=False)

    print("Transaction-cost sensitivity (round-trip bps, applied only to active strategies):")
    print(table2.to_string(index=False))
    print()
    print(f"Results written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
