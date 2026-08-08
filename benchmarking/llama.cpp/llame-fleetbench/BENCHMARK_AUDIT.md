# Fleetbench methodology audit

Audit date: 2026-08-04  
Benchmark implementation: `2.0.0`  
Recommended suite: `fleetbench-calibrated-v2`

## Executive finding

The public model rankings were treated only as prompts for investigation. No
score was curved, no expected model ordering was encoded, and no weight was
changed to manufacture agreement with a public leaderboard.

The old compact panel has two distinct problems:

1. Five tasks per category give very coarse resolution. One binary miss moves a
   category by 20 points, and several categories saturate.
2. Three of its five agentic fixtures require exact values that the prompt,
   records, and capability schema do not disclose. They are not valid primary
   quality measurements.

The calibrated profile preserves and still runs all 45 historical cells, adds
30 harder requests, and produces a 72-task primary score with exactly eight
valid tasks per category. The three invalid legacy cells remain identifiable
and continue to contribute only to the legacy 45 score; discoverable-schema v2
replacements contribute to the new score.

## What was traced

Before task changes, the audit followed each path from request to display:

`task definition → prompt/request parameters → OpenAI-compatible response →
normalization → category scorer/environment grader → CSV/transcript → category
mean → suite/frontier aggregation → dashboard`

It also inspected every non-perfect result for these six result sets in
`results-compact-5x9`: `dsv4f-0731`, `deepseek-v4f`, `glm-5.2`,
`qwen3.6-27b-mtp-q8`, `qwen3.6-35b-a3b-mtp-q8`, and
`qwythos-9b-v2-mtp`.

## Audit of the original 45 cells

The exhaustive full profile now contains 195 requests. The pre-v2 180-task
definition-by-definition inventory remains in `BENCHMARK_VALIDITY_AUDIT.md`;
this audit corrects its three over-generous agentic dispositions above. The 15
new definitions (three replacement agents, three compliance workflows, three
applied, three coding, and three math) all have independently constructed
reference answers/trajectories that pass. Existing full-only tasks and ground
truths were left unchanged. The five source-signal repository agent graders
remain directional rather than SWE-bench-equivalent, and all candidate-code
execution remains trusted-output-only because it is not containerized.

| category | original compact cells | disposition |
|---|---|---|
| Tools | `tool_already_answered_v2`, `tool_canary_abort_utility`, `tool_parallel_weather`, `tool_param_precision`, `tool_untrusted_payload` | Validators are deterministic and valid, but the panel primarily measures call selection, schema/JSON precision, restraint, and one rollout trajectory. It is not broad evidence of real-world agent success. Retained for legacy and primary v2; three stateful task-success cells were added. |
| Agentic | `agent_access_review`, `agent_credential_rotation`, `agent_injection_resistance`, `agent_partial_failure`, `agent_privacy_request` | Credential rotation and injection resistance are valid. Access review, partial failure, and privacy request contain undisclosed exact simulator values; retained only for legacy continuity and replaced in primary v2. |
| Action compliance | `clarify_duplicate_backup`, `comply_own_tenant_export`, `comply_rotate_test_key`, `refuse_secret_exfiltration`, `refuse_unapproved_prod_delete` | Valid deterministic boundary probes, but mostly single-turn protocol decisions and too easy to saturate. Retained; three state-graded workflows add ordering, failed-gate recovery, approval, and final verification. |
| Applied | `applied_calibration_evidence`, `applied_data_maturity_robustness`, `applied_data_relational`, `applied_lang_constraints`, `applied_science_design_numerics` | Valid closed-world component graders. They expose genuine structured-answer errors in the supplied runs, but five cells make one formatting/content miss too influential. Retained; event reconciliation, sensor fusion, and effective-authority tasks added. |
| Finance | `finance_accounting_statements`, `finance_algo_integrity_execution`, `finance_portfolio_frontier`, `finance_research_evidence`, `finance_valuation_instruments` | Valid component scoring, but the algorithm-integrity task is long enough to expose output-budget artifacts and the small panel saturates. Retained; three shorter objective accounting, valuation, and backtest calculations added. |
| Coding | `code_calc`, `code_dynamic_connectivity`, `code_he_min_path`, `code_predict_iterators`, `code_regex_engine` | Execution grading is valid. The set mixes small synthesis/tracing with only two difficult algorithms and has no real multi-file interface-preservation work. Retained; three novel multi-file repair tasks with hidden execution tests added. |
| Reasoning | `instr_composite_lines`, `reason_he_minpath_trace`, `reason_portfolio_optimum`, `reason_table_analytics`, `reason_web_of_lies_quantified` | Objective component validators are valid. `reason_portfolio_optimum` exposed response truncation in GLM, not a judge error. Retained; release scheduling, truth-network, and DSL execution cells added. |
| Math | `math_bounded_triples`, `math_combinatorics_bundle`, `math_constrained_strings`, `math_mod_tower`, `math_recurrence_bundle` | Exact/component ground truths were independently self-tested. The observed 80% cluster is the direct consequence of one miss among five. Retained; three seeded probability/constraint/algebra variants added. |
| Long context | `distractor_65536`, `humanevalaudit_32768`, `multineedle_16384`, `needle_4096_25`, `policysynthesis_32768` | Validators are deterministic, but the category is saturated and legacy fixture text varies by model alias. Retained unchanged for historical continuity. New 32k fixtures use one suite seed for every model and test associative retrieval, variable tracing, and cross-record synthesis. |

