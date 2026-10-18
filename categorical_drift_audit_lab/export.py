"""Validate and sanitize an owner-pinned successful evaluation receipt.

This module does not import the auditor or evaluator. Trusted pins must come
from the owner's completed-operation verification; a caller-chosen digest does
not independently establish provenance or registry state.
"""

import hashlib
import json
import math
import sys


MAX_RECEIPT_BYTES = 262144
MAX_DEPTH = 16
METRIC_NAMES = (
    "identical_tv", "identical_jsd_bits", "identical_novel_mass",
    "identical_missing_mass", "proportional_tv", "proportional_jsd_bits",
    "proportional_novel_mass", "proportional_missing_mass",
    "balanced_shift_tv", "balanced_shift_jsd_bits",
    "balanced_shift_novel_mass", "balanced_shift_missing_mass",
    "novel_support_tv", "novel_support_jsd_bits", "novel_support_novel_mass",
    "novel_support_missing_mass", "missing_support_tv",
    "missing_support_jsd_bits", "missing_support_novel_mass",
    "missing_support_missing_mass", "disjoint_tv", "disjoint_jsd_bits",
    "disjoint_novel_mass", "disjoint_missing_mass", "case_count",
    "production_audit_calls",
)
CHECK_NAMES = (
    "identical_oracle", "proportional_oracle", "balanced_shift_oracle",
    "novel_support_oracle", "missing_support_oracle", "disjoint_oracle",
    "bounded_scores", "symmetric_pair", "proportional_invariance",
    "complete_accounting",
)
LIMITATIONS = (
    "descriptive empirical counts only",
    "six fixed examples",
    "binary64 tolerance 1e-12",
    "operational resource bounds rather than hard containment",
)
_PIN_NAMES = (
    "receipt_sha256", "source_sha256", "proof_sha256", "runner_sha256",
    "benchmark_id", "lease_id", "manifest_sha256", "launch_token",
    "reserved_cpu_seconds", "memory_limit_bytes", "wall_limit_seconds",
)
_FLAGS = ("--receipt",) + tuple("--" + key.replace("_", "-") for key in _PIN_NAMES)
_DIGEST_NAMES = (
    "receipt_sha256", "source_sha256", "proof_sha256", "runner_sha256",
    "manifest_sha256",
)
_ERROR = b'{"schema":"categorical-drift-export-error/1","error":"invalid_receipt"}\n'


def _invalid():
    raise ValueError("invalid_receipt")


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _digest(value):
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _identifier(value):
    return type(value) is str and 0 < len(value) <= 256 and value.isascii()


def _validate_pins(pins):
    if (type(pins) is not dict or len(pins) != len(_PIN_NAMES)
            or any(type(key) is not str for key in pins)
            or set(pins) != set(_PIN_NAMES)):
        _invalid()
    if any(not _digest(pins[name]) for name in _DIGEST_NAMES):
        _invalid()
    benchmark = pins["benchmark_id"]
    if type(benchmark) is not int or not 0 < benchmark < 10**20:
        _invalid()
    if any(not _identifier(pins[name]) for name in ("lease_id", "launch_token")):
        _invalid()
    cpu = pins["reserved_cpu_seconds"]
    wall = pins["wall_limit_seconds"]
    if (not _number(cpu) or not 0 < cpu <= 10
            or not _number(wall) or not 0 < wall <= 30
            or type(pins["memory_limit_bytes"]) is not int
            or pins["memory_limit_bytes"] != 134217728):
        _invalid()


def _lexical_depth(text):
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                _invalid()
        elif char in "]}":
            depth -= 1
            if depth < 0:
                _invalid()
    # The decoder, rather than this bounded pass, validates bracket types,
    # escapes and all remaining JSON syntax.


def _string(value):
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        _invalid()
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _string(key)
        if key in result:
            _invalid()
        result[key] = value
    return result


def _integer(token):
    if len(token.lstrip("-")) > 20:
        _invalid()
    return int(token)


def _float(token):
    value = float(token)
    if not math.isfinite(value):
        _invalid()
    return value


def _constant(_token):
    _invalid()


def _strings(value):
    if type(value) is str:
        _string(value)
    elif type(value) is list:
        for item in value:
            _strings(item)
    elif type(value) is dict:
        for key, item in value.items():
            _string(key)
            _strings(item)


