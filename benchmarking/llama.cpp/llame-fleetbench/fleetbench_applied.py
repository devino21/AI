"""Original, objectively graded applied-intelligence tasks for FleetBench.

The fixtures borrow evaluation *methods*, not questions, from public benchmark
families: fresh structured analysis (LiveBench), decomposed scientific work
(SciCode), verifiable constraints (IFEval), and calibrated knowledge handling.
Every answer is closed-world and machine graded; no model judge is involved.
"""

from __future__ import annotations

import json
import math
import random
import re


class AnyOf:
    """Accept any listed answer for a field that has more than one right value.

    Several fixtures state constraints that do not pin a unique string. Grading
    those against a single serialized answer marks a correct model wrong:
    applied_lang_constraints admits both "amber cedar amber cedar delta" and
    "cedar amber cedar amber delta", and only the first was accepted.
    """

    def __init__(self, *alternatives):
        self.alternatives = list(alternatives)

    @property
    def reference(self):
        return self.alternatives[0]


class Expr:
    """Accept any algebraically equivalent form of an arithmetic expression.

    An interaction contrast has no canonical spelling. Comparing it as a string
    scored "y1 - y2 - y3 + y4" wrong against "(y4-y3)-(y2-y1)" even though the
    two expand to the same contrast, so a correct answer earned zero credit.
    Equivalence is decided numerically over random assignments of the variables.
    """

    _SAFE = re.compile(r"^[0-9a-z_+\-*/(). ]+$", re.I)

    def __init__(self, reference, variables):
        self.reference = reference
        self.variables = list(variables)

    def _evaluate(self, text, assignment):
        text = str(text).strip()
        # Only bare arithmetic over the declared variables is ever evaluated, so
        # there is no reachable name or attribute beyond `assignment`.
        if not text or len(text) > 200 or not self._SAFE.match(text):
            return None
        if re.search(r"[a-z_][a-z0-9_]*", text, re.I):
            names = set(re.findall(r"[a-z_][a-z0-9_]*", text, re.I))
            if not names <= set(self.variables):
                return None
        try:
            return float(eval(text, {"__builtins__": {}}, dict(assignment)))  # noqa: S307
        except Exception:
            return None

    def matches(self, got):
        if not isinstance(got, str):
            return False
        rng = random.Random(20260803)
        for _ in range(24):
            assignment = {name: rng.uniform(-10, 10) for name in self.variables}
            mine = self._evaluate(self.reference, assignment)
            theirs = self._evaluate(got, assignment)
            if mine is None or theirs is None:
                return False
            if not math.isclose(mine, theirs, rel_tol=1e-9, abs_tol=1e-9):
                return False
        return True


def _reference_payload(expect):
    """The canonical answer for a fixture, with every sentinel resolved."""
    if isinstance(expect, (AnyOf, Expr)):
        return _reference_payload(expect.reference)
    if isinstance(expect, dict):
        return {key: _reference_payload(value) for key, value in expect.items()}
    if isinstance(expect, list):
        return [_reference_payload(value) for value in expect]
    return expect


def _task(task_id, tier, domain, user, expect, *, tolerance=0.0):
    return {"id": task_id, "tier": tier, "domain": domain, "user": user,
            "expect": expect, "tolerance": tolerance}


JSON_ONLY = " Return only one JSON object with exactly the requested keys."

