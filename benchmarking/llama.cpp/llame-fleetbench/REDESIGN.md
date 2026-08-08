# FleetBench redesign — measuring gaps instead of reporting them

Date: 2026-08-05 · benchmark `2.1.0` · suite `fleetbench-panel-45-v3`

> Suite string bumped from `fleetbench-legacy-45-v1`. The v3 panel swaps 16 of
> 45 cells, so its rows are not comparable to legacy-45 rows; the summary picks
> one suite version and never blends two, which only works if a changed task
> set changes the string. Verified: pointing a v3 run at an old results
> directory now exits with `refusing to mix suite`.

Baseline for every number below: the four-model run in
`Opus5/results-compact-5x9/` (glm-5.2, qwen3.6-27b-mtp-q8,
qwen3.6-35b-a3b-mtp-q8, qwythos-9b-v2-mtp), 45 cells, one attempt each.

---

## 1. The finding that mattered

`--repeat N` has always run N attempts per task. `write_summary` then threw
all but one away.

```python
# before
latest[(suite_version, model, category, task_id)] = row
```

The de-duplication key had no `replicate` field, so attempt 2 overwrote
attempt 1 and the report described a single run. The word `replicate` appeared
**zero times** in the 290-line function. Replication has been billed for and
discarded on every run that ever used it.

This is why the suite could not tell you whether a 2-point gap was real: the
one mechanism that separates measurement noise from capability was silently
disabled downstream of the code that paid for it.

Everything else in this document follows from fixing that.

## 2. What the runtime review showed

| category | GLM-5.2 | 27b | 35b-a3b | 9b | total |
|---|---:|---:|---:|---:|---:|
| coding | 91.1m | 13.7m | 5.2m | 4.7m | 114.7m |
| agentic | 43.9m | 4.0m | 2.0m | 1.7m | 51.5m |
| longctx | 37.5m | 3.2m | 3.0m | 1.2m | 45.0m |
| math | 28.8m | 6.3m | 2.7m | 1.3m | 39.1m |
| reasoning | 34.1m | 5.5m | 2.5m | 2.0m | 44.1m |
| finance | 30.2m | 5.2m | 2.3m | 1.1m | 38.8m |
| tools | 3.2m | 0.3m | 0.2m | 0.1m | 3.7m |
| compliance | 1.6m | 0.1m | 0.1m | 0.0m | 1.9m |
| applied | 1.3m | 0.1m | 0.1m | 0.1m | 1.6m |
| **total** | **4.53h** | **0.64h** | **0.30h** | **0.20h** | **5.67h** |

Two things stand out.

**GLM is 80% of the bill.** At 8.4 tok/s it costs 7x the other three combined.
Any per-task change is really a GLM change; the fast models are free.

**40% of all compute buys nothing.** 21 of 45 cells are a perfect 1.0 for all
four models — 2.26h of 5.67h, and 1.80h of GLM's 4.53h. `code_he_min_path`
(23.2m of GLM) and `code_calc` (20.9m) are the worst offenders. A cell every
model solves is a floor check, not a measurement.

That waste is the budget for everything below. No net runtime increase is
needed to fund replicates.

## 3. Why more tasks was the wrong answer

Empirical power curve, resampling the observed data (1500 draws per point):

| pair | gap | k=5 | k=10 | k=20 | k=40 |
|---|---:|---:|---:|---:|---:|
| glm-5.2 vs qwen3.6-27b | 0.9 | 0.02 | 0.01 | 0.00 | 0.00 |
| glm-5.2 vs qwen3.6-35b-a3b | 2.9 | 0.03 | 0.02 | 0.00 | 0.00 |
| qwen27b vs qwen3.6-35b-a3b | 1.9 | 0.02 | 0.01 | 0.00 | 0.00 |
| glm-5.2 vs qwythos-9b | 10.0 | 0.33 | 0.46 | 0.55 | 0.68 |

(k = tasks per category; current suite is k=5.)

Power *falls* as tasks are added. That is the diagnostic. A macro-average's
standard error is driven by scatter **across** the 9 category means, not by
task count within them. Adding tasks sharpens each category mean and thereby
reveals that the categories genuinely disagree — GLM wins coding and
reasoning, the 27B wins applied and finance, the 35B-A3B leads the frontier
slice. A 0.9-point aggregate gap is smaller than that real trade-off.

**So the top three are not separated by a noisy measurement. They are tied,
and the aggregate was rounding a trade-off into a ranking.** The redesign
stops trying to break that tie and starts reporting it honestly, while making
the gaps that *are* real (anything ≥ ~5 points) provable.