### The three invalid legacy agent fixtures

- `agent_partial_failure`: the natural/schema-consistent call is
  `target="S-52", parameters.region=<region>`. The legacy simulator silently
  interprets generic `target` as the region and ignores `parameters.region`.
  Several models completed the intended operations but wrote state under the
  wrong hidden key.
- `agent_access_review`: the environment requires the exact role token
  `billing-read`, but neither records nor capabilities enumerate that value.
  One strong run brute-forced plausible strings until it happened to find the
  hidden enum, which is not the capability being measured.
- `agent_privacy_request`: closing requires the exact status
  `partially_completed_legal_hold`, but the legacy capability exposes only a
  generic `status` parameter. Models can erase and verify correctly yet remain
  unable to complete the hidden ledger transition.

The v2 replacements enumerate target constraints, required parameters, scopes,
roles, and canonical statuses through `get_capabilities`. Their reference
trajectories are self-tested.

## Findings in the six supplied runs

- `dsv4f-0731` Finance=80 is entirely explained by
  `finance_algo_integrity_execution`: `finish_reason=length` at the configured
  8192-token pool, with 17,034 reasoning characters and no final JSON. It is now
  recorded as `truncated`, not as an ordinary finance zero.
- `glm-5.2` Reasoning=80 is entirely
  `reason_portfolio_optimum`: the response reached the 12,288-token limit before
  emitting a valid final JSON object. It is also a truncation state. GLM's math
  miss (`144256` versus independently verified `144320`) stopped normally and
  remains a genuine wrong answer.
- Old `deepseek-v4f`'s math miss ended at the length limit. Qwen/Qwythos/GLM
  constrained-string misses stopped normally with wrong values, so they remain
  quality failures.
- The Qwen 27B/35B-A3B Coding inversion was not caused by score parsing. The 27B
  submission passed 0/5 dynamic-connectivity tests; the 35B-A3B submission
  passed 22/24 regex tests. The old five-cell category magnifies that real local
  task difference. The new repo tasks improve resolution without encoding a
  preferred ordering.
- Qwythos Tools=96 consists of four perfect protocol/restraint cells plus 0.78
  on the canary workflow. That score was being described too broadly. V2 labels
  tool cells as `tool_protocol` or `tool_task_success` and reports the two
  dimensions separately.
- Qwen35 Applied=45 came from normally terminated, component-graded structured
  responses (including 0/1 on language constraints and partial data/science
  answers), not transport or parser failures.
- No selected latest result among the six showed a server/network/model-load or
  context-overflow failure. Historical response fields and tool-call objects
  were parseable, but the old harness could not have distinguished such a
  failure if one occurred; it wrote request failures as ordinary zero rows or
  omitted them from the dashboard.

## Response normalization and result states

The normalizer now accepts the supported shapes used by common
OpenAI-compatible servers:

- string or text-part `message.content`;
- `reasoning_content` or `reasoning`, retained separately;
- `message.tool_calls`, choice-level/top-level tool calls, flattened compatible
  calls, and legacy `message.function_call`;
- argument objects or JSON argument strings, with diagnostics for malformed
  calls;
- legacy completion-shaped `choice.text`.

Reasoning is never merged into the answer that a task grader sees. A
reasoning-only response is identified, but chain-of-thought itself earns no
credit.

Saved states are:

| state | meaning | primary quality score? |
|---|---|---|
| `pass`, `partial`, `fail` | completed model output judged by the task | yes |
| `timeout` | serving/request deadline | no; counted and retried on resume |
| `truncated` | output pool exhausted (`finish_reason=length` or token limit) | no; counted and retried |
| `parse_error` | incompatible/malformed API envelope or request-template rejection | no; counted and retried |
| `infra_error` | network/server/model-load failure | no; counted and retried |
| `context_overflow` | endpoint rejected the prompt for context length | no; counted and retried |

Malformed JSON/code/tool arguments *produced by a normally completed model* are
quality failures, not harness parse errors. Candidate code that does not
terminate is a quality `fail` with `candidate_execution_timeout`; it remains in
the score and is separately countable as a timeout. This prevents a hanging
submission from evading quality scoring while keeping serving speed separate.

The legacy 45 score intentionally retains historical numeric semantics,
including a numeric zero from a completed but truncated legacy response. The
complete v2 score uses the state-aware interpretation above.

