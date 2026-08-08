"""Original, closed-world finance-research tasks for FleetBench.

The suite measures calculation and research judgment without live market data,
investment recommendations, or an LLM judge.  Every required fact is supplied
in the prompt and every answer is graded as structured JSON.
"""

from __future__ import annotations

import json
import math
import re


def _task(task_id, tier, domain, user, expect, *, tolerance=0.0):
    return {"id": task_id, "tier": tier, "domain": domain, "user": user,
            "expect": expect, "tolerance": tolerance}


JSON_ONLY = " Return only one JSON object with exactly the requested keys."


FINANCE_TASKS = [
    # Accounting and statement analysis.
    _task("finance_accounting_statements", "core", "accounting", """Part A: a company reports
revenue 500, cash operating costs 310, depreciation 40, interest expense 10,
and a 25% tax rate. It has no other income or expenses. Compute EBITDA, EBIT,
pre-tax income, taxes, and net income. Part B is an independent cash-flow case:
start with net income 84; depreciation is 22; accounts receivable increased 15;
inventory decreased 6; accounts payable decreased 4; capital expenditures were
31; debt issuance was 20; and dividends paid were 8. Using the indirect method,
compute CFO, CFI, CFF, and net change in cash. Use negatives for outflows.""" + JSON_ONLY +
          ' Keys: "ebitda", "ebit", "pretax_income", "taxes", "net_income", "cfo", "cfi", "cff", "net_change_cash".',
          {"ebitda": 190, "ebit": 150, "pretax_income": 140, "taxes": 35,
           "net_income": 105, "cfo": 93, "cfi": -31, "cff": 12,
           "net_change_cash": 74}),
    _task("finance_accounting_working_capital", "hard", "accounting", """Year 1 sales
are 730, COGS 438, average receivables 80, average inventory 65, and average
payables 54.75. Use a 365-day year. Compute DSO, DIO, DPO, and cash conversion
cycle in days, each rounded to 2 decimals.""" + JSON_ONLY +
          ' Keys: "dso", "dio", "dpo", "cash_conversion_cycle".',
          {"dso": 40, "dio": 54.17, "dpo": 45.63, "cash_conversion_cycle": 48.54},
          tolerance=.011),
    _task("finance_accounting_dilution", "hard", "accounting", """Net income is $96m.
There are 40m basic shares, 4m options with a $15 strike, and an average market
price of $24. There are also $50m of 4% convertible notes, convertible into 2m
shares; the tax rate is 25%. Use the treasury-stock method and if-converted
method. Compute diluted shares in millions and diluted EPS, rounded to 3 decimals.""" +
          JSON_ONLY + ' Keys: "diluted_shares_m", "diluted_eps".',
          {"diluted_shares_m": 43.5, "diluted_eps": 2.241}, tolerance=.0011),
    _task("finance_accounting_revenue_recognition", "frontier", "accounting", """A
two-year contract signed 1 July 2025 has a $240 subscription delivered evenly
over 24 months and a $60 implementation service completed at signing. The
customer prepays all $300. For calendar 2025, compute recognized revenue and
the 31 December 2025 contract liability. Assume implementation is a distinct
performance obligation and ignore tax.""" + JSON_ONLY +
          ' Keys: "revenue_2025", "contract_liability_2025_12_31".',
          {"revenue_2025": 120, "contract_liability_2025_12_31": 180}),

    # Valuation, fixed income, and corporate finance.
    _task("finance_valuation_market_multiples", "core", "valuation", """A firm has
120 shares outstanding at $25 each, debt of $850, cash of $300, and a 30%
non-controlling interest worth $90. It has no preferred stock. Compute equity
value and enterprise value. Using that computed enterprise value plus LTM revenue
910 and LTM EBITDA 280, and using the computed equity value plus LTM net income
150, compute EV/revenue, EV/EBITDA, and P/E. Round multiples to 3 decimals.""" +
          JSON_ONLY + ' Keys: "equity_value", "enterprise_value", "ev_revenue", "ev_ebitda", "pe".',
          {"equity_value": 3000, "enterprise_value": 3640, "ev_revenue": 4,
           "ev_ebitda": 13, "pe": 20}, tolerance=.0011),
    _task("finance_valuation_dcf", "hard", "valuation", """Forecast unlevered free cash
flow of 80, 92, and 105 in years 1-3. Discount at 10%. At the end of year 3 use
a perpetual growth rate of 3%. Compute the terminal value at year 3 and enterprise
value today. Round both to 2 decimals.""" + JSON_ONLY +
          ' Keys: "terminal_value_y3", "enterprise_value".',
          {"terminal_value_y3": 1545, "enterprise_value": 1388.43}, tolerance=.011),
    _task("finance_valuation_wacc", "hard", "valuation", """Equity market value is 600
and debt market value is 400. Cost of equity is 11%, pre-tax cost of debt is 6%,
and the tax rate is 25%. Compute after-tax cost of debt and WACC as percentages,
rounded to 2 decimals.""" + JSON_ONLY +
          ' Keys: "after_tax_cost_debt_pct", "wacc_pct".',
          {"after_tax_cost_debt_pct": 4.5, "wacc_pct": 8.4}, tolerance=.011),
    _task("finance_valuation_bond", "hard", "valuation", """A bond has face value
1,000, a 6% annual coupon paid annually, three years to maturity, and a yield to
maturity of 8% with annual compounding. Compute its price and Macaulay duration
in years, each rounded to 3 decimals.""" + JSON_ONLY +
          ' Keys: "price", "macaulay_duration".',
          {"price": 948.458, "macaulay_duration": 2.829}, tolerance=.0011),
    _task("finance_valuation_sensitivity", "frontier", "valuation", """Year-1 FCF is
100 and grows 5% in year 2, 4% in year 3, then at a perpetual rate. For each
case discount all annual cash flows at WACC and calculate terminal value at the
end of year 3 using FCF4/(WACC-g): bear WACC=11%, g=2%; base WACC=9%, g=3%;
bull WACC=8%, g=4%. Return enterprise values rounded to 2 decimals.""" + JSON_ONLY +
          ' Keys: "bear_ev", "base_ev", "bull_ev".',
          {"bear_ev": 1160.08, "base_ev": 1711.98, "bull_ev": 2523.15}, tolerance=.011),

    # Portfolio, risk, and market-data interpretation.
    _task("finance_portfolio_return", "core", "portfolio_risk", """A portfolio starts
with 60% in Asset A and 40% in Asset B. Over one period A returns 10% and B
returns -5%, with no rebalancing or cash flows. Compute portfolio return as a
percentage and each asset's ending weight as percentages, rounded to 2 decimals.""" +
          JSON_ONLY + ' Keys: "return_pct", "a_ending_weight_pct", "b_ending_weight_pct".',
          {"return_pct": 4, "a_ending_weight_pct": 63.46,
           "b_ending_weight_pct": 36.54}, tolerance=.011),
    _task("finance_portfolio_risk_model", "hard", "portfolio_risk", """Part A: a stock's covariance
with the market is 0.018 and market variance is 0.012. The risk-free rate is 4%,
expected market return is 10%, and the stock's expected return is 14%. Compute
beta, CAPM required return, and alpha. Part B: a two-asset portfolio has weights
60% and 40%, annual volatilities 20% and 10%, and correlation 0.25. Compute its
annual volatility. Express returns and volatility as percentages and round
volatility to 3 decimals.""" + JSON_ONLY +
          ' Keys: "beta", "capm_return_pct", "alpha_pct", "portfolio_volatility_pct".',
          {"beta": 1.5, "capm_return_pct": 13, "alpha_pct": 1,
           "portfolio_volatility_pct": 13.565}, tolerance=.0011),
    _task("finance_portfolio_attribution", "frontier", "portfolio_risk", """Use
Brinson-Fachler attribution with contribution formulas: allocation=(wp-wb)*(rb-Rb),
selection=wb*(rp-rb), interaction=(wp-wb)*(rp-rb). Benchmark total return Rb is
5%. Tech: wp=.60, wb=.40, rp=12%, rb=10%. Utilities: wp=.40, wb=.60, rp=2%,
rb=1.6666666667%. Compute total allocation, selection, interaction, and active
return in percentage points, rounded to 3 decimals.""" + JSON_ONLY +
          ' Keys: "allocation_pp", "selection_pp", "interaction_pp", "active_return_pp".',
          {"allocation_pp": 1.667, "selection_pp": 1.0, "interaction_pp": .333,
           "active_return_pp": 3.0}, tolerance=.0011),
    _task("finance_portfolio_fx", "frontier", "portfolio_risk", """A USD investor buys
a euro asset for EUR 1,000 when EUR/USD is 1.10 USD per EUR. One year later the
asset is worth EUR 1,080 and EUR/USD is 1.02. There are no distributions. Compute
the local asset return, the euro currency return versus USD, and the investor's
USD return, as percentages rounded to 2 decimals. Use compounded translation,
not addition.""" + JSON_ONLY +
          ' Keys: "local_return_pct", "currency_return_pct", "usd_return_pct".',
          {"local_return_pct": 8, "currency_return_pct": -7.27, "usd_return_pct": .15},
          tolerance=.011),

    # Research judgment: provenance, comparability, timing, and calibration.
    _task("finance_research_gaap_adjusted", "core", "research_judgment", """Use only
this excerpt: `FY revenue $900m. GAAP operating income $72m. Management's adjusted
operating income $108m excludes $24m stock compensation and $12m restructuring.`
Report GAAP margin, adjusted margin, and the total exclusions as percentages or
dollars as appropriate.""" + JSON_ONLY +
          ' Keys: "gaap_margin_pct", "adjusted_margin_pct", "exclusions_m".',
          {"gaap_margin_pct": 8, "adjusted_margin_pct": 12, "exclusions_m": 36}),
    _task("finance_research_comparables", "hard", "research_judgment", """Target T
has EBITDA 50 including a one-time insurance gain of 8. Comparable C has EBITDA
70 after a one-time litigation expense of 6. Normalize both by removing one-time
items. C's enterprise value is 640. Apply C's normalized EV/EBITDA multiple to
T's normalized EBITDA. Compute both normalized EBITDAs, C's multiple, and T's
implied enterprise value, rounded to 3 decimals.""" + JSON_ONLY +
          ' Keys: "t_normalized_ebitda", "c_normalized_ebitda", "c_ev_ebitda", "t_implied_ev".',
          {"t_normalized_ebitda": 42, "c_normalized_ebitda": 76,
           "c_ev_ebitda": 8.421, "t_implied_ev": 353.684}, tolerance=.0011),
    _task("finance_research_claim_support", "frontier", "research_judgment", """Use
only these records: `Q1 units 100, price $10`; `Q2 units 120, price $9`; `Q2 gross
margin 42%, versus Q1 40%`; `No competitor pricing data was collected.` Evaluate
three claims as supported or unsupported: (1) Q2 revenue grew versus Q1; (2) Q2
gross margin improved; (3) the company gained share because competitors raised
prices. Also compute Q1 and Q2 revenue.""" + JSON_ONLY +
          ' Keys: "q1_revenue", "q2_revenue", "claim1", "claim2", "claim3".',
          {"q1_revenue": 1000, "q2_revenue": 1080, "claim1": "supported",
           "claim2": "supported", "claim3": "unsupported"}),
    _task("finance_research_evidence_timeline", "frontier", "research_judgment", """Build a
point-in-time research snapshot as of 30 April. Records are: A=10-K filed 1 March,
debt $400m at 31 Dec; B=8-K filed 10 April, reporting a $75m repayment on 5 April;
C=draft lender deck dated 20 April but not public, debt $300m; D=10-Q filed 8 May,
debt $310m at 31 March; E=industry report published 15 April, market growth 4%;
F=revised industry dataset published 10 May, backfilled growth 2%. Determine debt
supportable on 30 April by updating the latest public balance only for the public
repayment, the market-growth figure then available, and evidence usage. Return
IDs alphabetically.""" + JSON_ONLY +
          ' Keys: "supportable_debt_m", "market_growth_pct", "used_evidence", "excluded_evidence".',
          {"supportable_debt_m": 325, "market_growth_pct": 4,
           "used_evidence": ["A", "B", "E"], "excluded_evidence": ["C", "D", "F"]}),

    # Algorithmic trading: signal interpretation, backtesting, market
    # microstructure, and bias controls. These capability families mirror the
    # evaluation methods used by Qlib, InvestorBench, StockBench, and
    # FinTradeBench, while the fixtures and answers are original.
    _task("finance_algo_position_sizing", "core", "algorithmic_trading", """Account
equity is $100,000. Risk exactly 1% of equity if the stop is hit. Entry is $50
and stop is $47.50. Ignore gaps, fees, and integer-lot constraints beyond whole
shares. Compute dollar risk budget, risk per share, shares, and position notional.""" +
          JSON_ONLY + ' Keys: "risk_budget", "risk_per_share", "shares", "notional".',
          {"risk_budget": 1000, "risk_per_share": 2.5, "shares": 400, "notional": 20000}),
    _task("finance_algo_rank_ic", "hard", "algorithmic_trading", """At time t, factor
scores are A=4, B=1, C=3, D=2. Next-period returns are A=1%, B=4%, C=2%, D=3%.
With rank 1 assigned to the lowest value, compute Spearman rank information
coefficient using 1-6*sum(d_i^2)/(n*(n^2-1)). Also identify the highest-factor
asset and the highest-return asset.""" + JSON_ONLY +
          ' Keys: "rank_ic", "highest_factor", "highest_return".',
          {"rank_ic": -1, "highest_factor": "A", "highest_return": "B"}, tolerance=.001),
    _task("finance_algo_signal_stack", "frontier", "algorithmic_trading", """Analyze
three independent signal blocks. (1) Closes [10,11,12,11,13]: compute SMA(2),
SMA(5), and choose long if SMA(2)>SMA(5), short if lower, else flat. (2) Closes
[100,102,101,104,103,107]: compute 5-period RSI from simple mean gain and simple
mean absolute loss, not Wilder smoothing. (3) Composite=0.5*z_momentum+
0.3*z_earnings_revision-0.2*z_leverage for X=(1.2,.4,-.5), Y=(.6,1.1,.2),
Z=(-.2,.8,-1.0). Compute scores and rank best to worst. Round RSI to 3 decimals
and composite scores to 2.""" + JSON_ONLY +
          ' Keys: "sma_2", "sma_5", "sma_position", "rsi_average_gain", "rsi_average_loss", "rsi", "x_score", "y_score", "z_score", "ranking".',
          {"sma_2": 12, "sma_5": 11.4, "sma_position": "long",
           "rsi_average_gain": 1.8, "rsi_average_loss": .4, "rsi": 81.818,
           "x_score": .82, "y_score": .59, "z_score": .34,
           "ranking": ["X", "Y", "Z"]}, tolerance=.0011),
    _task("finance_algo_backtest_with_costs", "frontier", "algorithmic_trading", """Part
A: a strategy starts at 100 and has daily simple returns [10%,-5%,2%,-8%,4%].
Compound them and compute cumulative return and maximum peak-to-trough drawdown
as positive percentages. Part B is independent: target exposures [1,1,-1,0]
apply to interval asset returns [2%,-1%,3%,-2%], with exposure initially 0.
Each exposure change costs 10 bps times absolute change. Compute arithmetic gross
return, turnover, cost, and net return without compounding. Round Part A to 3
decimals.""" + JSON_ONLY +
          ' Keys: "cumulative_return_pct", "max_drawdown_pct", "gross_return_pct", "turnover", "cost_pct", "net_return_pct".',
          {"cumulative_return_pct": 1.985, "max_drawdown_pct": 10.852,
           "gross_return_pct": -2, "turnover": 4, "cost_pct": .4,
           "net_return_pct": -2.4}, tolerance=.0011),
    _task("finance_algo_data_integrity_audit", "frontier", "algorithmic_trading", """Audit
three independent backtest issues. (1) A stock closes at $100, executes a 2-for-1
split, then closes at $52: compute naive return, adjusted return, and adjusted
day-0 close. (2) At the 3 May open, candidate features are A=2 May close, B=3 May
open, C=3 May close, D=filing published 2 May 18:00, E=macro revision published
10 May but backfilled to 1 May: classify usable and look-ahead IDs. (3) Year-end
universe is A,B,C; point-in-time 1 January members were A,B,D; D delisted in June
and C joined in September: give the January universe and tickers contaminated by
year-end selection. Sort ID/ticker lists alphabetically.""" + JSON_ONLY +
          ' Keys: "naive_return_pct", "adjusted_return_pct", "adjusted_day0_close", "usable_features", "lookahead_features", "january_universe", "contaminated_selection".',
          {"naive_return_pct": -48, "adjusted_return_pct": 4,
           "adjusted_day0_close": 50, "usable_features": ["A", "B", "D"],
           "lookahead_features": ["C", "E"], "january_universe": ["A", "B", "D"],
           "contaminated_selection": ["C", "D"]}, tolerance=.011),
    _task("finance_algo_orderbook_execution", "frontier", "algorithmic_trading", """At
arrival the best bid is 9.98 and best ask is 10.00. Ask depth is 100 shares at
10.00 then 100 at 10.05. A market buy for 180 shares consumes displayed asks in
price order with no fees. Compute fill quantity, VWAP, arrival midprice, and
slippage versus arrival midprice in basis points, rounded to 3 decimals.""" +
          JSON_ONLY + ' Keys: "filled_shares", "vwap", "arrival_mid", "slippage_bps".',
          {"filled_shares": 180, "vwap": 10.022, "arrival_mid": 9.99,
           "slippage_bps": 32.254}, tolerance=.0011),
    _task("finance_algo_event_replay", "frontier", "algorithmic_trading", """Replay
these four closes and end-of-day orders in order: prices [10,12,9,11], orders
[buy 50, hold, sell 20, sell 30]. Start with $1,000 cash and zero shares. Each
non-hold order fills fully at that day's close and incurs a fixed $1 fee. No
shorting or interest. Compute ending cash, ending shares, ending equity marked
at the final close, total fees, and profit.""" + JSON_ONLY +
          ' Keys: "ending_cash", "ending_shares", "ending_equity", "total_fees", "profit".',
          {"ending_cash": 1007, "ending_shares": 0, "ending_equity": 1007,
           "total_fees": 3, "profit": 7}),
]

