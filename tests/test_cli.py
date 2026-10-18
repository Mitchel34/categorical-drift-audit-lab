"""Serial, in-process tests of the bounded binary CLI; no evaluator calls."""

import io
import json
import unittest
from unittest import mock

from categorical_drift_audit_lab import cli


_DEMO = b'{"reference":{"a":4},"current":{"a":2,"b":2}}'


class ReadOnce(io.BytesIO):
    def __init__(self, raw):
        super().__init__(raw)
        self.sizes = []

    def read(self, size=-1):
        self.sizes.append(size)
        if len(self.sizes) > 1:
            raise AssertionError("stdin was read more than once")
        return super().read(size)


class NoRead:
    def read(self, _size):
        raise AssertionError("stdin must not be read")


class ReadError:
    def read(self, _size):
        raise OSError("details must stay private")


class FailedWriter:
    def __init__(self, mode):
        self.mode = mode
        self.data = bytearray()
        self.write_calls = 0
        self.flush_calls = 0
        self.close_calls = 0

    def write(self, payload):
        self.write_calls += 1
        if self.mode == "raise":
            raise OSError("details must stay private")
        if self.mode == "short":
            self.data.extend(payload[:3])
            return 3
        if self.mode == "none":
            return None
        if self.mode == "bool":
            return True
        self.data.extend(payload)
        return len(payload)

    def flush(self):
        self.flush_calls += 1
        if self.mode == "flush":
            raise OSError("details must stay private")


    def close(self):
        self.close_calls += 1


class BufferedFailureRaw(io.RawIOBase):
    """Owned in-process output fixture; never a subprocess or evaluator."""

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
        raise BrokenPipeError("details must stay private")

    def close(self):
        if self.closed:
            return
        super().close()
        if self.close_error:
            raise OSError("cleanup details must stay private")


def buffered_failure(buffer_size=8192, partial=False, close_error=False):
    raw = BufferedFailureRaw(partial, close_error)
    binary = io.BufferedWriter(raw, buffer_size=buffer_size)
    text = io.TextIOWrapper(binary, encoding="utf-8")
    return raw, binary, text


def dispose_fixture(raw, binary, text):
    # Test-owned cleanup also runs if an assertion fails; do not leave a
    # deliberately broken buffered object for unittest's own finalization.
    for stream in (raw, binary, text):
        try:
            stream.close()
        except Exception:
            pass


