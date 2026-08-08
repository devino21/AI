<img width="1122" height="1224" alt="Screenshot From 2026-08-08 14-23-00" src="https://github.com/user-attachments/assets/fad9058d-0653-4a90-be57-a2ea60d3c4cd" />


# Manual Model Benchmark Prompt Suite

A practical, manual benchmarking suite for testing local and hosted LLMs through real prompts rather than a backend benchmark runner.

The suite is designed for **agent-style and workflow-oriented evaluation**. Each test is self-contained: copy the prompt into the model or agent, let it respond normally, then reveal the expected result and compare.

No setup scripts, preprocessing, benchmark harness, or special runtime is required.

---

## Files

### Version 1 — Continuity Edition

**File:** `manual_model_benchmark_suite_continuity.html`

Version 1 focuses heavily on **continuity and state retention**.

Prompts commonly:

- Introduce requirements early.
- Change one assumption later.
- Preserve requirements that were *not* changed.
- Reject a previously proposed solution.
- Require calculations using the updated state.
- Require the model to reconcile information spread throughout the prompt.
- Test whether the agent remembers the actual objective after several intermediate details.

This version is particularly useful for testing models that will be used in coding agents, infrastructure agents, research workflows, and long-running conversations.

---

### Version 2 — Alternate Techniques

**File:** `manual_model_benchmark_suite_v2.html`

Version 2 uses a different set of stress techniques so that success on Version 1 does not automatically translate into success on Version 2.

Techniques include:

- Distractor-heavy context.
- Counterfactual reasoning.
- Conflicting evidence.
- Hidden dependency chains.
- Weighted-average and aggregation traps.
- State-machine reconstruction.
- Constraint propagation.
- Evidence ranking.
- Prompt-injection resistance.
- Tool-budget planning.
- Multi-agent delegation.
- Ambiguity handling.
- Self-audit requirements.
- Nested exceptions.
- Replanning after a preferred action becomes unavailable.
- Similar entity names intended to test state separation.

The two versions are intended to be complementary.

---

# Benchmark Categories

Both suites are organized around practical workflow categories rather than academic trivia.

Typical sections include:

- Reasoning
- Coding
- Finance
- Data Analysis
- Linux / Sysadmin
- Instruction Following
- Research / Synthesis
- Agent Planning
- Continuity / Long Context

The exact prompts differ between versions.

---

# How to Run a Test

1. Open the HTML file in a browser.
2. Choose a benchmark card.
3. Click **Copy Prompt**.
4. Paste the prompt into the model or agent you want to test.
5. Allow the model to complete the task normally.
6. Click **Reveal Expected Result** in the benchmark page.
7. Compare the model's response with the expected result.

Each prompt contains all information needed to complete the task.

There should be **no preprocessing, temporary files, shell setup, or external benchmark harness** required unless the prompt itself explicitly asks the agent to reason about such material.

---

# Recommended Testing Procedure

For useful comparisons, try to keep the test environment consistent between models.

Recommended controls:

- Use the same system prompt.
- Use the same agent harness when possible.
- Use the same tool permissions.
- Use the same temperature and sampling configuration.
- Start a fresh conversation for each independent benchmark unless the test specifically evaluates conversation continuity.
- Do not give one model hints that another model did not receive.
- Do not reveal the expected result until the model has completed its answer.

For local models, it can also be useful to record:

- Model name
- Quantization
- Context size
- llama.cpp or inference-engine build
- GPU configuration
- Tokens per second
- Time to first token

These values are optional and are **not required by the benchmark pages**.

---

# What Counts as a Good Result?

The expected result is intended as a **gold reference**, not necessarily a required word-for-word answer.

A strong response should generally:

- Reach the correct conclusion.
- Preserve all relevant constraints.
- Use the correct updated facts.
- Ignore irrelevant distractors.
- Perform calculations correctly.
- Avoid inventing missing information.
- Follow output-format requirements.
- Notice conflicts or ambiguity when they matter.
- Revise the plan when later information invalidates an earlier approach.
- Maintain entity and configuration state correctly.
- Explain important reasoning clearly enough to verify the result.

For coding or configuration tasks, equivalent implementations may be valid even when they differ from the reference answer.

---

# Expected Results

Each benchmark includes a hidden **Expected Result** section.

Use it to verify things such as:

- Required conclusions.
- Correct calculations.
- Required constraints.
- Important facts the model must retain.
- Facts the model must discard after a correction.
- Invalid approaches the model should reject.
- Required output structure.
- Key edge cases.

The expected result is deliberately more specific than a simple answer key because many of these tests evaluate **process consistency and state tracking**, not only the final sentence.

---

# Continuity Testing

Several tests are designed to expose a common weakness in local and smaller models: losing track of state as more information is introduced.