# Closely related, same-tier cases share one request while retaining their
# original prompts and every independently graded answer leaf.  Keeping bundles
# within one domain and tier preserves both the capability mix and --tier
# semantics; the outer object merely namespaces each original response.
_finance_original = {task["id"]: task for task in FINANCE_TASKS}
_FINANCE_BUNDLES = [
    ("finance_accounting_operations", "hard", "accounting", [
        "finance_accounting_working_capital", "finance_accounting_dilution"]),
    ("finance_valuation_instruments", "hard", "valuation", [
        "finance_valuation_dcf", "finance_valuation_wacc", "finance_valuation_bond"]),
    ("finance_portfolio_frontier", "frontier", "portfolio_risk", [
        "finance_portfolio_attribution", "finance_portfolio_fx"]),
    ("finance_research_evidence", "frontier", "research_judgment", [
        "finance_research_claim_support", "finance_research_evidence_timeline"]),
    ("finance_algo_signals_backtest", "frontier", "algorithmic_trading", [
        "finance_algo_signal_stack", "finance_algo_backtest_with_costs"]),
    ("finance_algo_integrity_execution", "frontier", "algorithmic_trading", [
        "finance_algo_data_integrity_audit", "finance_algo_orderbook_execution",
        "finance_algo_event_replay"]),
]
_BUNDLED_FINANCE_IDS = {task_id for _, _, _, ids in _FINANCE_BUNDLES for task_id in ids}


