"""Completeness audit: compare local library vs DBLP vs upstream per venue-year.

For each venue-year it prints three counts and the gaps:
  - local:    papers in src/assets/data/meta_json/<Pub> - <Year>.json
  - dblp:     papers in the DBLP TOC (via analyzers.dblp_fetcher, rate-limited)
  - upstream: papers in the author's committed meta_json (git show upstream/main:...)

Gaps tell you what action to take:
  - dblp/upstream has papers local lacks  -> fetch_new (own chain) or merge upstream
  - local has papers dblp/upstream lack    -> fine (you're ahead, or hand-added)

Run `git fetch upstream` first for a fresh upstream comparison.

Usage (from repo root):
    uv run tools/audit_completeness.py [--venue KEY] [--recent N] [--all]
                                        [--year YYYY] [--no-dblp] [--no-upstream]

By default audits the most recent --recent (=2) years per venue (a full DBLP
sweep of every venue-year is slow due to rate limits). --all overrides.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analyzers import dblp_fetcher

META_DIR = os.path.join('src', 'assets', 'data', 'meta_json')
FUZZY_DUP_RATIO = 0.9  # keep in sync with tools/fetch_new.py


def compact(title):
    return ''.join(c for c in title if c.isalnum()).lower()


def _norm(title):
    return re.sub(r'[^a-z0-9 ]+', ' ', title.lower()).strip()


def real_gap(source_titles, local_compact, local_norms):
    """Titles in `source_titles` genuinely absent from local, using the same
    exact+fuzzy match fetch_new uses (so titles worded slightly differently in
    DBLP vs the venue site aren't reported as false gaps)."""
    missing = []
    for key, norm in source_titles:
        if key in local_compact:
            continue
        if any(difflib.SequenceMatcher(None, norm, ln).ratio() >= FUZZY_DUP_RATIO
               for ln in local_norms):
            continue
        missing.append(key)
    return missing


def local_titles(pub, year):
    path = os.path.join(META_DIR, f'{pub} - {year}.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return [p['title'] for p in json.load(f)]


def upstream_titles(pub, year):
    """Papers in upstream/main's committed meta_json for this venue-year."""
    ref = f'upstream/main:{META_DIR}/{pub} - {year}.json'.replace('\\', '/')
    try:
        out = subprocess.run(['git', 'show', ref], capture_output=True, text=True,
                             encoding='utf-8')
    except FileNotFoundError:
        return None
    if out.returncode != 0:
        return None
    try:
        return [p['title'] for p in json.loads(out.stdout)]
    except json.JSONDecodeError:
        return None


def dblp_titles(pub, site):
    toc = site.get('dblp_toc') or pub.get('dblp_toc_template', '')
    if not toc:
        return None
    toc = toc.format(year=site['year'])
    papers, _ = dblp_fetcher.fetch_toc(toc)
    return [p['title'] for p in papers] if papers else []


def main():
    ap = argparse.ArgumentParser(description='Audit library completeness')
    ap.add_argument('--venue', help='data.yml publication key')
    ap.add_argument('--year', type=int, help='restrict to one year')
    ap.add_argument('--recent', type=int, default=2, help='most recent N years/venue (default 2)')
    ap.add_argument('--all', action='store_true', help='audit every year (slow)')
    ap.add_argument('--no-dblp', action='store_true', help='skip DBLP (offline, fast)')
    ap.add_argument('--no-upstream', action='store_true', help='skip upstream comparison')
    args = ap.parse_args()

    with open('data.yml', 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    print(f"{'venue-year':28} {'local':>6} {'dblp':>6} {'upstr':>6}  gaps")
    print('-' * 72)
    actions = []
    for pub_key, pub in config.items():
        if args.venue and pub_key != args.venue:
            continue
        sites = pub['sites']
        if not args.all and not args.year:
            sites = sorted(sites, key=lambda s: s['year'], reverse=True)[:args.recent]
        for site in sites:
            if args.year and site['year'] != args.year:
                continue
            label = f"{pub['name']} - {site['year']}"
            local = local_titles(pub['name'], site['year'])
            dblp = None if args.no_dblp else dblp_titles(pub, site)
            upstream = None if args.no_upstream else upstream_titles(pub['name'], site['year'])

            lc = '-' if local is None else len(local)
            dc = '-' if dblp is None else len(dblp)
            uc = '-' if upstream is None else len(upstream)
            local = local or []
            local_compact = {compact(t) for t in local}
            local_norms = [_norm(t) for t in local]

            gaps = []
            if dblp:
                miss = real_gap([(compact(t), _norm(t)) for t in dblp], local_compact, local_norms)
                if miss:
                    gaps.append(f'dblp+{len(miss)}')
                    actions.append(f'  fetch_new --venue {pub_key} --year {site["year"]}  '
                                   f'(+{len(miss)} from DBLP)')
            if upstream:
                miss = real_gap([(compact(t), _norm(t)) for t in upstream], local_compact, local_norms)
                if miss:
                    gaps.append(f'upstream+{len(miss)}')
                    actions.append(f'  merge upstream for {label}  (+{len(miss)} author papers)')
            print(f'{label:28} {lc:>6} {dc:>6} {uc:>6}  {", ".join(gaps) if gaps else "ok"}')

    if actions:
        print('\nsuggested actions:')
        for a in dict.fromkeys(actions):  # dedup, keep order
            print(a)
    else:
        print('\nNo gaps found in audited venue-years.')


if __name__ == '__main__':
    main()
