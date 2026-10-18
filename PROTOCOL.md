# Categorical Drift Audit Lab protocol

Protocol version: 1, candidate for independent plan review. No measured results are included.

This small Python standard-library tool compares two empirical categorical count distributions. It reports total variation, base-2 Jensen–Shannon divergence, novel-current mass and missing-reference mass. It supplies descriptive arithmetic only: no model, training, significance test, drift threshold, causal conclusion or model-quality claim.

## Library input and validation

The public function is `categorical_drift_audit_lab.core.audit(reference, current)`. The package initializer declares version metadata only; it does not import core or trigger evaluation. Each argument must have exact built-in type `dict`; subclasses, other mapping types and arbitrary objects are rejected. Each maps category strings to counts. Counts have exact type `int`, so Boolean values are invalid. Each side has 1–64 declared keys, counts from 0 through 1,000,000 inclusive, and a total from 1 through 1,000,000 inclusive. The union has at most 128 declared keys. Each category has exact type `str` and matches ASCII `[A-Za-z0-9][A-Za-z0-9_.-]{0,31}`. No coercion or normalization occurs. Validate both complete inputs before computing scores; never mutate either argument. The pure core imports only math; identifier validation uses bounded ASCII character checks rather than a regex-module import.

Validation failure raises `ValueError("invalid_input")`. All validation failures share that fixed message; do not echo input, category names or exception details. Validation order is reference shape, current shape, each reference item in insertion order, each current item in insertion order, positive bounded totals, then union size. Ordering affects no error payload because all validation messages are identical. Valid unequal totals are normalized independently.

An absent category and an explicit zero count both have zero empirical probability. Declared keys and positive-count support are distinct. Preserve zero keys in the declared union, include them in category rows, and exclude them from positive support and novel/missing lists. No smoothing, pseudocounts, implicit OTHER group or omitted positive mass.

## Arithmetic and exact output schema

Let `categories = sorted(set(reference) | set(current))`, using ascending ASCII code points. Let integer totals be `R` and `C`. For each category in that order, `p = reference.get(category, 0) / R`, `q = current.get(category, 0) / C`, and `m = (p + q) / 2.0`. Use ordinary Python binary64 division and arithmetic. Use `math.fsum` for every probability or score accumulation, with terms supplied in that same category order.

- `total_variation = 0.5 * fsum(abs(p-q))`.
- `jsd_bits = 0.5 * fsum(p*log2(p/m) for p>0) + 0.5 * fsum(q*log2(q/m) for q>0)`. The two side sums are separate and are added in reference-then-current order. A zero term contributes nothing; never evaluate `log2(0)` or `0/0`.
- `novel_current_mass = fsum(q for p==0 and q>0)`.
- `missing_reference_mass = fsum(p for q==0 and p>0)`.

The result is an exact-key dictionary:

| Key | Value |
|---|---|
| `schema` | literal `categorical-drift-audit/1` |
| `reference_total`, `current_total` | exact positive integer totals |
| `reference_support`, `current_support` | counts of strictly positive categories, integers |
| `declared_union_size` | integer number of category rows, including zeros |
| `total_variation`, `jsd_bits`, `novel_current_mass`, `missing_reference_mass` | finite binary64 scores |
| `novel_categories` | sorted categories with `p==0` and `q>0` |
| `missing_categories` | sorted categories with `q==0` and `p>0` |
| `categories` | sorted list of the exact row objects below |

Each category row has exactly `category` (string), `reference_count` (integer), `current_count` (integer), `reference_probability` (finite float) and `current_probability` (finite float). Missing counts are represented as integer zero. Totals/support, lists and rows explain scores; they are not additional measured evaluation metrics.

Never round, clip, clamp, smooth or substitute scores to force a check to pass. If an arithmetic result is nonfinite, raise `ValueError("numeric_error")`; this is an honest failure, not a repaired result. Preserve finite raw values, including signed zero. Mathematical range checks may use the validation tolerance below, but do not modify the underlying values. JSON preserves the round-trip binary64 values; presentation does not replace them with formatted decimal summaries.

## Bounded JSON command line

The module command is `python -m categorical_drift_audit_lab`. The installed console command is `categorical-drift-audit`. With no arguments it reads one JSON document from stdin and writes one result JSON document to stdout followed by a newline. `--demo` uses the static demo below and reads no stdin. No file-path argument, network route, interactive prompt or evaluator command is provided.

Stdin is binary UTF-8, without a BOM, at most 65,536 bytes. Read at most 65,537 bytes once; excess is an error. Decode strictly. Accept surrounding JSON whitespace, reject trailing non-whitespace and multiple documents. A string-aware lexical pass rejects structural nesting deeper than two container levels before parsing; braces and brackets inside strings do not change depth. The only accepted containers are the root object and its two count objects. Escape syntax is still validated by the JSON parser. Input must reach EOF; the admitted outer wall limit handles an open/blocking stream. The CLI does not claim an independent stdin timeout.

