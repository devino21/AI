# Benchmark landscape review (2026-07-18)

## Sources reviewed

The supplied leaderboard and guide pages were used as discovery sources:
LiveBench, Artificial Analysis, BenchLM, IBM, Vellum, Evidently, Hugging Face's
Open LLM Leaderboard and benchmark collection, and Iternal. Method decisions
were then checked against primary benchmark documentation and repositories.

| Signal in current benchmark practice | Primary source | FleetBench decision |
|---|---|---|
| Frequently refreshed, broad, objectively graded language and data-analysis tasks | [LiveBench repository](https://github.com/LiveBench/LiveBench) | Add original closed-world data and language tasks; retain deterministic grading. Do not claim an official LiveBench score. |
| Real research problems decomposed into scientific subproblems with tests | [SciCode repository](https://github.com/scicode-bench/SciCode) and [paper](https://arxiv.org/abs/2407.13168) | Add compact scientific calculations and experimental reasoning with independently checked fields. A future containerized track could add full scientific code. |
| Programmatically verifiable instruction constraints | [Google IFEval code](https://github.com/google-research/google-research/tree/master/instruction_following_eval) and [paper](https://arxiv.org/abs/2311.07911) | Require exact schemas and constraints, avoiding judge-model bias. Existing FleetBench instruction tasks already cover much of this family. |
| Narrative multi-step soft reasoning | [MuSR project](https://zayne-sprague.github.io/MuSR/) | Existing FleetBench frontier reasoning already has ledgers, truth networks, object tracking, and ZebraLogic-style narratives; do not duplicate it in this addition. |
| Agent, coding, science, and general capability should not be collapsed into one opaque score | [Artificial Analysis methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking) | Preserve separate Agentic, Applied, Coding, Reasoning, and other columns plus task-level evidence. |
| Benchmark evidence needs freshness, version, cadence, saturation, and provenance context | [BenchLM methodology](https://benchlm.ai/methodology) | Add a versioned manifest and benchmark card; recommend revision and repeat-count reporting. Static public prompts remain a documented limitation. |
| IFEval, BBH, MATH L5, GPQA, MuSR, and MMLU-Pro are complementary families | [Open LLM Leaderboard documentation](https://huggingface.co/docs/leaderboards/open_llm_leaderboard/about) | Avoid importing exam questions or mixing incomparable upstream raw scores. FleetBench already covers exact math, instruction following, and symbolic reasoning; add the practical gaps instead. |

## Implemented gap

`fleetbench_applied.py` retains 18 original cases across four domains, emitted
in 10 runtime requests:

- data analysis: 6;
- language precision and multilingual extraction: 4;
- scientific reasoning: 4;
- epistemic calibration and false-premise handling: 4.

All ground truth is derivable from the prompt. The grader requires the exact
requested JSON key set and awards equal component credit. Numeric tolerances are
explicit per task. This makes results reproducible and auditable without an LLM
judge, while avoiding reuse or leakage of upstream benchmark questions.

## Deferred candidates

- Full SWE-bench, Terminal-Bench, OSWorld, and SciCode-style tracks require
  isolated repositories/containers, larger runtime budgets, and dataset/license
  management. They should be separate harness modes rather than lightweight chat
  tasks.
- Broad factual or professional-exam suites require contamination controls and
  dataset versioning. Closed-world calibration probes were chosen for this pass.
- A real multilingual suite needs native-speaker validation across languages;
  the included multilingual task is intentionally only an evidence-extraction
  probe.
- Fresh rotating question generation would improve contamination resistance but
  needs a signed fixture-release process so scores remain comparable.
