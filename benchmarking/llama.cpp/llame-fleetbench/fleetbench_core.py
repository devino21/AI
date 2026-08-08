"""Shared protocol, result-state, and uncertainty helpers for Fleetbench.

This module deliberately has no third-party dependencies.  Keeping the
OpenAI-compatible response normalizer and score aggregation independent from
the runner makes their edge cases unit-testable without loading a model or
starting an HTTP server.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


BENCHMARK_VERSION = "2.0.0"
LEGACY_SUITE_VERSION = "fleetbench-legacy-45-v1"
CALIBRATED_SUITE_VERSION = "fleetbench-calibrated-v2"
FULL_SUITE_VERSION = "fleetbench-full-v2"

QUALITY_STATES = frozenset({"pass", "partial", "fail"})
NON_QUALITY_STATES = frozenset({
    "timeout", "truncated", "parse_error", "infra_error", "context_overflow",
})
RESULT_STATES = QUALITY_STATES | NON_QUALITY_STATES


class BenchmarkFailure(Exception):
    """A classified harness/request failure that is not a model-quality zero."""

    result_state = "infra_error"
    failure_type = "infrastructure_failure"

    def __init__(self, message: str, *, detail: str | None = None,
                 failure_type: str | None = None):
        super().__init__(message)
        self.detail = detail or message
        if failure_type:
            self.failure_type = failure_type


class ResponseParseFailure(BenchmarkFailure):
    result_state = "parse_error"
    failure_type = "response_protocol_error"


class ContextOverflowFailure(BenchmarkFailure):
    result_state = "context_overflow"
    failure_type = "context_overflow"


class RequestTimeoutFailure(BenchmarkFailure):
    result_state = "timeout"
    failure_type = "request_timeout"


class InfrastructureFailure(BenchmarkFailure):
    result_state = "infra_error"
    failure_type = "server_or_network_error"


class ModelLoadFailure(InfrastructureFailure):
    failure_type = "model_load_or_reload_error"


@dataclass(frozen=True)
class ResultClassification:
    state: str
    failure_type: str = ""

    @property
    def quality_eligible(self) -> bool:
        return self.state in QUALITY_STATES


def message_text(value: Any) -> str:
    """Normalize text from common Chat Completions-compatible content forms."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Mapping):
                # OpenAI-compatible gateways use several content-part labels.
                candidate = item.get("text")
                if isinstance(candidate, Mapping):
                    candidate = candidate.get("value")
                if not isinstance(candidate, str):
                    candidate = item.get("content") or item.get("output_text")
                if isinstance(candidate, str):
                    parts.append(candidate)
        return "".join(parts)
    return ""


def _normalize_tool_call(raw: Any, index: int) -> tuple[dict[str, Any], list[str]]:
    diagnostics: list[str] = []
    if not isinstance(raw, Mapping):
        return ({"id": f"call_{index}", "type": "function",
                 "function": {"name": "", "arguments": "{}"}},
                [f"tool_calls[{index}] is not an object"])

    function = raw.get("function")
    if not isinstance(function, Mapping):
        # Some compatible servers flatten name/arguments onto the call object.
        function = {"name": raw.get("name"), "arguments": raw.get("arguments", "{}")}
        diagnostics.append(f"tool_calls[{index}] used flattened function fields")

    name = function.get("name")
    if not isinstance(name, str) or not name.strip():
        diagnostics.append(f"tool_calls[{index}] has no function name")
        name = "" if name is None else str(name)

    arguments = function.get("arguments", "{}")
    if isinstance(arguments, Mapping):
        arguments = json.dumps(arguments, separators=(",", ":"), sort_keys=True)
    elif not isinstance(arguments, str):
        diagnostics.append(f"tool_calls[{index}] arguments are neither JSON text nor an object")
        try:
            arguments = json.dumps(arguments, separators=(",", ":"))
        except (TypeError, ValueError):
            arguments = "{}"
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
            if not isinstance(parsed, dict):
                diagnostics.append(f"tool_calls[{index}] arguments JSON is not an object")
        except json.JSONDecodeError:
            diagnostics.append(f"tool_calls[{index}] arguments are invalid JSON")

    call_id = raw.get("id")
    if not isinstance(call_id, str) or not call_id:
        call_id = f"call_{index}"
        diagnostics.append(f"tool_calls[{index}] had no id; generated {call_id}")
    return ({"id": call_id, "type": "function",
             "function": {"name": name, "arguments": arguments}}, diagnostics)


