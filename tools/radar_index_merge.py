"""Validate and merge radar extraction shards into a venue-year index.

Two modes are supported:

``full`` (the default)
    Merge complete index rows for papers that are not indexed yet.  Every new
    row must use the technique-v2 array, while untouched legacy rows in an
    existing index may still contain the historical string value.

``technique``
    Migrate only ``technique``.  The existing index must cover the meta file
    exactly and every output row contains only copied identity fields plus a
    technique-v2 array.  No other index field is changed.

The merger trusts only output filenames declared by ``manifest.json``.  It
validates the complete batch before writing and uses a same-directory temporary
file plus ``os.replace`` so a failed run cannot leave a partial index.
"""

from __future__ import annotations

import argparse
import copy
import datetime as _datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable


META_DIR = Path("src") / "assets" / "data" / "meta_json"
INDEX_DIR = Path("radar") / "index"
SCHEMA_VERSION = "technique-v2"

TECHNIQUE_FIELDS = (
    "name",
    "type",
    "target",
    "action",
    "effect",
    "grounding",
    "limitation",
)
TECHNIQUE_TYPES = (
    "algorithm",
    "model",
    "architecture",
    "protocol",
    "system-mechanism",
    "hardware-mechanism",
    "data-construction",
    "instrumentation",
    "analysis-method",
    "testing-method",
    "measurement-method",
    "formal-method",
    "user-study",
    "other",
)
GROUNDING_VALUES = ("explicit", "partial")
FULL_FIELDS = (
    "key",
    "id",
    "title",
    "paper",
    "method",
    "technique",
    "problem",
    "scenario",
    "evidence",
    "lens",
    "date",
)
TECHNIQUE_OUTPUT_FIELDS = ("key", "id", "title", "paper", "technique")
SHARD_INPUT_FIELDS = ("key", "id", "title", "abstract", "paper")
EVIDENCE_VALUES = (
    "real-world",
    "benchmark",
    "user study",
    "simulation",
    "theory",
    "unknown",
)


class ValidationError(ValueError):
    """Raised when a shard batch cannot be merged safely."""


def compact(title: str) -> str:
    """Return the title key used by the rest of the paper pipeline."""

    return "".join(char for char in title if char.isalnum()).lower()


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _read_json(path: Path, label: str) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"{label} is invalid JSON: {path} ({exc.msg} at line {exc.lineno}, column {exc.colno})"
        ) from exc


def validate_technique(value: Any, context: str = "technique") -> dict[str, Any]:
    """Validate one technique-v2 array and return audit counters.

    This mirrors ``radar/schema/technique-v2.schema.json`` without adding a
    runtime JSON Schema dependency.
    """

    if not isinstance(value, list):
        raise ValidationError(f"{context} must be an array")
    if len(value) > 4:
        raise ValidationError(f"{context} must contain at most 4 technique points")

    type_counts = {kind: 0 for kind in TECHNIQUE_TYPES}
    partial = other = duplicate_points = 0
    seen: set[tuple[str, str, str, str]] = set()

    for position, point in enumerate(value):
        point_context = f"{context}[{position}]"
        if not isinstance(point, dict):
            raise ValidationError(f"{point_context} must be an object")
        fields = set(point)
        expected = set(TECHNIQUE_FIELDS)
        if fields != expected:
            missing = sorted(expected - fields)
            extra = sorted(fields - expected)
            details = []
            if missing:
                details.append(f"missing fields {missing}")
            if extra:
                details.append(f"extra fields {extra}")
            raise ValidationError(f"{point_context} has invalid fields: {', '.join(details)}")

        for field in ("name", "target", "action", "effect"):
            if not _nonempty_string(point[field]):
                raise ValidationError(f"{point_context}.{field} must be a non-empty string")
        if len(point["name"]) > 80:
            raise ValidationError(f"{point_context}.name must be at most 80 characters")

        kind = point["type"]
        if kind not in TECHNIQUE_TYPES:
            raise ValidationError(
                f"{point_context}.type must be one of {list(TECHNIQUE_TYPES)}"
            )
        grounding = point["grounding"]
        if grounding not in GROUNDING_VALUES:
            raise ValidationError(
                f"{point_context}.grounding must be one of {list(GROUNDING_VALUES)}"
            )
        limitation = point["limitation"]
        if grounding == "explicit" and limitation is not None:
            raise ValidationError(
                f"{point_context}.limitation must be null when grounding is explicit"
            )
        if grounding == "partial" and not _nonempty_string(limitation):
            raise ValidationError(
                f"{point_context}.limitation must be a non-empty string when grounding is partial"
            )

        type_counts[kind] += 1
        partial += grounding == "partial"
        other += kind == "other"
        # Duplicate auditing is deliberately based on the clustering identity,
        # not on incidental differences in effect/grounding/limitation.
        signature = tuple(
            " ".join(point[field].split()).casefold()
            for field in ("type", "name", "target", "action")
        )
        if signature in seen:
            duplicate_points += 1
        seen.add(signature)

    return {
        "nonempty": bool(value),
        "empty": not value,
        "partial": partial,
        "other": other,
        "duplicate_points": duplicate_points,
        "type_counts": type_counts,
    }