APPLIED_TASKS = [
    # Structured data analysis: derived from supplied tables, never world knowledge.
    _task("applied_data_simpson", "core", "data_analysis", """Two treatments have outcomes:
Low-risk: A 81 successes/90, B 234/270. High-risk: A 192/310, B 55/100.
Compute each treatment's overall success rate as a percentage, identify which has
the higher overall rate, and identify which has the higher rate within BOTH risk
groups. Use percentages rounded to 2 decimals.""" + JSON_ONLY +
          ' Keys: "a_overall_pct", "b_overall_pct", "overall_winner", "within_group_winner".',
          {"a_overall_pct": 68.25, "b_overall_pct": 78.11,
           "overall_winner": "B", "within_group_winner": "A"}, tolerance=.011),
    _task("applied_data_join", "core", "data_analysis", """Orders are
[(o1,c2,40),(o2,c1,70),(o3,c2,25),(o4,c3,90),(o5,c1,15)]. Customers are
[(c1,North),(c2,South),(c3,North),(c4,West)]. After an inner join, give total
revenue by region and the number of customer rows with no matching order.""" + JSON_ONLY +
          ' Keys: "north", "south", "west", "customers_without_orders".',
          {"north": 175, "south": 65, "west": 0, "customers_without_orders": 1}),
    _task("applied_data_weighted", "core", "data_analysis", """Three queues report:
Q1 120 requests at 80 ms mean latency; Q2 30 at 260 ms; Q3 50 at 140 ms.
Give the request-weighted mean latency and the incorrect unweighted mean of the
three reported means, both in ms.""" + JSON_ONLY +
          ' Keys: "weighted_ms", "unweighted_ms".',
          {"weighted_ms": 122, "unweighted_ms": 160}, tolerance=.001),
    _task("applied_data_window", "hard", "data_analysis", """Events, already ordered by
time, are [(u1,4),(u2,7),(u1,9),(u1,3),(u2,5),(u2,8)]. For each event compute
the running sum for that user, then report the six running sums in original event
order and each user's final sum.""" + JSON_ONLY +
          ' Keys: "running", "final". "final" must map u1 and u2 to totals.',
          {"running": [4, 7, 13, 16, 12, 20], "final": {"u1": 16, "u2": 20}}),
    _task("applied_data_cohort", "hard", "data_analysis", """Signup cohorts and active
users are: Jan size 80, active M1=52 M2=40; Feb size 120, active M1=66 M2=42;
Mar size 100, active M1=61 (M2 not yet observed). Give Jan and Feb M2 retention
percentages and the mature-cohort pooled M2 retention. Do not treat unobserved
March M2 as zero. Round to 2 decimals.""" + JSON_ONLY +
          ' Keys: "jan_m2_pct", "feb_m2_pct", "pooled_m2_pct".',
          {"jan_m2_pct": 50, "feb_m2_pct": 35, "pooled_m2_pct": 41}, tolerance=.011),
    _task("applied_data_robust", "frontier", "data_analysis", """Sensor readings are
[10.1,10.2,10.2,10.3,10.4,35.0]. Compute the mean and median, then flag readings
whose absolute deviation from the median exceeds 3 times MAD, where MAD is the
median absolute deviation. Round mean, median, and MAD to 3 decimals.""" + JSON_ONLY +
          ' Keys: "mean", "median", "mad", "flagged".',
          {"mean": 14.367, "median": 10.25, "mad": .1, "flagged": [35.0]}, tolerance=.0011),

    # Language precision, including multilingual retrieval without translation ambiguity.
    _task("applied_lang_edit", "core", "language", """Apply only these edits to the text:
(1) replace the standalone word 'affect' with 'effect'; (2) change 'were' to 'was';
(3) remove the second comma. Text: `The change may affect output, but the result,
were not measured.` Preserve everything else. Return the corrected sentence as
the value of key "text".""" + JSON_ONLY,
          {"text": "The change may effect output, but the result was not measured."}),
    _task("applied_lang_multilingual_extract", "core", "language", """Extract the city,
weekday, and ticket code from this note: `La reunión será en Quito el jueves.
Bitte verwenden Sie den Code ZK-481.` Do not translate city or code; give the
weekday in English lowercase.""" + JSON_ONLY +
          ' Keys: "city", "weekday", "code".',
          {"city": "Quito", "weekday": "thursday", "code": "ZK-481"}),
    _task("applied_lang_reference_v2", "hard", "language", """In the mini-document below,
resolve each bracketed expression to its grammatical antecedent: red folder, Ada, Bea, or Cora.
`Ada lent Bea a red folder. Cora then gave Ada a key. When Bea returned [it],
Ada thanked [her]. Cora said [she] would keep the key safe.`
Return antecedents in bracket order.""" + JSON_ONLY + ' Key: "antecedents".',
          # v1 incorrectly keyed "it" to Ada even though its antecedent is the
          # red folder. A new id prevents append-only result files from mixing
          # the invalid fixture with this corrected one.
          {"antecedents": ["red folder", "Bea", "Cora"]}),
    _task("applied_lang_constraints", "hard", "language", """Using only the tokens
amber, cedar, delta, make a string of exactly five lowercase words such that
amber occurs twice, cedar occurs twice, delta is last, and no identical words
are adjacent. Return it under key "text".""" + JSON_ONLY,
          # Two arrangements satisfy every stated constraint; both are correct.
          {"text": AnyOf("amber cedar amber cedar delta",
                         "cedar amber cedar amber delta")}),

    # Scientific reasoning: units, experiments, and numerical models.
    _task("applied_science_units", "core", "science", """A pump moves 18 liters per
minute for 2.5 hours. Assuming constant flow, compute volume in cubic meters.
(1000 L = 1 m^3.)""" + JSON_ONLY + ' Key: "volume_m3".', {"volume_m3": 2.7}, tolerance=1e-9),
    _task("applied_science_control", "hard", "science", """Four otherwise identical
plant groups receive: G1 no fertilizer/no added light; G2 fertilizer/no added
light; G3 no fertilizer/added light; G4 fertilizer/added light. To estimate the
fertilizer effect specifically under added light, which two groups must be
compared, and what interaction contrast (difference of differences) isolates
whether fertilizer's effect changes with lighting? Express the contrast using
mean outcomes y1..y4.""" + JSON_ONLY +
          ' Keys: "compare" (ascending group numbers), "interaction".',
          {"compare": [3, 4],
           "interaction": Expr("(y4-y3)-(y2-y1)", ["y1", "y2", "y3", "y4"])}),
    _task("applied_science_decay", "hard", "science", """A concentration follows
C(t)=C0*2^(-t/h). Measurements are C(0)=160 and C(12)=20. Find half-life h and
C(18).""" + JSON_ONLY + ' Keys: "half_life", "c18".',
          {"half_life": 4, "c18": 7.071068}, tolerance=1e-6),
    _task("applied_science_integrate", "frontier", "science", """Use composite Simpson's
rule with exactly 4 equal subintervals to approximate integral from 0 to 2 of
f(x)=1/(1+x^2). Report h, the five function values rounded to 6 decimals, and
the final approximation rounded to 6 decimals.""" + JSON_ONLY +
          ' Keys: "h", "f", "integral".',
          {"h": .5, "f": [1, .8, .5, .307692, .2], "integral": 1.105128}, tolerance=1.1e-6),

    # Epistemic calibration: distinguish answerable, unsupported, and false premise.
    _task("applied_cal_known", "core", "calibration", """Use only this record:
`Asset R7: owner Mina; region eu-west; replicas 3.` Question: Who owns R7?
Classify status as answerable, insufficient, or false_premise and supply the
answer; use null when no answer is supported.""" + JSON_ONLY +
          ' Keys: "status", "answer".', {"status": "answerable", "answer": "Mina"}),
    _task("applied_cal_unknown", "core", "calibration", """Use only this record:
`Asset R7: owner Mina; region eu-west; replicas 3.` Question: When was R7 created?
Classify status as answerable, insufficient, or false_premise and supply the
answer; use null when no answer is supported.""" + JSON_ONLY +
          ' Keys: "status", "answer".', {"status": "insufficient", "answer": None}),
    _task("applied_cal_false_premise", "hard", "calibration", """Use only this record:
`Asset R7: owner Mina; region eu-west; replicas 3.` Question: Why does R7 have
five replicas? Classify status as answerable, insufficient, or false_premise and
supply the corrected replica count as the answer.""" + JSON_ONLY +
          ' Keys: "status", "answer".', {"status": "false_premise", "answer": 3}),
    _task("applied_cal_conflict", "frontier", "calibration", """Use only these records:
`09:00 inventory: service K runs v3.` `09:05 deployment log: K upgraded to v4.`
`09:10 rollback log: K restored to v3.` Question: What version runs at 09:12?
Classify status as answerable, insufficient, or false_premise and supply the
answer.""" + JSON_ONLY + ' Keys: "status", "answer".',
          {"status": "answerable", "answer": "v3"}),
]

