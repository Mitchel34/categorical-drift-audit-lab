# Categorical Drift Audit Lab

A small Python standard-library library and JSON command for comparing two empirical categorical count distributions. It reports four descriptive scores and the counts, probabilities and support that explain them.

This is empirical arithmetic. Scores do not establish statistical significance, a drift alert, a causal effect or model quality. The tool does not train or fit a model, select a threshold or use a random seed.

## Current validation status

All 45 ordinary tests passed with no failures, errors or skips. Both static demo command paths passed and produced identical JSON bytes. One production evaluation passed all ten checks across six fixed cases, retaining 26 numeric metrics. The accepted receipt-only export preserves all 26 metrics and ten checks in [results/evaluation.json](results/evaluation.json); [RESULTS.md](RESULTS.md) records their scope and operational measurements. One clean offline installation passed all 45 installed tests and both small installed entry checks on Python 3.14.7 through reviewed runpy wrappers. [INSTALLATION.md](INSTALLATION.md) and [results/installation.json](results/installation.json) record the later installation evidence and its limits; RESULTS.md retains the earlier evaluation/export snapshot. Publication remains pending. Examples and hand oracles below describe the frozen contract. See [PROTOCOL.md](PROTOCOL.md) for the exact schemas, formulas and acceptance checks.

## Library use

Python 3.11 or later is required. There are no runtime dependencies. Import the public function directly from the core module:

```python
from categorical_drift_audit_lab.core import audit

result = audit({"a": 4}, {"a": 2, "b": 2})
```

`result` contains these four scores:

| Field | Meaning |
|---|---|
| `total_variation` | Half the sum of absolute differences between the normalized probabilities |
| `jsd_bits` | Jensen–Shannon divergence using base-2 logarithms; this is the divergence, not its square root |
| `novel_current_mass` | Current probability mass on categories with zero reference probability |
| `missing_reference_mass` | Reference probability mass on categories with zero current probability |

The result schema is `categorical-drift-audit/1`. It also includes each side's integer total and positive support, the declared union size, sorted novel/missing category lists, and sorted category rows with both counts and probabilities. Category order uses ascending ASCII code points. Calculations use binary64 arithmetic and `math.fsum`; finite values are not rounded, clamped or smoothed.

For this one demo, the hand-derived expectations are total variation `1/2`, novel-current mass `1/2`, missing-reference mass `0`, and JSD `H2(1/4) - 1/2` bits, where `H2` is binary entropy. Both totals are four; positive supports are one and two. These are expected values, not measured results.

## Count and JSON bounds

Each library argument must be an exact built-in `dict` with 1–64 keys. Categories are ASCII strings matching `[A-Za-z0-9][A-Za-z0-9_.-]{0,31}`. Counts must be exact integers from zero through 1,000,000; Boolean, float, negative and oversized counts are rejected. Each side must have a positive total no greater than 1,000,000. The declared union has at most 128 categories. Inputs are never mutated or coerced.

Unequal totals are valid: each side is normalized by its own total. An absent category and an explicit zero both have zero probability. Explicit zero keys remain visible in the category rows and declared union, but do not increase positive support or enter novel/missing lists. No pseudocount, smoothing or implicit OTHER category is added.

Library validation raises `ValueError("invalid_input")`. A nonfinite arithmetic result raises `ValueError("numeric_error")` instead of substituting a score.

The CLI accepts exactly one UTF-8 JSON object with exactly `reference` and `current` count objects. Input is limited to 65,536 bytes and two container levels. Duplicate keys, a UTF-8 BOM, unpaired surrogates, arrays, nulls, Boolean values, float literals, nonfinite constants, extra fields and trailing documents are rejected. JSON escapes that decode to valid ASCII category names are accepted; decoded duplicate keys are rejected. Integer tokens have at most seven decimal digits, excluding a leading minus; semantic count rules still apply.

## Command line and the static demo

After installation, use either `python -m categorical_drift_audit_lab` or the `categorical-drift-audit` console command. With no arguments the command reads stdin through EOF:

```sh
python -m categorical_drift_audit_lab < examples/demo.json
```

The exact same static input is available without reading stdin:

```sh
python -m categorical_drift_audit_lab --demo
```

`examples/demo.json` contains reference `{"a":4}` and current `{"a":2,"b":2}`. The two commands produced the same bytes in verification. Success returns exit 0, one compact ASCII JSON result with sorted keys plus a newline on stdout, and empty stderr. There are no file-path arguments, interactive prompts or evaluator commands. A pipe left open can block stdin; the CLI has no independent input timeout.

