# FleetBench Applied Intelligence — benchmark card

## Purpose

Measure applied capabilities that broad aggregate leaderboards often expose but
that FleetBench previously did not report separately: structured data analysis,
language precision, scientific problem-solving, and epistemic calibration.

## Composition and scoring

The suite retains 18 original, closed-world synthetic cases: 6 data analysis,
4 language, 4 science, and 4 calibration. Related cases are emitted in 10
runtime requests. Each prompt requests an exact JSON schema. The grader checks
every requested field independently, awards equal partial credit by field,
rejects missing or extra keys, and uses a declared absolute tolerance for
numerical outputs where rounding is required. It never uses an LLM judge.

Tasks span `core`, `hard`, and `frontier` tiers. Category score is earned points
divided by attempted tasks. The report and dashboard also split results by the
four domains.

The optional `--profile compact` panel selects 5 of the 10 runtime requests
while retaining all four domains. The default full profile uses all 10.

## Provenance

All question text and ground truth are original FleetBench fixtures, version
1.1. They use method-level ideas from LiveBench (objective language and data
analysis), SciCode (scientific problems decomposed into checkable results), and
IFEval (programmatically verifiable constraints). No upstream benchmark item is
copied. Run `python3 fleetbench.py --applied-manifest` for the machine-readable
inventory.

## Limitations

- Closed-world tasks favor reproducibility over breadth of factual knowledge.
- Multilingual coverage is a precision probe, not a comprehensive multilingual
  benchmark.
- Scientific tasks are compact numerical/experimental exercises, not a
  substitute for full research-code evaluation in an isolated runtime.
- Calibration measures whether a model respects supplied evidence; it does not
  establish real-world factuality or confidence calibration.
- Public static prompts can eventually become contaminated. Version prompts and
  rotate fixtures before making long-lived leaderboard claims.

## Recommended reporting

Publish the FleetBench revision, task manifest, tier selection, model and
quantization, inference settings, per-domain scores, task-level CSV, and repeat
count. Do not present this category as an official LiveBench, SciCode, or IFEval
score.