The root has exactly `reference` and `current`, both count objects. Reject duplicate JSON keys at every object level, unknown root fields, arrays, null, Boolean values, all float literals including `1.0` and `1e0`, nonfinite constants, invalid UTF-8, unpaired surrogates and malformed/deep JSON. JSON escapes that decode to valid ASCII category names are accepted; decoded duplicate names remain duplicates. Integer lexical tokens longer than seven decimal digits excluding a leading minus are rejected before integer conversion; semantic validation rejects negatives, oversize values and zero totals. This bounds parsing independently of the interpreter's general integer-conversion setting.

CLI success: exit 0, one sorted-key compact ASCII JSON result plus newline on stdout, empty stderr. Failures before output begins leave stdout empty. They write one compact JSON error plus newline on stderr, with exactly `schema: "categorical-drift-error/1"` and `error` from this finite set:

| Error | Exit | Meaning |
|---|---:|---|
| `usage` | 2 | Any arguments other than no arguments or exactly `--demo` |
| `invalid_input` | 2 | Byte, UTF-8, lexical, JSON, schema, category or count validation failure |
| `io_error` | 2 | Input/output `OSError`, including unavailable binary stdin or failed output |
| `numeric_error` | 3 | Nonfinite score or arithmetic failure after valid input |

No traceback, raw input, path or platform exception string is emitted. A failed stdout write may leave a partial document, and a failed stderr stream may make the error message itself unwritable; retain the nonzero exit without claiming delivery. `KeyboardInterrupt` and interpreter termination are outside the finite input-error contract.

## Literal evaluation fixtures and hand oracles

Evaluate exactly these six pairs, once each, in this order. The production entry `evaluate()` is defined in the same pure `core.py` file as `audit`; no second algorithm copy exists. Module import defines functions/constants and performs no audit. `evaluate()` invokes `audit` exactly six times and retains the six outputs for every subsequent comparison. No PRNG, seed, sweep, fit, repeat, rescaling call, swap call or hidden preliminary audit.

Let `H2(x) = -x*log2(x) - (1-x)*log2(1-x)`, evaluated directly at the two literal arguments 1/4 and 1/8. This independent two-term entropy identity does not invoke or sum over the production auditor. Let `Jb = 1-H2(1/4)` and `Jn = H2(1/8)-H2(1/4)/2`. Rational TV and mass expectations below are hand-derived. Oracle values are prospective expressions, not measured results.

| Case | Reference | Current | TV | JSD bits | Novel mass | Missing mass | R,C | Supports R,C | Union |
|---|---|---|---:|---|---:|---:|---|---|---:|
| `identical` | `{a:2,b:2}` | `{a:2,b:2}` | 0 | 0 | 0 | 0 | 4,4 | 2,2 | 2 |
| `proportional` | `{a:1,b:3}` | `{a:2,b:6}` | 0 | 0 | 0 | 0 | 4,8 | 2,2 | 2 |
| `balanced_shift` | `{a:3,b:1}` | `{a:1,b:3}` | 1/2 | `Jb` | 0 | 0 | 4,4 | 2,2 | 2 |
| `novel_support` | `{a:4}` | `{a:3,b:1}` | 1/4 | `Jn` | 1/4 | 0 | 4,4 | 1,2 | 2 |
| `missing_support` | `{a:3,b:1}` | `{a:4}` | 1/4 | `Jn` | 0 | 1/4 | 4,4 | 2,1 | 2 |
| `disjoint` | `{a:4}` | `{b:4}` | 1 | 1 | 1 | 1 | 4,4 | 1,1 | 2 |

Comparison tolerance is absolute `1e-12`, relative tolerance zero: `abs(actual-expected) <= 1e-12`, with an explicit finite-number requirement. Counts, support, sizes, names, accounting and Booleans use exact comparison, never numeric tolerance.

Exactly 26 numeric metrics are returned in `metrics`:

| Case | Four metric keys, in TV/JSD/novel/missing order |
|---|---|
| identical | `identical_tv`, `identical_jsd_bits`, `identical_novel_mass`, `identical_missing_mass` |
| proportional | `proportional_tv`, `proportional_jsd_bits`, `proportional_novel_mass`, `proportional_missing_mass` |
| balanced_shift | `balanced_shift_tv`, `balanced_shift_jsd_bits`, `balanced_shift_novel_mass`, `balanced_shift_missing_mass` |
| novel_support | `novel_support_tv`, `novel_support_jsd_bits`, `novel_support_novel_mass`, `novel_support_missing_mass` |
| missing_support | `missing_support_tv`, `missing_support_jsd_bits`, `missing_support_novel_mass`, `missing_support_missing_mass` |
| disjoint | `disjoint_tv`, `disjoint_jsd_bits`, `disjoint_novel_mass`, `disjoint_missing_mass` |

