# Categorical Drift Audit Lab installation verification

One offline installation completed and passed independent artifact, output, custody and resource review. [results/installation.json](results/installation.json) is the exact reviewed sanitized facts file and the authoritative installation record. No installation, evaluation, genuine receipt export, test or demo was repeated to prepare this documentation.

This later record supplies the installation status after the earlier evaluation/export snapshot in [RESULTS.md](RESULTS.md), which is preserved unchanged. Publication and independent remote verification remain pending.

## Verified route and scope

The recorded runtime was Python 3.14.7 with pip 26.2.1. One pip wheel invocation built the local dependency-free package with no index, dependencies, build isolation or cache. A fresh virtual environment used its interpreter-bundled pip and installed that exact local wheel offline. The saved evidence does not independently count the build backend's internal calls. Python 3.11 is the declared minimum; no other Python version was tested.

All 45 unchanged installed ordinary tests passed from outside the source tree: six core tests, twenty CLI tests and nineteen exporter tests, with no failures, errors or skips. Source `PYTHONPATH` was absent. The checks guarded the full production evaluation and its independent oracle from execution; the genuine receipt exporter was not rerun. A fresh exporter import did not load the core.

Two small installed entry checks passed: the module's `--demo` route used its built-in static fixture, and the installed console-script source received stdin. Both ran through reviewed runpy wrappers under the fresh environment interpreter and produced identical 532-byte outputs with empty stderr. Installed script bytes and executable mode were verified; direct OS shebang execution was not independently tested.

| Verified artifact fact | Count |
|---|---:|
| Wheel entries | 9 |
| Installed project RECORD entries | 13 |
| Installed project bytecode entries | 0 |
| Bootstrap pip RECORD entries | 885 |
| Accounted generated bootstrap bytecode entries | 404 |

Wheel entries, installed project bytes and RECORD coverage were verified against the unchanged package sources. Bootstrap source/metadata bytes and the retained bytecode names/hashes were accounted for separately. Bootstrap bytecode semantics or reproducibility were not verified. The fifteen source files totaling 122,994 bytes were unchanged through installation; the later documentation-only additions do not alter those tested execution inputs.

## Resources and measurement limits

The separate private allocation was 60 CPU seconds, with 55 active and five closeout wall seconds, one compute thread and a 268,435,456-byte operational memory limit. That reservation is distinct from measured consumption and was retained in full. Earlier ordinary, evaluation and export allowances were not renewed or refunded.

| Saved installation prefix field | Value |
|---|---:|
| aggregate_cpu_seconds | 14.147867249999997 |
| conservative_child_cpu_seconds | 6.262494249999999 |
| supervisor_cpu_seconds | 7.8853729999999995 |
| wall_seconds | 12.36352283298038 |
| operational_memory_bytes | 215826432 |
| parent_peak_rss_bytes | 72679424 |
| observed_child_frontier_peak_bytes | 143147008 |
| observed_child_peak_sum_bytes | 143147008 |

These observations cover the sequence prefix and exclude final receipt serialization/writing, outer process shutdown and registry closeout. Wall time is a prefix interval, without an inclusive end-to-end timing claim. CPU combines the supervisor prefix with conservative observed-child accounting: descendant waited CPU may double count, and unseen transient processes plus excluded intervals prevent complete CPU accounting. Memory combines the parent's high-water mark and conservative observed child frontier peak; it does not represent simultaneous RSS or an OS hard limit.

All twelve direct child steps were reaped and all observed owned groups closed. Bounded venv diagnostic retention omitted 57 custody entries and one memory entry; other steps had zero diagnostic omissions. Final normal reaping and group closure evidence remained retained. This is sampled operational evidence: transient descendants can escape observations, the trace is not lossless, and no OS hard containment, atomic heavy exclusion or global host idleness is established.

## Evidence limits

Independent review reconciled saved files and actual outputs without repeating the installation. Saved tool captures are retained records and are not independent platform attestations. Effective approval policy, client overrides, full automated approval review and billing remain unverified. The installed tests and hand-sized entry checks establish their recorded scope; they do not prove testing of other versions, operating systems or direct shebang execution.

No dependency download, paid CI/API use, credential or security/configuration change, new license grant or hosted workflow was part of this installation. Original source and sanitized results are the public candidate; raw receipts and private orchestration evidence remain private.