def _finance_bundle(bundle_id, tier, domain, task_ids):
    sections = []
    expected = {}
    tolerance = 0.0
    for index, task_id in enumerate(task_ids, 1):
        task = _finance_original[task_id]
        sections.append(f"SUBTASK {index} — {task_id}:\n{task['user']}")
        expected[task_id] = task["expect"]
        tolerance = max(tolerance, task.get("tolerance", 0.0))
    user = (
        "Solve the independent finance subtasks below. Ignore each subtask's local response-"
        "envelope instruction; solve its requested fields, then return one JSON object. The outer "
        "keys must be exactly the subtask ids, and each value must be that subtask's requested JSON "
        "object. No Markdown or explanation.\n\n" + "\n\n".join(sections)
    )
    return _task(bundle_id, tier, domain, user, expected, tolerance=tolerance)


FINANCE_TASKS = [task for task in FINANCE_TASKS if task["id"] not in _BUNDLED_FINANCE_IDS]
FINANCE_TASKS += [_finance_bundle(*spec) for spec in _FINANCE_BUNDLES]


def _extract_objects(text):
    """Every parseable JSON object in the text, outermost-first, in order.

    This replaced a single-object helper that returned only the FIRST parseable
    object. A model that narrates before answering, restates the schema, or emits
    one object per subtask was therefore graded on the wrong object:
    laguna-s-2.1-q8's finance_research_evidence answer had both subtasks
    numerically perfect as sibling objects and scored 0.0, because only the first
    was ever examined.
    """
    decoder = json.JSONDecoder()
    text = text or ""
    found, index = [], 0
    while index < len(text):
        start = text.find("{", index)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(value, dict):
            found.append(value)
            index = start + end
        else:
            index = start + 1
    return found