For every case the four metrics directly copy `total_variation`, `jsd_bits`, `novel_current_mass` and `missing_reference_mass` from its retained output. The remaining keys are exact integers `case_count=6` and `production_audit_calls=6`. Increment a local call counter immediately before each of the six calls; do not simply emit a constant as evidence of invocation count. No durations, oracle values, category fields or additional measurements are inserted into `metrics`.

Exactly ten check objects, each with exactly `name` and Boolean `passed`, appear in this order:

1. `identical_oracle`: all four scores match that row's independent expected scores within tolerance, and totals, supports, declared union, rows and novel/missing lists match the literal inputs exactly. Row probabilities match literal count/total fractions within tolerance.
2. `proportional_oracle`: the same predicate for proportional.
3. `balanced_shift_oracle`: the same predicate for balanced_shift.
4. `novel_support_oracle`: the same predicate for novel_support; novel list is `["b"]`, missing list empty.
5. `missing_support_oracle`: the same predicate for missing_support; novel list empty, missing list `["b"]`.
6. `disjoint_oracle`: the same predicate for disjoint; novel list `["b"]`, missing list `["a"]`.
7. `bounded_scores`: all 24 retained score values are finite numbers of exact built-in numeric type excluding bool, and each is in `[-1e-12, 1+1e-12]`. This tolerance checks arithmetic only and never changes a score.
8. `symmetric_pair`: already retained novel_support and missing_support outputs have matching TV/JSD within tolerance; novel mass of each matches missing mass of its counterpart. No extra swapped-input call occurs.
9. `proportional_invariance`: the four already retained identical and proportional scores match within tolerance, and the literal proportional integer counts satisfy current-count = 2*reference-count for both categories. This establishes the specified examples only, not exhaustive scaling invariance.
10. `complete_accounting`: exact case names/order, six retained outputs, call counter 6, literal 20 supplied key/count entries, total 12 union-category positions, exact 26 metric keys, integer accounting values 6, and each output's exact result schema and row order. The ten check-name schema is independently checked by tests/export validation; it is not asserted by a self-referential partial list during construction.

For oracle checks, the empty novel/missing lists apply to identical, proportional and balanced_shift. Every row list is `["a","b"]`. Row counts are literal counts with missing keys filled by zero. `complete_accounting` checks each output key set against the output schema above. Checks return their actual Boolean outcomes; no outcome is forced to true. The production return object has exactly `checks` and `metrics`.

## Demo and focused ordinary tests

One static demo uses reference `{"a":4}` and current `{"a":2,"b":2}`. Its hand oracles are TV=1/2, JSD=`H2(1/4)-1/2`, novel mass=1/2, missing mass=0; totals=4/4, positive supports=1/2 and novel category b. The fixture file `examples/demo.json` contains that exact root input. `--demo` and stdin on that file must produce the same result bytes. No other demo case is introduced.

Ordinary verification consists of one serial `unittest` suite plus exactly two admitted demo CLI paths. Tests never call `evaluate()` or dynamically load the full evaluation function. They do not iterate over the complete six-case production fixture table. The suite has these focused groups:

- Library: the demo hand oracle, input non-mutation, deterministic insertion-order independence, explicit-zero support behavior, one count-rescaling comparison and one argument-swap comparison. The separate structural-property pair is reference `{"a":1,"b":2,"c":1}`, current `{"a":1,"b":1,"c":2}`. Compare that retained output to the output after multiplying every count on both sides by exactly two, and to one reversed-argument output. Reordering uses those same literal counts in reversed insertion order. Explicit-zero behavior uses the demo pair with `"z":0` added to both sides: z remains a declared row with zero probabilities and belongs to neither positive support nor novel/missing lists. These tests do not reproduce the production evaluation matrix.
- Invalid library input: table-driven exact-type, identifier, count, total, support-bound and empty-input failures, including bool and dict subclasses. Verify the fixed message.
- Streams/CLI: in-process main entry with injected binary input/output streams; accepted whitespace/escaped ASCII and invalid duplicate/unknown keys, floats, constants, UTF-8, BOM, trailing document, nested containers, malformed escapes, 65,536/65,537 byte boundary and read/write failures. The 65,536-byte valid document is padded with JSON whitespace. A short prefix that declares deep nesting is rejected before JSON construction. No external process per test case.
- Receipt exporter: explicitly labelled invented synthetic test receipts; exact pinned digest success and rejection of changed bytes, wrong identity/source/counts, missing/duplicate/nonfinite metrics/checks, private-field leakage and a failure receipt. This tests parsing/copying only, with no evaluator import or invocation.
- Packaging metadata/file allowlist is statically inspected before the later separate installation operation; ordinary tests do not build, install or create an environment.

