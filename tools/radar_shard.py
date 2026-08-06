"""Create manifest-bound shards for full index extraction or technique migration.

Usage examples (from the repository root)::

    uv run tools/radar_shard.py --pub "NDSS" --year 2025
    uv run tools/radar_shard.py --pub "NDSS" --year 2025 --mode technique
    uv run tools/radar_shard.py --pub "NDSS" --year 2025 --mode technique --force

``full`` keeps the historical incremental behavior and selects papers whose
keys are absent from the index.  ``technique`` requires a 100%-aligned existing
index and, by default, selects only rows whose technique is still a string;
``--force`` selects all rows, including valid technique-v2 arrays.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # Running as ``python tools/radar_shard.py`` places tools/ on sys.path.
    from radar_index_merge import SCHEMA_VERSION, ValidationError, validate_technique
except ImportError:  # Importing as ``tools.radar_shard`` from tests.
    from tools.radar_index_merge import SCHEMA_VERSION, ValidationError, validate_technique


META_DIR = Path("src") / "assets" / "data" / "meta_json"
INDEX_DIR = Path("radar") / "index"


def compact(title: str) -> str:
    return "".join(char for char in title if char.isalnum()).lower()


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


def _load_meta(pub: str, year: int) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    path = META_DIR / f"{pub} - {year}.json"
    rows = _read_json(path, "meta file")
    if not isinstance(rows, list):
        raise ValidationError(f"meta file must contain a JSON array: {path}")

    by_key: dict[str, dict[str, Any]] = {}
    for position, paper in enumerate(rows):
        if not isinstance(paper, dict) or not isinstance(paper.get("title"), str) or not paper["title"].strip():
            raise ValidationError(f"meta row {position} has no valid title")
        key = compact(paper["title"])
        if not key:
            raise ValidationError(f"meta row {position} produces an empty key")
        if key in by_key:
            raise ValidationError(f"meta file contains duplicate key: {key}")
        by_key[key] = paper
    return rows, by_key


def _load_index(pub: str, year: int) -> tuple[Path, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    path = INDEX_DIR / f"{pub} - {year}.json"
    if not path.exists():
        return path, [], {}
    rows = _read_json(path, "existing index")
    if not isinstance(rows, list):
        raise ValidationError(f"existing index must contain a JSON array: {path}")
    by_key: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("key"), str) or not row["key"].strip():
            raise ValidationError(f"existing index row {position} has no valid key")
        key = row["key"]
        if key in by_key:
            raise ValidationError(f"existing index contains duplicate key: {key}")
        by_key[key] = row
    return path, rows, by_key


def _record(key: str, paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": key,
        "id": paper.get("id"),
        "title": paper["title"],
        "abstract": paper.get("abstract", "#"),
        "paper": paper.get("paper", "#"),
    }


def select_papers(
    pub: str, year: int, mode: str = "full", force: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Return ``(all_meta, selected_records, already_done)`` for a shard run."""

    if mode not in ("full", "technique"):
        raise ValidationError(f"unsupported mode: {mode}")
    if force and mode != "technique":
        raise ValidationError("--force is only valid with --mode technique")

    papers, meta_by_key = _load_meta(pub, year)
    index_path, _, index_by_key = _load_index(pub, year)
    meta_keys = set(meta_by_key)
    index_keys = set(index_by_key)
    drift = index_keys - meta_keys
    if drift:
        raise ValidationError(
            f"existing index contains {len(drift)} key(s) absent from meta: {sorted(drift)[:5]}"
        )

    if mode == "full":
        selected = [
            _record(compact(paper["title"]), paper)
            for paper in papers
            if compact(paper["title"]) not in index_keys
        ]
        return papers, selected, len(index_keys)

    if not index_path.exists():
        raise ValidationError("technique mode requires an existing index")
    missing = meta_keys - index_keys
    if missing:
        raise ValidationError(
            "technique mode requires 100% meta/index alignment; "
            f"index is missing {len(missing)} key(s): {sorted(missing)[:5]}"
        )

    selected: list[dict[str, Any]] = []
    already_done = 0
    for paper in papers:
        key = compact(paper["title"])
        value = index_by_key[key].get("technique")
        if isinstance(value, str):
            selected.append(_record(key, paper))
        elif isinstance(value, list):
            validate_technique(value, f"existing index {key}.technique")
            if force:
                selected.append(_record(key, paper))
            else:
                already_done += 1
        else:
            raise ValidationError(
                f"existing index {key}.technique must be a legacy string or valid technique-v2 array"
            )
    return papers, selected, already_done


def create_shards(
    pub: str,
    year: int,
    out_dir: Path,
    size: int = 40,
    mode: str = "full",
    force: bool = False,
) -> dict[str, Any]:
    """Create input shard files and return the manifest written alongside them."""

    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValidationError("--size must be a positive integer")
    papers, selected, already_done = select_papers(pub, year, mode, force)
    out_dir.mkdir(parents=True, exist_ok=True)

    shards: list[dict[str, Any]] = []
    expected_keys = [record["key"] for record in selected]
    for offset in range(0, len(selected), size):
        records = selected[offset : offset + size]
        shard_number = offset // size
        input_name = f"shard_{shard_number:02d}.json"
        output_name = f"out_{shard_number:02d}.json"
        with (out_dir / input_name).open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        shards.append(
            {
                "input": input_name,
                "output": output_name,
                "count": len(records),
                "expected_keys": [record["key"] for record in records],
            }
        )

    manifest = {
        "publication": pub,
        "year": year,
        "mode": mode,
        "schema_version": SCHEMA_VERSION,
        "total_papers": len(papers),
        "already_indexed": already_done,
        "to_index": len(selected),
        "shard_size": size,
        "force": force,
        "expected_keys": expected_keys,
        "shards": shards,
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Shard papers for radar index extraction")
    parser.add_argument("--pub", required=True, help='publication name, e.g. "USENIX Sec"')
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--mode", choices=("full", "technique"), default="full")
    parser.add_argument("--force", action="store_true", help="redo existing v2 arrays in technique mode")
    parser.add_argument("--size", type=int, default=40, help="papers per shard (default 40)")
    parser.add_argument("--out", help="output dir (default radar/_shards/<Pub> - <Year>)")
    args = parser.parse_args(argv)
    out_dir = Path(args.out) if args.out else Path("radar") / "_shards" / f"{args.pub} - {args.year}"
    try:
        manifest = create_shards(
            args.pub,
            args.year,
            out_dir,
            size=args.size,
            mode=args.mode,
            force=args.force,
        )
    except (OSError, ValidationError) as exc:
        raise SystemExit(f"sharding aborted: {exc}") from exc

    print(
        f"{args.pub} {args.year} [{args.mode}]: total={manifest['total_papers']} "
        f"already_done={manifest['already_indexed']} to_index={manifest['to_index']} "
        f"-> {len(manifest['shards'])} shard(s) in {out_dir}"
    )
    if not manifest["shards"]:
        print("Nothing to extract for this mode.")


if __name__ == "__main__":
    main()