def _empty_answer_detail(response, fallback):
    """Report an exhausted token budget as truncation, not as a missing answer.

    Mirrors the helper of the same name in fleetbench.py; duplicated rather than
    imported to keep the task modules free of a dependency on the runner.
    """
    used = response.get("completion_tokens")
    limit = response.get("requested_max_tokens")
    exhausted = response.get("finish_reason") == "length" or (
        used and limit and int(used) >= int(limit))
    if not exhausted:
        return fallback
    reasoning_chars = len(response.get("reasoning_content") or "")
    evidence = f"; {reasoning_chars} reasoning chars" if reasoning_chars else ""
    return f"{fallback} - generation exhausted {limit} tokens{evidence}"


_ORDINAL_KEY_RE = re.compile(r"^\s*(?:subtask|task|part|section)?\s*[_\-#]?\s*(\d+)\b", re.I)


def _normalize_key(key):
    """Casefold a key and reduce every run of non-alphanumerics to one space."""
    return re.sub(r"[^a-z0-9]+", " ", str(key).lower()).strip()


def _align_bundle_keys(value, expected):
    """Map decorated response keys onto subtask ids.

    Bundle prompts label each section `SUBTASK N - <task_id>`, so both the
    ordinal and the heading are more salient than the bare id, and models
    routinely key their JSON by one of them. That is a labelling choice the
    prompt invites, not a wrong answer.

    The original implementation matched a key that was *only* an ordinal
    ("SUBTASK 1", "1"). It did not match the most common deviation of all --
    echoing the prompt's own heading verbatim, "SUBTASK 1 - finance_algo_data_
    integrity_audit" -- which scored 0.0 on answers whose numbers were entirely
    correct: 18 such records across seven models, including a 0/16 for
    qwen3.6-35b-a3b-mtp-q8 on finance_algo_integrity_execution. Resolution now
    runs id-substring first, then ordinal prefix, and is accepted only when the
    result is a bijection onto the expected ids.
    """
    if not isinstance(value, dict) or len(value) != len(expected):
        return value
    order = list(expected)
    normalized_ids = [_normalize_key(task_id) for task_id in order]
    aligned = {}
    for key, sub in value.items():
        if not isinstance(key, str):
            return value
        index = None
        normalized = _normalize_key(key)
        # The id appearing anywhere in the key is the strongest signal, and it
        # survives any surrounding decoration the model copied from the prompt.
        hits = [i for i, task_id in enumerate(normalized_ids) if task_id in normalized]
        if len(hits) == 1:
            index = hits[0]
        else:
            match = _ORDINAL_KEY_RE.match(key)
            if match is not None:
                index = int(match.group(1)) - 1
        if index is None or not 0 <= index < len(order) or order[index] in aligned:
            return value
        aligned[order[index]] = sub
    return aligned


