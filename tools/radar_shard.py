"""Split a venue-year's un-indexed papers into shards for subagent extraction.

radar-digest Stage 1 builds a per-paper method index. This script prepares the
inputs: it reads meta_json, skips papers already present in the existing index
(incremental), and writes shard_NN.json batches (id/title/abstract/paper) plus a
manifest.json. Each shard is handed to one subagent that emits index rows.

Usage (from repo root):
    uv run tools/radar_shard.py --pub "USENIX Sec" --year 2025 [--size 40] [--out DIR]

Default --out: radar/_shards/<Publication> - <Year>/
"""
import argparse
import json
import os

META_DIR = os.path.join('src', 'assets', 'data', 'meta_json')
INDEX_DIR = os.path.join('radar', 'index')


def compact(title):
    # same normalization used across the pipeline (main.py compact())
    return ''.join(c for c in title if c.isalnum()).lower()


def load_index_keys(pub, year):
    path = os.path.join(INDEX_DIR, f'{pub} - {year}.json')
    if not os.path.exists(path):
        return set()
    with open(path, 'r', encoding='utf-8') as f:
        return {row.get('key', '') for row in json.load(f)}


def main():
    ap = argparse.ArgumentParser(description='Shard papers for index extraction')
    ap.add_argument('--pub', required=True, help='publication name, e.g. "USENIX Sec"')
    ap.add_argument('--year', required=True, type=int)
    ap.add_argument('--size', type=int, default=40, help='papers per shard (default 40)')
    ap.add_argument('--out', help='output dir (default radar/_shards/<Pub> - <Year>)')
    args = ap.parse_args()

    meta_path = os.path.join(META_DIR, f'{args.pub} - {args.year}.json')
    if not os.path.exists(meta_path):
        raise SystemExit(f'meta file not found: {meta_path}')
    with open(meta_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    done = load_index_keys(args.pub, args.year)
    todo = [p for p in papers if compact(p['title']) not in done]

    out_dir = args.out or os.path.join('radar', '_shards', f'{args.pub} - {args.year}')
    os.makedirs(out_dir, exist_ok=True)

    shards = []
    for i in range(0, len(todo), args.size):
        batch = todo[i:i + args.size]
        shard_name = f'shard_{i // args.size:02d}.json'
        records = [{
            'key': compact(p['title']),
            'id': p.get('id'),
            'title': p['title'],
            'abstract': p.get('abstract', '#'),
            'paper': p.get('paper', '#'),
        } for p in batch]
        with open(os.path.join(out_dir, shard_name), 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        shards.append({'shard': shard_name, 'count': len(records),
                       'out': shard_name.replace('shard_', 'out_')})

    manifest = {
        'publication': args.pub, 'year': args.year,
        'total_papers': len(papers), 'already_indexed': len(done),
        'to_index': len(todo), 'shard_size': args.size, 'shards': shards,
    }
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f'{args.pub} {args.year}: total={len(papers)} indexed={len(done)} '
          f'to_index={len(todo)} -> {len(shards)} shard(s) in {out_dir}')
    if not shards:
        print('Nothing to index (all papers already in index).')


if __name__ == '__main__':
    main()
