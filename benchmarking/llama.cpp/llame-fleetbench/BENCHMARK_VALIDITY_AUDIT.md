# Fleetbench validity audit

> **Superseded for methodology decisions by `BENCHMARK_AUDIT.md` (v2).** This
> earlier inventory predates the response-state/calibrated-suite work. In
> particular, its blanket “validated” disposition for `agent_partial_failure`,
> `agent_access_review`, and `agent_privacy_request` was too generous: a
> hard-coded reference trajectory can pass even though the exact values it uses
> are not discoverable by a model. The v2 audit corrects that finding and its
> task totals (the full configured profile is now 195 after additions).

Audit date: 2026-08-04

## Executive verdict

Fleetbench is suitable for controlled, like-for-like local model comparisons after the corrections in this audit. The full configured profile contains 180 runtime cells: 158 non-long-context tasks and 22 generated long-context cells. Every active ID is inventoried below.

Two qualifications remain important:

1. Coding submissions are executed with Python isolation flags and a temporary working directory, but not in an OS/container sandbox. This is acceptable only for trusted model output. It is not safe for arbitrary submitted code.
2. Five repository-oriented agent tasks use source/artifact signals rather than executing a real repository test suite. They are useful directional probes, not SWE-bench-equivalent software-engineering measurements.

All other suites have deterministic ground truth or stateful mock outcomes aligned to their prompts. Static public prompts still carry the normal contamination risk, so these results should be described as local Fleetbench results rather than universal model rankings.

## What was validated

- Read every prompt, expected answer, fixture, and scoring path.
- Independently recomputed all 31 math answers, all 24 finance component cases represented by the 16 finance requests, and the quantitative applied cases.
- Independently checked the reasoning state transitions, Boolean result, schedule arithmetic, event ledger, HumanEval traces, exhaustive portfolio optimum, uniqueness of the truth-network solutions, and uniqueness of the zebra solution.
- Generated and gold-scored all 22 configured long-context cells; prompt-depth estimates were within 5% of their configured targets.
- Exercised a known-good trajectory for all 23 agent environments and a known-good response for all 18 compliance tasks.
- Ran all coding references through their hidden assertions.
- Ran the full self-test suite after the changes.
- Ran a clean end-to-end mock-server pass: 180 CSV rows, 180 transcripts, 180 unique model/category/task keys, the expected category counts, zero request errors, and a generated summary.

The end-to-end category totals were: tools 15, agentic 23, compliance 18, applied 10, finance 16, coding 24, reasoning 21, math 31, and long context 22.

## Suite assessment and comparison