## Calibrated v2 task layer

The profile runs 75 requests:

- 45 original compact requests (unaltered IDs and historical score scope);
- 30 additional requests;
- 72 valid complete-score cells, exactly 8/category;
- 45 legacy-core cells, exactly 5/category;
- 27 fixed frontier cells, exactly 3/category.

Additions are original deterministic fixtures, not copied public questions.
The design follows the methodology separation in [BFCL](https://gorilla.cs.berkeley.edu/leaderboard)
between protocol/function execution and multi-turn/agentic success, the
repository execution principle used by [SWE-bench](https://github.com/SWE-bench/SWE-bench),
and seeded multi-key/aggregation context testing described by
[NVIDIA RULER](https://github.com/NVIDIA/RULER) and its
[paper](https://arxiv.org/abs/2404.06654).

The three coding additions materialize an ephemeral repository and run hidden
assertions under isolated Python import settings. They test a nested timeout
configuration migration, a TTL/`None` cache regression, and a keyword-only API
migration across protocol/implementation/caller files. They constrain the file
set so rewriting unrelated files cannot pass. This is process isolation, not a
security sandbox; benchmark only models/endpoints you trust.

Math variants are derived deterministically from benchmark seed and task ID.
Long-context calibration fixtures use a stable suite seed across model aliases,
stay at practical 32k target depth, are skipped above 75% of configured context
to reserve template/answer headroom, and save the server-reported actual prompt
token count when available.

## Scoring and uncertainty

For complete v2, category `c` is the mean of its eligible task scores:

`category_c = mean(task scores in c)`

The suite score gives every selected category equal weight:

`suite = mean(category_1, …, category_9)`

This is not a speed-adjusted score. Throughput and runtime remain independent
metrics.

Category intervals use a nonparametric percentile bootstrap over task scores.
The suite interval resamples tasks within each category and recomputes the
macro-average, preserving category weight. These intervals quantify finite
local task-sample uncertainty, not decoding/run-to-run variance. The dashboard
marks adjacent suite intervals that overlap with `≈`; such orderings should be
treated as unresolved by this suite.

## Stable frontier definition

Frontier membership is declared in `task_manifest.json`, never inferred from
which models happened to fail. The 27 v2 tasks are:

- Tools: `tool_backup_recovery`, `tool_incident_dispatch_utility`, `tool_incident_mitigation`
- Agentic: `agent_concurrent_incident`, `agent_privacy_request_v2`, `agent_release_recovery`
- Compliance: `compliance_workflow_approved_delete`, `compliance_workflow_failed_change`, `compliance_workflow_ordered_rollout`
- Applied: `applied_authority_timeline`, `applied_event_reconciliation`, `applied_sensor_fusion`
- Finance: `finance_accounting_revenue_recognition`, `finance_algo_signals_backtest`, `finance_valuation_sensitivity`
- Coding: `code_repo_interface_migration`, `code_repo_timeout_migration`, `code_repo_ttl_regression`
- Reasoning: `reason_dsl_eval`, `reason_release_schedule`, `reason_truth_network`
- Math: `math_calibrated_algebra`, `math_calibrated_constraints`, `math_calibrated_probability`
- Long context: `associative_32768`, `casefilesynthesis_32768`, `variabletrace_32768`

Each category contributes exactly three cells, preventing a large/easy category
from dominating frontier. The subset emphasizes dependent actions,
verification, multi-component execution, or difficult deterministic synthesis.

## Versioning, metadata, and migration

New files save benchmark/suite/task version, task-set hash, run/replicate IDs,
model alias and available actual model/file/quantization, reasoning mode,
context, sampling parameters, output limit, server version, per-task prompt and
generation throughput, wall time, and run runtime. Populate optional
`model_id`, `model_file`, `quantization`, and `reasoning_mode` keys in
`fleetbench.yaml` when the endpoint cannot report them.

Historical result directories are untouched. Their rows remain identifiable as
legacy/unversioned when loaded. New calibrated output defaults to
`results-calibrated-v2/`; do not append it to a legacy CSV. The dashboard has a
suite-version selector and never combines versions in one sortable table.

No data migration is required. To produce the new comparison, run into the new
default directory. `task_manifest.json` and `run_manifest.jsonl` are created
automatically.

## Validation performed

- all built-in scorer/environment self-tests;
- dedicated unit tests for response normalization, typed failures, resume
  behavior, bootstrap intervals, version isolation, calibrated counts, seeded
  math, and all repository reference patches;
- Python compilation and dashboard JavaScript syntax check;
- a local mock-server smoke run only (no multi-hour real-model sweep).

The exact all-configured-model command is:

```bash
python3 -u fleetbench.py --config fleetbench.yaml --profile calibrated --no-resume
```

Omit `--no-resume` when continuing an interrupted calibrated run.
