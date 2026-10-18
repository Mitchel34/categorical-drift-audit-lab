# Categorical Drift Audit Lab measured results

The authoritative numeric record is [results/evaluation.json](results/evaluation.json). It preserves the exact original stdout bytes from the single accepted receipt-only export. Every value and check below was compared with that saved output; no evaluation, test or demo was repeated to prepare these files.

The single production evaluation completed six fixed synthetic count comparisons with six audit calls, retaining 26 numeric metrics and ten passing integrity checks. The ordinary suite passed all 45 tests, and both tiny demo paths produced identical bytes. Clean offline installation and public delivery remain pending.

## Retained scores

| Case | Total variation | JSD bits | Novel-current mass | Missing-reference mass |
|---|---:|---:|---:|---:|
| identical | 0.0 | 0.0 | 0.0 | 0.0 |
| proportional | 0.0 | 0.0 | 0.0 | 0.0 |
| balanced_shift | 0.5 | 0.18872187554086717 | 0.0 | 0.0 |
| novel_support | 0.25 | 0.1379253809700299 | 0.25 | 0.0 |
| missing_support | 0.25 | 0.1379253809700299 | 0.0 | 0.25 |
| disjoint | 1.0 | 1.0 | 1.0 | 1.0 |

`case_count = 6`; `production_audit_calls = 6`. These two integer counters plus the 24 scores above are the complete 26-metric record. Values are copied without rounding, clipping, recomputation or replacement.

## Retained integrity checks

| Check | Passed |
|---|---|
| identical_oracle | true |
| proportional_oracle | true |
| balanced_shift_oracle | true |
| novel_support_oracle | true |
| missing_support_oracle | true |
| disjoint_oracle | true |
| bounded_scores | true |
| symmetric_pair | true |
| proportional_invariance | true |
| complete_accounting | true |

## Evaluation scope and operational resources

Absolute numerical tolerance was 1e-12, relative tolerance zero. The fixed examples check the implementation against literal rational and independent entropy identities; they do not establish statistical significance, a drift threshold, model quality, causality or general production reliability. Counts are normalized independently, explicit zero keys have zero mass, and Jensen–Shannon output is divergence in bits without a square root.

| Retained fact | Value | Scope |
|---|---:|---|
| Conservative CPU charge, seconds | 10.0 | At least the full admitted reservation; not measured elapsed CPU or a refundable allowance |
| Measured CPU before final receipt/database closeout, seconds | 0.09092199999999998 | Lower-bound observation; not full-operation usage |
| Receipt conservative peak memory, bytes | 75415552 | Sum of process high-water marks at the receipt's scope; not simultaneous RSS or hard memory containment |
| Wrapper CPU before final terminal, seconds | 0.25684 | Parent and waited-child cumulative CPU before final terminal/outer shutdown; a lower-bound observation |
| Wrapper conservative memory, bytes | 76972032 | Parent plus waited-child high-water marks at the wrapper's scope; not simultaneous RSS or hard containment |
| Receipt elapsed wall, seconds | 0.11479320799116977 | Ends before final receipt/database closeout |
| Wrapper wall from source entry, seconds | 0.2655469170131255 | Prefix observation before wrapper terminal/outer shutdown; excludes earlier interpreter startup |
| Tool-reported wall, seconds | 0.179788898 | A separate observed clock; differs from wrapper timing |

The different wall observations remain distinct; none is asserted to be an inclusive whole-route timer or a performance benchmark. The qualified operational ceilings were one compute thread plus one supervisor, 128 MiB, 10 CPU seconds and 30 wall seconds. The runner reserved 0.25 CPU seconds for closeout, leaving a 9.75-second run allowance. These operational controls do not imply hard containment against hostile code.

## Reproducibility and retained evidence

The unchanged shared core defines both the library auditor and the frozen six-case evaluator. Ordinary tests and the receipt-only exporter do not run the full evaluator. The accepted public JSON contains the frozen seven-key allowlist, all 26 retained metrics, the ten retained checks, the evaluated core digest and four fixed limitations: descriptive empirical counts only; six fixed examples; binary64 tolerance 1e-12; operational resource bounds rather than hard containment. The exporter copied the retained receipt data without importing the core or recomputing scores. The saved original JSON remains authoritative for numeric types, values and signed zero. Raw receipts and private runtime identities are excluded from the public files. Missing or failed evidence is never reconstructed or replaced by a repeated evaluation.

`evaluation_source_sha256`: `95df0d60bf85091b61ef5a6d5518f62573395775e1880e8dd23d5903d7e26220`

## Receipt-only export observations

The exporter ran once, exited successfully and produced 1,561 bytes of stdout with empty stderr. Its owned child was reaped and its observed process group closed. Independent review accepted all 26 typed metric values, ten ordered Boolean checks and the exact public field set against the retained data. This export parsed and copied saved data; it did not perform a second scientific evaluation.

| Retained export fact | Value | Scope |
|---|---:|---|
| Aggregate CPU before final terminal, seconds | 0.16237000000000001 | Supervisor and waited child; prefix observation excluding final terminal serialization/write and outer shutdown |
| Child CPU from wait4, seconds | 0.04208 | Waited direct child only; included in aggregate CPU |
| Operational memory observation, bytes | 57081856 | Parent high-water mark plus observed child peak; not simultaneous RSS or hard whole-tree containment |
| Controller wall from source entry, seconds | 0.17179087499971502 | Prefix observation; excludes earlier interpreter startup and final terminal/outer shutdown |
| Tool-reported wall, seconds | 0.085635187 | Separate observed clock; numerical discrepancy with controller timing remains unresolved |

The separate export allocation was two aggregate CPU seconds and ten wall seconds, including eight active and two closeout seconds, with one compute thread and a 128 MiB operational memory ceiling. Prior evaluation and ordinary allowances were not renewed or refunded. The export wall observations remain distinct; neither is asserted to be an inclusive whole-route timer. Process, memory, output and disk observations provide operational bounds, without a hard containment claim.

Clean offline installation and publication remain pending separate admission and verification. The recorded tests, evaluation and export do not establish those later outcomes.
