# agentbench/45

A manual, agent-driven mirror of fleetbench. 45 prompts across 9 categories,
each with a deterministic answer key, on a clickable matrix you fill in as
you go. Same task shape as fleetbench, same scoring axis — just run by an
agent hitting the endpoint one prompt at a time instead of by a backend
harness.

## Files

| File | Purpose |
| --- | --- |
| `agentbench.html` | The whole run sheet. Open in any browser; works offline. |
| `answer_key_verification.py` | Python script that generated every expected value on the run sheet. Re-run when you want to fork a task and need the answer for the new numbers. |
| `README.md` | This file. |

## Quick start

1. Open `agentbench.html`.
2. Fill in **model**, **quant + ctx**, **sampling**, **repetition** at the top of the scorecard.
3. Work down the task cards. For each one:
   - Copy the prompt (each snippet has a copy button; each category has a "copy all 5 prompts" button).
   - Send it to `llama-swap` at `192.168.68.11:8080` in a **fresh conversation**.
   - Compare the raw output against the **Answer Key** on the card.
   - Click the corresponding matrix cell to cycle unscored → pass → partial → fail. Or use the pass/partial/fail buttons on the card itself.
4. Export JSON, CSV, or a markdown row when you're done.

Nothing persists on reload — export before you close the tab.

## What's on the page

- **Scorecard** — 45-cell matrix with live category and suite percentages, plus a frontier-only breakout.
- **Protocol** — runner and grader contracts (copy-paste blocks) and a single-request `curl` example against llama-swap.
- **Method** — why the suite is built the way it is, with the public benchmarks each category tracks (BFCL, τ²-bench, IFEval, RULER, CRUXEval, FinanceReasoning, MisguidedAttention).
- **45 tasks** — each with the exact prompt, the answer key, auto-fail conditions, and a grader note.
- **Failure-pattern decoder** — seven rows separating instrumentation problems from actual capability gaps. Read this before concluding a model is bad at something.

## Category map

| Code | Category | What it measures |
| --- | --- | --- |
| T1–T5 | Tool calling | Selection, parallel calls, missing-arg refusal, multi-hop chains, abstention |
| A1–A5 | Agentic behaviour | Planning, error recovery, policy adherence, step budgets, ambiguity |
| C1–C5 | Action compliance | Format constraints, JSON discipline, acrostics, cross-turn carryover, precedence |
| P1–P5 | Applied ops | Log extraction, config diff RCA, KV cache math, procedure synthesis, table policies |
| F1–F5 | Finance | Amortisation, EAR, NPV/IRR, unit economics, FCF |
| K1–K5 | Coding | Bytes-vs-chars, bug repair, execution prediction, semver, stateful traces |
| R1–R5 | Reasoning | CRT trap, misguided attention, variable tracking, logic grid, truth network |
| M1–M5 | Math | Factorial valuation, cyclic colouring, tribonacci mod, Diophantine, multiplicative order |
| L1–L5 | Long context | Single needle, multi-key, multi-query, variable tracking, aggregation + recency |

Tier split: 15 **core** / 21 **hard** / 9 **frontier** (one frontier per category).

## Scoring

| Score | Means | Fleetbench equivalent |
| --- | --- | --- |
| 1.0 | Answer correct, format respected, no auto-fail | Full task point |
| 0.5 | Right substance, one stated format or scope rule broken | Partial credit |
| 0.0 | Wrong, absent, or auto-failed | No point |

Suite score is **points ÷ tasks attempted** — same denominator fleetbench
uses, so a manual 45 lands on the same axis as a scripted 45.

**Auto-fail overrides everything.** If a card lists an auto-fail condition
and the model triggers it, the score is 0.0 no matter how good the rest of
the answer looks. This is what keeps a polite refusal from scoring the same
as correct behaviour.

## Sampling discipline

The single most important thing across a fleet run: **hold sampling identical
across every model.** The runner contract specifies:

```
temperature 0.0, top_p 1.0, top_k 0, seed 1, max_tokens 8192
```

Some profiles override temperature server-side (thinking models sometimes do
this). Record which ones ignore your settings — those runs are not directly
comparable to the rest.

Three repetitions per model before you rank anything. Two models inside ~2
suite points of each other are the same model as far as this instrument
can measure.

## Verifying an answer key

If a result disagrees with what the run sheet claims, verify before assuming
the model is wrong:

```
python3 answer_key_verification.py
```

Prints a labelled table of every computed value: KV cache math, amortisation
figures, IRR, all math answers, the logic-grid solution, the truth-network
solution, CRUXEval trace outputs, and more. Uses only the standard library.

## Adding or modifying tasks

Every task lives in the `CATS` array inside the single `<script>` block near
the bottom of `agentbench.html`. Task shape:

```javascript
{
  id: "T6",
  tier: "core" | "hard" | "frontier",
  probes: "one-line summary of what this measures",
  prompt: `the exact prompt to send`,
  expected: ["bullet 1", "bullet 2"],       // rendered as the answer key
  autofail: ["condition 1", "condition 2"], // any of these = 0.0
  grade: "grader note — how to disambiguate 0.5 from 1.0"
}
```

Variants:

- **Multi-turn** — replace `prompt` with `turns: [{label: "turn 1 — send this", text: "..."}, ...]`.
- **System message** — add `system: "..."` before `prompt`.
- **Shared preamble** — add `pre: {title: "...", body: "..."}` to a whole category (like the tool inventory in `T`); tasks whose prompt starts with `[tool inventory above]` get it spliced in on copy.

Rules for a new task:

- Keep `id` unique across the whole suite; use the category letter plus a number.
- The answer key must be **deterministically checkable** — if you'd need to judge tone or plausibility, it doesn't belong here.
- Rerun `answer_key_verification.py` on any task where the numbers change.
- The matrix and category totals reconfigure automatically as long as `id` stays unique and `tier` is one of the three values.

## Known limits

- **n=5 per category.** One grader disagreement moves that category 20 points. This suite is better-instrumented than fleetbench, not more powerful statistically. If you want defensible rankings between close models, grow the categories to n=10 by cloning cards with new numbers.
- **Long-context haystacks are ~1000–2000 tokens.** Enough to test retrieval, distractor discrimination, tracking, and recency. Not enough to stress a 131K window. Paste a haystack multiple times if you want to push length; the needle depth stays proportional.
- **No LLM-judge fallback.** Everything is verified mechanically. Rubric grading exists only for the 0.5 / 1.0 boundary on tasks that ask for a specific format, and the rubric is spelled out on each card.
- **Runner and grader must be different agents.** Ideally different model families. The whole design assumes the grader has no idea which model produced what — if you use the same agent for both roles, the run degrades to a self-graded vibe check.

## What the deliverable is not

- Not a leaderboard. It's a run sheet.
- Not automatic. You (or an agent you drive) send every prompt.
- Not a replacement for `llama-bench` on throughput — record t/s alongside scores, don't try to derive them from these tasks.
- Not stable across seed changes if you regenerate the long-context haystacks. The needles are placed by fraction; a different seed reorders the filler around them. Answer keys still hold.
