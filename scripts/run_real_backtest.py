"""
run_real_backtest.py
=====================
Reproduces the locked baseline backtest end to end and writes every
result file into results/baseline_results/ and results/monthly_selections/.

Usage (from the repository root):
    python scripts/run_real_backtest.py

No arguments are required: it reads data/indian_quant_monthly_data_v2.csv
and data/nifty50_monthly_data.csv, and writes its outputs under results/.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, os.path.join(REPO_ROOT, "validation"))

import backtest_engine  # noqa: E402
import validate  # noqa: E402

PRICES_CSV = os.path.join(REPO_ROOT, "data", "indian_quant_monthly_data_v2.csv")
BENCHMARK_CSV = os.path.join(REPO_ROOT, "data", "nifty50_monthly_data.csv")
BASELINE_DIR = os.path.join(REPO_ROOT, "results", "baseline_results")
SELECTIONS_DIR = os.path.join(REPO_ROOT, "results", "monthly_selections")


def main():
    os.makedirs(BASELINE_DIR, exist_ok=True)
    os.makedirs(SELECTIONS_DIR, exist_ok=True)

    result = backtest_engine.run_baseline(PRICES_CSV, BENCHMARK_CSV)

    # --- Sanity checks (the same checks reported in the paper) ---
    sanity = validate.run_sanity_checks(
        result["mom_portfolio"], result["mr_portfolio"], result["bench_portfolio"], result["ranking_table"]
    )
    manual_calc = validate.manual_calculation_example(
        result["ranking_table"], result["mom_portfolio"], result["monthly"]
    )

    n_failed = sum(1 for s in sanity if not s["passed"])
    print(f"Sanity checks: {len(sanity) - n_failed} passed, {n_failed} failed")
    for s in sanity:
        status = "PASS" if s["passed"] else "FAIL"
        print(f"  [{status}] {s['check']}")

    # --- Write results ---
    result["monthly"].to_csv(os.path.join(BASELINE_DIR, "clean_monthly_stock_dataset.csv"), index=False)
    result["mom_portfolio"].to_csv(os.path.join(BASELINE_DIR, "momentum_backtest.csv"), index=False)
    result["mr_portfolio"].to_csv(os.path.join(BASELINE_DIR, "mean_reversion_backtest.csv"), index=False)
    result["bench_portfolio"].to_csv(os.path.join(BASELINE_DIR, "nifty50_benchmark.csv"), index=False)
    result["metrics_table"].to_csv(os.path.join(BASELINE_DIR, "performance_metrics.csv"), index=False)
    result["mom_drawdown"].reset_index().to_csv(os.path.join(BASELINE_DIR, "drawdown_momentum.csv"), index=False)
    result["mr_drawdown"].reset_index().to_csv(os.path.join(BASELINE_DIR, "drawdown_mean_reversion.csv"), index=False)
    result["bench_drawdown"].reset_index().to_csv(os.path.join(BASELINE_DIR, "drawdown_nifty50.csv"), index=False)
    result["data_quality_report"].to_dataframe().to_csv(os.path.join(BASELINE_DIR, "data_quality_report.csv"), index=False)
    pd_sanity = __import__("pandas").DataFrame(sanity)
    pd_sanity.to_csv(os.path.join(BASELINE_DIR, "sanity_check_results.csv"), index=False)
    with open(os.path.join(BASELINE_DIR, "manual_calculation_example.txt"), "w") as f:
        f.write(manual_calc)

    result["ranking_table"].to_csv(os.path.join(SELECTIONS_DIR, "stock_ranking_table.csv"), index=False)
    result["mom_portfolio"][["Month", "Stock1", "Stock2", "Score1", "Score2", "PortfolioReturn", "PortfolioValue"]].to_csv(
        os.path.join(SELECTIONS_DIR, "momentum_selections.csv"), index=False
    )
    result["mr_portfolio"][["Month", "Stock1", "Stock2", "Score1", "Score2", "PortfolioReturn", "PortfolioValue"]].to_csv(
        os.path.join(SELECTIONS_DIR, "mean_reversion_selections.csv"), index=False
    )

    print()
    print("Final values:")
    print(result["metrics_table"][["Strategy", "Final Value", "Total Return", "CAGR", "Sharpe Ratio (rf=0%)", "Maximum Drawdown"]]
          .to_string(index=False))
    print()
    print(f"Results written to: {BASELINE_DIR} and {SELECTIONS_DIR}")


if __name__ == "__main__":
    main()
