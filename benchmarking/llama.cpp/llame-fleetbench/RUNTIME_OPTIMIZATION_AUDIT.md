# FleetBench runtime optimization audit

Audit date: 2026-07-20. Source evidence: the current Python task definitions,
the latest record for each `(model, category, task_id)` in `results/runs.csv`,
the corresponding tool traces, and the supplied dashboard screenshot.

## Executive result

### Routine compact profile (rebalanced 2026-08-04)

FleetBench now offers an explicit `--profile compact` 45-request stratified
panel alongside the unchanged default 180-request exhaustive inventory:

| category | full | compact |
|---|---:|---:|
| tools | 15 | 5 |
| agentic | 23 | 5 |
| compliance | 18 | 5 |
| applied | 10 | 5 |
| finance | 16 | 5 |
| coding | 24 | 5 |
| reasoning | 21 | 5 |
| math | 31 | 5 |
| long context | 22 | 5 |
| **total** | **180** | **45 (-75%)** |

Selection is capability-stratified and informed by recorded discrimination and
runtime. Equal five-task columns prevent the category mix itself from weighting
one dashboard category more heavily than another. It preserves all nine
dashboard categories, all three compliance behavior types, tool safety/utility,
stateful agent workflows, applied domains,
finance domains, code synthesis/repair, structured reasoning, mathematical
families, and retrieval plus synthesis at short and long context. Saturated
duplicates and cross-category overlaps remain available through
`suite_profile: full`.

The original uneven 45-task selection projected about 3.0 hours against
GLM-5.2's historical durations. The balanced panel retains the same request
count but changes several IDs, including a 16k multi-needle cell, so the old
estimate remains approximate until the revised panel is measured directly.
Compact runs use serial requests and, when selected through the CLI, default to
a separate `results-compact-5x9` directory for valid apples-to-apples comparisons.

The screenshot represents 191 pre-finance task units:

| category | before | after | change | decision |
|---|---:|---:|---:|---|
| tools | 15 | 15 | 0 | preserve distinct tool behaviors; cap one runaway trajectory |
| agentic | 23 | 23 | 0 | preserve independent mutable environments; cap one low-yield trajectory |
| compliance | 18 | 18 | 0 | preserve balanced comply/refuse/clarify sampling |
| applied | 18 | 10 | -8 | merge related calculations/evidence checks |
| coding | 27 | 24 | -3 | merge small functions into executed compound implementations |
| reasoning | 27 | 21 | -6 | bundle short arithmetic and reflection probes |
| math | 39 | 31 | -8 | bundle repeated methods and retain higher-signal exact problems |
| long context | 24 | 22 | -2 | omit saturated 65k plain-needle cells; retain harder 65k shapes |
| **screenshot suite** | **191** | **164** | **-27 (14.1%)** | |
| finance (new) | 24 | 16 | -8 | same-tier/domain bundles with leaf-level grading |
| **current full suite** | **215 without this audit** | **180** | **-35 (16.3%)** | |

These are task units, not raw HTTP calls. Multi-turn tool and agentic tasks make
several calls within one unit. The dispatch round cap reduces HTTP calls on
repetitive failures in addition to the 35-unit reduction. Independent
non-long-context environments may also overlap through `request_concurrency`;
the checked-in configuration uses one slot while long-context remains serial.

## Measured cost baseline

Latest recorded results contain 1,193 task records across eight models. They do
not include the newly added finance category.

| category | distinct tasks in data | median task wall time | aggregate recorded time |
|---|---:|---:|---:|
| math | 39 | 35.01 s | 3.18 h |
| long context | 24 | 39.72 s | 2.35 h |
| coding | 27 | 33.95 s | 2.32 h |
| agentic | 23 | 34.30 s | 2.22 h |
| reasoning | 27 | 13.99 s | 1.41 h |
| tools | 15 | 8.11 s | 0.83 h |
| applied | 18 | 13.36 s | 0.58 h |
| compliance | 18 | 4.27 s | 0.17 h |

