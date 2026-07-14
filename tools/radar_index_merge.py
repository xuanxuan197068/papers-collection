"""Merge subagent shard outputs into a venue-year method index.

Reads out_NN.json files (produced by index-extraction subagents) from a shard
dir, validates required fields, dedups by key against any existing index, sorts
by id, and writes radar/index/<Publication> - <Year>.json. Reports coverage and
any papers still missing from the index (present in meta_json, absent here).

Usage (from repo root):
    uv run tools/radar_index_merge.py --pub "USENIX Sec" --year 2025 [--in DIR]
"""
import argparse
import glob
import json
import os

META_DIR = os.path.join('src', 'assets', 'data', 'meta_json')
INDEX_DIR = os.path.join('radar', 'index')
REQUIRED = ('key', 'title', 'method', 'technique', 'problem', 'scenario', 'evidence')


def compact(title):
    return ''.join(c for c in title if c.isalnum()).lower()


def load_existing(pub, year):
    path = os.path.join(INDEX_DIR, f'{pub} - {year}.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return {row['key']: row for row in json.load(f)}


def main():
    ap = argparse.ArgumentParser(description='Merge shard outputs into an index')
    ap.add_argument('--pub', required=True)
    ap.add_argument('--year', required=True, type=int)
    ap.add_argument('--in', dest='in_dir', help='shard dir (default radar/_shards/<Pub> - <Year>)')
    args = ap.parse_args()

    in_dir = args.in_dir or os.path.join('radar', '_shards', f'{args.pub} - {args.year}')
    out_files = sorted(glob.glob(os.path.join(in_dir, 'out_*.json')))
    if not out_files:
        raise SystemExit(f'no out_*.json found in {in_dir}')

    merged = load_existing(args.pub, args.year)
    added = updated = skipped = 0
    for of in out_files:
        with open(of, 'r', encoding='utf-8') as f:
            try:
                rows = json.load(f)
            except json.JSONDecodeError as e:
                print(f'  [warn] {os.path.basename(of)} invalid JSON: {e}; skipped')
                continue
        for row in rows:
            missing = [k for k in REQUIRED if not row.get(k)]
            if missing:
                print(f"  [warn] row '{str(row.get('title'))[:50]}' missing {missing}; skipped")
                skipped += 1
                continue
            row.setdefault('lens', [])
            key = row['key']
            if key in merged:
                updated += 1
            else:
                added += 1
            merged[key] = row

    # Prune rows whose key isn't a real paper in meta_json. Extraction subagents
    # occasionally alter the copied key; such rows are garbage (they leave the real
    # paper un-indexed), so drop them and let a gap re-shard fill the real ones.
    meta_path = os.path.join(META_DIR, f'{args.pub} - {args.year}.json')
    meta_keys = None
    pruned = 0
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        meta_keys = {compact(p['title']) for p in meta}
        for key in list(merged):
            if key not in meta_keys:
                del merged[key]
                pruned += 1
        if pruned:
            print(f'  [info] pruned {pruned} row(s) with keys not in meta_json (extraction drift)')

    # sort by id when present, else by title
    rows_out = sorted(merged.values(), key=lambda r: (r.get('id') is None, r.get('id') or 0, r['title']))
    os.makedirs(INDEX_DIR, exist_ok=True)
    out_path = os.path.join(INDEX_DIR, f'{args.pub} - {args.year}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(rows_out, f, ensure_ascii=False, indent=2)

    coverage = ''
    if meta_keys is not None:
        missing = meta_keys - set(merged)
        coverage = f'{len(meta_keys) - len(missing)}/{len(meta_keys)}'
        if missing:
            print(f'  [info] {len(missing)} paper(s) still un-indexed (re-shard to fill)')
    print(f'{args.pub} {args.year}: +{added} new, {updated} updated, {skipped} skipped '
          f'-> {out_path} ({len(rows_out)} rows; coverage {coverage})')


if __name__ == '__main__':
    main()
