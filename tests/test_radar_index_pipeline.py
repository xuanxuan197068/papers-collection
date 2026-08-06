"""Regression tests for the manifest-bound radar index pipeline."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import radar_index_merge as merge
from tools import radar_shard as shard


PUB = "TestConf"
YEAR = 2025
REPO_ROOT = Path(__file__).resolve().parents[1]


def point(
    name: str = "Graph pruning",
    kind: str = "algorithm",
    grounding: str = "explicit",
    limitation=None,
):
    return {
        "name": name,
        "type": kind,
        "target": "irrelevant graph branches",
        "action": "remove branches that cannot reach a sensitive sink",
        "effect": "reduce the search space before path enumeration",
        "grounding": grounding,
        "limitation": limitation,
    }


class RadarPipelineTest(unittest.TestCase):
    def setUp(self):
        self._old_cwd = Path.cwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)
        self.root = Path.cwd()
        (self.root / "src/assets/data/meta_json").mkdir(parents=True)
        (self.root / "radar/index").mkdir(parents=True)
        self.meta = [
            {
                "id": number,
                "title": f"Paper {number}: A Technique",
                "abstract": f"Abstract {number}",
                "paper": f"https://example.test/{number}",
            }
            for number in range(1, 4)
        ]
        self.write_json(self.meta_path, self.meta)

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._temp.cleanup()

    @property
    def meta_path(self):
        return self.root / f"src/assets/data/meta_json/{PUB} - {YEAR}.json"

    @property
    def index_path(self):
        return self.root / f"radar/index/{PUB} - {YEAR}.json"

    def write_json(self, path: Path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def index_row(self, paper, technique="legacy technique", **extra):
        row = {
            "key": shard.compact(paper["title"]),
            "id": paper["id"],
            "title": paper["title"],
            "paper": paper["paper"],
            "method": f"Method {paper['id']}",
            "technique": technique,
            "problem": f"Problem {paper['id']}",
            "scenario": f"Scenario {paper['id']}",
            "evidence": "benchmark",
            "lens": [],
            "date": "2026-07-14",
        }
        row.update(extra)
        return row

    def full_output(self, paper, technique=None):
        return self.index_row(paper, technique if technique is not None else [point()])

    def technique_output(self, record, technique=None):
        return {
            "key": record["key"],
            "id": record["id"],
            "title": record["title"],
            "paper": record["paper"],
            "technique": [point()] if technique is None else technique,
        }

    def create_technique_batch(self, index_rows, out_name="batch", size=40, force=False):
        self.write_json(self.index_path, index_rows)
        out_dir = self.root / out_name
        manifest = shard.create_shards(PUB, YEAR, out_dir, size=size, mode="technique", force=force)
        for item in manifest["shards"]:
            records = json.loads((out_dir / item["input"]).read_text(encoding="utf-8"))
            self.write_json(out_dir / item["output"], [self.technique_output(row) for row in records])
        return out_dir, manifest

    def test_full_shard_is_incremental_and_manifest_is_complete(self):
        self.write_json(self.index_path, [self.index_row(self.meta[0])])
        out_dir = self.root / "full"
        manifest = shard.create_shards(PUB, YEAR, out_dir, size=1)

        expected = [shard.compact(paper["title"]) for paper in self.meta[1:]]
        self.assertEqual(manifest["mode"], "full")
        self.assertEqual(manifest["schema_version"], "technique-v2")
        self.assertEqual(manifest["already_indexed"], 1)
        self.assertEqual(manifest["expected_keys"], expected)
        self.assertEqual(manifest["to_index"], 2)
        self.assertEqual(len(manifest["shards"]), 2)
        self.assertEqual(
            set(manifest["shards"][0]),
            {"input", "output", "count", "expected_keys"},
        )
        first = json.loads((out_dir / "shard_00.json").read_text(encoding="utf-8"))[0]
        self.assertEqual(set(first), {"key", "id", "title", "abstract", "paper"})
        with self.assertRaisesRegex(merge.ValidationError, "only valid"):
            shard.create_shards(PUB, YEAR, self.root / "bad-force", mode="full", force=True)

    def test_technique_shard_selects_legacy_and_force_redoes_valid_arrays(self):
        rows = [
            self.index_row(self.meta[0], "legacy"),
            self.index_row(self.meta[1], [point()]),
            self.index_row(self.meta[2], []),
        ]
        self.write_json(self.index_path, rows)

        normal = shard.create_shards(PUB, YEAR, self.root / "normal", mode="technique")
        self.assertEqual(normal["to_index"], 1)
        self.assertEqual(normal["already_indexed"], 2)
        self.assertEqual(normal["expected_keys"], [rows[0]["key"]])

        forced = shard.create_shards(
            PUB, YEAR, self.root / "forced", mode="technique", force=True, size=2
        )
        self.assertEqual(forced["to_index"], 3)
        self.assertEqual(forced["already_indexed"], 0)
        self.assertEqual([item["count"] for item in forced["shards"]], [2, 1])

    def test_technique_shard_requires_exact_index_coverage(self):
        self.write_json(self.index_path, [self.index_row(self.meta[0])])
        with self.assertRaisesRegex(merge.ValidationError, "100% meta/index alignment"):
            shard.create_shards(PUB, YEAR, self.root / "batch", mode="technique")

        drift = self.index_row(self.meta[0])
        drift["key"] = "not-in-meta"
        self.write_json(
            self.index_path,
            [drift, self.index_row(self.meta[1]), self.index_row(self.meta[2])],
        )
        with self.assertRaisesRegex(merge.ValidationError, "absent from meta"):
            shard.create_shards(PUB, YEAR, self.root / "drift", mode="technique")

    def test_technique_shard_rejects_invalid_existing_arrays(self):
        bad = point()
        bad["limitation"] = "must not be present"
        rows = [
            self.index_row(self.meta[0], "legacy"),
            self.index_row(self.meta[1], [bad]),
            self.index_row(self.meta[2], []),
        ]
        self.write_json(self.index_path, rows)
        with self.assertRaisesRegex(merge.ValidationError, "must be null"):
            shard.create_shards(PUB, YEAR, self.root / "batch", mode="technique")

    def test_nested_technique_schema_and_grounding_conditions(self):
        explicit = point()
        partial = point(
            name="Symbolic constraint",
            kind="formal-method",
            grounding="partial",
            limitation="the abstract omits the solver and constraint encoding",
        )
        audit = merge.validate_technique([explicit, partial], "fixture")
        self.assertEqual(audit["nonempty"], True)
        self.assertEqual(audit["partial"], 1)
        self.assertEqual(audit["type_counts"]["formal-method"], 1)
        self.assertEqual(merge.validate_technique([], "empty")["empty"], True)

        duplicate_with_different_incidental_fields = copy.deepcopy(explicit)
        duplicate_with_different_incidental_fields["effect"] = "a differently worded effect"
        duplicate_with_different_incidental_fields["grounding"] = "partial"
        duplicate_with_different_incidental_fields["limitation"] = "implementation details omitted"
        duplicate_with_different_incidental_fields["name"] = "  GRAPH   PRUNING "
        duplicate_audit = merge.validate_technique(
            [explicit, duplicate_with_different_incidental_fields], "duplicates"
        )
        self.assertEqual(duplicate_audit["duplicate_points"], 1)

        invalid = []
        too_many = [point(name=f"Point {number}") for number in range(5)]
        invalid.append((too_many, "at most 4"))
        bad_type = point()
        bad_type["type"] = "magic"
        invalid.append(([bad_type], "must be one of"))
        explicit_limit = point(limitation="unsupported")
        invalid.append(([explicit_limit], "must be null"))
        partial_without_limit = point(grounding="partial", limitation=None)
        invalid.append(([partial_without_limit], "non-empty string"))
        extra = point()
        extra["confidence"] = 0.9
        invalid.append(([extra], "extra fields"))
        missing = point()
        del missing["effect"]
        invalid.append(([missing], "missing fields"))
        for value, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(merge.ValidationError, message):
                    merge.validate_technique(value, "invalid")

    def test_json_schema_contract_matches_python_validator_constants(self):
        schema_path = REPO_ROOT / "radar/schema/technique-v2.schema.json"
        contract = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema_path.name, f"{merge.SCHEMA_VERSION}.schema.json")
        self.assertEqual(contract["type"], "array")
        self.assertEqual(contract["maxItems"], 4)
        item = contract["items"]
        self.assertEqual(item["additionalProperties"], False)
        self.assertEqual(item["required"], list(merge.TECHNIQUE_FIELDS))
        self.assertEqual(item["properties"]["type"]["enum"], list(merge.TECHNIQUE_TYPES))
        self.assertEqual(
            item["properties"]["grounding"]["enum"], list(merge.GROUNDING_VALUES)
        )
        conditional_groundings = {
            rule["if"]["properties"]["grounding"]["const"] for rule in item["allOf"]
        }
        self.assertEqual(conditional_groundings, set(merge.GROUNDING_VALUES))

    def test_technique_check_only_and_merge_preserve_every_other_field(self):
        before = [
            self.index_row(paper, "legacy", custom={"order": paper["id"]})
            for paper in self.meta
        ]
        out_dir, manifest = self.create_technique_batch(before, size=2)
        techniques = [
            [point()],
            [],
            [
                point(
                    name="Custom harness",
                    kind="other",
                    grounding="partial",
                    limitation="the abstract does not name the harness implementation",
                )
            ],
        ]
        cursor = 0
        for item in manifest["shards"]:
            records = json.loads((out_dir / item["input"]).read_text(encoding="utf-8"))
            rows = []
            for record in records:
                rows.append(self.technique_output(record, techniques[cursor]))
                cursor += 1
            self.write_json(out_dir / item["output"], rows)

        old_bytes = self.index_path.read_bytes()
        old_hash = hashlib.sha256(old_bytes).hexdigest()
        checked = merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)
        self.assertEqual(hashlib.sha256(self.index_path.read_bytes()).hexdigest(), old_hash)
        self.assertEqual(checked["updated"], 3)
        self.assertEqual(checked["technique_audit"]["empty"], 1)
        self.assertEqual(checked["technique_audit"]["partial"], 1)
        self.assertEqual(checked["technique_audit"]["other"], 1)

        merged_report = merge.merge_index(PUB, YEAR, out_dir, "technique")
        after = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.assertEqual(merged_report["updated"], 3)
        self.assertEqual([row["technique"] for row in after], techniques)
        stripped_before = [{key: value for key, value in row.items() if key != "technique"} for row in before]
        stripped_after = [{key: value for key, value in row.items() if key != "technique"} for row in after]
        self.assertEqual(stripped_after, stripped_before)

    def test_merge_reads_only_outputs_declared_by_manifest(self):
        rows = [self.index_row(paper) for paper in self.meta]
        out_dir, _ = self.create_technique_batch(rows)
        (out_dir / "out_99.json").write_text("{ definitely invalid", encoding="utf-8")
        report = merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)
        self.assertEqual(report["validated"], 3)

    def test_output_rows_may_reorder_but_must_copy_their_input_identity(self):
        rows = [self.index_row(paper) for paper in self.meta]
        out_dir, manifest = self.create_technique_batch(rows)
        output_path = out_dir / manifest["shards"][0]["output"]
        outputs = json.loads(output_path.read_text(encoding="utf-8"))
        self.write_json(output_path, list(reversed(outputs)))
        report = merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)
        self.assertEqual(report["validated"], 3)

    def test_declared_shard_input_is_strictly_validated(self):
        rows = [self.index_row(paper) for paper in self.meta]

        out_dir, manifest = self.create_technique_batch(rows, out_name="invalid-input-json")
        input_path = out_dir / manifest["shards"][0]["input"]
        input_path.write_text("[invalid", encoding="utf-8")
        with self.assertRaisesRegex(merge.ValidationError, "invalid JSON"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

        out_dir, manifest = self.create_technique_batch(rows, out_name="short-input")
        input_path = out_dir / manifest["shards"][0]["input"]
        inputs = json.loads(input_path.read_text(encoding="utf-8"))
        self.write_json(input_path, inputs[:-1])
        with self.assertRaisesRegex(merge.ValidationError, "row count mismatch"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

        out_dir, manifest = self.create_technique_batch(rows, out_name="input-extra-field")
        input_path = out_dir / manifest["shards"][0]["input"]
        inputs = json.loads(input_path.read_text(encoding="utf-8"))
        inputs[0]["method"] = "not an input field"
        self.write_json(input_path, inputs)
        with self.assertRaisesRegex(merge.ValidationError, "exactly the shard input fields"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

        out_dir, manifest = self.create_technique_batch(rows, out_name="input-identity-drift")
        input_path = out_dir / manifest["shards"][0]["input"]
        inputs = json.loads(input_path.read_text(encoding="utf-8"))
        inputs[0]["title"] = "tampered title"
        self.write_json(input_path, inputs)
        with self.assertRaisesRegex(merge.ValidationError, "identity drift"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

    def test_declared_invalid_json_aborts_without_writing(self):
        rows = [self.index_row(paper) for paper in self.meta]
        out_dir, manifest = self.create_technique_batch(rows)
        declared = out_dir / manifest["shards"][0]["output"]
        declared.write_text("[invalid", encoding="utf-8")
        before = self.index_path.read_bytes()
        with self.assertRaisesRegex(merge.ValidationError, "invalid JSON"):
            merge.merge_index(PUB, YEAR, out_dir, "technique")
        self.assertEqual(self.index_path.read_bytes(), before)

    def test_missing_duplicate_and_drifted_keys_are_rejected(self):
        rows = [self.index_row(paper) for paper in self.meta]

        out_dir, manifest = self.create_technique_batch(rows, out_name="missing", size=3)
        output_path = out_dir / manifest["shards"][0]["output"]
        outputs = json.loads(output_path.read_text(encoding="utf-8"))
        self.write_json(output_path, outputs[:-1])
        with self.assertRaisesRegex(merge.ValidationError, "row count mismatch"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

        out_dir, manifest = self.create_technique_batch(rows, out_name="duplicate", size=3)
        output_path = out_dir / manifest["shards"][0]["output"]
        outputs = json.loads(output_path.read_text(encoding="utf-8"))
        outputs[1] = copy.deepcopy(outputs[0])
        self.write_json(output_path, outputs)
        with self.assertRaisesRegex(merge.ValidationError, "duplicate output key"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

        out_dir, manifest = self.create_technique_batch(rows, out_name="drift", size=3)
        output_path = out_dir / manifest["shards"][0]["output"]
        outputs = json.loads(output_path.read_text(encoding="utf-8"))
        outputs[0]["key"] = "invented-key"
        self.write_json(output_path, outputs)
        with self.assertRaisesRegex(merge.ValidationError, "absent from meta"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

    def test_identity_drift_and_extra_output_fields_are_rejected(self):
        rows = [self.index_row(paper) for paper in self.meta]
        out_dir, manifest = self.create_technique_batch(rows)
        output_path = out_dir / manifest["shards"][0]["output"]
        outputs = json.loads(output_path.read_text(encoding="utf-8"))
        outputs[0]["title"] = "Changed title"
        self.write_json(output_path, outputs)
        with self.assertRaisesRegex(merge.ValidationError, "does not exactly copy shard input"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

        outputs[0]["title"] = self.meta[0]["title"]
        outputs[0]["method"] = "must not be included"
        self.write_json(output_path, outputs)
        with self.assertRaisesRegex(merge.ValidationError, "only identity fields"):
            merge.merge_index(PUB, YEAR, out_dir, "technique", check_only=True)

    def test_technique_merge_preserves_preexisting_identity_typography(self):
        rows = [self.index_row(paper) for paper in self.meta]
        historical_title = "Paper 1 - A Technique"  # same compact key, different punctuation
        rows[0]["title"] = historical_title
        out_dir, _ = self.create_technique_batch(rows, out_name="historical-identity")

        merge.merge_index(PUB, YEAR, out_dir, "technique")
        after = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.assertEqual(after[0]["title"], historical_title)
        self.assertEqual(after[0]["id"], self.meta[0]["id"])
        self.assertEqual(after[0]["paper"], self.meta[0]["paper"])

    def test_full_merge_requires_v2_for_new_rows_but_keeps_legacy_untouched(self):
        legacy = self.index_row(self.meta[0], "legacy string")
        self.write_json(self.index_path, [legacy])
        out_dir = self.root / "full-batch"
        manifest = shard.create_shards(PUB, YEAR, out_dir, mode="full")
        records = json.loads((out_dir / manifest["shards"][0]["input"]).read_text(encoding="utf-8"))
        outputs = [self.full_output(self.meta[record["id"] - 1]) for record in records]
        self.write_json(out_dir / manifest["shards"][0]["output"], outputs)

        report = merge.merge_index(PUB, YEAR, out_dir, "full")
        after = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.assertEqual(report["added"], 2)
        self.assertEqual(len(after), 3)
        self.assertEqual(after[0]["technique"], "legacy string")
        self.assertTrue(all(isinstance(row["technique"], list) for row in after[1:]))

        # A newly generated legacy string is never accepted in full mode.
        self.write_json(self.index_path, [legacy])
        outputs[0]["technique"] = "new legacy string"
        self.write_json(out_dir / manifest["shards"][0]["output"], outputs)
        with self.assertRaisesRegex(merge.ValidationError, "must be an array"):
            merge.merge_index(PUB, YEAR, out_dir, "full", check_only=True)

    def test_duplicate_existing_index_rows_are_rejected(self):
        row = self.index_row(self.meta[0])
        self.write_json(self.index_path, [row, copy.deepcopy(row)])
        with self.assertRaisesRegex(merge.ValidationError, "duplicate key"):
            shard.create_shards(PUB, YEAR, self.root / "batch", mode="full")

    def test_atomic_replace_failure_preserves_original_and_cleans_temp(self):
        target = self.root / "atomic.json"
        target.write_text("old-content", encoding="utf-8")
        with mock.patch.object(merge.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "replace failed"):
                merge.atomic_write_json(target, {"new": True})
        self.assertEqual(target.read_text(encoding="utf-8"), "old-content")
        self.assertEqual(list(self.root.glob(".atomic.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