The ordinary suite and both tiny demo invocations share one pooled allowance: one compute thread, at most 128 MiB operational memory, 20 aggregate CPU seconds and 30 aggregate wall seconds. All startup/closeout scope is owner-defined and retained; a second invocation does not reset the allowance. No execution is implied by this protocol. A failed/uncertain attempt is retained for owner reconciliation, never automatically repeated.

## Planned package and offline installation

Package name `categorical-drift-audit-lab`, import `categorical_drift_audit_lab`, version `0.1.0`, Python requirement `>=3.11`. The current qualified interpreter is the validation target; no claim of tested cross-version or cross-platform behavior follows. Runtime dependencies are empty. No license metadata, badge or LICENSE file is added.

Planned original source layout: `categorical_drift_audit_lab/{__init__,__main__,core,cli,export}.py`, `tests/{test_core,test_cli,test_export}.py`, `examples/demo.json`, `README.md`, `PROTOCOL.md`, `pyproject.toml` and `_build_backend.py`. Generated public results are added only from the genuine reviewed retained receipt. There is no hosted demo, CI workflow, service, downloaded data or external framework.

The small standard-library build backend implements `build_wheel` and an empty `get_requires_for_build_wheel`, with build-system `requires=[]` and backend-path `.`. It packages only the five module files and distribution metadata into a `py3-none-any` wheel. It never imports core/evaluate, reads private evidence, includes tests/results/private files or uses a package index. Metadata includes the console entry point and no Requires-Dist/license value. RECORD uses URL-safe unpadded SHA256 and exact byte sizes; the RECORD row itself has empty hash/size. Paths, ordering and ZIP timestamps are deterministic. No source distribution or editable install is required.

The separately admitted installation operation will build one local wheel with existing pip using `--no-index --no-deps --no-build-isolation --no-cache-dir`, create one fresh private venv with its interpreter-bundled pip, install only that exact local wheel with `--no-index --no-deps --no-cache-dir`, and verify imports plus module/console CLI behavior from a directory outside the source tree with source PYTHONPATH absent. It must retain source/wheel/file hashes and resolved installed module paths. The owner pins the exact executable paths, finite commands, resource ceilings and existing-tool qualifications before its once-only dispatch. These steps are prospective; no build, venv, package install or network operation is admitted here.

## Retained results and publication

Export only from the exact genuine retained production receipt and its owner-pinned SHA256. The exporter never imports core or calls evaluate, never fabricates a receipt and never treats test fixtures as measured evidence. The private adapter/binding plan separately specifies the source-checked production receipt fields and owner completion evidence; those private identities and paths do not belong in public files.

The intended public JSON contains exactly `schema: "categorical-drift-evaluation/1"`, `protocol_version: 1`, `outcome`, `metrics`, `checks`, `evaluation_source_sha256` and `limitations`. The last field is a fixed string list: descriptive empirical counts only; six fixed examples; binary64 tolerance 1e-12; operational resource bounds rather than hard containment. Metrics/checks are copied without recomputation, rounding or renaming. Only the reviewed core source digest is public; raw receipts, process IDs, task/lease/operation identities, paths and host/configuration data are excluded. Markdown results, if emitted, derive from the same parsed payload, include all 26 values and ten Boolean outcomes and preserve JSON as the authoritative numeric record.

Failure receipts and adverse results must remain private and unmodified even when public delivery is blocked. The qualified production runner retains the actual complete schema-valid metrics/check payload captured within its existing combined 64 KiB output bound, including false checks and complete payloads followed by terminal resource failure. Retention does not change failed status, resource limits, charges or custody requirements. Malformed, incomplete or overflowed output remains null and an explicit evidence gap; it cannot be represented as 26 zero values, passing checks or reconstructed measurements. Do not rerun an evaluation to replace missing results. Public success exporters continue rejecting every failed receipt, including one with retained measurements. Separate project admission remains required before evaluation.

Publication requires passed implementation/tests/evaluation/docs, clean installation outside source, independent complete source/test/evidence/docs/full-history review, separate exact publication admission and independent remote verification of the reviewed commit, tree, file bytes/modes, refs/history, visibility/owner and Actions state. Original source and sanitized results only; no paid CI/API, credentials, configuration/security changes, new schedule or license grant.