def _resource_fields(receipt, pins):
    numeric = (
        "cpu_seconds", "wall_seconds", "worker_cpu_seconds",
        "supervisor_cpu_seconds", "cpu_limit_seconds", "wall_limit_seconds",
        "measured_cpu_before_closeout_seconds", "closeout_cpu_margin_seconds",
    )
    memory = (
        "peak_memory_bytes", "worker_peak_memory_bytes",
        "supervisor_peak_memory_bytes", "memory_limit_bytes",
    )
    if any(not _number(receipt.get(key)) or receipt[key] < 0 for key in numeric):
        _invalid()
    if any(type(receipt.get(key)) is not int or receipt[key] < 0 for key in memory):
        _invalid()
    reserved = pins["reserved_cpu_seconds"]
    margin = min(0.25, reserved * 0.1)
    measured = receipt["measured_cpu_before_closeout_seconds"]
    if (receipt["closeout_cpu_margin_seconds"] != margin
            or receipt["cpu_limit_seconds"] != reserved - margin
            or receipt["cpu_limit_seconds"] <= 0
            or receipt["cpu_seconds"] < reserved
            or receipt["cpu_seconds"] < measured
            or receipt["cpu_seconds"] > 10
            or receipt["memory_limit_bytes"] != pins["memory_limit_bytes"]
            or receipt["peak_memory_bytes"] > pins["memory_limit_bytes"]
            or receipt["worker_peak_memory_bytes"] > receipt["peak_memory_bytes"]
            or receipt["supervisor_peak_memory_bytes"] > receipt["peak_memory_bytes"]
            or receipt["wall_limit_seconds"] != pins["wall_limit_seconds"]
            or receipt["wall_limit_seconds"] <= 0
            or receipt["wall_seconds"] > pins["wall_limit_seconds"]):
        _invalid()


def _result(receipt):
    result = receipt.get("result")
    if type(result) is not dict or set(result) != {"metrics", "checks"}:
        _invalid()
    metrics = result["metrics"]
    checks = result["checks"]
    if type(metrics) is not dict or set(metrics) != set(METRIC_NAMES):
        _invalid()
    for name in METRIC_NAMES:
        value = metrics[name]
        if not _number(value):
            _invalid()
        if name in ("case_count", "production_audit_calls"):
            if type(value) is not int or value != 6:
                _invalid()
        elif not -1e-12 <= value <= 1 + 1e-12:
            _invalid()
    if type(checks) is not list or len(checks) != len(CHECK_NAMES):
        _invalid()
    clean_checks = []
    for expected_name, check in zip(CHECK_NAMES, checks):
        if (type(check) is not dict or set(check) != {"name", "passed"}
                or type(check["name"]) is not str
                or check["name"] != expected_name
                or type(check["passed"]) is not bool
                or check["passed"] is not True):
            _invalid()
        clean_checks.append({"name": check["name"], "passed": check["passed"]})
    return {name: metrics[name] for name in METRIC_NAMES}, clean_checks


def parse_receipt(raw, pins):
    """Return public data from exact receipt bytes and trusted typed pins.

    ``pins`` has exactly the CLI pin names with hyphens replaced by underscores
    (excluding ``receipt``); benchmark and memory are ints, CPU/wall int or
    float, and other pins are strings. No files are opened by this function.
    Every rejection raises ``ValueError("invalid_receipt")``.
    """
    try:
        _validate_pins(pins)
        if type(raw) is not bytes or len(raw) > MAX_RECEIPT_BYTES:
            _invalid()
        # Receipt identity is over original bytes, before decoding or parsing.
        if hashlib.sha256(raw).hexdigest() != pins["receipt_sha256"]:
            _invalid()
        if raw.startswith(b"\xef\xbb\xbf"):
            _invalid()
        text = raw.decode("utf-8", errors="strict")
        _lexical_depth(text)
        receipt = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                             parse_float=_float, parse_constant=_constant)
        _strings(receipt)
        if type(receipt) is not dict:
            _invalid()
        required_values = {
            "kind": "benchmark-receipt",
            "control_mode": "trusted-local-python-operational-v1",
            "outcome": "pass",
            "reason": "passed",
            "cpu_accounting": "at_least_full_reservation_and_observed_usage_no_refund",
        }
        for key, expected in required_values.items():
            if type(receipt.get(key)) is not str or receipt[key] != expected:
                _invalid()
        for key in ("source_sha256", "proof_sha256", "runner_sha256",
                    "manifest_sha256", "lease_id", "launch_token"):
            if type(receipt.get(key)) is not str or receipt[key] != pins[key]:
                _invalid()
        if (type(receipt.get("benchmark_id")) is not int
                or receipt["benchmark_id"] != pins["benchmark_id"]):
            _invalid()
        for key in ("process_tree_stopped", "owned_child_reaped",
                    "limits_installation_confirmed",
                    "measured_cpu_is_lower_bound_before_final_receipt_and_db"):
            if receipt.get(key) is not True:
                _invalid()
        for key in ("descendants_allowed", "memory_hard_limit",
                    "cpu_hard_limit_against_hostile_code", "os_network_sandbox",
                    "hostile_code_safe", "additional_external_services_used"):
            if receipt.get(key) is not False:
                _invalid()
        for key, expected in (("wait4_status", 0), ("compute_threads", 1),
                              ("monitor_threads", 0), ("supervisor_threads", 1)):
            if type(receipt.get(key)) is not int or receipt[key] != expected:
                _invalid()
        pid = receipt.get("owned_child_pid")
        identity = receipt.get("process_identity")
        if (type(pid) is not int or pid <= 0 or type(identity) is not dict
                or type(identity.get("pid")) is not int or identity["pid"] != pid):
            _invalid()
        _resource_fields(receipt, pins)
        metrics, checks = _result(receipt)
        return {
            "schema": "categorical-drift-evaluation/1", "protocol_version": 1,
            "outcome": "pass", "metrics": metrics, "checks": checks,
            "evaluation_source_sha256": pins["source_sha256"],
            "limitations": list(LIMITATIONS),
        }
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ValueError("invalid_receipt") from None