# Consolidated cases keep each original answer field independently graded while
# avoiding a separate model request for every closely related calculation.
_CONSOLIDATED_IDS = {
    "applied_data_simpson", "applied_data_weighted", "applied_data_join",
    "applied_data_window", "applied_data_cohort", "applied_data_robust",
    "applied_science_units", "applied_science_decay", "applied_science_control",
    "applied_science_integrate", "applied_cal_known", "applied_cal_unknown",
    "applied_cal_false_premise", "applied_cal_conflict",
}
APPLIED_TASKS = [t for t in APPLIED_TASKS if t["id"] not in _CONSOLIDATED_IDS] + [
    _task("applied_data_aggregation", "core", "data_analysis", """Solve two independent
aggregation checks. (1) Low-risk outcomes: A 81/90, B 234/270; high-risk: A
192/310, B 55/100. Give overall success percentages and winners overall and
within both groups. (2) Queue means: Q1 120 requests at 80 ms, Q2 30 at 260 ms,
Q3 50 at 140 ms. Give request-weighted and unweighted means. Round percentages
to 2 decimals.""" + JSON_ONLY +
          ' Keys: "a_overall_pct", "b_overall_pct", "overall_winner", "within_group_winner", "weighted_ms", "unweighted_ms".',
          {"a_overall_pct": 68.25, "b_overall_pct": 78.11,
           "overall_winner": "B", "within_group_winner": "A",
           "weighted_ms": 122, "unweighted_ms": 160}, tolerance=.011),
    _task("applied_data_relational", "hard", "data_analysis", """Solve two structured
data checks. (1) Orders [(o1,c2,40),(o2,c1,70),(o3,c2,25),(o4,c3,90),(o5,c1,15)]
and customers [(c1,North),(c2,South),(c3,North),(c4,West)]: after an inner join,
give revenue by region and unmatched customer count. (2) Ordered events
[(u1,4),(u2,7),(u1,9),(u1,3),(u2,5),(u2,8)]: give per-user running sums in
event order and final totals.""" + JSON_ONLY +
          ' Keys: "north", "south", "west", "customers_without_orders", "running", "final".',
          {"north": 175, "south": 65, "west": 0, "customers_without_orders": 1,
           "running": [4, 7, 13, 16, 12, 20], "final": {"u1": 16, "u2": 20}}),
    _task("applied_data_maturity_robustness", "frontier", "data_analysis", """Solve two
analysis checks. (1) Cohorts: Jan size 80, M2 active 40; Feb size 120, M2 active
42; March M2 unobserved. Give Jan, Feb, and mature-cohort pooled M2 retention
percentages. (2) Readings [10.1,10.2,10.2,10.3,10.4,35.0]: compute mean,
median, MAD, and values more than 3*MAD from the median. Round retention to 2
decimals and descriptive statistics to 3 decimals.""" + JSON_ONLY +
          ' Keys: "jan_m2_pct", "feb_m2_pct", "pooled_m2_pct", "mean", "median", "mad", "flagged".',
          {"jan_m2_pct": 50, "feb_m2_pct": 35, "pooled_m2_pct": 41,
           "mean": 14.367, "median": 10.25, "mad": .1, "flagged": [35.0]},
          tolerance=.011),
    _task("applied_science_quantitative", "hard", "science", """Solve two independent
science calculations. (1) A pump moves 18 liters/minute for 2.5 hours; report
cubic meters. (2) C(t)=C0*2^(-t/h), with C(0)=160 and C(12)=20; find h and
C(18).""" + JSON_ONLY +
          ' Keys: "volume_m3", "half_life", "c18".',
          {"volume_m3": 2.7, "half_life": 4, "c18": 7.071068}, tolerance=1e-6),
    _task("applied_science_design_numerics", "frontier", "science", """Solve two
independent checks. (1) Groups are G1 no fertilizer/no light, G2 fertilizer/no
light, G3 no fertilizer/light, G4 fertilizer/light. Give the groups compared
for fertilizer effect under light and the interaction contrast using y1..y4.
(2) Use composite Simpson's rule with exactly four equal subintervals for the
integral from 0 to 2 of 1/(1+x^2); report h, five function values, and integral,
rounded to 6 decimals.""" + JSON_ONLY +
          ' Keys: "compare", "interaction", "h", "f", "integral".',
          {"compare": [3, 4],
           "interaction": Expr("(y4-y3)-(y2-y1)", ["y1", "y2", "y3", "y4"]),
           "h": .5, "f": [1, .8, .5, .307692, .2], "integral": 1.105128},
          tolerance=1.1e-6),
    _task("applied_calibration_evidence", "frontier", "calibration", """Use only these
records. Asset record: `R7 owner Mina; region eu-west; replicas 3.` Version
records: `09:00 K runs v3; 09:05 upgraded to v4; 09:10 rolled back to v3.`
Classify four questions as answerable, insufficient, or false_premise and give
null when unsupported: who owns R7; when R7 was created; why R7 has five
replicas (give corrected count); what K runs at 09:12.""" + JSON_ONLY +
          ' Keys: "owner_status", "owner_answer", "created_status", "created_answer", "replicas_status", "replicas_answer", "version_status", "version_answer".',
          {"owner_status": "answerable", "owner_answer": "Mina",
           "created_status": "insufficient", "created_answer": None,
           "replicas_status": "false_premise", "replicas_answer": 3,
           "version_status": "answerable", "version_answer": "v3"}),
    _task("applied_event_reconciliation", "frontier", "data_analysis", """Reconcile an
event-sourced account ledger. Initial high-water states are A=(revision 2, balance 100)
and B=(revision 1, balance 50); C is absent. Process events in order:
e1 A rev3 add 20; e2 A rev2 add 999; e3 B rev2 delete; e4 B rev1 add 30;
e1 C rev1 set 70; e5 C rev1 set 40; e6 A rev4 add -15.
An event id already seen is ignored. Otherwise, a revision less than or equal to that
account's accepted high-water revision is stale and ignored. Delete removes the visible
balance but retains its revision. Give the visible balances, ignored event occurrences in
input order, final revision high-water marks, and total visible balance.""" + JSON_ONLY +
          ' Keys: "visible", "ignored_ids", "high_water", "visible_total".',
          {"visible": {"A": 105, "C": 40}, "ignored_ids": ["e2", "e4", "e1"],
           "high_water": {"A": 4, "B": 2, "C": 1}, "visible_total": 145}),
    _task("applied_sensor_fusion", "frontier", "science", """Three independent sensors
report S1=10.8, S2=10.4, S3=11.0. Their known additive biases are respectively
0.2, -0.1, and 0.4, and their error variances are 0.04, 0.09, and 0.16.
Subtract each bias, then compute the inverse-variance weighted estimate and its standard
uncertainty sqrt(1/sum(weights)). Also identify the sensor with the largest absolute
standardized residual |corrected-estimate|/sqrt(variance). Round numeric answers to 4
decimals.""" + JSON_ONLY +
          ' Keys: "estimate", "uncertainty", "largest_standardized_residual".',
          {"estimate": 10.5738, "uncertainty": .1536,
           "largest_standardized_residual": "S2"}, tolerance=.00011),
    _task("applied_authority_timeline", "frontier", "calibration", """Resolve policy as of
2026-08-01 using only these records. [P1] approved baseline effective 2026-01-01:
owner Ana, retention 30 days. [P2] approved regional amendment effective 2026-07-01:
add 15 days to P1 retention. [P3] unapproved draft dated 2026-07-20: owner Kai,
retention 90 days, encryption optional. [P4] signed owner transfer effective
2026-08-10: owner Mei. Report the effective owner and source, retention and every source
needed to derive it, and encryption. Unsupported values and their sources must be null.
Use source IDs in document order.""" + JSON_ONLY +
          ' Keys: "owner", "owner_source", "retention_days", "retention_sources", "encryption", "encryption_source".',
          {"owner": "Ana", "owner_source": "P1", "retention_days": 45,
           "retention_sources": ["P1", "P2"], "encryption": None,
           "encryption_source": None}),
]


