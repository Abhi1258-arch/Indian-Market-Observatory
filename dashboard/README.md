# Dashboard

The Indian Market Observatory dashboard is a presentation layer built on
top of the results in this repository. It does not perform any of its own
calculations — every number it displays is copied from the locked,
validated results in `results/` and `paper/`.

**Live dashboard:** https://claude.ai/artifact/GCzvoNWEzFzXXFLu9cE1Tt

The dashboard includes:

- Overview, research question, and study metadata
- Baseline results and the main cumulative-value chart (Momentum / Mean
  Reversion / Nifty 50 Price Index, all starting at ₹100,000)
- Full performance metrics table
- Methodology and formulas
- A filterable monthly selection explorer
- Risk analysis (drawdown, volatility, Sharpe comparison)
- Robustness & sensitivity page (common active-period check, transaction-cost
  sensitivity, concentration and benchmark-limitation notes)
- Behavioral finance framework, interpretation, limitations, and
  reproducibility sections

This repository does not attempt to reproduce the dashboard's front-end
code, since it is a static, self-contained HTML/JS presentation file with
no separate backend. Regenerating it from the numbers in `results/` is a
presentation task, not a research task, and is intentionally kept outside
this reproducibility package.