def _load_meta(pub: str, year: int) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    path = META_DIR / f"{pub} - {year}.json"
    rows = _read_json(path, "meta file")
    if not isinstance(rows, list):
        raise ValidationError(f"meta file must contain a JSON array: {path}")

    by_key: dict[str, dict[str, Any]] = {}
    for position, paper in enumerate(rows):
        if not isinstance(paper, dict) or not _nonempty_string(paper.get("title")):
            raise ValidationError(f"meta row {position} has no valid title")
        key = compact(paper["title"])
        if not key:
            raise ValidationError(f"meta row {position} produces an empty key")
        if key in by_key:
            raise ValidationError(f"meta file contains duplicate key: {key}")
        by_key[key] = paper
    return rows, by_key


def _load_existing(pub: str, year: int) -> tuple[Path, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    path = INDEX_DIR / f"{pub} - {year}.json"
    if not path.exists():
        return path, [], {}
    rows = _read_json(path, "existing index")
    if not isinstance(rows, list):
        raise ValidationError(f"existing index must contain a JSON array: {path}")

    by_key: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict) or not _nonempty_string(row.get("key")):
            raise ValidationError(f"existing index row {position} has no valid key")
        key = row["key"]
        if key in by_key:
            raise ValidationError(f"existing index contains duplicate key: {key}")
        by_key[key] = row
    return path, rows, by_key


def _safe_manifest_filename(value: Any, context: str) -> str:
    if not _nonempty_string(value):
        raise ValidationError(f"{context} must be a filename")
    candidate = Path(value)
    if candidate.name != value or candidate.is_absolute() or value in (".", ".."):
        raise ValidationError(f"{context} must be a plain filename, got {value!r}")
    return value


