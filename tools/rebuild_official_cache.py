"""Rebuild official_cache/*.json from src/assets/data/meta_json/*.json.

The upstream repo ships its original bib/csv sources in an AES-encrypted
private_source.zip whose password we do not have. The generated meta_json
files contain the same paper data, so the intermediate JSON files that
`main.py --analyze` consumes can be reconstructed from them.

Naming mirrors main.py: a str official_file maps 'oakland26.bib' ->
'oakland26.json'; a list maps ['asplos25-1.bib', ...] -> 'asplos25.json'.

Run from the repo root:
    uv run tools/rebuild_official_cache.py [--force]
"""
import json
import os
import sys

import yaml

META_DIR = os.path.join('src', 'assets', 'data', 'meta_json')
OUT_DIR = 'official_cache'


def json_name_for(official_file):
    if isinstance(official_file, list):
        first = official_file[0]
        return first[:first.index('-')] + '.json'
    return official_file[:official_file.index('.')] + '.json'


def main():
    force = '--force' in sys.argv
    with open('data.yml', 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    os.makedirs(OUT_DIR, exist_ok=True)
    written = skipped = missing = 0
    for pub_key, pub in config.items():
        for site in pub['sites']:
            official_file = site.get('official_file')
            if official_file is None:
                continue
            out_name = json_name_for(official_file)
            out_path = os.path.join(OUT_DIR, out_name)
            if os.path.exists(out_path) and not force:
                skipped += 1
                continue
            meta_path = os.path.join(META_DIR, f"{pub['name']} - {site['year']}.json")
            if not os.path.exists(meta_path):
                print(f"[miss] no meta file for {pub['name']} {site['year']}")
                missing += 1
                continue
            with open(meta_path, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            records = [{
                'title': p['title'],
                'abstract': p.get('abstract', '#'),
                'paper': p.get('paper', '#'),
                'publication': p.get('publication', pub['name']),
            } for p in papers]
            with open(out_path, 'w', encoding='utf8') as f:
                json.dump(records, f, ensure_ascii=False)
            print(f'[ok] {out_name}: {len(records)} papers')
            written += 1
    print(f'Done. wrote {written}, skipped {skipped} existing, missing {missing}.')


if __name__ == '__main__':
    main()
