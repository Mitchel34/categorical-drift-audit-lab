"""Focused hand and structural tests; never invoke the production evaluator."""

import math
import unittest

from categorical_drift_audit_lab.core import audit


class CountAuditTests(unittest.TestCase):
    def test_demo_hand_oracle_and_schema(self):
        result = audit({"a": 4}, {"a": 2, "b": 2})
        entropy_quarter = -(1 / 4) * math.log2(1 / 4) - (3 / 4) * math.log2(3 / 4)
        self.assertEqual(set(result), {
            "schema", "reference_total", "current_total", "reference_support", "current_support",
            "declared_union_size", "total_variation", "jsd_bits", "novel_current_mass",
            "missing_reference_mass", "novel_categories", "missing_categories", "categories",
        })
        self.assertEqual(result["schema"], "categorical-drift-audit/1")
        self.assertAlmostEqual(result["total_variation"], 1 / 2, delta=1e-12)
        self.assertAlmostEqual(result["jsd_bits"], entropy_quarter - 1 / 2, delta=1e-12)
        self.assertEqual(result["novel_current_mass"], 1 / 2)
        self.assertEqual(result["missing_reference_mass"], 0)
        self.assertEqual((result["reference_total"], result["current_total"]), (4, 4))
        self.assertEqual((result["reference_support"], result["current_support"]), (1, 2))
        self.assertEqual(result["declared_union_size"], 2)
        self.assertEqual(result["novel_categories"], ["b"])
        self.assertEqual(result["missing_categories"], [])
        self.assertEqual(result["categories"], [
            {"category": "a", "reference_count": 4, "current_count": 2,
             "reference_probability": 1.0, "current_probability": 0.5},
            {"category": "b", "reference_count": 0, "current_count": 2,
             "reference_probability": 0.0, "current_probability": 0.5},
        ])
        for field in ("total_variation", "jsd_bits", "novel_current_mass", "missing_reference_mass"):
            self.assertIs(type(result[field]), float)

    def test_nonmutation_order_scale_and_swap(self):
        reference = {"a": 1, "b": 2, "c": 1}
        current = {"a": 1, "b": 1, "c": 2}
        old_reference, old_current = reference.copy(), current.copy()
        result = audit(reference, current)
        self.assertEqual(reference, old_reference)
        self.assertEqual(current, old_current)
        reordered = audit(dict(reversed(tuple(reference.items()))), dict(reversed(tuple(current.items()))))
        self.assertEqual(result, reordered)
        scaled = audit({key: count * 2 for key, count in reference.items()},
                       {key: count * 2 for key, count in current.items()})
        swapped = audit(current, reference)
        for field in ("total_variation", "jsd_bits", "novel_current_mass", "missing_reference_mass"):
            self.assertAlmostEqual(result[field], scaled[field], delta=1e-12)
        self.assertEqual((scaled["reference_total"], scaled["current_total"]), (8, 8))
        for field in ("total_variation", "jsd_bits"):
            self.assertAlmostEqual(result[field], swapped[field], delta=1e-12)
        self.assertAlmostEqual(result["novel_current_mass"], swapped["missing_reference_mass"], delta=1e-12)
        self.assertAlmostEqual(result["missing_reference_mass"], swapped["novel_current_mass"], delta=1e-12)

    def test_explicit_zero_keys_preserve_declared_rows(self):
        result = audit({"a": 4, "z": 0}, {"a": 2, "b": 2, "z": 0})
        self.assertEqual(result["declared_union_size"], 3)
        self.assertEqual((result["reference_support"], result["current_support"]), (1, 2))
        self.assertEqual(result["novel_categories"], ["b"])
        self.assertEqual(result["missing_categories"], [])
        self.assertEqual(result["categories"][-1], {
            "category": "z", "reference_count": 0, "current_count": 0,
            "reference_probability": 0.0, "current_probability": 0.0,
        })

    def test_unequal_totals_are_independently_normalized(self):
        result = audit({"a": 4}, {"a": 4, "b": 4})
        self.assertEqual((result["reference_total"], result["current_total"]), (4, 8))
        self.assertEqual(result["total_variation"], 1 / 2)
        self.assertEqual(result["novel_current_mass"], 1 / 2)

    def test_rejects_invalid_counts_shapes_and_categories(self):
        class Counts(dict):
            pass

        class Count(int):
            pass

        class Category(str):
            pass

        invalid = [
            {}, [], None, Counts({"a": 1}), {"a": 0}, {"a": True}, {"a": 1.0},
            {"a": Count(1)}, {"a": -1}, {"a": 1_000_001}, {"a": 600_000, "b": 600_000},
            {"": 1}, {".a": 1}, {"a b": 1}, {"é": 1}, {"a" * 33: 1},
            {1: 1}, {Category("a"): 1}, {"a": "1"}, {"a": None},
            {"a" + str(i): 1 for i in range(65)},
        ]
        for bad in invalid:
            for reference, current in ((bad, {"a": 1}), ({"a": 1}, bad)):
                with self.subTest(value=repr(bad), reference_side=reference is bad):
                    with self.assertRaisesRegex(ValueError, "^invalid_input$"):
                        audit(reference, current)

    def test_inclusive_bounds_and_ascii_order(self):
        reference = {"r" + str(i): 0 for i in range(64)}
        current = {"s" + str(i): 0 for i in range(64)}
        reference["r0"], current["s0"] = 1_000_000, 1_000_000
        result = audit(reference, current)
        self.assertEqual(result["declared_union_size"], 128)
        self.assertEqual((result["reference_total"], result["current_total"]), (1_000_000, 1_000_000))
        identifier = "A" + "a" * 28 + "_.-"
        ordered = audit({identifier: 1, "0": 1, "a": 1}, {"Z": 1})
        self.assertEqual([row["category"] for row in ordered["categories"]], sorted((identifier, "0", "a", "Z")))


if __name__ == "__main__":
    unittest.main()
