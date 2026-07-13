"""Own update chain: pull venue TOCs from DBLP, merge, fill abstracts.

For every data.yml site marked `source: dblp`, this script
  1. fetches the DBLP TOC (dblp_toc_template / dblp_toc -> analyzers.dblp_fetcher),
  2. merges against already-known papers (official_cache json, falling back to
     the committed meta_json) keyed by compact title -- existing entries keep
     their abstracts/links, only genuinely new papers are appended,
  3. fills missing abstracts (analyzers.abstract_enricher) unless the venue's
     abstract_policy is 'lazy',
  4. writes official_cache/<official_file> for main.py --analyze to consume,
  5. records papers that still lack an abstract in radar/state/missing_abstracts.json.

Usage (from repo root):
    uv run tools/fetch_new.py [--venue KEY] [--year YYYY] [--dry-run]
                              [--policy full|lazy] [--max-enrich N] [--retry-missing]

Afterwards run `uv run main.py --analyze` to regenerate the frontend JSON.
"""
import argparse
import datetime
import difflib
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analyzers import dblp_fetcher
from analyzers import abstract_enricher

META_DIR = os.path.join('src', 'assets', 'data', 'meta_json')
CACHE_DIR = 'official_cache'
MISSING_PATH = os.path.join('radar', 'state', 'missing_abstracts.json')
LINK_PREFERENCE = ('usenix.org', 'ndss-symposium.org', 'dl.acm.org', 'doi.org')


def compact(title):
    # same normalization as main.py uses for duplicate detection
    return ''.join(c for c in title if c.isalnum()).lower()


def _norm(title):
    return re.sub(r'[^a-z0-9 ]+', ' ', title.lower()).strip()


FUZZY_DUP_RATIO = 0.9


def is_known(title, known_compact, known_norms):
    """DBLP and venue sites often word the same title slightly differently
    (case, singular/plural, subtitle tweaks); fall back to fuzzy matching so
    those variants don't produce duplicate entries."""
    if compact(title) in known_compact:
        return True
    n = _norm(title)
    for existing in known_norms:
        if difflib.SequenceMatcher(None, n, existing).ratio() >= FUZZY_DUP_RATIO:
            print(f'  [dup] "{title[:60]}" fuzzy-matches an existing entry; skipping')
            return True
    return False


def pick_link(links):
    for domain in LINK_PREFERENCE:
        for link in links:
            if domain in link:
                return link
    return links[0] if links else '#'


def load_existing(official_json, pub_name, year):
    """Known papers for this venue-year, in stable order."""
    path = os.path.join(CACHE_DIR, official_json)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    meta_path = os.path.join(META_DIR, f'{pub_name} - {year}.json')
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            return [{
                'title': p['title'],
                'abstract': p.get('abstract', '#'),
                'paper': p.get('paper', '#'),
                'publication': p.get('publication', pub_name),
            } for p in json.load(f)]
    return []