The screenshot's per-model totals (roughly 1.1–3.6 hours) agree with the CSV
order of magnitude. Model speed and missing/incomplete records explain why a
single universal number would be misleading.

## Savings estimate

No post-change fleet run exists yet, so the time saving is a projection rather
than a measured benchmark. For every compound group and model, the estimate
uses:

`new time = slowest old member + 25% * time of the remaining old members`

This assumes the compound response pays the full cost of its hardest component
and one quarter of each added component. Across the recorded dataset this saves
about **0.54 aggregate model-hours** from compound tasks. The theoretical lower
bound if added fields were free is 0.72 hours. Capping the incident-dispatch
loop at three rounds projects another **5.5 aggregate minutes** on the three
models that repeated both retrievals for all six rounds.

For models with all 14 consolidation groups present, projected task-merging
savings are approximately **3.0–7.6 minutes per model** (1.9–6.6% of their
whole recorded suite). The dispatch cap adds about **1.2–2.4 minutes** on each
affected repeating model. Finance's 24→16 request consolidation is not included
because the recorded timings predate the new bundles.

Actual savings must be measured by running the revised suite. Compound prompts
can take longer than their hardest old member, especially on reasoning models;
the task-count reduction alone must not be presented as equivalent wall-time
reduction.

## Complete task inventory and disposition

### Tools — 15 retained

`tool_simple_call`, `tool_param_precision`, `tool_restraint_v2`, `tool_selection`,
`tool_multiturn_extract`, `tool_error_recovery`, `tool_chain_2hop`,
`tool_missing_param_v2`, `tool_already_answered_v2`, `tool_parallel_weather`,
`tool_untrusted_payload`, `tool_incident_mitigation`, `tool_backup_recovery`,
`tool_canary_abort_utility`, `tool_incident_dispatch_utility`.

These cover different call/no-call, argument, adversarial, recovery, state, and
utility failure modes. Combining them would change the tool surface or permit
one answer to leak another answer. The dispatch task is retained, but its six
rounds were wasteful: successful models finish with two calls, while three
models repeated both reads for 12 calls and scored zero. Its cap is now three
rounds, still allowing six calls and the best observed partial trajectory.

### Agentic — 23 retained

`agent_repo_bugfix`, `agent_config_migration`, `agent_log_forensics`,
`agent_data_pipeline`, `agent_test_driven_feature`, `agent_dependency_repair`,
`agent_policy_workflow`, `agent_injection_resistance`, `agent_research_synthesis`,
`agent_concurrent_incident`, `agent_repo_refactor`, `agent_partial_failure`,
`agent_access_review`, `agent_privacy_request`, `agent_release_recovery`,
`agent_calendar_negotiation`, `agent_tenant_isolation`, `agent_temporal_research`,
`agent_pagination_audit`, `agent_memory_reconciliation`,
`agent_ambiguity_restraint`, `agent_credential_rotation`,
`agent_incident_prioritization`.

Each owns a different mutable end state and safety policy. Merging environments
would reduce causal attribution and safety efficacy. The test-driven feature
task was the second most expensive agentic case and every recorded model scored
0.25 or below; its maximum rounds are reduced from 18 to 12. Calendar remains
unchanged because successful traces genuinely needed 7–14 calls.

### Compliance — 18 retained

All six `comply_*`, six `refuse_*`, and six `clarify_*` cases remain separate.
The balanced behavior design depends on independent decisions, and the entire
category consumed only 0.17 aggregate recorded hours. It is a poor target for
merging.

### Applied — 18 to 10

Retained language-format probes: `applied_lang_edit`,
`applied_lang_multilingual_extract`, `applied_lang_reference_v2`,
`applied_lang_constraints`.

Merged cases:

- Simpson reversal + weighted mean → `applied_data_aggregation`
- join + per-user window → `applied_data_relational`
- cohort maturity + robust anomaly → `applied_data_maturity_robustness`
- units + decay → `applied_science_quantitative`
- experimental contrast + Simpson integration → `applied_science_design_numerics`
- four known/unknown/false-premise/time-order checks → `applied_calibration_evidence`

All original answer components remain independently scored.

### Finance — 24 original cases in 16 requests

Four accounting, five valuation, four portfolio/risk, four research-judgment,
and seven algorithmic-trading cases remain. Same-tier cases within a capability
family are namespaced into six compound requests; recursive leaf grading keeps
every original field independently scored. This takes the category from 24 to
16 requests. Its exact inventory and benchmark crosswalk are in
`FINANCE_BENCHMARK_CARD.md` and
`FINANCE_BENCHMARK_RESEARCH.md`.

### Coding — 27 to 24

Merged executed cases:

- log parsing + top-k words → `code_text_utilities`
- LIS + nested-dict flattening → `code_sequence_structures`
- Roman numerals + base conversion → `code_numeral_conversion`

RLE remains a standalone basic synthesis calibration. Wildcard DP, interval
merge, expression parsing, stateful simulators, repair tasks, concurrency,
HumanEval-derived contracts, and output-prediction cases remain separate. Their
specifications and hidden edge cases are materially different. Compound coding
answers execute the union of the original hidden assertions, so no test case is
dropped.

### Reasoning — 27 to 21

Four short arithmetic problems become `reason_arithmetic_bundle_v2`; four classic
reflection traps become `reason_reflection_bundle`. Every answer is a separately
graded JSON field. Exact JSON, word-count, word-prefix, composite formatting,
state tracking, scheduling, truth networks, ARC-like induction, portfolio
optimization, DSL execution, table analysis, and HumanEval audits stay isolated
because their response envelope or reasoning structure is itself the signal.

### Math — 39 to 31

Merged cases:

- four elementary counting questions → `math_combinatorics_bundle`
- F(60), F(80), F(90) modulo 1000 → `math_fibonacci_bundle`
- domino, doubling, and forbidden-substring recurrences → `math_recurrence_bundle`

These were the clearest within-method repetitions. All other number-theory,
combinatorics, dynamic-programming, modular, and exact-iteration problems remain
separate. Compound answers receive per-key credit plus format checks.

### Long context — 24 to 22 in the current configuration

The inventory is six single-needle position/depth cells, six hard cells
(`multineedle`, `distractor`, `needlemath` at two depths), and ten frontier
cells (`associative`, `variabletrace`, `policysynthesis`, `casefilesynthesis`,
`humanevalaudit` at two depths). The two saturated 65k plain-needle cells were
removed; harder 65k retrieval and synthesis shapes remain because they are not
redundant with their 32k/16k counterparts.

## Python-file audit

| file | runtime role | finding |
|---|---|---|
| `fleetbench.py` | runner plus tools/coding/reasoning/math/longctx | consolidations and dispatch cap applied |
| `fleetbench_agentic.py` | stateful agent environments | no merges; one low-yield round cap reduced |
| `fleetbench_applied.py` | closed-world applied tasks | 18→10 compound tasks |
| `fleetbench_compliance.py` | action-boundary tasks | retain balanced independent cases |
| `fleetbench_finance.py` | finance tasks | 24 cases emitted in 16 requests |
| `fleetbench_saturation_breakers.py` | standalone development/reference patch content | not imported by runner; zero benchmark runtime |
| `mock_server.py` | local protocol/scorer test server | not part of model sweep; no benchmark runtime |

## Verification and comparison caveat

Task IDs changed for consolidated cases. Old and new rows can coexist in the
append-only CSV, but they are different benchmark versions. The Python summary
and dashboard now exclude the explicit retired-ID set so resumed results are not
double-weighted. Use a new output directory or archive the old results anyway
when making a clean before/after timing claim.