# A recovered-but-wrong envelope keeps most of its field credit. Structure is a
# genuine instruction-following requirement so it is not free, but it used to be
# scored harder than being wrong, which inverted the ranking: a model with a
# perfect answer in the wrong shape scored 0.0 while a model with the right shape
# and half its numbers wrong scored 0.5.
_ENVELOPE_FACTOR = 0.85


def _recover_envelope(objects, expected):
    """Best-effort reconstruction of the expected envelope from what was emitted.

    Returns (value, envelope_ok); `envelope_ok` is False whenever recovery was
    needed, so the caller applies the structural deduction.
    """
    expected_keys = set(expected)
    nested = {k: v for k, v in expected.items() if isinstance(v, dict)}

    for obj in objects:                              # already correct
        if set(obj) == expected_keys:
            return obj, True

    for obj in objects:                              # ordinal subtask keys
        aligned = _align_bundle_keys(obj, expected)
        if set(aligned) == expected_keys:
            # Full credit, matching the long-standing behavior of
            # `_align_bundle_keys`: the bundle prompt itself labels each section
            # "SUBTASK N — <task_id>", so keying by the ordinal is a labelling
            # choice the prompt invites, not a deviation from the envelope.
            return aligned, True

    if nested and len(objects) > 1:                  # one sibling object per subtask
        assembled, used = {}, set()
        for key, want in nested.items():
            best, cover = None, 0
            for position, obj in enumerate(objects):
                if position in used:
                    continue
                overlap = len(set(want) & set(obj))
                if overlap > cover:
                    best, cover = position, overlap
            if best is not None:
                assembled[key] = objects[best]
                used.add(best)
        if set(assembled) == expected_keys:
            return assembled, False

    if nested:                                       # subtasks merged flat
        merged = {}
        for obj in objects:
            merged.update(obj)
        assembled = {key: {k: merged[k] for k in want}
                     for key, want in nested.items() if set(want) <= set(merged)}
        if set(assembled) == expected_keys:
            return assembled, False

    # Nothing reassembled: grade whichever object covers the most expected keys,
    # so partial work still earns partial credit instead of a flat zero.
    return max(objects, key=lambda o: len(expected_keys & set(o))), False