def load_missing():
    if os.path.exists(MISSING_PATH):
        with open(MISSING_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_missing(missing):
    os.makedirs(os.path.dirname(MISSING_PATH), exist_ok=True)
    with open(MISSING_PATH, 'w', encoding='utf-8') as f:
        json.dump(missing, f, ensure_ascii=False, indent=2)


def process_site(pub_key, pub, site, args, missing):
    year = site['year']
    pub_name = pub['name']
    label = f'{pub_name} - {year}'
    official_file = site.get('official_file')
    if not isinstance(official_file, str) or not official_file.endswith('.json'):
        print(f'[skip] {label}: `source: dblp` sites need `official_file: <name>.json` in data.yml')
        return None

    toc = site.get('dblp_toc') or pub.get('dblp_toc_template', '').format(year=year)
    if not toc:
        print(f'[skip] {label}: no dblp_toc_template/dblp_toc configured')
        return None

    print(f'[{label}] TOC {toc}')
    papers, log = dblp_fetcher.fetch_toc(toc)
    if not papers:
        print(f'[{label}] DBLP has no data yet (xml={log["venue_xml_status"]}, '
              f'api={log["search_api_status"]}) -- leaving existing data untouched')
        return {'label': label, 'dblp': 0, 'existing': None, 'new': 0, 'enrich': None}

    records = load_existing(official_file, pub_name, year)
    known_compact = {compact(r['title']) for r in records}
    known_norms = [_norm(r['title']) for r in records]
    n_existing = len(records)
    for p in papers:
        if not compact(p['title']) or is_known(p['title'], known_compact, known_norms):
            continue
        known_compact.add(compact(p['title']))
        known_norms.append(_norm(p['title']))
        records.append({
            'title': p['title'],
            'authors': ', '.join(p['authors']),
            'abstract': '#',
            'paper': pick_link(p['links']),
            'publication': pub_name,
            'dblp_key': p['dblp_key'],
        })
    n_new = len(records) - n_existing
    print(f'[{label}] dblp={len(papers)} existing={n_existing} new={n_new}')

    policy = args.policy or site.get('abstract_policy') or pub.get('abstract_policy', 'full')
    stats = None
    if policy == 'full' and not args.dry_run:
        skip_titles = set() if args.retry_missing else set(missing.get(label, {}))
        todo = [r for r in records
                if abstract_enricher.needs_abstract(r) and r['title'] not in skip_titles]
        if skip_titles and todo != records:
            n_skipped = sum(1 for r in records
                            if abstract_enricher.needs_abstract(r) and r['title'] in skip_titles)
            if n_skipped:
                print(f'[{label}] skipping {n_skipped} known-missing (use --retry-missing to retry)')
        stats = abstract_enricher.enrich_records(todo, max_records=args.max_enrich)
        now = datetime.datetime.now().strftime('%Y-%m-%d')
        entry = missing.setdefault(label, {})
        for r in records:
            if abstract_enricher.needs_abstract(r):
                if r['title'] not in skip_titles or args.retry_missing:
                    info = entry.setdefault(r['title'], {'attempts': 0})
                    info['attempts'] += 1
                    info['last_attempt'] = now
                    info['paper'] = r.get('paper', '#')
            else:
                entry.pop(r['title'], None)
        if not entry:
            missing.pop(label, None)
    elif policy == 'lazy':
        print(f'[{label}] abstract_policy=lazy -> abstracts deferred to on-demand enrichment')

    if args.dry_run:
        print(f'[{label}] dry run -- nothing written')
    else:
        os.makedirs(CACHE_DIR, exist_ok=True)
        out_path = os.path.join(CACHE_DIR, official_file)
        with open(out_path, 'w', encoding='utf8') as f:
            json.dump(records, f, ensure_ascii=False)
        print(f'[{label}] wrote {out_path} ({len(records)} papers)')
    return {'label': label, 'dblp': len(papers), 'existing': n_existing,
            'new': n_new, 'enrich': stats}


def main():
    parser = argparse.ArgumentParser(description='Fetch new papers via DBLP')
    parser.add_argument('--venue', help='data.yml publication key, e.g. ndss')
    parser.add_argument('--year', type=int, help='restrict to one year')
    parser.add_argument('--dry-run', action='store_true', help='fetch and report, write nothing')
    parser.add_argument('--policy', choices=['full', 'lazy'], help='override abstract policy')
    parser.add_argument('--max-enrich', type=int, help='cap enrichment lookups this run')
    parser.add_argument('--retry-missing', action='store_true',
                        help='retry titles already recorded in missing_abstracts.json')
    args = parser.parse_args()

    with open('data.yml', 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    missing = load_missing()
    results = []
    for pub_key, pub in config.items():
        if args.venue and pub_key != args.venue:
            continue
        for site in pub['sites']:
            if site.get('source') != 'dblp':
                continue
            if args.year and site['year'] != args.year:
                continue
            result = process_site(pub_key, pub, site, args, missing)
            if result:
                results.append(result)

    if not args.dry_run:
        save_missing(missing)

    if not results:
        print('No `source: dblp` sites matched. Mark sites in data.yml with '
              '`source: dblp` (+ `official_file: <name>.json`) to use this chain.')
        return
    print('\n=== fetch report ===')
    for r in results:
        line = f"{r['label']}: dblp={r['dblp']} new={r['new']}"
        if r['enrich']:
            e = r['enrich']
            line += (f" | abstracts: todo={e['todo']} arxiv={e['arxiv']}"
                     f" s2={e['semantic_scholar']} pdf={e['pdf']} failed={e['failed']}")
        print(line)
    print("Next: uv run main.py --analyze  (regenerates src/assets/data JSON)")


if __name__ == '__main__':
    main()