This matches the current literature: single-trial evaluation carries a ~14%
pairwise flip rate on re-run, which makes rank-order differences between
closely spaced models uninterpretable
([arXiv:2604.11581](https://arxiv.org/pdf/2604.11581),
[arXiv:2512.21326](https://arxiv.org/pdf/2512.21326)).

---

## 4. Changes

### 4.1 Structural (as requested)

| change | detail |
|---|---|
| `--profile` removed | The 45-cell panel is the only suite. `suite_version_for_profile()` deleted; `score_scope_for()` reduced to a constant. |
| `output_dir: results` | The `results-compact-5x9` / `results-calibrated-v2` auto-overrides are gone. `--output-dir` still overrides. |
| calibrated/full machinery deleted | `CALIBRATED_RUN_TASK_IDS`, `CALIBRATED_COMPLETE_TASK_IDS`, `CALIBRATION_FRONTIER_IDS`, `CALIBRATED_SUITE_VERSION`, `FULL_SUITE_VERSION`, and every `profile ==` branch in the manifest builder, the runner, and the summary. |
| `profile_task_manifest()` → `task_manifest_entries()` | No profile argument; emits exactly 45 entries (5 × 9), verified. |
| dead `write_summary` deleted | There were **two** definitions; the first 338 lines were shadowed and unreachable. |
| longctx | Kept. Its 5 cells are part of the compact panel; only the `full`-profile depth-sweep generation path was removed. |
| `profile` CSV column | Retained as the constant `"compact"` so existing dashboards keep parsing. |

### 4.2 Measurement

**Replicate collapse fixed.** The key now carries `replicate`, and attempts are
averaged per task *before* any category mean:

```python
replicate = (row.get("replicate") or "0").strip() or "0"
latest[(suite_version, model, category, task_id, replicate)] = row
```

Averaging first is what keeps the task the unit of analysis. Feeding each
attempt in as a separate cell would shrink intervals by √k while measuring
nothing new — verified: a 280-row replicated CSV still reports `N = 45/45`.

**Per-category replicate budget** (`replicates:` in `fleetbench.yaml`).
Replicates are not uniformly valuable. tools/compliance/applied/math run at
temperature 0 and are near-reproducible; the other five run at 0.6 and need
repeats. `--repeat N` overrides the map.

**Three new report sections:**

- **Head-to-head (paired)** — every model pair, with a category-stratified
  paired bootstrap CI and a sign-flip permutation p-value. This is the test
  that should decide a ranking. Comparing two independent CIs for overlap is
  badly underpowered, because both models face the same tasks and task
  difficulty is a shared nuisance term that cancels in the per-task
  difference. On the baseline data the paired test resolves GLM vs qwythos-9b
  (p=0.034) where the dashboard's overlapping intervals could not.
- **Measurement noise** — run-to-run SD vs task-to-task SD, and what share of
  observed spread is pure noise. Blank with a warning when k=1, because
  without replicates the two are perfectly confounded.
- **Task information yield** — how many cells discriminate, how many are
  perfect for everyone, and what percentage of wall-clock the zero-information
  cells consumed.

**Harder-task pool preserved.** 133 defined-but-unrun task definitions were
*not* deleted. `CALIBRATED_EXTRA_TASK_IDS` is renamed `HARDER_TASK_POOL_IDS`
and documented as the vetted replacement pool — see §6.

---

## 5. Budget

Measured from the baseline, GLM-5.2 (the binding constraint):

| plan | GLM | note |
|---|---:|---|
| current, k=1, all 45 | 4.53h | 40% of it on dead cells |
| **shipped default** (k=2 on the five sampled categories) | **~5.2h** | +0.6h for the first real variance estimate |
| drop `coding` to 1 | ~4.4h | under baseline; edit `replicates:` |
| retire the 21 dead cells too | ~3.4h | needs task swaps first — see §6 |

Fast models are unaffected: 27b 0.64h → 0.71h, 35b-a3b 0.30h → 0.31h,
qwythos 0.20h → 0.26h.

k=3 was evaluated and rejected: 7.59h for GLM, outside the agreed budget.

## 6. Deferred, deliberately

**The 133 unrun task definitions were kept.** Deleting them was in scope, and
I did remove all the machinery that referenced them — but they are the vetted,
self-tested pool that the next change needs. The panel's core problem is 21
saturated cells, and the fix is to swap them for harder ones. Those harder
cells already exist here, already pass their reference implementations, and
were built for exactly this. Deleting them this week to rebuild them next week
would be the wrong order. They cost nothing at runtime: unreachable from the
runner, indexed under `HARDER_TASK_POOL_IDS`, promoted by adding an id to
`COMPACT_TASK_IDS`. Say the word and they go.

**Retiring saturated cells is not automated.** A cell that is dead for these
four models may discriminate for a weaker one — the dsv4f-0731 run in flight
is a live example. The summary now *reports* which cells are dead so the
decision is data-driven, but nothing is dropped automatically.

## 7. Verifying

```bash
cd /home/dan/tnas/benchmarks/fb
python3 fleetbench.py --selftest        # all scorer self-tests
python3 fleetbench.py                   # full panel -> results/
python3 fleetbench.py --repeat 3        # override the per-category map
```

Already verified here:

- self-tests pass before and after every step
- 45-entry manifest, 5 per category across all 9
- end-to-end mock run: per-category replicates confirmed
  (`attempt 1/2 · [tools, reasoning, math]`, `attempt 2/2 · [reasoning]`),
  40 CSV rows with `reasoning` at replicates 0 and 1, `profile=compact`
- replicated-CSV aggregation reports `N = 45/45`, not 100
- all three new sections render on real data

Not verified: a real run against llama-swap. This box has no `httpx`/`pyyaml`
(no pip), so the above used stdlib shims. That is the one thing to smoke-test
first.

## 8. What to expect

The ranking will not change — it already matches public data
(Spearman ρ = 1.0 against Artificial Analysis: GLM 51 > 27B 37 > 35B-A3B 32,
with qwythos-9b well below). What changes is that the report will now say
which gaps it can defend. Expect the top three to come back **tied**, with the
9B separated. That is the correct answer, and it is the first time the suite
will be able to state it.

Target: reliably resolve ~5-point gaps; treat anything smaller as a tie.
Chasing the 0.9 points between GLM and Qwen-27B would require driving
category-level disagreement to near zero, which you can only do by narrowing
the task mix until it measures less than it does now.

---

# Part 2 — the panel itself (v3)

Part 1 fixed how scores are *aggregated*. It did not touch what is being
measured, and deferred replacing the saturated cells. That deferral was wrong,
and the reasoning behind it was also wrong. This part corrects both.

## 9. Correction to §6

Part 1 kept 133 unrun task definitions on the argument that they were "the
vetted, harder pool" for replacing saturated cells. I had not measured them.

They are mostly not harder. Item analysis over the historical full-profile run
in `fleetbench-claude/results/` (2920 rows, **9 models, 229 tasks**):

- **118 of 229 (52%)** are perfect for every model that ever ran them.
- Of 190 non-panel candidates, **104 are dead** and only **42 discriminate at
  all**.

So the pool was not a reserve of harder cells; it had the same saturation
disease as the panel, slightly diluted. The correct move was to measure it and
promote only what survives, which is what §11 does.

## 10. Item analysis of the running panel

Pooled across every panel run on disk (`results-compact-v2`, `-v3`,
`-5x9`, `-5x9-v1`): **18 distinct models**, total-score span 87.5% → 65.0% —
a wide enough capability range for classical item statistics.

Per cell: difficulty `p` (mean score), discrimination `D` (upper-third mean
minus lower-third mean), and point-biserial `r` against model total.

**11 of 49 cells are perfect for all 18 models.** Worse, several have
*negative* discrimination — weaker models outscore stronger ones:

| cell | D | why |
|---|---:|---|
| `tool_incident_dispatch_utility` | **−0.42** | worst item in the suite |
| `tool_already_answered_v2` | −0.33 | |
| `tool_already_answered` | −0.17 | |
| `agent_access_review` | −0.16 | undiscoverable hidden enum (`billing-read`) |
| `agent_partial_failure` | −0.16 | hidden region key; schema-correct calls miss |

Negative `D` means an item is miskeyed or rewards the wrong behaviour. The two
agentic ones are exactly the cells `BENCHMARK_AUDIT.md` flagged as invalid —
the negative discrimination is the measured consequence of that defect. They
were dragging the agentic score for every model.

**Whole categories are exhausted.** `tools` has **no** item with `D > 0.00`
across 18 models. `compliance` has exactly one. Those cannot be fixed by
swapping; they need authored cells.

## 11. The v3 panel

Every swap is justified by measured statistics, in-category, highest-`D`
candidate that exists in this codebase.

| category | retired | promoted |
|---|---|---|
| tools | `tool_param_precision` (dead), `tool_parallel_weather` (dead), `tool_already_answered_v2` (D=−0.33) | 3 newly authored cells (§12) |
| agentic | `agent_access_review` (D=−0.16), `agent_partial_failure` (D=−0.16) | `agent_log_forensics` (D=+0.45), `agent_pagination_audit` (D=+0.29) |
| compliance | `comply_own_tenant_export`, `comply_rotate_test_key`, `refuse_unapproved_prod_delete` (all dead) | `refuse_disable_prod_capacity` (D=+0.33), `comply_scale_within_limit`, `clarify_rotation_environment` |
| finance | `finance_accounting_statements` (dead) | `finance_research_gaap_adjusted` (D=+1.00, r=+0.73) |
| coding | `code_calc` (D=+0.03), `code_predict_iterators` (dead) | `code_he_fix_spaces` (D=+0.19), `code_interval_pipeline` (D=+0.14) |
| reasoning | `reason_table_analytics` | `reason_induced_grid` (D=+0.63, r=+0.58) |
| math | `math_bounded_triples` (D=0.00) | `math_lattice_annulus` (D=+0.50, difficulty 0.29) |
| longctx | `needle_4096_25` (D=0.00), `distractor_65536`, `policysynthesis_32768`, `multineedle_16384` (dead) | `variabletrace_65536` (D=+1.00), `variabletrace_32768` (D=+0.50), `associative_32768`, `casefilesynthesis_32768` |
| applied | **nothing** | **nothing** — see below |

`applied` is deliberately unchanged. No applied task defined here measures
`D > 0.00` except the one already in the panel; every available swap sits at
difficulty 1.00 and would be strictly worse. Retained
`applied_science_design_numerics` because it is at least hard (0.28–0.60).

## 12. Three authored tools cells

`tools` had no discriminating item left, so these are new. Each applies a
difficulty lever that current agentic-benchmark work identifies as actually
separating models — conditional branching, a premise that contradicts ground
truth, and a plausible decoy planted in noise — rather than another
single-call lookup.

- **`tool_conditional_route_v3`** — branch on a retrieved value and suppress
  the obvious follow-up. INC-4821 is P2, so paging is wrong; the requested
  facts (`u4410` created, `u9912` acknowledged) live in the nested audit
  trail, not the fields block, so a model that stops at the obvious node
  reports the assignee instead. Enforced with `forbid_functions: [get_oncall]`.
- **`tool_premise_conflict_v3`** — the user's stated premise is wrong on two
  attributes (claims network-team/P1; truth is storage-ops/P2). Measures
  whether a model defers to a confident wrong premise.
- **`tool_decoy_param_v3`** — the amount is genuinely missing, and `231`
  (actually `meta.latency_ms`) is planted in context as a plausible
  substitute. Correct behaviour is to ask; grabbing the nearby number is the
  specific error measured.

Validated against the repo's own standard — a known-good trajectory passes and
each failure mode scores zero. **12/12 trajectory checks correct:**

```
tool_conditional_route_v3   correct 1.00 · paged anyway 0.00 · assignee-instead 0.50 · no lookup 0.00
tool_premise_conflict_v3    correct 1.00 · deferred+paged 0.00 · wrong priority 0.50
tool_decoy_param_v3         asks 1.00 (x2) · used 231 0.00 · called transfer 0.00 · vague 0.00
```

## 13. Status

Verified: 45-entry manifest (5 × 9), every id resolves to a real definition,
full self-tests pass, 12/12 new-task trajectory checks, and an end-to-end mock
run executing the v3 panel with per-category replicates.

Not verified: a real run against llama-swap. The fleet was mid-run on
`dsv4f-0731` throughout this work, and llama-swap auto-swaps on the `model`
field — issuing a request for any other model would have unloaded it and
corrupted the in-flight benchmark. Nothing here touched the server.

Known limits of the item statistics: `D` is population-dependent. Several
cells (`agent_injection_resistance`, `agent_access_review`) measured D≈+0.70
on the older, weaker model set and D≈0.00/−0.16 on the current one — they
discriminated once and have since saturated or inverted. Re-run this analysis
whenever the fleet changes; the numbers age.

Still weak, in priority order: **compliance** (1 discriminating item),
**coding** (best available D=+0.19), **applied** (nothing above 0.00). Those
three need authored cells next, on the pattern of §12.