def _decimal(text, ceiling):
    if (type(text) is not str or not 0 < len(text) <= 16
            or text.count(".") > 1
            or any(char not in "0123456789." for char in text)
            or not any(char in "0123456789" for char in text)):
        _invalid()
    value = float(text)
    if not math.isfinite(value) or not 0 < value <= ceiling:
        _invalid()
    return value


def _arguments(argv):
    if (type(argv) is not list or len(argv) != 2 * len(_FLAGS)
            or any(type(arg) is not str for arg in argv)):
        _invalid()
    values = {}
    for offset in range(0, len(argv), 2):
        flag, value = argv[offset:offset + 2]
        if flag not in _FLAGS or flag in values:
            _invalid()
        values[flag] = value
    if set(values) != set(_FLAGS):
        _invalid()
    benchmark = values["--benchmark-id"]
    memory = values["--memory-limit-bytes"]
    if (not 0 < len(benchmark) <= 20
            or any(char not in "0123456789" for char in benchmark)
            or not 0 < len(memory) <= 20
            or any(char not in "0123456789" for char in memory)):
        _invalid()
    pins = {key: values["--" + key.replace("_", "-")] for key in _PIN_NAMES}
    pins["benchmark_id"] = int(benchmark)
    pins["memory_limit_bytes"] = int(memory)
    pins["reserved_cpu_seconds"] = _decimal(values["--reserved-cpu-seconds"], 10)
    pins["wall_limit_seconds"] = _decimal(values["--wall-limit-seconds"], 30)
    _validate_pins(pins)
    return values["--receipt"], pins


def _write(stream, payload):
    written = stream.write(payload)
    if type(written) is not int or written != len(payload):
        raise OSError("output_failure")
    stream.flush()


def _quiesce_failed_default(owner, binary=None):
    """Close only a failed process-owned path, raw first, without diagnostics."""
    if owner is None:
        return
    if binary is None:
        try:
            binary = owner.buffer
        except Exception:
            binary = None
    try:
        raw = binary.raw
    except Exception:
        raw = None
    for stream in (raw, binary, owner):
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass


def _report(stderr):
    owner = sys.stderr if stderr is None else None
    errors = None
    try:
        errors = owner.buffer if stderr is None else stderr
        _write(errors, _ERROR)
    except Exception:
        _quiesce_failed_default(owner, errors)
    return 2


def main(argv=None, stdout=None, stderr=None):
    """Read one bounded receipt file and write binary JSON, with fixed errors."""
    try:
        args = list(sys.argv[1:]) if argv is None else argv
        receipt_path, pins = _arguments(args)
        with open(receipt_path, "rb") as stream:
            raw = stream.read(MAX_RECEIPT_BYTES + 1)
        public = parse_receipt(raw, pins)
        payload = (json.dumps(public, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    except Exception:
        return _report(stderr)

    owner = sys.stdout if stdout is None else None
    output = None
    try:
        output = owner.buffer if stdout is None else stdout
        _write(output, payload)
    except Exception:
        _quiesce_failed_default(owner, output)
        return _report(stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