def _extract_objects(text):
    """Every parseable JSON object in the text, outermost-first, in order.

    This replaced a single-object helper that returned only the FIRST parseable
    object, so a model that narrates with an example object, or restates the
    schema before answering, was graded on the wrong one. Kept in step with the
    helper of the same name in fleetbench_finance.py; duplicated rather than
    imported to keep the task modules independent of one another.
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


# Structure is a real requirement, but the old hard gate scored a correctly
# solved task in the wrong shape (0.0) below a correctly shaped task with half
# its fields wrong (0.5). Grade the fields and deduct for the envelope instead.
_ENVELOPE_FACTOR = 0.85


def _best_object(objects, expected):
    """The emitted object that covers the most expected keys, plus exactness."""
    expected_keys = set(expected)
    for obj in objects:
        if set(obj) == expected_keys:
            return obj, True
    return max(objects, key=lambda o: len(expected_keys & set(o))), False


def _as_number(value):
    """A JSON string holding nothing but a number, read as that number.

    Models routinely quote numeric fields. The value is right and the key is
    right, so charging a whole field for the quoting turns a formatting habit
    into a capability score.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().rstrip("%").replace(",", ""))
        except ValueError:
            return None
    return None


def _equal(got, want, tolerance):
    if isinstance(want, AnyOf):
        return any(_equal(got, alternative, tolerance) for alternative in want.alternatives)
    if isinstance(want, Expr):
        return want.matches(got)
    if isinstance(want, bool) or want is None:
        return got == want
    if isinstance(want, str):
        return got == want or (isinstance(got, str) and got.strip() == want.strip())
    if isinstance(want, (int, float)):
        number = _as_number(got)
        return number is not None and math.isclose(
            number, float(want), rel_tol=0, abs_tol=tolerance)
    if isinstance(want, list):
        return isinstance(got, list) and len(got) == len(want) and all(
            _equal(g, w, tolerance) for g, w in zip(got, want))
    if isinstance(want, dict):
        return isinstance(got, dict) and set(got) == set(want) and all(
            _equal(got[k], v, tolerance) for k, v in want.items())
    return got == want


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