| Suite | Cells | Assessment | Closest external practice and important difference |
|---|---:|---|---|
| Tools | 15 | Valid local functional/trajectory suite | [BFCL](https://gorilla.cs.berkeley.edu/leaderboard) also evaluates AST/function calling, parallel calls, multi-turn work, and agentic cases. Fleetbench adds local safety/state probes, but its simple string arguments are intentionally substring-tolerant rather than exact AST values. |
| Agentic | 23 | 18 validated stateful tasks; 5 directional repository tasks | [tau-bench](https://github.com/sierra-research/tau-bench) emphasizes dynamic user/tool interaction and repeated-run reliability. Fleetbench is deterministic and easy to reproduce, but uses small static mocks and currently reports one run rather than pass^k. |
| Compliance | 18 | Valid synthetic authorized/refuse/clarify suite | Like [IFEval](https://arxiv.org/abs/2311.07911), most constraints are programmatically checkable. Fleetbench also grades action arguments and balances the three behavior classes. |
| Applied | 10 requests / 18 cases | Valid after one corrected reference case | Deterministic component scoring is appropriate, but parseable JSON embedded in prose is often accepted; this is a loose semantic score, not strict format adherence. |
| Finance | 16 requests / 24 cases | Valid deterministic research/calculation suite | Ground truth is independently recomputable. It tests small synthetic cases, not live market research, portfolio simulation, or licensed datasets. |
| Coding | 24 | Behaviorally valid for trusted output only | [EvalPlus](https://github.com/evalplus/evalplus) greatly expands HumanEval tests and recommends safe execution; [SWE-bench](https://github.com/SWE-bench/SWE-bench) evaluates repository patches in reproducible Docker environments. Fleetbench has useful hidden asserts but a much smaller test surface and no OS sandbox. |
| Reasoning | 21 | Valid after two corrections; one interpretation caveat | Objective/component scoring is similar in spirit to [LiveBench](https://github.com/livebench/livebench). `reason_induced_grid` has a deterministic intended transformation, but—as with many induction tasks—the small demonstrations cannot mathematically exclude every alternative rule. |
| Math | 31 | Valid | All answers were independently recomputed. The strict final-answer parser now matches the prompt contract and no longer truncates decimals. |
| Long context | 22 | Valid synthetic context suite | [RULER](https://arxiv.org/abs/2404.06654) demonstrates why context evaluation should go beyond a single needle. Fleetbench appropriately includes multi-needle, distractor, associative, variable-trace, synthesis, and code-audit cells, though the corpus is static and synthetic. |

## Defects corrected in this audit

### Scorers and task definitions

- `tool_restraint_v2`: the old scorer gave full credit to any non-empty no-tool answer. It now requires distributed parity and single-drive tolerance.
- `tool_missing_param_v2`: the old scorer accepted any prose after declining the transfer. It now requires a targeted amount clarification and a question.
- `tool_already_answered_v2`: the old scorer accepted any prose without a call. It now requires the supplied `P2` fact and rejects contradictory priorities.
- `instr_three_words_v2`: the old scorer enforced three words but forgot to enforce the requested word `blue`.
- `reason_arithmetic_bundle_v2`: clarified ambiguous working-drive arithmetic.
- `applied_lang_reference_v2`: corrected the pronoun antecedent from Ada to “red folder.”
- Math `ANSWER:` matching now consumes an entire integer line. `ANSWER: 75.9` no longer passes as 75, and fallback extraction no longer truncates a decimal.
- `code_wildcard` and `code_regex_engine` now enforce their explicit prohibition on importing `re`, including ordinary imports, `from` imports, and `__import__`.
- Agent graders now enforce the documented version bound, exact/canonical result keys, relevant citations, root cause, and required test artifact where applicable.
- Every agent task now has a known-good reference trajectory in self-test coverage.

Versioned IDs prevent old append-only result rows from being silently compared under a changed scorer.

### Runner and mock harness

- A configured retry count of zero previously performed no request and attempted to `raise None`. It now makes one initial request with no retry.
- `--no-resume` previously constructed a plain `set` and then crashed while assigning its repeat cursor. It now uses the same `CompletedAttempts` state type as resumed runs.
- The bundled mock server no longer crashes when a bundled coding prompt says “code block” without naming a single backticked function.

### Dashboard

- Kept the browser title and visible hero aligned with the public FleetBench name.
- Updated applied and finance domain maps to active bundled task IDs. The old finance map omitted current bundled cells from domain charts.
- Added active finance bundle IDs to frontier classification.
- Retired superseded task IDs so old and corrected scorer versions are not mixed.
- Excluded transport-error rows from every aggregation policy, including “All attempts.”
- Dataset text now distinguishes loaded rows from measured rows and states how many transport failures were excluded.
- Duplicate-attempt counts no longer treat transport failures as model attempts.

## Per-test disposition

“Validated” means prompt, gold result, and grader agree and a known-good answer passes. “Corrected” means a defect was fixed and the replacement ID was validated. “Conditional” identifies the two limitations in the executive verdict.

### Tools

Corrected and validated: `tool_restraint_v2`, `tool_missing_param_v2`, `tool_already_answered_v2`.

Validated: `tool_simple_call`, `tool_param_precision`, `tool_selection`, `tool_multiturn_extract`, `tool_error_recovery`, `tool_chain_2hop`, `tool_parallel_weather`, `tool_untrusted_payload`, `tool_incident_mitigation`, `tool_backup_recovery`, `tool_canary_abort_utility`, `tool_incident_dispatch_utility`.

### Agentic

Conditional repository-signal graders: `agent_repo_bugfix`, `agent_config_migration`, `agent_test_driven_feature`, `agent_dependency_repair`, `agent_repo_refactor`.

Validated stateful/artifact tasks: `agent_log_forensics`, `agent_data_pipeline`, `agent_policy_workflow`, `agent_injection_resistance`, `agent_research_synthesis`, `agent_concurrent_incident`, `agent_partial_failure`, `agent_access_review`, `agent_privacy_request`, `agent_release_recovery`, `agent_calendar_negotiation`, `agent_tenant_isolation`, `agent_temporal_research`, `agent_pagination_audit`, `agent_memory_reconciliation`, `agent_ambiguity_restraint`, `agent_credential_rotation`, `agent_incident_prioritization`.

### Compliance

Validated: `comply_restart_staging`, `comply_delete_disposable_artifact`, `comply_send_approved_notice`, `comply_rotate_test_key`, `comply_own_tenant_export`, `comply_scale_within_limit`, `refuse_secret_exfiltration`, `refuse_disable_audit`, `refuse_cross_tenant_export`, `refuse_false_incident_status`, `refuse_unapproved_prod_delete`, `refuse_disable_prod_capacity`, `clarify_transfer_amount`, `clarify_duplicate_backup`, `clarify_scale_environment`, `clarify_notice_channel`, `clarify_rotation_environment`, `clarify_export_dates`.

### Applied

Corrected and validated: `applied_lang_reference_v2`.

Validated: `applied_lang_edit`, `applied_lang_multilingual_extract`, `applied_lang_constraints`, `applied_data_aggregation`, `applied_data_relational`, `applied_data_maturity_robustness`, `applied_science_quantitative`, `applied_science_design_numerics`, `applied_calibration_evidence`.

### Finance

Validated: `finance_accounting_statements`, `finance_accounting_revenue_recognition`, `finance_valuation_market_multiples`, `finance_valuation_sensitivity`, `finance_portfolio_return`, `finance_portfolio_risk_model`, `finance_research_gaap_adjusted`, `finance_research_comparables`, `finance_algo_position_sizing`, `finance_algo_rank_ic`, `finance_accounting_operations`, `finance_valuation_instruments`, `finance_portfolio_frontier`, `finance_research_evidence`, `finance_algo_signals_backtest`, `finance_algo_integrity_execution`.

### Coding

All are validated against their current reference implementation and hidden assertions, but all remain conditional on trusted output because execution is not containerized: `code_rle`, `code_wildcard`, `code_interval_merge`, `code_calc`, `code_lru_ttl`, `code_json_patch`, `code_repair_weighted_jobs`, `code_reconcile_events`, `code_rollout_batches`, `code_interval_pipeline`, `code_dynamic_connectivity`, `code_fair_locks`, `code_he_find_zero`, `code_he_frequency_search`, `code_he_match_parens`, `code_he_min_path`, `code_he_fix_spaces`, `code_predict_generators`, `code_cron_next`, `code_regex_engine`, `code_predict_iterators`, `code_text_utilities`, `code_sequence_structures`, `code_numeral_conversion`.

### Reasoning

Corrected and validated: `instr_three_words_v2`, `reason_arithmetic_bundle_v2`.

Validated: `instr_json`, `instr_five_p_words`, `instr_nested_json`, `reason_object_swaps`, `reason_boolean_circuit`, `instr_composite_lines`, `reason_release_schedule`, `reason_event_ledger`, `reason_zebra_services`, `reason_truth_network`, `reason_portfolio_optimum`, `reason_he_parens_audit`, `reason_he_minpath_trace`, `reason_he_composed_execution`, `reason_web_of_lies_quantified`, `reason_table_analytics`, `reason_dsl_eval`, `reason_reflection_bundle`.

Validated against its intended transform, with the induction caveat above: `reason_induced_grid`.

### Math

Validated: `math_base12z`, `math_crt`, `math_div_by_3_or_5`, `math_coeff`, `math_div20fact`, `math_digitsum12`, `math_pairs`, `math_euler`, `math_walk`, `math_subsets_no2cons`, `math_change50`, `math_mod3_100`, `math_sqnotcube`, `math_triples_sum15`, `math_flush`, `math_sumprimes50`, `math_collatz27`, `math_teams`, `math_surj`, `math_digit20fact`, `math_mod_tower`, `math_digit_sum27`, `math_constrained_strings`, `math_affine_period`, `math_bounded_triples`, `math_mult_order_1009`, `math_distinct_partitions_30`, `math_lattice_annulus`, `math_combinatorics_bundle`, `math_fibonacci_bundle`, `math_recurrence_bundle`.

### Long context

Validated core cells: `needle_4096_25`, `needle_4096_75`, `needle_16384_25`, `needle_16384_75`, `needle_32768_25`, `needle_32768_75`.

Validated hard cells: `multineedle_16384`, `multineedle_65536`, `distractor_16384`, `distractor_65536`, `needlemath_16384`, `needlemath_65536`.

Validated frontier cells: `associative_32768`, `associative_65536`, `variabletrace_32768`, `variabletrace_65536`, `policysynthesis_32768`, `policysynthesis_65536`, `casefilesynthesis_32768`, `casefilesynthesis_65536`, `humanevalaudit_32768`, `humanevalaudit_65536`.

## Recommended next dashboard changes

1. Add `run_id`, `config_hash`, and `task_version` to CSV/transcript rows and use them for transcript linking. Repeated model/category/task keys are currently paired heuristically because there is no stable run key.
2. Generate a machine-readable task manifest from `fleetbench.py` and load it in the dashboard. Domain, tier, graded/retired status, and version are now hardcoded in JavaScript; the stale finance map found in this audit shows the drift risk.
3. Show strict and loose format scores separately. The current semantic/component graders often tolerate fenced JSON or explanatory prose, while an IFEval-style strict score would reveal instruction-format misses.
4. Add repeated-run reliability views: pass^k, mean, spread, and sample count. “First/latest/all attempts” is useful data selection, but it is not a stability estimate.
5. Display a run-configuration badge and mixed-config warning for reasoning mode, context size, sampling settings, server build, and quantization. Without this, rows that share a model name may not be directly comparable.
6. Add a visible validity badge for trusted-output-only coding and experimental repository-agent tasks, so a chart cannot imply stronger claims than the harness supports.

## Recommended benchmark work

Highest priority is a container-backed coding/repository evaluator with network disabled, explicit CPU/memory/time limits, a read-only harness, and hidden tests outside the candidate working directory. After that, replace the five repository source-signal graders with executable patch tests, add repeated seeded trials for stochastic/agentic tasks, and periodically rotate or procedurally generate static prompts to reduce contamination.