def _equal(got, want, tolerance):
    if isinstance(want, bool) or want is None or isinstance(want, str):
        return got == want
    if isinstance(want, (int, float)):
        return isinstance(got, (int, float)) and not isinstance(got, bool) and math.isclose(
            float(got), float(want), rel_tol=0, abs_tol=tolerance)
    if isinstance(want, list):
        return isinstance(got, list) and len(got) == len(want) and all(
            _equal(g, w, tolerance) for g, w in zip(got, want))
    if isinstance(want, dict):
        return isinstance(got, dict) and set(got) == set(want) and all(
            _equal(got[k], v, tolerance) for k, v in want.items())
    return got == want


def score_finance(task, response):
    objects = _extract_objects(response.get("content") or "")
    if not objects:
        return 0.0, _empty_answer_detail(response, "no JSON object")
    expected = task["expect"]
    value, envelope_ok = _recover_envelope(objects, expected)
    def leaves(got, want):
        if isinstance(want, dict):
            for key, child in want.items():
                yield from leaves(got.get(key) if isinstance(got, dict) else None, child)
        else:
            yield _equal(got, want, task.get("tolerance", 0.0))

    results = list(leaves(value, expected))
    correct = sum(results)
    score = correct / len(results)
    detail = f"{correct}/{len(results)} independently graded fields"
    if not envelope_ok:
        score *= _ENVELOPE_FACTOR
        detail += (f"; envelope deviated (got {sorted(value)}, "
                   f"expected {sorted(expected)}) -{1 - _ENVELOPE_FACTOR:.0%}")
    return round(score, 3), detail