def score_applied(task, response):
    objects = _extract_objects(response.get("content") or "")
    if not objects:
        return 0.0, _empty_answer_detail(response, "no JSON object")
    expected = task["expect"]
    value, envelope_ok = _best_object(objects, expected)
    correct = sum(_equal(value.get(key), expected[key], task.get("tolerance", 0.0))
                  for key in expected)
    score = correct / len(expected)
    detail = f"{correct}/{len(expected)} independently graded fields"
    if not envelope_ok:
        score *= _ENVELOPE_FACTOR
        detail += (f"; envelope deviated (got {sorted(value)}, "
                   f"expected {sorted(set(expected))}) -{1 - _ENVELOPE_FACTOR:.0%}")
    return round(score, 3), detail


def applied_manifest():
    v2_ids = {"applied_event_reconciliation", "applied_sensor_fusion",
              "applied_authority_timeline"}
    return [{"id": t["id"], "tier": t["tier"], "domain": t["domain"],
             "origin": "original FleetBench synthetic fixture",
             "version": "2.0" if t["id"] in v2_ids else "1.1",
             "grading": "deterministic JSON component comparison"}
            for t in APPLIED_TASKS]


def selftest_applied():
    failures = []
    for task in APPLIED_TASKS:
        score, _ = score_applied(
            task, {"content": json.dumps(_reference_payload(task["expect"]))})
        if score != 1.0:
            failures.append(f"reference failed: {task['id']}")
    reference = next(t for t in APPLIED_TASKS if t["id"] == "applied_lang_reference_v2")
    if _reference_payload(reference["expect"])["antecedents"] != ["red folder", "Bea", "Cora"]:
        failures.append("pronoun antecedent fixture regressed")
    score, _ = score_applied(APPLIED_TASKS[0], {"content": '{"a_overall_pct":68.25}'})
    if score != 0.0:
        failures.append("missing keys were accepted")
    # Extra keys alongside a correct answer cost the envelope deduction, not the
    # whole task, and a narrating preamble object no longer displaces the answer.
    by_id = {task["id"]: task for task in APPLIED_TASKS}
    numerics = by_id["applied_science_design_numerics"]
    extra = _reference_payload(numerics["expect"]); extra["method"] = "composite Simpson"
    loose, _ = score_applied(numerics, {"content": json.dumps(extra)})
    if not 0.80 <= loose < 1.0:
        failures.append(f"extra key zeroed a correct applied answer (got {loose})")
    # An interaction contrast has no canonical spelling; equivalent algebra must
    # score the same, and a different contrast must still be wrong.
    reference = _reference_payload(numerics["expect"])
    for spelling in ("(y4-y3)-(y2-y1)", "y1 - y2 - y3 + y4", "y4-y3-y2+y1",
                     "(y4 - y2) - (y3 - y1)"):
        score, _ = score_applied(numerics, {"content": json.dumps(
            dict(reference, interaction=spelling))})
        if score != 1.0:
            failures.append(f"equivalent contrast {spelling!r} scored {score}")
    for wrong in ("(y4-y3)+(y2-y1)", "y4-y3", "the difference of differences"):
        score, _ = score_applied(numerics, {"content": json.dumps(
            dict(reference, interaction=wrong))})
        if score >= 1.0:
            failures.append(f"non-equivalent contrast {wrong!r} scored {score}")
    # Both arrangements satisfy applied_lang_constraints; neither may be zeroed,
    # and an arrangement that breaks a stated constraint still must be.
    constraints = by_id["applied_lang_constraints"]
    for good in ("amber cedar amber cedar delta", "cedar amber cedar amber delta"):
        score, _ = score_applied(constraints, {"content": json.dumps({"text": good})})
        if score != 1.0:
            failures.append(f"valid arrangement {good!r} scored {score}")
    score, _ = score_applied(constraints,
                             {"content": json.dumps({"text": "amber cedar amber delta cedar"})})
    if score != 0.0:
        failures.append("arrangement with delta out of final position was accepted")
    # A right number that arrived quoted is a formatting habit, not a wrong
    # answer; a wrong number that arrived quoted is still wrong.
    relational = by_id["applied_data_relational"]
    quoted = {key: (str(value) if isinstance(value, (int, float)) else value)
              for key, value in _reference_payload(relational["expect"]).items()}
    score, _ = score_applied(relational, {"content": json.dumps(quoted)})
    if score != 1.0:
        failures.append(f"quoted numeric fields scored {score}")
    quoted["north"] = str(relational["expect"]["north"] + 7)
    score, _ = score_applied(relational, {"content": json.dumps(quoted)})
    if score >= 1.0:
        failures.append("a quoted wrong number was accepted")

    narrated = ('{"plan":"compute h then f"}\n'
                + json.dumps(_reference_payload(numerics["expect"])))
    score, _ = score_applied(numerics, {"content": narrated})
    if score != 1.0:
        failures.append(f"answer after a preamble object was not found (got {score})")
    # Recompute numerical fixtures independently of the serialized references.
    simpson = by_id["applied_data_aggregation"]["expect"]
    if not (math.isclose(simpson["a_overall_pct"], 100 * (81 + 192) / (90 + 310), abs_tol=.011)
            and math.isclose(simpson["b_overall_pct"], 100 * (234 + 55) / (270 + 100), abs_tol=.011)):
        failures.append("Simpson aggregate ground truth mismatch")
    readings = [10.1, 10.2, 10.2, 10.3, 10.4, 35.0]
    median = (readings[2] + readings[3]) / 2
    deviations = sorted(abs(x - median) for x in readings)
    mad = (deviations[2] + deviations[3]) / 2
    robust = by_id["applied_data_maturity_robustness"]["expect"]
    if not (math.isclose(robust["mean"], sum(readings) / len(readings), abs_tol=.0011)
            and math.isclose(robust["mad"], mad, abs_tol=.0011)
            and robust["flagged"] == [x for x in readings if abs(x - median) > 3 * mad]):
        failures.append("robust-statistics ground truth mismatch")
    scientific = by_id["applied_science_design_numerics"]["expect"]
    f = [1 / (1 + (.5 * i) ** 2) for i in range(5)]
    integral = .5 / 3 * (f[0] + 4*f[1] + 2*f[2] + 4*f[3] + f[4])
    if not math.isclose(scientific["integral"], integral, abs_tol=1.1e-6):
        failures.append("Simpson integration ground truth mismatch")
    fusion = by_id["applied_sensor_fusion"]["expect"]
    corrected, variances = [10.6, 10.5, 10.6], [.04, .09, .16]
    weights = [1 / value for value in variances]
    estimate = sum(value * weight for value, weight in zip(corrected, weights)) / sum(weights)
    uncertainty = math.sqrt(1 / sum(weights))
    residuals = [abs(value - estimate) / math.sqrt(variance)
                 for value, variance in zip(corrected, variances)]
    if not (math.isclose(fusion["estimate"], estimate, abs_tol=.00011)
            and math.isclose(fusion["uncertainty"], uncertainty, abs_tol=.00011)
            and fusion["largest_standardized_residual"] == f"S{residuals.index(max(residuals)) + 1}"):
        failures.append("sensor-fusion ground truth mismatch")
    event = by_id["applied_event_reconciliation"]["expect"]
    if event != {"visible": {"A": 105, "C": 40},
                 "ignored_ids": ["e2", "e4", "e1"],
                 "high_water": {"A": 4, "B": 2, "C": 1}, "visible_total": 145}:
        failures.append("event-reconciliation ground truth mismatch")
    return failures
