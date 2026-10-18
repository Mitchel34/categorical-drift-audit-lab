"""Bounded empirical categorical-count arithmetic and its six-case evaluation.

Importing this module performs no audit. The pure evaluation entry point shares
the library implementation and uses only six frozen synthetic count pairs.
"""

import math


_FIRST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
_REST = _FIRST + "_.-"
_SCORES = ("total_variation", "jsd_bits", "novel_current_mass", "missing_reference_mass")
_SUFFIXES = ("tv", "jsd_bits", "novel_mass", "missing_mass")
_RESULT_KEYS = frozenset((
    "schema", "reference_total", "current_total", "reference_support",
    "current_support", "declared_union_size", "total_variation", "jsd_bits",
    "novel_current_mass", "missing_reference_mass", "novel_categories",
    "missing_categories", "categories",
))
_ROW_KEYS = frozenset((
    "category", "reference_count", "current_count",
    "reference_probability", "current_probability",
))
_TOLERANCE = 1e-12


def _validate(reference, current):
    if type(reference) is not dict or not 1 <= len(reference) <= 64:
        raise ValueError("invalid_input")
    if type(current) is not dict or not 1 <= len(current) <= 64:
        raise ValueError("invalid_input")
    for counts in (reference, current):
        for category, count in counts.items():
            if (type(category) is not str or not 1 <= len(category) <= 32
                    or category[0] not in _FIRST
                    or any(character not in _REST for character in category[1:])
                    or type(count) is not int or not 0 <= count <= 1_000_000):
                raise ValueError("invalid_input")
    reference_total = sum(reference.values())
    current_total = sum(current.values())
    if not (1 <= reference_total <= 1_000_000 and 1 <= current_total <= 1_000_000):
        raise ValueError("invalid_input")
    categories = sorted(set(reference) | set(current))
    if len(categories) > 128:
        raise ValueError("invalid_input")
    return reference_total, current_total, categories


def audit(reference, current):
    """Compare exact bounded count dictionaries; preserve raw binary64 scores.

    Raises ValueError('invalid_input') for invalid input and
    ValueError('numeric_error') if arithmetic cannot produce finite scores.
    The inputs are never mutated and no significance claim is made.
    """
    reference_total, current_total, categories = _validate(reference, current)
    rows = []
    try:
        for category in categories:
            reference_count = reference.get(category, 0)
            current_count = current.get(category, 0)
            rows.append({
                "category": category,
                "reference_count": reference_count,
                "current_count": current_count,
                "reference_probability": reference_count / reference_total,
                "current_probability": current_count / current_total,
            })
        pairs = [(row["reference_probability"], row["current_probability"]) for row in rows]
        total_variation = 0.5 * math.fsum(abs(p - q) for p, q in pairs)
        reference_terms = math.fsum(
            p * math.log2(p / ((p + q) / 2.0)) for p, q in pairs if p > 0
        )
        current_terms = math.fsum(
            q * math.log2(q / ((p + q) / 2.0)) for p, q in pairs if q > 0
        )
        jsd_bits = 0.5 * reference_terms + 0.5 * current_terms
        novel_mass = math.fsum(q for p, q in pairs if p == 0 and q > 0)
        missing_mass = math.fsum(p for p, q in pairs if q == 0 and p > 0)
        if not all(math.isfinite(value) for value in (total_variation, jsd_bits, novel_mass, missing_mass)):
            raise ValueError("numeric_error")
    except (ArithmeticError, ValueError):
        raise ValueError("numeric_error") from None
    return {
        "schema": "categorical-drift-audit/1",
        "reference_total": reference_total,
        "current_total": current_total,
        "reference_support": sum(count > 0 for count in reference.values()),
        "current_support": sum(count > 0 for count in current.values()),
        "declared_union_size": len(categories),
        "total_variation": total_variation,
        "jsd_bits": jsd_bits,
        "novel_current_mass": novel_mass,
        "missing_reference_mass": missing_mass,
        "novel_categories": [
            row["category"] for row in rows
            if row["reference_count"] == 0 and row["current_count"] > 0
        ],
        "missing_categories": [
            row["category"] for row in rows
            if row["current_count"] == 0 and row["reference_count"] > 0
        ],
        "categories": rows,
    }


def _near(actual, expected):
    return (type(actual) in (int, float) and math.isfinite(actual)
            and abs(actual - expected) <= _TOLERANCE)


def _entropy(x):
    return -x * math.log2(x) - (1 - x) * math.log2(1 - x)


def _oracle(output, scores, metadata, expected_rows, novel, missing):
    if type(output) is not dict or set(output) != _RESULT_KEYS:
        return False
    if output["schema"] != "categorical-drift-audit/1":
        return False
    if any(type(output[key]) is not float or not _near(output[key], value)
           for key, value in zip(_SCORES, scores)):
        return False
    integer_fields = ("reference_total", "current_total", "reference_support", "current_support", "declared_union_size")
    if any(type(output[key]) is not int or output[key] != value
           for key, value in zip(integer_fields, metadata)):
        return False
    if (type(output["novel_categories"]) is not list or output["novel_categories"] != novel
            or type(output["missing_categories"]) is not list or output["missing_categories"] != missing
            or type(output["categories"]) is not list
            or len(output["categories"]) != len(expected_rows)):
        return False
    for row, expected in zip(output["categories"], expected_rows):
        category, reference_count, current_count, p, q = expected
        if (type(row) is not dict or set(row) != _ROW_KEYS
                or type(row["category"]) is not str or row["category"] != category
                or type(row["reference_count"]) is not int or row["reference_count"] != reference_count
                or type(row["current_count"]) is not int or row["current_count"] != current_count
                or type(row["reference_probability"]) is not float or not _near(row["reference_probability"], p)
                or type(row["current_probability"]) is not float or not _near(row["current_probability"], q)):
            return False
    return True