def _unique_string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or any(not _nonempty_string(item) for item in value):
        raise ValidationError(f"{context} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ValidationError(f"{context} contains duplicate keys")
    return value


def _validate_manifest(
    manifest: Any, pub: str, year: int, mode: str
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(manifest, dict):
        raise ValidationError("manifest must be a JSON object")
    expected_header = {
        "publication": pub,
        "year": year,
        "mode": mode,
        "schema_version": SCHEMA_VERSION,
    }
    for field, expected in expected_header.items():
        if manifest.get(field) != expected:
            raise ValidationError(
                f"manifest {field} mismatch: expected {expected!r}, got {manifest.get(field)!r}"
            )

    expected_keys = _unique_string_list(manifest.get("expected_keys"), "manifest.expected_keys")
    if manifest.get("to_index") != len(expected_keys):
        raise ValidationError("manifest.to_index does not match expected_keys length")
    shards = manifest.get("shards")
    if not isinstance(shards, list):
        raise ValidationError("manifest.shards must be an array")

    normalized: list[dict[str, Any]] = []
    combined_keys: list[str] = []
    inputs: set[str] = set()
    outputs: set[str] = set()
    for position, shard in enumerate(shards):
        context = f"manifest.shards[{position}]"
        if not isinstance(shard, dict):
            raise ValidationError(f"{context} must be an object")
        input_name = _safe_manifest_filename(shard.get("input"), f"{context}.input")
        output_name = _safe_manifest_filename(shard.get("output"), f"{context}.output")
        if input_name in inputs:
            raise ValidationError(f"manifest declares duplicate input file: {input_name}")
        if output_name in outputs:
            raise ValidationError(f"manifest declares duplicate output file: {output_name}")
        inputs.add(input_name)
        outputs.add(output_name)

        count = shard.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValidationError(f"{context}.count must be a non-negative integer")
        shard_keys = _unique_string_list(shard.get("expected_keys"), f"{context}.expected_keys")
        if count != len(shard_keys):
            raise ValidationError(f"{context}.count does not match expected_keys length")
        combined_keys.extend(shard_keys)
        normalized.append(
            {
                "input": input_name,
                "output": output_name,
                "count": count,
                "expected_keys": shard_keys,
            }
        )

    if combined_keys != expected_keys:
        raise ValidationError(
            "manifest.expected_keys must equal the ordered concatenation of shard expected_keys"
        )
    return normalized, expected_keys


def _expected_identity(key: str, paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": key,
        "id": paper.get("id"),
        "title": paper["title"],
        "paper": paper.get("paper", "#"),
    }


def _validate_identity(row: dict[str, Any], key: str, paper: dict[str, Any], context: str) -> None:
    expected = _expected_identity(key, paper)
    for field, value in expected.items():
        if field not in row:
            raise ValidationError(f"{context} is missing identity field {field}")
        if type(row[field]) is not type(value) or row[field] != value:  # exact JSON identity copy
            raise ValidationError(
                f"{context}.{field} identity drift: expected {value!r}, got {row[field]!r}"
            )


def _validate_input_row(
    row: Any, key: str, paper: dict[str, Any], context: str
) -> None:
    if not isinstance(row, dict):
        raise ValidationError(f"{context} must be an object")
    fields = set(row)
    expected = set(SHARD_INPUT_FIELDS)
    if fields != expected:
        missing = sorted(expected - fields)
        extra = sorted(fields - expected)
        raise ValidationError(
            f"{context} must contain exactly the shard input fields; "
            f"missing={missing}, extra={extra}"
        )
    _validate_identity(row, key, paper, context)
    expected_abstract = paper.get("abstract", "#")
    if type(row["abstract"]) is not type(expected_abstract) or row["abstract"] != expected_abstract:
        raise ValidationError(
            f"{context}.abstract drift: expected {expected_abstract!r}, got {row['abstract']!r}"
        )


def _validate_output_identity_against_input(
    row: dict[str, Any], input_row: dict[str, Any], context: str
) -> None:
    for field in ("key", "id", "title", "paper"):
        expected = input_row[field]
        if field not in row:
            raise ValidationError(f"{context} is missing identity field {field}")
        if type(row[field]) is not type(expected) or row[field] != expected:
            raise ValidationError(
                f"{context}.{field} does not exactly copy shard input: "
                f"expected {expected!r}, got {row[field]!r}"
            )


def _validate_full_row(row: Any, key: str, paper: dict[str, Any], context: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValidationError(f"{context} must be an object")
    fields = set(row)
    expected = set(FULL_FIELDS)
    if fields != expected:
        missing = sorted(expected - fields)
        extra = sorted(fields - expected)
        raise ValidationError(
            f"{context} must contain exactly the full index fields; missing={missing}, extra={extra}"
        )
    _validate_identity(row, key, paper, context)
    for field in ("method", "problem", "scenario"):
        if not _nonempty_string(row[field]):
            raise ValidationError(f"{context}.{field} must be a non-empty string")
    if row["evidence"] not in EVIDENCE_VALUES:
        raise ValidationError(f"{context}.evidence must be one of {list(EVIDENCE_VALUES)}")
    if not isinstance(row["lens"], list) or any(
        not _nonempty_string(item) for item in row["lens"]
    ):
        raise ValidationError(f"{context}.lens must be an array of non-empty strings")
    if len(row["lens"]) != len(set(row["lens"])):
        raise ValidationError(f"{context}.lens contains duplicates")
    if not _nonempty_string(row["date"]):
        raise ValidationError(f"{context}.date must be an ISO date string")
    try:
        _datetime.date.fromisoformat(row["date"])
    except ValueError as exc:
        raise ValidationError(f"{context}.date must be an ISO date string") from exc
    return validate_technique(row["technique"], f"{context}.technique")


def _validate_technique_row(
    row: Any, key: str, paper: dict[str, Any], context: str
) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValidationError(f"{context} must be an object")
    fields = set(row)
    expected = set(TECHNIQUE_OUTPUT_FIELDS)
    if fields != expected:
        missing = sorted(expected - fields)
        extra = sorted(fields - expected)
        raise ValidationError(
            f"{context} must contain only identity fields and technique; missing={missing}, extra={extra}"
        )
    _validate_identity(row, key, paper, context)
    return validate_technique(row["technique"], f"{context}.technique")


def _combine_audit(audits: Iterable[dict[str, Any]]) -> dict[str, Any]:
    combined = {
        "nonempty": 0,
        "empty": 0,
        "partial": 0,
        "other": 0,
        "duplicate_points": 0,
        "type_counts": {kind: 0 for kind in TECHNIQUE_TYPES},
    }
    for audit in audits:
        combined["nonempty"] += int(audit["nonempty"])
        combined["empty"] += int(audit["empty"])
        combined["partial"] += audit["partial"]
        combined["other"] += audit["other"]
        combined["duplicate_points"] += audit["duplicate_points"]
        for kind, count in audit["type_counts"].items():
            combined["type_counts"][kind] += count
    return combined


def atomic_write_json(path: Path, value: Any) -> None:
    """Atomically write *value* as UTF-8 JSON, leaving the old file on failure."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def merge_index(pub: str, year: int, in_dir: Path, mode: str, check_only: bool = False) -> dict[str, Any]:
    """Validate one manifest batch and optionally merge it into the index."""

    if mode not in ("full", "technique"):
        raise ValidationError(f"unsupported mode: {mode}")

    manifest = _read_json(in_dir / "manifest.json", "manifest")
    shards, expected_keys = _validate_manifest(manifest, pub, year, mode)
    _, meta_by_key = _load_meta(pub, year)
    index_path, existing_rows, existing_by_key = _load_existing(pub, year)

    meta_keys = set(meta_by_key)
    existing_keys = set(existing_by_key)
    drift = existing_keys - meta_keys
    if drift:
        raise ValidationError(
            f"existing index contains {len(drift)} key(s) absent from meta: {sorted(drift)[:5]}"
        )
    if mode == "technique":
        if not index_path.exists():
            raise ValidationError("technique mode requires an existing index")
        missing = meta_keys - existing_keys
        if missing:
            raise ValidationError(
                "technique mode requires 100% meta/index alignment; "
                f"index is missing {len(missing)} key(s): {sorted(missing)[:5]}"
            )

    unexpected = set(expected_keys) - meta_keys
    if unexpected:
        raise ValidationError(
            f"manifest contains {len(unexpected)} key(s) absent from meta: {sorted(unexpected)[:5]}"
        )
    if mode == "technique":
        not_in_index = set(expected_keys) - existing_keys
        if not_in_index:
            raise ValidationError(
                f"manifest contains {len(not_in_index)} key(s) absent from existing index"
            )

    # Validate every declared input before looking at any generated output.  A
    # manifest therefore cannot point at stale/tampered context while presenting
    # otherwise plausible output rows.
    inputs_by_output: dict[str, dict[str, dict[str, Any]]] = {}
    all_input_keys: set[str] = set()
    for shard_info in shards:
        input_rows = _read_json(
            in_dir / shard_info["input"], f"shard input {shard_info['input']}"
        )
        if not isinstance(input_rows, list):
            raise ValidationError(
                f"shard input {shard_info['input']} must contain a JSON array"
            )
        if len(input_rows) != shard_info["count"]:
            raise ValidationError(
                f"shard input {shard_info['input']} row count mismatch: "
                f"expected {shard_info['count']}, got {len(input_rows)}"
            )

        input_by_key: dict[str, dict[str, Any]] = {}
        for row_position, row in enumerate(input_rows):
            context = f"{shard_info['input']} row {row_position}"
            if not isinstance(row, dict) or not _nonempty_string(row.get("key")):
                raise ValidationError(f"{context} has no valid key")
            key = row["key"]
            if key in all_input_keys:
                raise ValidationError(f"duplicate shard input key: {key}")
            if key not in meta_by_key:
                raise ValidationError(f"{context} key is absent from meta: {key}")
            _validate_input_row(row, key, meta_by_key[key], context)
            all_input_keys.add(key)
            input_by_key[key] = row

        if set(input_by_key) != set(shard_info["expected_keys"]):
            missing = sorted(set(shard_info["expected_keys"]) - set(input_by_key))
            extra = sorted(set(input_by_key) - set(shard_info["expected_keys"]))
            raise ValidationError(
                f"shard input {shard_info['input']} key set mismatch; "
                f"missing={missing}, extra={extra}"
            )
        inputs_by_output[shard_info["output"]] = input_by_key

    if all_input_keys != set(expected_keys):
        missing = sorted(set(expected_keys) - all_input_keys)
        extra = sorted(all_input_keys - set(expected_keys))
        raise ValidationError(f"input batch key set mismatch; missing={missing}, extra={extra}")

    output_rows: list[dict[str, Any]] = []
    output_keys: set[str] = set()
    audits: list[dict[str, Any]] = []
    for shard_position, shard in enumerate(shards):
        output_path = in_dir / shard["output"]
        rows = _read_json(output_path, f"shard output {shard['output']}")
        if not isinstance(rows, list):
            raise ValidationError(f"shard output {shard['output']} must contain a JSON array")
        if len(rows) != shard["count"]:
            raise ValidationError(
                f"shard output {shard['output']} row count mismatch: "
                f"expected {shard['count']}, got {len(rows)}"
            )

        shard_keys: list[str] = []
        for row_position, row in enumerate(rows):
            context = f"{shard['output']} row {row_position}"
            if not isinstance(row, dict) or not _nonempty_string(row.get("key")):
                raise ValidationError(f"{context} has no valid key")
            key = row["key"]
            if key in output_keys:
                raise ValidationError(f"duplicate output key: {key}")
            output_keys.add(key)
            shard_keys.append(key)
            if key not in meta_by_key:
                raise ValidationError(f"{context} key is absent from meta: {key}")
            input_by_key = inputs_by_output[shard["output"]]
            if key not in input_by_key:
                raise ValidationError(
                    f"{context} key is absent from its declared shard input: {key}"
                )
            _validate_output_identity_against_input(row, input_by_key[key], context)
            if mode == "technique":
                audit = _validate_technique_row(row, key, meta_by_key[key], context)
            else:
                audit = _validate_full_row(row, key, meta_by_key[key], context)
            audits.append(audit)
            output_rows.append(row)

        if set(shard_keys) != set(shard["expected_keys"]):
            missing = sorted(set(shard["expected_keys"]) - set(shard_keys))
            extra = sorted(set(shard_keys) - set(shard["expected_keys"]))
            raise ValidationError(
                f"shard output {shard['output']} key set mismatch; missing={missing}, extra={extra}"
            )

    if output_keys != set(expected_keys):
        missing = sorted(set(expected_keys) - output_keys)
        extra = sorted(output_keys - set(expected_keys))
        raise ValidationError(f"batch key set mismatch; missing={missing}, extra={extra}")

    added = updated = 0
    if mode == "technique":
        replacements = {row["key"]: row["technique"] for row in output_rows}
        rows_out = copy.deepcopy(existing_rows)
        for row in rows_out:
            if row["key"] in replacements:
                row["technique"] = replacements[row["key"]]
                updated += 1
    else:
        merged = copy.deepcopy(existing_by_key)
        for row in output_rows:
            if row["key"] in merged:
                updated += 1
            else:
                added += 1
            merged[row["key"]] = copy.deepcopy(row)
        rows_out = sorted(
            merged.values(),
            key=lambda row: (
                row.get("id") is None,
                row.get("id") if row.get("id") is not None else 0,
                row["title"],
            ),
        )

    if not check_only:
        atomic_write_json(index_path, rows_out)

    audit = _combine_audit(audits)
    return {
        "mode": mode,
        "check_only": check_only,
        "index_path": str(index_path),
        "rows": len(rows_out),
        "validated": len(output_rows),
        "added": added,
        "updated": updated,
        "coverage": f"{len(existing_keys | output_keys)}/{len(meta_keys)}",
        "technique_audit": audit,
    }


def _print_report(pub: str, year: int, report: dict[str, Any]) -> None:
    prefix = "CHECK ONLY - " if report["check_only"] else ""
    print(
        f"{prefix}{pub} {year} [{report['mode']}]: validated={report['validated']} "
        f"+{report['added']} new, {report['updated']} updated -> {report['index_path']} "
        f"({report['rows']} rows; coverage {report['coverage']})"
    )
    audit = report["technique_audit"]
    print(
        "  technique-v2: "
        f"nonempty={audit['nonempty']} empty={audit['empty']} "
        f"partial={audit['partial']} other={audit['other']} "
        f"duplicate_points={audit['duplicate_points']}"
    )
    populated_types = [
        f"{kind}={count}" for kind, count in audit["type_counts"].items() if count
    ]
    print(f"  types: {', '.join(populated_types) if populated_types else '(none)'}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Merge validated radar extraction shards")
    parser.add_argument("--pub", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--mode", choices=("full", "technique"), default="full")
    parser.add_argument(
        "--in",
        dest="in_dir",
        help="shard dir (default radar/_shards/<Pub> - <Year>)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate and report without changing the index",
    )
    args = parser.parse_args(argv)
    in_dir = Path(args.in_dir) if args.in_dir else Path("radar") / "_shards" / f"{args.pub} - {args.year}"
    try:
        report = merge_index(args.pub, args.year, in_dir, args.mode, args.check_only)
    except (OSError, ValidationError) as exc:
        raise SystemExit(f"merge aborted: {exc}") from exc
    _print_report(args.pub, args.year, report)


if __name__ == "__main__":
    main()
