# FleetBench finance benchmark card

## Purpose

The `finance` category measures whether a model can help with finance research
when the relevant source facts are supplied. It covers arithmetic accuracy and
research discipline; it does not measure live-data retrieval or the quality of
investment advice.

## Inventory

The suite contains 24 original, synthetic, closed-world cases emitted in 16
model requests. Related same-tier checks are combined into compound prompts but
retain independently scored answer leaves:

| domain | core | hard | frontier | total |
|---|---:|---:|---:|---:|
| accounting | 1 | 2 | 1 | 4 |
| valuation | 1 | 3 | 1 | 5 |
| portfolio and risk | 1 | 1 | 2 | 4 |
| research judgment | 1 | 1 | 2 | 4 |
| algorithmic trading | 1 | 1 | 5 | 7 |
| **original cases** | **5** | **8** | **11** | **24** |
| **runtime requests** | **5** | **5** | **6** | **16** |

Export the machine-readable inventory with:

```bash
python3 fleetbench.py --finance-manifest
```

The optional `--profile compact` panel selects 5 high-signal requests, one per
domain: accounting, valuation, portfolio/risk, research evidence, and
algorithmic execution. The default full profile uses all 16 runtime requests.

## Evaluation

Each prompt requests one exact JSON object. The grader compares fields
independently, gives component-level partial credit, and uses an explicit
absolute tolerance only for rounded numerical answers. Extra or missing keys
fail the response because output precision is part of the task.

Reference answers are exercised by `python3 fleetbench.py --selftest`.
Representative DCF and bond answers are also recomputed independently in that
self-test rather than merely round-tripping stored answers. The same applies to
the equity-curve drawdown and order-book execution fixtures.

## Data and contamination

All fixtures were written for FleetBench and contain synthetic companies,
portfolios, and evidence records. They do not reproduce questions from finance
certification exams, interview banks, or proprietary datasets. No task requires
internet access, and answers cannot become stale with market prices.

The prompts and answers are public in this repository. Results therefore test
capability on disclosed tasks, not resistance to benchmark memorization.

## Reporting guidance

Report the FleetBench version or commit, selected tiers, model and quantization,
serving configuration, reasoning mode, and both overall and domain scores. Use
the dashboard's latest-per-task aggregation or clearly identify a different
attempt policy. Do not describe the score as financial advice quality, analyst
certification, or performance on live markets.

## Limitations

- The suite does not browse filings, terminals, news, or market-data feeds.
- It does not test spreadsheet operation, chart reading, source-link citation,
  or long-form report writing.
- It samples common corporate-finance and public-markets workflows but is not a
  complete accounting, tax, banking, insurance, or regulatory examination.
- Deterministic grading rewards the requested result and format, not the quality
  of an unobserved reasoning chain.
- The fixtures do not authorize real trades or individualized recommendations.

For the literature review and exact method mapping used to select these task
families, see [FINANCE_BENCHMARK_RESEARCH.md](FINANCE_BENCHMARK_RESEARCH.md).