def evaluate():
    """Return exactly 26 metrics and ten honest checks from six audit calls.

    The production runner is the only admitted evaluation route. Ordinary unit
    tests and receipt exporters never call this function.
    """
    cases = (
        ("identical", {"a": 2, "b": 2}, {"a": 2, "b": 2}),
        ("proportional", {"a": 1, "b": 3}, {"a": 2, "b": 6}),
        ("balanced_shift", {"a": 3, "b": 1}, {"a": 1, "b": 3}),
        ("novel_support", {"a": 4}, {"a": 3, "b": 1}),
        ("missing_support", {"a": 3, "b": 1}, {"a": 4}),
        ("disjoint", {"a": 4}, {"b": 4}),
    )
    quarter_entropy = _entropy(1 / 4)
    eighth_entropy = _entropy(1 / 8)
    balanced_jsd = 1 - quarter_entropy
    novel_jsd = eighth_entropy - quarter_entropy / 2
    expected = (
        ((0, 0, 0, 0), (4, 4, 2, 2, 2),
         (("a", 2, 2, 1 / 2, 1 / 2), ("b", 2, 2, 1 / 2, 1 / 2)), [], []),
        ((0, 0, 0, 0), (4, 8, 2, 2, 2),
         (("a", 1, 2, 1 / 4, 1 / 4), ("b", 3, 6, 3 / 4, 3 / 4)), [], []),
        ((1 / 2, balanced_jsd, 0, 0), (4, 4, 2, 2, 2),
         (("a", 3, 1, 3 / 4, 1 / 4), ("b", 1, 3, 1 / 4, 3 / 4)), [], []),
        ((1 / 4, novel_jsd, 1 / 4, 0), (4, 4, 1, 2, 2),
         (("a", 4, 3, 1.0, 3 / 4), ("b", 0, 1, 0.0, 1 / 4)), ["b"], []),
        ((1 / 4, novel_jsd, 0, 1 / 4), (4, 4, 2, 1, 2),
         (("a", 3, 4, 3 / 4, 1.0), ("b", 1, 0, 1 / 4, 0.0)), [], ["b"]),
        ((1, 1, 1, 1), (4, 4, 1, 1, 2),
         (("a", 4, 0, 1.0, 0.0), ("b", 0, 4, 0.0, 1.0)), ["b"], ["a"]),
    )
    retained = {}
    calls = 0
    for name, reference, current in cases:
        calls += 1
        retained[name] = audit(reference, current)
    metrics = {}
    for name, reference, current in cases:
        for key, suffix in zip(_SCORES, _SUFFIXES):
            metrics[name + "_" + suffix] = retained[name][key]
    metrics["case_count"] = len(cases)
    metrics["production_audit_calls"] = calls
    checks = []
    for case, oracle in zip(cases, expected):
        name = case[0]
        scores, metadata, rows, novel, missing = oracle
        checks.append({"name": name + "_oracle", "passed": _oracle(retained[name], scores, metadata, rows, novel, missing)})
    all_scores = [retained[name][key] for name, reference, current in cases for key in _SCORES]
    checks.append({
        "name": "bounded_scores",
        "passed": all(type(value) in (int, float) and math.isfinite(value)
                      and -_TOLERANCE <= value <= 1 + _TOLERANCE for value in all_scores),
    })
    novel = retained["novel_support"]
    missing = retained["missing_support"]
    checks.append({
        "name": "symmetric_pair",
        "passed": (_near(novel["total_variation"], missing["total_variation"])
                   and _near(novel["jsd_bits"], missing["jsd_bits"])
                   and _near(novel["novel_current_mass"], missing["missing_reference_mass"])
                   and _near(novel["missing_reference_mass"], missing["novel_current_mass"])),
    })
    checks.append({
        "name": "proportional_invariance",
        "passed": (all(_near(retained["identical"][key], retained["proportional"][key]) for key in _SCORES)
                   and all(cases[1][2][key] == 2 * cases[1][1][key] for key in ("a", "b"))),
    })
    names = ("identical", "proportional", "balanced_shift", "novel_support", "missing_support", "disjoint")
    expected_metric_keys = {name + "_" + suffix for name in names for suffix in _SUFFIXES}
    expected_metric_keys.update(("case_count", "production_audit_calls"))
    checks.append({
        "name": "complete_accounting",
        "passed": (tuple(case[0] for case in cases) == names
                   and tuple(retained) == names and len(retained) == 6 and calls == 6
                   and sum(len(reference) + len(current) for name, reference, current in cases) == 20
                   and sum(len(set(reference) | set(current)) for name, reference, current in cases) == 12
                   and set(metrics) == expected_metric_keys and len(metrics) == 26
                   and type(metrics["case_count"]) is int and metrics["case_count"] == 6
                   and type(metrics["production_audit_calls"]) is int and metrics["production_audit_calls"] == 6
                   and all(type(output) is dict and set(output) == _RESULT_KEYS
                           and [row["category"] for row in output["categories"]] == ["a", "b"]
                           and all(type(row) is dict and set(row) == _ROW_KEYS for row in output["categories"])
                           for output in retained.values())),
    })
    return {"checks": checks, "metrics": metrics}
