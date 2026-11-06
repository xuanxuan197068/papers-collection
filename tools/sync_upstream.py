"""Apply a reviewed audit_upstream snapshot, then verify the local rebuild.

Usage: uv run tools/sync_upstream.py --report radar/sync/upstream-YYYY-MM-DD
       (preview by default; --apply writes caches; --verify checks the rebuild)
Configuration changes are reviewed separately in data.yml. No repository merge,
network fetching, commits, or semantic re-extraction are performed here.
"""
import argparse
import collections
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_upstream import compact, usable
from tools.rebuild_official_cache import json_name_for

CORE = ("title", "abstract", "paper", "publication")
META_FIELDS = {"id", "year", "title", "category", "publication", "paper", "abstract", "status"}
UPDATE_KINDS = {"upstream_fills_missing", "upstream_releases_embargo"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".sync-tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def edition(row):
    return f"{row['publication']} - {row['year']}"


def core(row):
    return {field: row.get(field, "#") for field in CORE}


def verify(expected, result, report_dir, finalize):
    rows = []
    id_map = {}
    for label, wanted in expected.items():
        actual = read(ROOT / "src/assets/data/meta_json" / f"{label}.json")
        if len(actual) != len(wanted):
            raise ValueError(f"{label}: wrong rebuilt count")
        for got, want in zip(actual, wanted):
            if set(got) != META_FIELDS:
                raise ValueError(f"{label}: incompatible output schema")
            for field in META_FIELDS - {"id"}:
                if got[field] != want[field]:
                    raise ValueError(f"{label}: unexpected {field} change in {want['title']}")
            if "id" in want:
                id_map[str(want["id"])] = got["id"]
        rows.extend(actual)
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(range(1, len(rows) + 1)):
        raise ValueError("Rebuilt IDs must be unique and contiguous")
    full = read(ROOT / "src/assets/data/data.json")
    expected_list = {r["id"]: {k: v for k, v in r.items() if k != "abstract"} for r in rows}
    if len(full) != len(rows) or any(expected_list.get(r["id"]) != r for r in full):
        raise ValueError("data.json disagrees with rebuilt meta_json")
    stats = read(ROOT / "src/assets/data/data-statistics.json")
    if stats["total"] != len(rows) or stats["byPublication"] != dict(collections.Counter(r["publication"] for r in rows)):
        raise ValueError("Rebuilt statistics disagree")
    quick = read(ROOT / "src/assets/data/data-quick-view.json")
    for row in quick:
        if expected_list.get(row["id"]) != row:
            raise ValueError("Quick-view row disagrees with full data")
    if collections.Counter(r["publication"] for r in quick) != {p: min(n, 100) for p, n in stats["byPublication"].items()}:
        raise ValueError("Quick-view counts disagree")
    for path in (ROOT / "src/assets/data").rglob("*.json"):
        read(path)
    # No semantic fields are changed: rebind only integer IDs after main.py
    # shifts them. Missing coverage of newly added papers remains explicit.
    index_changes = {}
    for path in sorted((ROOT / "radar/index").glob("*.json")):
        if path.stem not in expected:
            continue
        source = read(ROOT / "src/assets/data/meta_json" / path.name)
        by_title = collections.defaultdict(list)
        for row in source:
            by_title[compact(row["title"])].append(row)
        index = read(path)
        changed = 0
        for row in index:
            candidates = by_title[compact(row["title"])]
            if len(candidates) != 1:
                raise ValueError(f"Ambiguous method-index identity: {path.name}: {row['title']}")
            if row["id"] != candidates[0]["id"]:
                row["id"] = candidates[0]["id"]
                changed += 1
        if changed:
            index_changes[path.name] = changed
            if finalize:
                write(path, index)
    rebound = dict(result.get("method_index_ids_rebound", {}))
    rebound.update(index_changes)
    result.update({"verified_total": len(rows), "verified_editions": len(expected),
                   "method_index_ids_rebound": rebound})
    if finalize:
        result["phase"] = "verified"
        write(report_dir / "id-map.json", id_map)
        write(report_dir / "sync-result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", required=True)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    report_dir = (ROOT / args.report).resolve()
    audit_path = report_dir / "audit.json"
    audit = read(audit_path)
    snapshot = ROOT / audit["summary"]["snapshot_dir"]
    work = ROOT / "cache/upstream-sync" / audit["summary"]["date"]
    backup = work / "backup"
    expected_path = work / "expected.json"
    result_path = report_dir / "sync-result.json"
    if args.verify:
        verify(read(expected_path), read(result_path), report_dir, finalize=True)
        return
    if result_path.exists() and read(result_path).get("phase") == "verified":
        verify(read(expected_path), read(result_path), report_dir, finalize=False)
        print("Already synchronized; no data written.")
        return

    for relative, expected_hash in audit["local_files_sha256"].items():
        if digest(ROOT / relative) != expected_hash:
            raise ValueError(f"Local data changed since review: {relative}; audit again first")
    for entry in read(snapshot / "manifest.json"):
        if digest(snapshot / entry["path"]) != entry["sha256"]:
            raise ValueError(f"Snapshot changed since review: {entry['path']}")
    aliases = audit["review_decisions"].get("document_aliases", {})
    original = {}
    original_by_id = {}
    for relative in audit["local_files_sha256"]:
        records = read(ROOT / relative)
        original[Path(relative).stem] = records
        for row in records:
            original_by_id[row["id"]] = row
    expected = deepcopy(original)
    edits = collections.Counter()
    changed_editions = set()
    for match in audit["matched_field_differences"]:
        change = match["changes"].get("abstract", {})
        if change.get("kind") not in UPDATE_KINDS:
            continue
        local, remote = match["local"], match["upstream"]
        source = read(snapshot / "meta_json" / f"{edition(remote)}.json")
        remote_full = next(r for r in source if r["id"] == remote["id"])
        old = original_by_id[local["id"]]
        if any(old[k] != local[k] for k in ("title", "paper", "publication", "year")):
            raise ValueError("Reviewed match no longer agrees with local identity")
        label = edition(old)
        index = next(i for i, r in enumerate(original[label]) if r["id"] == old["id"])
        target = expected[label][index]
        target["abstract"] = remote_full["abstract"]
        edits[change["kind"]] += 1
        if old["title"] == "Paper Title Under Embargo":
            target["title"] = remote["title"]
            edits["embargo_titles_replaced"] += 1
        if old["paper"] in aliases:
            target["paper"] = aliases[old["paper"]]
            edits["urls_corrected"] += 1
        changed_editions.add(label)
    for row in audit["import_candidates"]:
        if not usable(row.get("abstract")):
            raise ValueError(f"Candidate lacks a usable abstract: {row['title']}")
        label = edition(row)
        target = {k: v for k, v in row.items() if k in META_FIELDS}
        target.pop("id", None)
        target["status"] = "notchecked"
        if target["paper"] in aliases:
            target["paper"] = aliases[target["paper"]]
            edits["urls_corrected"] += 1
        expected.setdefault(label, []).append(target)
        changed_editions.add(label)
    total = sum(map(len, expected.values()))
    if total != audit["summary"]["local_total"] + len(audit["import_candidates"]):
        raise ValueError("Planned total does not reconcile")
    config = yaml.safe_load((ROOT / "data.yml").read_text(encoding="utf-8"))
    sites = {f"{p['name']} - {s['year']}": (p, s) for p in config.values() for s in p["sites"]}
    outputs = {}
    for label in sorted(changed_editions):
        if label not in sites or not sites[label][1].get("official_file"):
            raise ValueError(f"Configure a JSON official_file before applying: {label}")
        pub, site = sites[label]
        filename = json_name_for(site["official_file"])
        path = ROOT / "official_cache" / filename
        previous = read(path) if path.exists() else []
        if previous and label in original:
            if list(map(core, previous)) != list(map(core, original[label])):
                raise ValueError(f"Cache/meta disagreement for {label}; refusing to overwrite cache")
        old_len = len(original.get(label, []))
        records = []
        for i, row in enumerate(expected[label]):
            if row["category"] != pub["category"] or row["publication"] != pub["name"]:
                raise ValueError(f"Configuration changes paper identity: {label}")
            row["status"] = site.get("status", "notchecked")
            record = deepcopy(previous[i]) if i < len(previous) else {}
            record.update(core(row))
            if i < old_len and row["abstract"] != original[label][i]["abstract"]:
                record["abstract_source"] = "upstream_snapshot"
            records.append(record)
        outputs[path] = records
    result = {"phase": "prepared", "audit_sha256": digest(audit_path),
              "upstream_revision": audit["summary"]["upstream_git_revision"],
              "before_total": audit["summary"]["local_total"], "added": len(audit["import_candidates"]),
              "expected_total": total, "excluded_nonpapers": len(audit["excluded_nonpapers"]),
              "local_only_preserved": len(audit["local_only"]), "updates": dict(edits),
              "cache_editions": {p.name: len(rows) for p, rows in outputs.items()},
              "backup": str(backup.relative_to(ROOT))}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.apply:
        print("Preview only; nothing written.")
        return
    if not (backup / "data.yml").exists():
        raise ValueError("A pre-sync configuration/data backup is required")
    # Back up every overwritten cache before writing any of them.
    for path in outputs:
        saved = backup / "official_cache" / path.name
        if path.exists() and not saved.exists():
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(path.read_bytes())
    write(expected_path, expected)
    for path, rows in outputs.items():
        write(path, rows)
    missing_path = ROOT / "radar/state/missing_abstracts.json"
    missing = read(missing_path)
    removed = 0
    for label in list(missing):
        available = {r["title"] for r in expected.get(label, []) if usable(r.get("abstract"))}
        for title in list(missing[label]):
            if title in available:
                del missing[label][title]
                removed += 1
        if not missing[label]:
            del missing[label]
    write(missing_path, missing)
    result["missing_log_resolved"] = removed
    write(result_path, result)
    print("Caches updated. Next: uv run main.py --analyze, then this command with --verify.")


if __name__ == "__main__":
    main()
