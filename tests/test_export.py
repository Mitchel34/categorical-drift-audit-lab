"""SYNTHETIC TEST FIXTURE — NOT PROJECT EVIDENCE.

All receipts, bindings and numbers below are invented parser fixtures. They do
not represent a production run, and no auditor or evaluator is imported here.
"""

import copy
import hashlib
import io
import json
import math
import unittest
from unittest import mock

from categorical_drift_audit_lab.export import main, parse_receipt


METRICS = (
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
CHECKS = (
    "identical_oracle", "proportional_oracle", "balanced_shift_oracle",
    "novel_support_oracle", "missing_support_oracle", "disjoint_oracle",
    "bounded_scores", "symmetric_pair", "proportional_invariance",
    "complete_accounting",
)
ERROR = b'{"schema":"categorical-drift-export-error/1","error":"invalid_receipt"}\n'


def fixture():
    """SYNTHETIC TEST FIXTURE — NOT PROJECT EVIDENCE; deliberately invented."""
    metrics = {name: 0.125 for name in METRICS[:-2]}
    metrics.update(case_count=6, production_audit_calls=6)
    return {
        "kind": "benchmark-receipt",
        "control_mode": "trusted-local-python-operational-v1",
        "outcome": "pass", "reason": "passed",
        "source_sha256": "a" * 64, "proof_sha256": "b" * 64,
        "runner_sha256": "c" * 64, "manifest_sha256": "d" * 64,
        "benchmark_id": 7, "lease_id": "synthetic-lease",
        "launch_token": "synthetic-token",
        "process_tree_stopped": True, "owned_child_reaped": True,
        "descendants_allowed": False, "limits_installation_confirmed": True,
        "owned_child_pid": 4242, "wait4_status": 0,
        "process_identity": {"pid": 4242, "owner": "SYNTHETIC_PRIVATE_SENTINEL"},
        "compute_threads": 1, "monitor_threads": 0, "supervisor_threads": 1,
        "memory_hard_limit": False, "cpu_hard_limit_against_hostile_code": False,
        "os_network_sandbox": False, "hostile_code_safe": False,
        "additional_external_services_used": False,
        "cpu_accounting": "at_least_full_reservation_and_observed_usage_no_refund",
        "measured_cpu_is_lower_bound_before_final_receipt_and_db": True,
        "closeout_cpu_margin_seconds": 0.25, "cpu_limit_seconds": 9.75,
        "cpu_seconds": 10.0, "worker_cpu_seconds": 0.125,
        "supervisor_cpu_seconds": 0.125,
        "measured_cpu_before_closeout_seconds": 0.375,
        "memory_limit_bytes": 134217728, "peak_memory_bytes": 2048,
        "worker_peak_memory_bytes": 1024, "supervisor_peak_memory_bytes": 1024,
        "wall_limit_seconds": 30.0, "wall_seconds": 0.5,
        "result": {"metrics": metrics,
                   "checks": [{"name": name, "passed": True} for name in CHECKS]},
        "future_private_field": {"text": "SYNTHETIC_PRIVATE_SENTINEL"},
    }


def encoded(receipt):
    return (json.dumps(receipt, indent=2, allow_nan=False) + "\n").encode("utf-8")


def pins(raw):
    return {
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "source_sha256": "a" * 64, "proof_sha256": "b" * 64,
        "runner_sha256": "c" * 64, "manifest_sha256": "d" * 64,
        "benchmark_id": 7, "lease_id": "synthetic-lease",
        "launch_token": "synthetic-token", "reserved_cpu_seconds": 10.0,
        "memory_limit_bytes": 134217728, "wall_limit_seconds": 30.0,
    }


def arguments(bound):
    result = ["--receipt", "synthetic-receipt.json"]
    for key, value in bound.items():
        result.extend(["--" + key.replace("_", "-"), str(value)])
    return result


class TrackedFile(io.BytesIO):
    def __init__(self, raw):
        super().__init__(raw)
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


class BrokenOutput:
    def __init__(self):
        self.close_calls = 0

    def write(self, _payload):
        raise OSError("SYNTHETIC_PRIVATE_SENTINEL")

    def flush(self):
        raise OSError("SYNTHETIC_PRIVATE_SENTINEL")


    def close(self):
        self.close_calls += 1


class BufferedFailureRaw(io.RawIOBase):
    """SYNTHETIC TEST FIXTURE — NOT PROJECT EVIDENCE; owned broken output."""

    def __init__(self, partial=False, close_error=False):
        super().__init__()
        self.write_calls = 0
        self.delivered = bytearray()
        self.partial = partial
        self.close_error = close_error

    def writable(self):
        return True

    def write(self, payload):
        self.write_calls += 1
        if self.partial and self.write_calls == 1:
            self.delivered.extend(payload[:3])
            return 3
        raise BrokenPipeError("SYNTHETIC_PRIVATE_SENTINEL")

    def close(self):
        if self.closed:
            return
        super().close()
        if self.close_error:
            raise OSError("SYNTHETIC_PRIVATE_SENTINEL")


def buffered_failure(buffer_size=8192, partial=False, close_error=False):
    raw = BufferedFailureRaw(partial, close_error)
    binary = io.BufferedWriter(raw, buffer_size=buffer_size)
    text = io.TextIOWrapper(binary, encoding="utf-8")
    return raw, binary, text


def dispose_fixture(raw, binary, text):
    for stream in (raw, binary, text):
        try:
            stream.close()
        except Exception:
            pass


class ExportTests(unittest.TestCase):
    def rejected(self, raw, bound=None):
        with self.assertRaisesRegex(ValueError, "^invalid_receipt$"):
            parse_receipt(raw, pins(raw) if bound is None else bound)

    def reject_changed(self, path, value):
        receipt = fixture()
        target = receipt
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        self.rejected(encoded(receipt))

    def test_success_copies_all_values_and_only_public_fields(self):
        receipt = fixture()
        receipt["result"]["metrics"]["identical_tv"] = -0.0
        receipt["result"]["metrics"]["balanced_shift_jsd_bits"] = 0.3333333333333333
        before = copy.deepcopy(receipt)
        raw = encoded(receipt)
        public = parse_receipt(raw, pins(raw))
        self.assertEqual(receipt, before)
        self.assertEqual(set(public), {
            "schema", "protocol_version", "outcome", "metrics", "checks",
            "evaluation_source_sha256", "limitations",
        })
        self.assertEqual(public["schema"], "categorical-drift-evaluation/1")
        self.assertEqual(type(public["protocol_version"]), int)
        self.assertEqual(public["protocol_version"], 1)
        self.assertEqual(public["outcome"], "pass")
        self.assertEqual(public["metrics"], receipt["result"]["metrics"])
        self.assertEqual(len(public["metrics"]), 26)
        self.assertEqual(set(public["metrics"]), set(METRICS))
        self.assertEqual(math.copysign(1, public["metrics"]["identical_tv"]), -1)
        self.assertEqual(public["checks"], receipt["result"]["checks"])
        self.assertEqual([check["name"] for check in public["checks"]], list(CHECKS))
        self.assertEqual(public["evaluation_source_sha256"], "a" * 64)
        self.assertEqual(public["limitations"], [
            "descriptive empirical counts only", "six fixed examples",
            "binary64 tolerance 1e-12",
            "operational resource bounds rather than hard containment",
        ])
        serialized = json.dumps(public)
        for private in ("SYNTHETIC_PRIVATE_SENTINEL", "synthetic-lease",
                        "synthetic-token", "process_identity", "receipt_sha256",
                        "benchmark_id", "proof_sha256", "runner_sha256"):
            self.assertNotIn(private, serialized)

    def test_raw_hash_is_checked_before_json_parsing(self):
        raw = encoded(fixture())
        with mock.patch("categorical_drift_audit_lab.export.json.loads") as decoder:
            self.rejected(raw + b" ", pins(raw))
            decoder.assert_not_called()
        # Equivalent reserialized JSON is a different raw receipt identity.
        compact = json.dumps(fixture(), separators=(",", ":")).encode("utf-8")
        self.rejected(compact, pins(raw))

    def test_each_owner_binding_and_exact_type_is_required(self):
        for key in ("source_sha256", "proof_sha256", "runner_sha256",
                    "manifest_sha256", "lease_id", "launch_token", "benchmark_id"):
            with self.subTest(key=key):
                wrong = 8 if key == "benchmark_id" else "invented-wrong-binding"
                self.reject_changed((key,), wrong)
        for key, value in (("benchmark_id", 7.0), ("benchmark_id", True),
                           ("source_sha256", 12), ("lease_id", False)):
            with self.subTest(key=key, value=value):
                self.reject_changed((key,), value)

    def test_pin_shapes_types_and_bounds_are_strict(self):
        raw = encoded(fixture())
        alterations = (
            ("receipt_sha256", "A" * 64), ("source_sha256", "a" * 63),
            ("proof_sha256", None), ("runner_sha256", "g" * 64),
            ("manifest_sha256", "d" * 65), ("benchmark_id", True),
            ("benchmark_id", 7.0), ("benchmark_id", 0),
            ("benchmark_id", 10**20), ("lease_id", ""),
            ("launch_token", "x" * 257), ("lease_id", "nonascii-\u00e9"),
            ("reserved_cpu_seconds", True), ("reserved_cpu_seconds", 0),
            ("reserved_cpu_seconds", 10.001), ("reserved_cpu_seconds", float("inf")),
            ("wall_limit_seconds", 30.001), ("wall_limit_seconds", -1),
            ("memory_limit_bytes", 134217728.0), ("memory_limit_bytes", 134217727),
        )
        for key, value in alterations:
            with self.subTest(key=key, value=value):
                bound = pins(raw)
                bound[key] = value
                self.rejected(raw, bound)
        bound = pins(raw)
        del bound["launch_token"]
        self.rejected(raw, bound)
        bound = pins(raw)
        bound["unapproved"] = "extra"
        self.rejected(raw, bound)
        self.rejected(raw.decode("utf-8"), pins(raw))
        self.rejected(bytearray(raw), pins(raw))

    def test_terminal_safety_and_threads_have_exact_scalars(self):
        for key in ("process_tree_stopped", "owned_child_reaped",
                    "limits_installation_confirmed",
                    "measured_cpu_is_lower_bound_before_final_receipt_and_db"):
            for value in (False, 1):
                with self.subTest(key=key, value=value):
                    self.reject_changed((key,), value)
        for key in ("descendants_allowed", "memory_hard_limit",
                    "cpu_hard_limit_against_hostile_code", "os_network_sandbox",
                    "hostile_code_safe", "additional_external_services_used"):
            for value in (True, 0):
                with self.subTest(key=key, value=value):
                    self.reject_changed((key,), value)
        for key, wrong in (("wait4_status", 1), ("compute_threads", 2),
                           ("monitor_threads", 1), ("supervisor_threads", 0)):
            for value in (wrong, float(fixture()[key]), bool(fixture()[key])):
                with self.subTest(key=key, value=value):
                    self.reject_changed((key,), value)
        for path, value in ((("owned_child_pid",), 0),
                            (("owned_child_pid",), True),
                            (("process_identity", "pid"), 4243),
                            (("process_identity", "pid"), 4242.0),
                            (("process_identity",), None)):
            with self.subTest(path=path, value=value):
                self.reject_changed(path, value)

    def test_kind_mode_status_and_failed_retained_payload_rejected(self):
        for key, value in (("kind", "invented"), ("control_mode", "invented"),
                           ("reason", "guest_failed"), ("outcome", "fail"),
                           ("cpu_accounting", "invented")):
            with self.subTest(key=key):
                self.reject_changed((key,), value)
        receipt = fixture()
        receipt.update(outcome="fail", reason="cpu_limit")
        self.assertEqual(len(receipt["result"]["metrics"]), 26)
        self.assertEqual(len(receipt["result"]["checks"]), 10)
        self.rejected(encoded(receipt))

    def test_metrics_names_count_types_bounds_and_accounting(self):
        for value in (True, "0.125", None, -2e-12, 1 + 2e-12):
            with self.subTest(value=value):
                self.reject_changed(("result", "metrics", "identical_tv"), value)
        for name in ("case_count", "production_audit_calls"):
            for value in (5, 7, 6.0, True):
                with self.subTest(name=name, value=value):
                    self.reject_changed(("result", "metrics", name), value)
        for action in ("missing", "extra", "renamed"):
            with self.subTest(action=action):
                receipt = fixture()
                metrics = receipt["result"]["metrics"]
                if action == "missing":
                    del metrics["disjoint_tv"]
                elif action == "extra":
                    metrics["invented_metric"] = 0
                else:
                    metrics["invented_metric"] = metrics.pop("disjoint_tv")
                self.rejected(encoded(receipt))
        receipt = fixture()
        receipt["result"]["unapproved"] = "SYNTHETIC_PRIVATE_SENTINEL"
        self.rejected(encoded(receipt))

    def test_checks_exact_order_names_count_keys_and_boolean(self):
        for change in ("missing", "extra", "duplicate", "reverse", "false",
                       "number", "extra-key", "wrong-name"):
            with self.subTest(change=change):
                receipt = fixture()
                checks = receipt["result"]["checks"]
                if change == "missing":
                    checks.pop()
                elif change == "extra":
                    checks.append({"name": "invented", "passed": True})
                elif change == "duplicate":
                    checks[1]["name"] = checks[0]["name"]
                elif change == "reverse":
                    checks.reverse()
                elif change == "false":
                    checks[0]["passed"] = False
                elif change == "number":
                    checks[0]["passed"] = 1
                elif change == "extra-key":
                    checks[0]["private"] = "SYNTHETIC_PRIVATE_SENTINEL"
                else:
                    checks[0]["name"] = "invented"
                self.rejected(encoded(receipt))

    def test_cap_formula_and_observed_accounting(self):
        wrong = (
            ("closeout_cpu_margin_seconds", 0.2), ("cpu_limit_seconds", 10),
            ("cpu_seconds", 9.99), ("cpu_seconds", 10.01),
            ("measured_cpu_before_closeout_seconds", 10.01),
            ("memory_limit_bytes", 134217727), ("memory_limit_bytes", 134217728.0),
            ("peak_memory_bytes", 134217729), ("peak_memory_bytes", 2048.0),
            ("worker_peak_memory_bytes", 2049), ("supervisor_peak_memory_bytes", 2049),
            ("wall_limit_seconds", 29), ("wall_seconds", 30.01),
        )
        for key, value in wrong:
            with self.subTest(key=key, value=value):
                self.reject_changed((key,), value)
        for key in ("cpu_seconds", "wall_seconds", "worker_cpu_seconds",
                    "supervisor_cpu_seconds", "cpu_limit_seconds", "wall_limit_seconds",
                    "measured_cpu_before_closeout_seconds", "closeout_cpu_margin_seconds",
                    "peak_memory_bytes", "worker_peak_memory_bytes",
                    "supervisor_peak_memory_bytes", "memory_limit_bytes"):
            for value in (True, -1):
                with self.subTest(key=key, value=value):
                    self.reject_changed((key,), value)
        # A smaller invented grant exercises min(.25, r*.1), not a hardcoded .25.
        receipt = fixture()
        receipt.update(closeout_cpu_margin_seconds=0.1, cpu_limit_seconds=0.9,
                       cpu_seconds=1.0, wall_limit_seconds=5.0)
        raw = encoded(receipt)
        bound = pins(raw)
        bound.update(reserved_cpu_seconds=1.0, wall_limit_seconds=5.0)
        self.assertEqual(parse_receipt(raw, bound)["outcome"], "pass")

    def test_duplicate_keys_nonfinite_and_long_integer_tokens(self):
        raw = encoded(fixture())
        bad = (
            raw.replace(b'"benchmark_id": 7', b'"benchmark_id": 7, "benchmark_id": 7'),
            raw.replace(b'"identical_tv": 0.125',
                        b'"identical_tv": 0.125, "identical_tv": 0.125'),
            raw.replace(b'"passed": true', b'"passed": true, "passed": true', 1),
            raw.replace(b'"identical_tv": 0.125', b'"identical_tv": NaN'),
            raw.replace(b'"identical_tv": 0.125', b'"identical_tv": Infinity'),
            raw.replace(b'"identical_tv": 0.125', b'"identical_tv": -Infinity'),
            raw.replace(b'"identical_tv": 0.125', b'"identical_tv": 1e309'),
            raw.replace(b'"benchmark_id": 7', b'"benchmark_id": 123456789012345678901'),
            raw.replace(b'"benchmark_id": 7', b'"benchmark_id": -123456789012345678901'),
        )
        for index, item in enumerate(bad):
            with self.subTest(index=index):
                self.rejected(item)

    def test_lexical_depth_and_byte_boundary(self):
        receipt = fixture()
        # Root plus 15 nested arrays is depth 16. Delimiters inside strings do
        # not count; ordinary JSON decoding still validates escape syntax.
        receipt["future_private_field"] = "braces { [ \\\" ] }"
        nested = "end"
        for _ in range(15):
            nested = [nested]
        receipt["private_nested"] = nested
        raw = encoded(receipt)
        self.assertEqual(parse_receipt(raw, pins(raw))["outcome"], "pass")
        receipt["private_nested"] = [nested]
        self.rejected(encoded(receipt))
        raw = encoded(fixture())
        padded = raw + b" " * (262144 - len(raw))
        self.assertEqual(len(padded), 262144)
        self.assertEqual(parse_receipt(padded, pins(padded))["outcome"], "pass")
        self.rejected(padded + b" ")

    def test_malformed_utf8_bom_surrogates_trailing_and_escaped_duplicates(self):
        raw = encoded(fixture())
        bad = (
            b"\xef\xbb\xbf" + raw, raw + b"\xff", raw + b"{}", raw[:-2],
            raw.replace(b'"synthetic-lease"', b'"bad\\q"'),
            raw.replace(b'"synthetic-lease"', b'"\\ud800"'),
            raw.replace(b'"benchmark_id": 7',
                        b'"benchmark_id": 7, "benchmark\\u005fid": 7'),
            b"[" * 17 + b"invalid",
        )
        for index, item in enumerate(bad):
            with self.subTest(index=index):
                self.rejected(item)

    def test_cli_success_binary_streams_and_single_bounded_read(self):
        raw = encoded(fixture())
        stream = TrackedFile(raw)
        stdout, stderr = io.BytesIO(), io.BytesIO()
        with mock.patch("builtins.open", return_value=stream) as opened:
            status = main(arguments(pins(raw)), stdout=stdout, stderr=stderr)
        self.assertEqual(status, 0)
        self.assertEqual(stderr.getvalue(), b"")
        opened.assert_called_once_with("synthetic-receipt.json", "rb")
        self.assertEqual(stream.read_sizes, [262145])
        public = parse_receipt(raw, pins(raw))
        expected = (json.dumps(public, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
        self.assertEqual(stdout.getvalue(), expected)

    def test_cli_required_unique_flags_and_no_help_or_raw_errors(self):
        raw = encoded(fixture())
        args = arguments(pins(raw))
        variants = [[], ["--help"], args[:-2], args + args[:2],
                    ["--unknown"] + args[1:], args + ["unapproved"],
                    [args[0], args[1], args[0], args[3]] + args[4:]]
        for invalid in variants:
            with self.subTest(invalid=invalid):
                stdout, stderr = io.BytesIO(), io.BytesIO()
                with mock.patch("builtins.open") as opened:
                    self.assertEqual(main(invalid, stdout, stderr), 2)
                opened.assert_not_called()
                self.assertEqual(stdout.getvalue(), b"")
                self.assertEqual(stderr.getvalue(), ERROR)

    def test_cli_bounded_decimal_syntax_and_caps(self):
        raw = encoded(fixture())
        for flag, value in (("--reserved-cpu-seconds", "+10"),
                            ("--reserved-cpu-seconds", "1e1"),
                            ("--reserved-cpu-seconds", "nan"),
                            ("--reserved-cpu-seconds", "10.00000000000001"),
                            ("--wall-limit-seconds", "31"),
                            ("--wall-limit-seconds", " " + "30"),
                            ("--wall-limit-seconds", "0"),
                            ("--benchmark-id", "7.0"),
                            ("--benchmark-id", "1" * 21),
                            ("--memory-limit-bytes", "134217728.0")):
            with self.subTest(flag=flag, value=value):
                args = arguments(pins(raw))
                args[args.index(flag) + 1] = value
                stdout, stderr = io.BytesIO(), io.BytesIO()
                with mock.patch("builtins.open") as opened:
                    self.assertEqual(main(args, stdout, stderr), 2)
                opened.assert_not_called()
                self.assertEqual(stdout.getvalue(), b"")
                self.assertEqual(stderr.getvalue(), ERROR)

    def test_cli_failure_payload_read_error_and_output_error_are_fixed(self):
        receipt = fixture()
        receipt.update(outcome="fail", reason="guest_failed")
        raw = encoded(receipt)
        stdout, stderr = io.BytesIO(), io.BytesIO()
        with mock.patch("builtins.open", return_value=io.BytesIO(raw)):
            self.assertEqual(main(arguments(pins(raw)), stdout, stderr), 2)
        self.assertEqual(stdout.getvalue(), b"")
        self.assertEqual(stderr.getvalue(), ERROR)
        good = encoded(fixture())
        stdout, stderr = io.BytesIO(), io.BytesIO()
        with mock.patch("builtins.open", side_effect=OSError("SYNTHETIC_PRIVATE_SENTINEL")):
            self.assertEqual(main(arguments(pins(good)), stdout, stderr), 2)
        self.assertEqual(stdout.getvalue(), b"")
        self.assertEqual(stderr.getvalue(), ERROR)
        stderr = io.BytesIO()
        broken_stdout = BrokenOutput()
        with mock.patch("builtins.open", return_value=io.BytesIO(good)):
            self.assertEqual(main(arguments(pins(good)), broken_stdout, stderr), 2)
        self.assertEqual(broken_stdout.close_calls, 0)
        self.assertEqual(stderr.getvalue(), ERROR)
        broken_stderr = BrokenOutput()
        with mock.patch("builtins.open", side_effect=OSError("invented")):
            self.assertEqual(main(arguments(pins(good)), io.BytesIO(), broken_stderr), 2)
        self.assertEqual(broken_stderr.close_calls, 0)

    def test_failed_default_stdout_quiesces_real_buffered_layers(self):
        raw_receipt = encoded(fixture())
        for size, partial, close_error in ((8192, False, False), (1, False, False),
                                            (8192, True, False), (8192, False, True)):
            with self.subTest(size=size, partial=partial, close_error=close_error):
                raw, binary, text = buffered_failure(size, partial, close_error)
                stderr = io.BytesIO()
                try:
                    with mock.patch("sys.stdout", text):
                        with mock.patch("builtins.open", return_value=io.BytesIO(raw_receipt)):
                            status = main(arguments(pins(raw_receipt)), stderr=stderr)
                    self.assertEqual(status, 2)
                    self.assertEqual(stderr.getvalue(), ERROR)
                    self.assertTrue(raw.closed and binary.closed and text.closed)
                    self.assertEqual(raw.write_calls, 2 if partial else 1)
                    self.assertEqual(len(raw.delivered), 3 if partial else 0)
                    attempts = raw.write_calls
                    text.close()
                    binary.close()
                    self.assertEqual(raw.write_calls, attempts)
                finally:
                    dispose_fixture(raw, binary, text)

    def test_failed_default_stderr_quiesces_real_buffered_layers(self):
        for size in (8192, 1):
            with self.subTest(size=size):
                raw, binary, text = buffered_failure(size)
                stdout = io.BytesIO()
                try:
                    with mock.patch("sys.stderr", text):
                        status = main([], stdout=stdout)
                    self.assertEqual(status, 2)
                    self.assertFalse(stdout.closed)
                    self.assertEqual(stdout.getvalue(), b"")
                    self.assertTrue(raw.closed and binary.closed and text.closed)
                    self.assertEqual(raw.write_calls, 1)
                    text.close()
                    binary.close()
                    self.assertEqual(raw.write_calls, 1)
                finally:
                    dispose_fixture(raw, binary, text)

    def test_injected_buffers_and_healthy_default_stdout_remain_open(self):
        raw_receipt = encoded(fixture())
        for role in ("stdout", "stderr"):
            with self.subTest(role=role):
                raw, binary, text = buffered_failure()
                try:
                    if role == "stdout":
                        with mock.patch("builtins.open", return_value=io.BytesIO(raw_receipt)):
                            status = main(arguments(pins(raw_receipt)), binary, io.BytesIO())
                    else:
                        status = main([], io.BytesIO(), binary)
                    self.assertEqual(status, 2)
                    self.assertFalse(raw.closed or binary.closed or text.closed)
                    self.assertEqual(raw.write_calls, 1)
                finally:
                    dispose_fixture(raw, binary, text)
        healthy = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        try:
            with mock.patch("sys.stdout", healthy):
                status = main([], stderr=io.BytesIO())
            self.assertEqual(status, 2)
            self.assertFalse(healthy.closed or healthy.buffer.closed)
        finally:
            healthy.close()


if __name__ == "__main__":
    unittest.main()
