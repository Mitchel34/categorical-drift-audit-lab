"""Bounded binary-JSON command line for the categorical count auditor."""

import json
import sys

from .core import audit


_MAX_INPUT_BYTES = 65_536
_ERROR_SCHEMA = "categorical-drift-error/1"


class _InvalidInput(ValueError):
    """An input failure whose details must not leave the process."""


def _binary_default(stream):
    try:
        binary = stream.buffer
    except (AttributeError, OSError, TypeError, ValueError):
        raise OSError("io_error") from None
    if binary is None:
        raise OSError("io_error")
    return binary


def _read_once(stream):
    try:
        raw = stream.read(_MAX_INPUT_BYTES + 1)
    except (AttributeError, OSError, TypeError, ValueError):
        raise OSError("io_error") from None
    if type(raw) is not bytes:
        raise OSError("io_error")
    if len(raw) > _MAX_INPUT_BYTES:
        raise _InvalidInput
    return raw


def _write_once(stream, payload):
    """A short write is a failure; never retry or claim complete delivery."""
    try:
        written = stream.write(payload)
        if type(written) is not int or written != len(payload):
            raise OSError("io_error")
        stream.flush()
    except (AttributeError, OSError, TypeError, ValueError):
        raise OSError("io_error") from None


def _quiesce_failed_default(owner, binary=None):
    """Discard a failed process-owned output path before shutdown can retry it."""
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
    # Close the raw delivery path first: closing a live buffer could reflush it.
    for stream in (raw, binary, owner):
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass


def _report(error, exit_code, stderr):
    payload = json.dumps(
        {"schema": _ERROR_SCHEMA, "error": error},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii") + b"\n"
    owner = sys.stderr if stderr is None else None
    stream = None
    try:
        stream = _binary_default(owner) if stderr is None else stderr
        _write_once(stream, payload)
    except OSError:
        _quiesce_failed_default(owner, stream)
    return exit_code


def _check_depth(document):
    """Bound container depth before the JSON decoder constructs containers."""
    depth = 0
    in_string = False
    escaped = False
    for character in document:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "{[":
            depth += 1
            if depth > 2:
                raise _InvalidInput
        elif character in "}]":
            depth -= 1
            if depth < 0:
                raise _InvalidInput
    if depth != 0 or in_string:
        raise _InvalidInput


def _integer(token):
    digits = token[1:] if token.startswith("-") else token
    if len(digits) > 7:
        raise _InvalidInput
    return int(token)


def _reject_number(_token):
    raise _InvalidInput


def _has_surrogate(value):
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result or _has_surrogate(key):
            raise _InvalidInput
        if type(value) is str and _has_surrogate(value):
            raise _InvalidInput
        result[key] = value
    return result


def _parse(raw):
    if raw.startswith(b"\xef\xbb\xbf"):
        raise _InvalidInput
    try:
        document = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise _InvalidInput from None
    _check_depth(document)
    try:
        root = json.loads(
            document,
            object_pairs_hook=_object,
            parse_int=_integer,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (ValueError, RecursionError):
        raise _InvalidInput from None
    if type(root) is not dict or set(root) != {"reference", "current"}:
        raise _InvalidInput
    if type(root["reference"]) is not dict or type(root["current"]) is not dict:
        raise _InvalidInput
    return root["reference"], root["current"]


def main(argv=None, stdin=None, stdout=None, stderr=None):
    """Return an exit code, using optional injected binary streams.

    Only an empty argument list or exactly ``["--demo"]`` is accepted. The
    default standard streams must expose their binary ``buffer`` interfaces.
    No input is read in demo or usage-error mode.
    """
    arguments = sys.argv[1:] if argv is None else argv
    if arguments != [] and arguments != ["--demo"]:
        return _report("usage", 2, stderr)

    try:
        if arguments == ["--demo"]:
            reference, current = {"a": 4}, {"a": 2, "b": 2}
        else:
            stream = _binary_default(sys.stdin) if stdin is None else stdin
            reference, current = _parse(_read_once(stream))
        result = audit(reference, current)
        try:
            payload = json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii") + b"\n"
        except (ValueError, ArithmeticError):
            raise ValueError("numeric_error") from None
    except _InvalidInput:
        return _report("invalid_input", 2, stderr)
    except OSError:
        return _report("io_error", 2, stderr)
    except ValueError as error:
        name = "numeric_error" if error.args == ("numeric_error",) else "invalid_input"
        return _report(name, 3 if name == "numeric_error" else 2, stderr)
    except ArithmeticError:
        return _report("numeric_error", 3, stderr)

    owner = sys.stdout if stdout is None else None
    stream = None
    try:
        stream = _binary_default(owner) if stdout is None else stdout
        _write_once(stream, payload)
    except OSError:
        _quiesce_failed_default(owner, stream)
        return _report("io_error", 2, stderr)
    return 0