def finance_manifest():
    return [{"id": t["id"], "tier": t["tier"], "domain": t["domain"],
             "origin": "original FleetBench synthetic fixture", "version": "1.1",
             "grading": "deterministic JSON component comparison"}
            for t in FINANCE_TASKS]


def selftest_finance():
    failures = []
    ids = [task["id"] for task in FINANCE_TASKS]
    if len(ids) != len(set(ids)):
        failures.append("task IDs are not unique")
    if {task["tier"] for task in FINANCE_TASKS} != {"core", "hard", "frontier"}:
        failures.append("tier inventory mismatch")
    if {task["domain"] for task in FINANCE_TASKS} != {
            "accounting", "valuation", "portfolio_risk", "research_judgment",
            "algorithmic_trading"}:
        failures.append("domain inventory mismatch")
    for task in FINANCE_TASKS:
        score, _ = score_finance(task, {"content": json.dumps(task["expect"])})
        if score != 1.0:
            failures.append(f"reference failed: {task['id']}")
    # A near-empty answer earns near-nothing, but is graded on the fields it did
    # supply rather than gated to a flat 0.0 by its key set.
    score, _ = score_finance(FINANCE_TASKS[0], {"content": '{"ebitda":190}'})
    if not 0.0 <= score <= 0.12:
        failures.append("missing keys were over-credited")
    exact, _ = score_finance(FINANCE_TASKS[0],
                             {"content": json.dumps(FINANCE_TASKS[0]["expect"])})
    extra = dict(FINANCE_TASKS[0]["expect"]); extra["commentary"] = "see above"
    loose, _ = score_finance(FINANCE_TASKS[0], {"content": json.dumps(extra)})
    if not 0.0 < loose < exact:
        failures.append("extra keys must cost the envelope deduction, not everything")

    # Regression: a bundle answered correctly as sibling objects instead of one
    # nested object. This is laguna-s-2.1-q8's real finance_research_evidence
    # response, which scored 0.0 while being numerically perfect on both
    # subtasks. Structure is still charged, but the work now counts.
    research = next(t for t in FINANCE_TASKS if t["id"] == "finance_research_evidence")
    siblings = "\n\n".join("```json\n" + json.dumps(part) + "\n```"
                           for part in research["expect"].values())
    score, detail = score_finance(research, {"content": siblings})
    if not 0.80 <= score < 1.0:
        failures.append(f"sibling-object bundle not recovered (got {score})")
    # And the flattened form of the same answer.
    flat = {}
    for part in research["expect"].values():
        flat.update(part)
    score, _ = score_finance(research, {"content": json.dumps(flat)})
    if not 0.80 <= score < 1.0:
        failures.append(f"flattened bundle not recovered (got {score})")
    # Narration before the answer must not be graded in place of the answer.
    narrated = ('{"note":"working below"}\n' + json.dumps(research["expect"]))
    score, _ = score_finance(research, {"content": narrated})
    if score != 1.0:
        failures.append(f"answer after a preamble object was not found (got {score})")
    # Regression: keys that echo the prompt's own section heading verbatim.
    # "SUBTASK 1 - <id>" is the most common bundle deviation there is and it
    # used to score 0.0 on numerically perfect answers -- qwen3.6-35b-a3b-mtp-q8
    # lost a 7/7 finance_portfolio_frontier that way. Ordinal-only keys and
    # id-only keys must keep working alongside it.
    frontier = next(t for t in FINANCE_TASKS if t["id"] == "finance_portfolio_frontier")
    ids = list(frontier["expect"])
    for label, relabel in (
            ("prompt heading", lambda i, k: f"SUBTASK {i} — {k}"),
            ("heading, hyphen", lambda i, k: f"SUBTASK {i} - {k}"),
            ("bare ordinal", lambda i, k: f"SUBTASK {i}"),
            ("digit only", lambda i, k: str(i)),
            ("upper-cased id", lambda i, k: k.upper()),
    ):
        payload = {relabel(index, key): frontier["expect"][key]
                   for index, key in enumerate(ids, 1)}
        score, detail = score_finance(frontier, {"content": json.dumps(payload)})
        if score != 1.0:
            failures.append(f"bundle keys by {label} scored {score} ({detail})")
    # Keys that resolve to neither an id nor an ordinal are still a deviation:
    # alignment must not degrade into "any two keys map to the two subtasks".
    opaque = {chr(ord("a") + index): frontier["expect"][key]
              for index, key in enumerate(ids)}
    score, detail = score_finance(frontier, {"content": json.dumps(opaque)})
    if "envelope deviated" not in detail:
        failures.append(f"unrecognizable bundle keys were treated as aligned ({detail})")

    bundle = next(task for task in FINANCE_TASKS
                  if task["id"] == "finance_accounting_operations")
    partial = json.loads(json.dumps(bundle["expect"]))
    partial["finance_accounting_dilution"]["diluted_eps"] = -1
    score, _ = score_finance(bundle, {"content": json.dumps(partial)})
    if not 0.0 < score < 1.0:
        failures.append("compound leaf error did not receive partial credit")

    # Ground-truth derivations refer to the original atomic fixtures even when
    # those fixtures are emitted inside a same-tier runtime bundle.
    by_id = _finance_original
    dcf = by_id["finance_valuation_dcf"]["expect"]
    ev = 80/1.1 + 92/1.1**2 + (105 + 105*1.03/(.10-.03))/1.1**3
    if not math.isclose(dcf["enterprise_value"], ev, abs_tol=.011):
        failures.append("DCF ground truth mismatch")
    bond = by_id["finance_valuation_bond"]["expect"]
    cashflows = [60, 60, 1060]
    pv = [cf / 1.08**year for year, cf in enumerate(cashflows, 1)]
    if not (math.isclose(bond["price"], sum(pv), abs_tol=.0011)
            and math.isclose(bond["macaulay_duration"],
                             sum((i + 1) * x for i, x in enumerate(pv)) / sum(pv),
                             abs_tol=.0011)):
        failures.append("bond ground truth mismatch")
    sensitivity = by_id["finance_valuation_sensitivity"]["expect"]
    fcf = [100, 105, 109.2]
    for key, wacc, growth in (("bear_ev", .11, .02), ("base_ev", .09, .03),
                              ("bull_ev", .08, .04)):
        calculated = sum(x / (1 + wacc) ** year for year, x in enumerate(fcf, 1))
        calculated += fcf[-1] * (1 + growth) / (wacc - growth) / (1 + wacc) ** 3
        if not math.isclose(sensitivity[key], calculated, abs_tol=.011):
            failures.append(f"DCF sensitivity ground truth mismatch: {key}")
    equity = [100]
    for ret in [.10, -.05, .02, -.08, .04]:
        equity.append(equity[-1] * (1 + ret))
    peak = equity[0]
    drawdowns = []
    for value in equity:
        peak = max(peak, value)
        drawdowns.append((peak - value) / peak)
    metrics = by_id["finance_algo_backtest_with_costs"]["expect"]
    if not (math.isclose(metrics["cumulative_return_pct"],
                         100 * (equity[-1] / equity[0] - 1), abs_tol=.0011)
            and math.isclose(metrics["max_drawdown_pct"],
                             100 * max(drawdowns), abs_tol=.0011)):
        failures.append("backtest metrics ground truth mismatch")
    execution = by_id["finance_algo_orderbook_execution"]["expect"]
    vwap = (100 * 10 + 80 * 10.05) / 180
    if not (math.isclose(execution["vwap"], vwap, abs_tol=.0011)
            and math.isclose(execution["slippage_bps"],
                             (vwap / 9.99 - 1) * 10000, abs_tol=.0011)):
        failures.append("order-book execution ground truth mismatch")
    return failures