class CliTests(unittest.TestCase):
    def invoke(self, raw, argv=None):
        stdin = ReadOnce(raw)
        stdout, stderr = io.BytesIO(), io.BytesIO()
        code = cli.main([] if argv is None else argv, stdin, stdout, stderr)
        return code, stdout.getvalue(), stderr.getvalue(), stdin

    def assert_error(self, raw, name="invalid_input", code=2):
        actual, stdout, stderr, stdin = self.invoke(raw)
        self.assertEqual(actual, code)
        self.assertEqual(stdout, b"")
        self.assertEqual(
            stderr,
            ('{"error":"' + name + '","schema":"categorical-drift-error/1"}\n').encode("ascii"),
        )
        self.assertEqual(stdin.sizes, [65_537])

    def test_demo_and_whitespace_escaped_stdin_have_identical_result_bytes(self):
        stdout, stderr = io.BytesIO(), io.BytesIO()
        self.assertEqual(cli.main(["--demo"], NoRead(), stdout, stderr), 0)
        demo_bytes = stdout.getvalue()
        self.assertEqual(stderr.getvalue(), b"")
        raw = b' \t\r\n{"current":{"b":2,"\\u0061":2},"reference":{"a":4}} \n'
        code, actual, errors, stdin = self.invoke(raw)
        self.assertEqual((code, actual, errors), (0, demo_bytes, b""))
        self.assertEqual(stdin.sizes, [65_537])
        result = json.loads(actual)
        self.assertEqual(result["schema"], "categorical-drift-audit/1")
        self.assertEqual((result["reference_total"], result["current_total"]), (4, 4))
        self.assertEqual(result["total_variation"], 0.5)
        self.assertEqual(result["novel_categories"], ["b"])
        self.assertEqual(actual, json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n")

    def test_usage_reads_no_input_and_emits_only_fixed_error(self):
        for arguments in (["--help"], ["demo.json"], ["--demo", "extra"], ["--demo", "--demo"]):
            with self.subTest(arguments=arguments):
                stdout, stderr = io.BytesIO(), io.BytesIO()
                with mock.patch.object(cli, "audit") as auditor:
                    self.assertEqual(cli.main(arguments, NoRead(), stdout, stderr), 2)
                auditor.assert_not_called()
                self.assertEqual(stdout.getvalue(), b"")
                self.assertEqual(stderr.getvalue(), b'{"error":"usage","schema":"categorical-drift-error/1"}\n')

    def test_exact_byte_limit_and_single_bounded_read(self):
        raw = _DEMO + b" " * (65_536 - len(_DEMO))
        code, stdout, stderr, stdin = self.invoke(raw)
        self.assertEqual(code, 0)
        self.assertTrue(stdout.endswith(b"\n"))
        self.assertEqual(stderr, b"")
        self.assertEqual(stdin.sizes, [65_537])
        for extra in (b" ", b" " * 100):
            with self.subTest(extra_bytes=len(extra)):
                with mock.patch.object(cli, "audit") as auditor:
                    self.assert_error(raw + extra)
                auditor.assert_not_called()

    def test_duplicate_decoded_keys_at_both_object_levels(self):
        for raw in (
            b'{"reference":{"a":4},"reference":{"a":4},"current":{"a":2,"b":2}}',
            b'{"reference":{"a":2,"a":2},"current":{"a":2,"b":2}}',
            b'{"reference":{"a":2,"\\u0061":2},"current":{"a":2,"b":2}}',
            b'{"reference":{"a":4},"current":{"b":2,"\\u0062":2}}',
        ):
            with self.subTest(raw=raw):
                self.assert_error(raw)

    def test_float_and_nonfinite_tokens_are_rejected(self):
        for token in (b"1.0", b"1e0", b"1E+0", b"-1.0", b"NaN", b"Infinity", b"-Infinity"):
            with self.subTest(token=token):
                self.assert_error(b'{"reference":{"a":' + token + b'},"current":{"a":1}}')

    def test_integer_lexical_bound_and_semantic_bounds(self):
        for token in (b"10000000", b"-10000000", b"1" * 60_000, b"1000001", b"-1", b"true", b"false"):
            with self.subTest(token_size=len(token), token_prefix=token[:10]):
                self.assert_error(b'{"reference":{"a":' + token + b'},"current":{"a":1}}')
        code, stdout, stderr, _stdin = self.invoke(b'{"reference":{"a":1000000},"current":{"a":1}}')
        self.assertEqual((code, stderr), (0, b""))
        self.assertEqual(json.loads(stdout)["reference_total"], 1_000_000)

    def test_utf8_bom_and_surrogates_are_rejected_without_input_echo(self):
        for raw in (
            b"\xef\xbb\xbf" + _DEMO,
            b"\xff" + _DEMO,
            b'{"reference":{"\xed\xa0\x80":1},"current":{"a":1}}',
            b'{"reference":{"\\ud800":1},"current":{"a":1}}',
            b'{"reference":{"a":"\\udfff"},"current":{"a":1}}',
        ):
            with self.subTest(raw=raw):
                self.assert_error(raw)

    def test_schema_shapes_and_trailing_documents_are_rejected(self):
        for raw in (
            b"", b"null", b"[]", b"true", b"{}", _DEMO + _DEMO,
            _DEMO + b" x", b'{"reference":{"a":1},"current":{"a":1},"extra":0}',
            b'{"reference":[1],"current":{"a":1}}',
            b'{"reference":null,"current":{"a":1}}',
            b'{"reference":{"a":1},"current":true}',
            b'{"reference":{"a":0},"current":{"a":1}}',
            b'{"reference":{"not allowed":1},"current":{"a":1}}',
        ):
            with self.subTest(raw=raw):
                self.assert_error(raw)

    def test_deep_prefix_is_rejected_before_json_construction(self):
        with mock.patch.object(cli.json, "loads", side_effect=AssertionError("decoder must not run")):
            self.assert_error(b'{"reference":{"a":[[[[[[[[[')
        self.assert_error(b'{"reference":{"a":{"b":1}},"current":{"a":1}}')

    def test_braces_and_escaped_quote_in_string_do_not_increase_depth(self):
        raw = b'{"reference":{"a":1},"current":{"\\\"[{}]":1}}'
        decoder = cli.json.loads
        with mock.patch.object(cli.json, "loads", wraps=decoder) as parser:
            self.assert_error(raw)
        parser.assert_called_once()

    def test_malformed_escape_and_json_are_rejected(self):
        for raw in (
            b'{"reference":{"\\q":1},"current":{"a":1}}',
            b'{"reference":{"\\u00zz":1},"current":{"a":1}}',
            b'{"reference":{"a":1,},"current":{"a":1}}',
            b'{"reference":{"a":1},"current":{"a":1}]',
            b'{"reference":{"a":1},"current":{"a":1}}"',
        ):
            with self.subTest(raw=raw):
                self.assert_error(raw)

    def test_read_failure_and_nonbinary_read_are_io_errors(self):
        for stdin in (ReadError(), io.StringIO("private input")):
            with self.subTest(stream=type(stdin).__name__):
                stdout, stderr = io.BytesIO(), io.BytesIO()
                self.assertEqual(cli.main([], stdin, stdout, stderr), 2)
                self.assertEqual(stdout.getvalue(), b"")
                self.assertEqual(stderr.getvalue(), b'{"error":"io_error","schema":"categorical-drift-error/1"}\n')

    def test_unavailable_default_binary_stdin_is_io_error(self):
        stdout, stderr = io.BytesIO(), io.BytesIO()
        with mock.patch.object(cli.sys, "stdin", io.StringIO("private input")):
            self.assertEqual(cli.main([], stdout=stdout, stderr=stderr), 2)
        self.assertEqual(stdout.getvalue(), b"")
        self.assertEqual(stderr.getvalue(), b'{"error":"io_error","schema":"categorical-drift-error/1"}\n')

    def test_output_errors_and_partial_delivery_keep_nonzero_status(self):
        for mode in ("raise", "short", "none", "bool", "flush"):
            with self.subTest(mode=mode):
                stdout, stderr = FailedWriter(mode), io.BytesIO()
                self.assertEqual(cli.main([], io.BytesIO(_DEMO), stdout, stderr), 2)
                self.assertEqual(stdout.write_calls, 1)
                self.assertEqual(stdout.close_calls, 0)
                self.assertEqual(stderr.getvalue(), b'{"error":"io_error","schema":"categorical-drift-error/1"}\n')
                if mode == "short":
                    self.assertEqual(len(stdout.data), 3)
                    self.assertEqual(stdout.flush_calls, 0)
                elif mode == "flush":
                    self.assertTrue(stdout.data.endswith(b"\n"))
                    self.assertEqual(stdout.flush_calls, 1)

    def test_unavailable_default_binary_stdout_is_io_error(self):
        stderr = io.BytesIO()
        with mock.patch.object(cli.sys, "stdout", io.StringIO()):
            self.assertEqual(cli.main([], io.BytesIO(_DEMO), stderr=stderr), 2)
        self.assertEqual(stderr.getvalue(), b'{"error":"io_error","schema":"categorical-drift-error/1"}\n')

    def test_unwritable_error_stream_preserves_failure_status(self):
        for mode in ("raise", "short", "none", "bool", "flush"):
            with self.subTest(mode=mode):
                stderr = FailedWriter(mode)
                self.assertEqual(cli.main(["bad"], NoRead(), io.BytesIO(), stderr), 2)
                self.assertEqual(stderr.close_calls, 0)
        with mock.patch.object(cli.sys, "stderr", io.StringIO()):
            self.assertEqual(cli.main(["bad"], NoRead(), io.BytesIO()), 2)

    def test_numeric_failure_has_fixed_payload_and_exit_three(self):
        for failure in (ValueError("numeric_error"), OverflowError("private detail")):
            with self.subTest(failure=type(failure).__name__):
                with mock.patch.object(cli, "audit", side_effect=failure):
                    self.assert_error(_DEMO, "numeric_error", 3)

    def test_failed_default_stdout_quiesces_real_buffered_layers(self):
        for size, partial, close_error in ((8192, False, False), (1, False, False),
                                            (8192, True, False), (8192, False, True)):
            with self.subTest(size=size, partial=partial, close_error=close_error):
                raw, binary, text = buffered_failure(size, partial, close_error)
                stderr = io.BytesIO()
                try:
                    with mock.patch.object(cli.sys, "stdout", text):
                        status = cli.main(["--demo"], stdin=NoRead(), stderr=stderr)
                    self.assertEqual(status, 2)
                    self.assertEqual(stderr.getvalue(), b'{"error":"io_error","schema":"categorical-drift-error/1"}\n')
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
                    with mock.patch.object(cli.sys, "stderr", text):
                        status = cli.main(["bad"], stdin=NoRead(), stdout=stdout)
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
        for role in ("stdout", "stderr"):
            with self.subTest(role=role):
                raw, binary, text = buffered_failure()
                try:
                    if role == "stdout":
                        status = cli.main(["--demo"], NoRead(), binary, io.BytesIO())
                    else:
                        status = cli.main(["bad"], NoRead(), io.BytesIO(), binary)
                    self.assertEqual(status, 2)
                    self.assertFalse(raw.closed or binary.closed or text.closed)
                    self.assertEqual(raw.write_calls, 1)
                finally:
                    dispose_fixture(raw, binary, text)
        healthy = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        try:
            with mock.patch.object(cli.sys, "stdout", healthy):
                status = cli.main(["bad"], stdin=NoRead(), stderr=io.BytesIO())
            self.assertEqual(status, 2)
            self.assertFalse(healthy.closed or healthy.buffer.closed)
        finally:
            healthy.close()


if __name__ == "__main__":
    unittest.main()
