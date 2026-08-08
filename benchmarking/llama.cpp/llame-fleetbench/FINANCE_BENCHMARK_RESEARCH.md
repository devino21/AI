# Finance benchmark design review

Reviewed 20 July 2026. This note records which public benchmark methods informed
FleetBench's finance category and, equally importantly, which methods were not
adopted because they conflict with FleetBench's offline, deterministic design.

## What current benchmarks measure

### Financial documents and numerical reasoning

- [FinQA](https://arxiv.org/abs/2109.00122) pairs financial reports with expert
  questions, supporting facts, and executable reasoning programs. Its important
  contribution for FleetBench is multi-step numerical reasoning whose result can
  be checked without a model judge.
- [TAT-QA](https://arxiv.org/abs/2105.07624) requires joint use of table cells and
  prose, with arithmetic, counting, comparison, sorting, and composed operations.
- [FinanceBench](https://arxiv.org/abs/2311.11944) evaluates open-book questions
  over company filings and includes evidence strings. It exposes retrieval,
  grounding, and hallucination failures that calculation-only suites miss.
- [BizBench](https://aclanthology.org/2024.acl-long.452/) separates extraction,
  formula knowledge, program synthesis, and final calculation in realistic
  business and finance problems.
- [FinDABench](https://aclanthology.org/2025.coling-main.48/) broadens evaluation
  to indicator calculation, sentiment/risk, abnormal-report analysis, and
  technical data-analysis work.
- [FinBen](https://arxiv.org/abs/2402.12659) provides a useful breadth taxonomy:
  extraction, textual analysis, QA, generation, risk, forecasting, and decisions.

These methods motivated FleetBench's accounting, valuation, portfolio-risk, and
research-judgment domains. The point-in-time, conflicting-filings, claim-support,
and normalized-comparables tasks are specifically intended to keep evidence
selection visible rather than reduce every finance question to arithmetic.

### Trading signals and hybrid reasoning

- [FinTradeBench](https://arxiv.org/abs/2603.19225) is the closest match to the
  requested use case. It separates fundamentals-focused, trading-signal-focused,
  and hybrid questions. Its reported results also suggest retrieval helps textual
  fundamentals more than time-series reasoning. FleetBench now includes explicit
  technical-signal, cross-sectional factor, and fundamental-plus-signal cases.
- [Qlib's official benchmarks](https://github.com/microsoft/qlib/tree/main/examples/benchmarks)
  evaluate alpha predictions using IC/Rank IC and portfolio backtests, reporting
  annualized return, information ratio, and maximum drawdown. Qlib also models
  transaction costs, tradability, portfolio construction, and nested execution.
  FleetBench adopts Rank IC, portfolio-path metrics, turnover/cost, and execution
  concepts in compact synthetic fixtures.

### Sequential trading agents

- [InvestorBench](https://aclanthology.org/2025.acl-long.126/) evaluates agents
  across stocks, crypto, and ETFs using cumulative return, Sharpe ratio,
  annualized volatility, and maximum drawdown.
- [StockBench](https://openreview.net/forum?id=9tFRj7cmrS) emphasizes realistic
  daily signals, continuous buy/sell/hold decisions, multi-month horizons,
  contamination control, profitability, and risk management.
- [PredictionMarketBench](https://arxiv.org/abs/2602.00133) uses deterministic,
  event-driven replay with order-book state, maker/taker semantics, fees, and
  settlement. This is a particularly good methodological fit for FleetBench.
- Live systems such as [Agent Market Arena](https://arxiv.org/abs/2510.11695)
  and [AI-Trader](https://arxiv.org/abs/2512.10971) address contamination through
  ongoing real-market evaluation and test autonomous information gathering.

These methods motivated transaction-cost accounting, point-in-time feature
auditing, survivorship-bias detection, order-book VWAP/slippage, and sequential
event replay. They also show the next logical extension: a dedicated stateful
trading-agent environment rather than additional one-response questions.

## FleetBench crosswalk

| capability used in public work | FleetBench task family | grading signal |
|---|---|---|
| executable financial programs | statements, DCF, bonds, dilution | exact JSON components and tolerances |
| mixed evidence and calculation | research and accounting cases | selected evidence plus computed result |
| fundamentals + market signals | hybrid composite signal | per-asset scores and rank |
| cross-sectional alpha quality | factor Rank IC | exact Spearman correlation |
| technical indicators | SMA and RSI | indicator values plus target state |
| risk sizing | stop-based position sizing | risk budget, quantity, notional |
| portfolio-path evaluation | return and drawdown | replayed equity-curve metrics |
| realistic costs | exposure turnover | gross return, turnover, cost, net return |
| corporate actions | split adjustment | naive versus economic return |
| walk-forward integrity | timestamped feature audit | usable versus look-ahead features |
| survivorship control | dated membership | correct universe and contaminated names |
| market microstructure | order-book sweep | fill, VWAP, midpoint slippage |
| continuous decisions | event replay | final cash, inventory, equity, fees, P&L |

All FleetBench questions are original synthetic fixtures. Closely related
methods are grouped into compound prompts to reduce model calls; each requested
field is still scored independently. “Inspired by” means
the evaluation method or capability family was adopted; no benchmark questions,
company examples, or answer keys were copied.

## Design choices

FleetBench deliberately uses short, closed episodes. That provides stable ground
truth, identical inputs across model runs, no API/data licensing burden, and no
chance that a model is rewarded merely because the sampled market rose. Scoring
is component-based and never uses an LLM judge.

Metrics and conventions are stated inside each prompt when multiple definitions
exist. This matters for RSI smoothing, return compounding, volatility estimators,
turnover, drawdown sign, execution benchmark, and action timing. Ambiguous
conventions would otherwise measure guesswork rather than finance competence.

The suite includes data-integrity traps because an economically impressive
backtest is meaningless when it uses future closes, later-restated macro data,
year-end constituents, unadjusted splits, or zero trading costs.

## What remains out of scope

The current category does not reproduce a full Qlib-style model-training
pipeline or a months-long InvestorBench/StockBench episode. It also does not
measure live retrieval, multimodal chart interpretation, order cancellation,
partial fills over time, borrow availability, margin calls, maker rebates,
settlement, or market impact beyond displayed depth.

A future stateful `finance_agentic` lane could expose tools for dated news,
fundamentals, prices, and an exchange simulator. It should use hidden synthetic
paths, strict observation timestamps, fees/slippage, position and leverage
limits, and score both risk-adjusted outcome and process safety. That is a larger
benchmark environment, not something that should be approximated by asking for
one lucky buy/sell answer.