def normalize_chat_response(data: Any, *, requested_max_tokens: int,
                            wall_s: float) -> dict[str, Any]:
    """Normalize supported Chat Completions response shapes.

    Hidden reasoning remains in ``reasoning_content`` and is never merged into
    ``content``.  This lets the runner diagnose a reasoning-only/empty answer
    without rewarding chain-of-thought text.
    """
    if not isinstance(data, Mapping):
        raise ResponseParseFailure("response body is not a JSON object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ResponseParseFailure("response has no non-empty choices array")
    choice = choices[0]
    if not isinstance(choice, Mapping):
        raise ResponseParseFailure("response choices[0] is not an object")

    raw_message = choice.get("message")
    if raw_message is None and isinstance(choice.get("text"), str):
        # Legacy completion-shaped compatibility response.
        raw_message = {"role": "assistant", "content": choice.get("text")}
    if not isinstance(raw_message, Mapping):
        raise ResponseParseFailure("response choice has no assistant message")

    content = message_text(raw_message.get("content"))
    raw_reasoning = (raw_message.get("reasoning_content")
                     if raw_message.get("reasoning_content") is not None
                     else raw_message.get("reasoning"))
    if raw_reasoning is None:
        raw_reasoning = (choice.get("reasoning_content")
                         if choice.get("reasoning_content") is not None
                         else choice.get("reasoning"))
    if raw_reasoning is None:
        raw_reasoning = data.get("reasoning_content")
    reasoning = message_text(raw_reasoning)

    raw_calls = raw_message.get("tool_calls")
    diagnostics: list[str] = []
    if raw_calls is None:
        raw_calls = choice.get("tool_calls")
        if raw_calls is not None:
            diagnostics.append("tool_calls were supplied on the choice rather than the message")
    if raw_calls is None:
        raw_calls = data.get("tool_calls")
        if raw_calls is not None:
            diagnostics.append("tool_calls were supplied at response top level")
    legacy_call = raw_message.get("function_call")
    if raw_calls is None and isinstance(legacy_call, Mapping):
        raw_calls = [{"type": "function", "function": legacy_call}]
        diagnostics.append("normalized legacy message.function_call")
    if raw_calls is None:
        raw_calls = []
    if not isinstance(raw_calls, list):
        raise ResponseParseFailure("tool_calls is present but is not an array")

    tool_calls = []
    for index, raw in enumerate(raw_calls):
        call, call_diagnostics = _normalize_tool_call(raw, index)
        tool_calls.append(call)
        diagnostics.extend(call_diagnostics)

    timings = data.get("timings") if isinstance(data.get("timings"), Mapping) else {}
    usage = data.get("usage") if isinstance(data.get("usage"), Mapping) else {}
    completion_details = (usage.get("completion_tokens_details")
                          if isinstance(usage.get("completion_tokens_details"), Mapping)
                          else {})
    pp = timings.get("prompt_per_second")
    tg = timings.get("predicted_per_second")
    if tg is None and isinstance(usage.get("completion_tokens"), (int, float)) and wall_s > 0:
        tg = usage["completion_tokens"] / wall_s

    message = {"role": raw_message.get("role", "assistant"), "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    if reasoning:
        message["reasoning_content"] = reasoning
    return {
        "message": message,
        "content": content,
        "reasoning_content": reasoning,
        "tool_calls": tool_calls,
        "tool_call_diagnostics": diagnostics,
        "finish_reason": choice.get("finish_reason"),
        "requested_max_tokens": requested_max_tokens,
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "pp_tps": pp,
        "tg_tps": tg,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "wall_s": round(wall_s, 2),
        "response_id": data.get("id"),
        "response_model": data.get("model"),
        "system_fingerprint": data.get("system_fingerprint"),
        "response_fields": sorted(str(key) for key in data),
        "raw": data,
    }


_STRUCTURED_FAILURE = re.compile(
    r"(?:no valid JSON|no JSON object|invalid JSON|JSON answer is not|no code block)", re.I
)


def classify_scored_result(score: float, detail: str,
                           response: Mapping[str, Any]) -> ResultClassification:
    """Classify a completed scorer result without changing its numeric score."""
    used = response.get("completion_tokens")
    limit = response.get("requested_max_tokens")
    exhausted = response.get("finish_reason") == "length"
    try:
        exhausted = exhausted or bool(used and limit and int(used) >= int(limit))
    except (TypeError, ValueError):
        pass
    if exhausted:
        return ResultClassification("truncated", "response_truncation")
    if "execution timeout" in (detail or "").lower():
        # Candidate code that fails to terminate is a functional quality
        # failure, not serving-speed noise. Keep the timeout failure_type so
        # reports can count it separately without letting it evade the score.
        return ResultClassification("fail", "candidate_execution_timeout")

    diagnostics = response.get("tool_call_diagnostics") or []
    malformed = [item for item in diagnostics if any(
        marker in item for marker in ("invalid JSON", "no function name", "not an object")
    )]
    if malformed and score < 1:
        return ResultClassification("fail", "malformed_tool_call")

    content = response.get("content") or ""
    calls = response.get("tool_calls") or []
    if not content.strip() and not calls:
        if response.get("reasoning_content"):
            return ResultClassification("fail", "reasoning_only_empty_answer")
        return ResultClassification("fail", "empty_assistant_content")
    if score < 1 and _STRUCTURED_FAILURE.search(detail or ""):
        return ResultClassification("fail", "malformed_model_response")
    if score >= 0.999:
        return ResultClassification("pass")
    if score > 0:
        return ResultClassification("partial", "quality_partial")
    return ResultClassification("fail", "wrong_answer_or_action")


def classify_exception(exc: BaseException) -> tuple[ResultClassification, str]:
    if isinstance(exc, BenchmarkFailure):
        return ResultClassification(exc.result_state, exc.failure_type), exc.detail
    name = type(exc).__name__
    return ResultClassification("infra_error", "unclassified_harness_exception"), f"{name}: {exc}"


def quality_eligible(row: Mapping[str, Any]) -> bool:
    state = str(row.get("result_state") or "").strip()
    if not state:
        # Backward compatibility: historical rows only encoded request failures
        # in their detail string.
        return not str(row.get("detail") or "").startswith("request error:")
    return state in QUALITY_STATES


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def bootstrap_interval(values: Iterable[float], *, confidence: float = 0.95,
                       iterations: int = 4000, seed: int = 731) -> tuple[float | None, float | None]:
    """Task-level nonparametric percentile-bootstrap interval for a mean."""
    sample = [float(value) for value in values if isinstance(value, (int, float))
              and math.isfinite(float(value))]
    if not sample:
        return None, None
    if len(sample) == 1 or len(set(sample)) == 1:
        value = sum(sample) / len(sample)
        return value, value
    rng = random.Random(seed)
    n = len(sample)
    means = sorted(sum(sample[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(max(200, int(iterations))))
    alpha = (1 - confidence) / 2
    return _percentile(means, alpha), _percentile(means, 1 - alpha)


def stratified_bootstrap_interval(category_scores: Mapping[str, Iterable[float]], *,
                                  confidence: float = 0.95,
                                  iterations: int = 4000,
                                  seed: int = 991) -> tuple[float | None, float | None]:
    """Bootstrap a macro-category suite score while preserving category weight."""
    groups = {
        category: [float(value) for value in values
                   if isinstance(value, (int, float)) and math.isfinite(float(value))]
        for category, values in category_scores.items()
    }
    groups = {category: values for category, values in groups.items() if values}
    if not groups:
        return None, None
    rng = random.Random(seed)
    draws = []
    for _ in range(max(200, int(iterations))):
        category_means = []
        for values in groups.values():
            n = len(values)
            category_means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
        draws.append(sum(category_means) / len(category_means))
    draws.sort()
    alpha = (1 - confidence) / 2
    return _percentile(draws, alpha), _percentile(draws, 1 - alpha)


def stable_task_set_hash(entries: Iterable[Mapping[str, Any]]) -> str:
    """Hash the versioned task identity/role manifest, independent of dict order."""
    canonical = sorted(
        ({str(key): value for key, value in entry.items()} for entry in entries),
        key=lambda entry: (str(entry.get("category", "")), str(entry.get("task_id", ""))),
    )
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()