A continuity test may follow a pattern like:

1. Establish configuration A.
2. Introduce several unrelated details.
3. Change one part of configuration A.
4. Explicitly reject another proposed change.
5. Add a new requirement.
6. Ask for the final valid configuration.

A strong model should:

- Apply the accepted change.
- Preserve unchanged settings.
- Remove or ignore rejected changes.
- Incorporate the new requirement.
- Produce a final answer consistent with the entire prompt.

This is often more revealing for agent use than a standalone knowledge question.

---

# Testing Agents vs. Base Models

The same prompts can be useful for both.

## Base Model

Paste the prompt directly into the model.

This primarily measures:

- Reasoning
- Instruction following
- Context retention
- Calculation
- Coding knowledge
- Synthesis

## Agent

Run the prompt through the full agent harness.

This additionally tests:

- Planning
- Task decomposition
- Tool-selection judgment
- Recovery from failed assumptions
- Scope control
- Delegation
- Resistance to irrelevant or malicious embedded instructions
- Maintaining the user's objective across multiple steps

When comparing agents, remember that the result reflects **both the underlying model and the agent harness**.

## SAMPLE
<img width="2098" height="1147" alt="Screenshot From 2026-08-08 13-42-51" src="https://github.com/user-attachments/assets/286e1a57-3fc5-4c18-a820-d7366d0b98d0" />
---

# Comparing Models

A simple comparison table works well:

| Test | Model A | Model B | Model C | Notes |
|---|---|---|---|---|
| Finance 1 | Pass | Pass | Partial | C missed month-4 change |
| Linux 2 | Pass | Fail | Pass | B chased wrong root cause |
| Continuity 1 | Partial | Pass | Fail | State retention differences |
| Coding 3 | Pass | Pass | Pass | Similar quality |

You can use any scoring scheme you prefer.

A simple manual scale is:

- **Pass** — Correct result and all important constraints handled.
- **Partial** — Mostly correct, but contains a meaningful omission or error.
- **Fail** — Incorrect conclusion, loses critical state, violates instructions, or misses the main task.

The HTML files intentionally do **not** enforce a scoring system.

---

# Suggested Use With Local LLMs

These suites are particularly useful for comparing models that may look similar on standard benchmarks but behave differently in real agent workflows.

Examples include comparing:

- Different quantizations of the same model.
- Dense vs. MoE models.
- Different context sizes.
- Different KV-cache quantization settings.
- MTP/speculative configurations.
- Different system prompts.
- Different agent harnesses.
- Local models vs. frontier APIs.
- A model before and after fine-tuning.

Because the tests are manual and human-readable, you can see *why* a model failed instead of receiving only a benchmark score.

---

# Versioning

The benchmark suites are intentionally versioned.

Do not replace old prompts when creating a new suite.

Keeping versions separate makes it possible to:

- Re-test a model on the same fixed prompt set.
- Compare historical results.
- Avoid accidentally training your evaluation process around one style of prompt.
- Add new reasoning techniques without changing older baselines.

Current suites:

- **V1:** Continuity-heavy benchmark set.
- **V2:** Alternate techniques and adversarial/constraint-heavy benchmark set.

Future versions can introduce new task families while preserving V1 and V2 as fixed references.

---

# Important Limitations

This is a **manual practical benchmark**, not a scientifically controlled standardized benchmark.

Results can be influenced by:

- System prompts.
- Sampling settings.
- Agent framework.
- Available tools.
- Context limits.
- Quantization.
- Inference engine.
- Previous conversation state.
- Tool failures.
- Model-specific chat templates.

For meaningful comparisons, keep as many of these variables fixed as possible.

Also remember that a prompt suite can only sample model behavior. A model that performs well here is not guaranteed to perform well on every real-world task.

---

# Design Philosophy

The suite emphasizes tasks that resemble actual model usage:

> Give the model a realistic objective, enough information to solve it, several opportunities to lose track of the task, and an expected result that lets a human verify whether it really understood the problem.

The goal is not to produce a single universal score.

The goal is to answer practical questions such as:

- Which model follows complicated instructions more reliably?
- Which model remembers configuration changes?
- Which model catches hidden dependencies?
- Which model handles financial reasoning correctly?
- Which model is better at Linux troubleshooting?
- Which model replans when its original approach becomes invalid?
- Which model resists distractors?
- Which model would I trust more as an autonomous or semi-autonomous agent?

---

## Quick Start

Open either HTML file and start with any card:

**V1**
`manual_model_benchmark_suite_continuity.html`

**V2**
`manual_model_benchmark_suite_v2.html`

Then:

**Copy Prompt → Run Model → Reveal Expected Result → Compare**

That is the entire benchmark workflow.