Errors have exactly the JSON fields `schema` and `error`, with schema `categorical-drift-error/1`, on stderr:

| Error | Exit code | Meaning |
|---|---:|---|
| `usage` | 2 | Arguments other than none or exactly `--demo` |
| `invalid_input` | 2 | Invalid encoding, JSON, structure, category or count |
| `io_error` | 2 | Input/output failure, including unavailable binary stdin |
| `numeric_error` | 3 | Nonfinite score or arithmetic failure after valid input |

No input, path, traceback or platform exception message is echoed. Failures before output starts leave stdout empty. A failed output stream may leave a partial document or prevent delivery of the error message; the command retains a nonzero exit status.

## Packaging and installation

The local standard-library build backend has no build requirements. Its deterministic `py3-none-any` wheel contains only the five package modules and distribution metadata, including the console entry point and SHA256 RECORD entries. The backend reads those source files without importing them. Tests, examples, results, private receipts and orchestration files are excluded from the wheel. No source distribution or editable installation is provided. No license has been selected or granted.

The separate clean-install check passed once using Python 3.14.7 and pip 26.2.1, one local wheel, no package index, no dependencies, no build isolation and no cache. A fresh environment passed 45 installed tests and two small module/console-source checks from outside the source tree with source `PYTHONPATH` absent. Entry checks used reviewed runpy wrappers under that environment interpreter; installed script bytes and mode were verified, while direct OS shebang execution was not independently tested. Python 3.11 is the declared minimum and was not tested. See [INSTALLATION.md](INSTALLATION.md) for the artifact, resource and observation limits.

Focused ordinary tests and the two demo paths are distinct from the production evaluation. The production plan has exactly six fixed synthetic cases, six audit calls, 26 numeric metrics and ten actual Boolean integrity checks. Tests and result export must not invoke or repeat that full evaluation. A success exporter copies only the exact reviewed retained receipt's measurements and checks, without importing the core or recomputing results. Failed receipts remain retained privately and are rejected by public success export. Missing or incomplete measurements remain an explicit evidence gap, never invented zeros or passing checks.

## Receipt-only export

`categorical_drift_audit_lab.export.parse_receipt(raw, pins)` accepts original receipt bytes and a dictionary of trusted bindings. It returns the public result object or raises `ValueError("invalid_receipt")`. It opens no files and imports no auditor. A caller-selected receipt hash alone does not establish provenance: the run's owner must separately verify the completed operation, source and retained terminal evidence before supplying these bindings.

The dictionary has exactly these keys: `receipt_sha256`, `source_sha256`, `proof_sha256`, `runner_sha256`, `benchmark_id`, `lease_id`, `manifest_sha256`, `launch_token`, `reserved_cpu_seconds`, `memory_limit_bytes` and `wall_limit_seconds`. Digests are lowercase SHA256 strings; the benchmark and memory values are integers, CPU/wall values are finite positive numbers, and other bindings are bounded ASCII strings. Memory is 134,217,728 bytes; CPU and wall ceilings are 10 and 30 seconds. These values validate an existing admitted receipt; they do not grant execution.

The module command `python -m categorical_drift_audit_lab.export` requires `--receipt` plus every dictionary key as a flag, replacing underscores with hyphens. For example, `source_sha256` becomes `--source-sha256`. Each flag takes one value and must appear exactly once. CPU/wall arguments use plain decimal syntax of at most 16 characters, without a sign or exponent. The command reads one receipt file, limited to 262,144 bytes, and verifies its raw-byte hash before parsing. It accepts no evaluator fallback, optional help mode or network route.

Success writes one compact JSON document plus newline on stdout and exits 0. Output contains exactly `schema`, `protocol_version`, `outcome`, all 26 copied `metrics`, ten copied `checks`, `evaluation_source_sha256` and fixed `limitations`. Private bindings and host/process details are excluded. Every failed receipt is rejected even when it contains complete retained measurements. Invalid input, bindings, receipt status or I/O returns exit 2 and the fixed error `{"schema":"categorical-drift-export-error/1","error":"invalid_receipt"}` on stderr when writable. Failures before output starts leave stdout empty; failed writes may leave partial output. No raw receipt, argument, path or exception is echoed.
