"""Fetch a venue's paper list from DBLP.

Primary source:  venue TOC XML   https://dblp.org/db/<toc>.xml
Fallback source: search API      q=toc:db/<toc>.bht:

<toc> is e.g. 'conf/uss/uss2025', built by tools/fetch_new.py from the
`dblp_toc_template` field in data.yml. Stdlib only, serial requests,
conservative rate limit shared across both endpoints.
"""
import json
import random
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RATE_LIMIT_S = 2.5
JITTER_FRAC = 0.5  # add up to +50% random wait so intervals aren't fixed
UA = "papers-collection-radar/0.1 (academic paper radar; personal use)"

_last_call = 0.0


def _throttle():
    global _last_call
    # base gap + random jitter -> non-constant cadence, gentler on DBLP for
    # long unattended runs (24h loop mode).
    target = RATE_LIMIT_S + random.uniform(0, JITTER_FRAC * RATE_LIMIT_S)
    wait = target - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()


def http_get(url, timeout=30):
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        print(f"  [warn] {url} -> {type(e).__name__}: {e}")
        return -1, b""


def clean_title(title):
    title = title.strip()
    return title[:-1] if title.endswith('.') else title


def parse_venue_xml(data):
    papers = []
    root = ET.fromstring(data)
    for record_type in ("inproceedings", "article"):
        for rec in root.iter(record_type):
            title_el = rec.find("title")
            title = "".join(title_el.itertext()).strip() if title_el is not None else ""
            authors = ["".join(a.itertext()).strip() for a in rec.findall("author")]
            ee = [e.text for e in rec.findall("ee") if e.text]
            if title:
                papers.append({
                    "dblp_key": rec.get("key", ""),
                    "title": clean_title(title),
                    "authors": authors,
                    "links": ee,
                    "source": "dblp_venue_xml",
                })
    return papers


def parse_search_api(data):
    papers = []
    obj = json.loads(data)
    hits = obj.get("result", {}).get("hits", {}).get("hit", [])
    for h in hits:
        info = h.get("info", {})
        title = (info.get("title") or "").strip()
        auth = info.get("authors", {}).get("author", [])
        if isinstance(auth, dict):
            auth = [auth]
        if title:
            papers.append({
                "dblp_key": info.get("key", ""),
                "title": clean_title(title),
                "authors": [a.get("text", "") for a in auth],
                "links": [info.get("ee")] if info.get("ee") else [],
                "source": "dblp_search_api",
            })
    return papers


def fetch_toc(toc):
    """Return (papers, log) for a DBLP TOC key like 'conf/uss/uss2025'.

    papers is [] when DBLP has no data for that TOC yet (e.g. proceedings
    not published); callers must treat that as "nothing to do", not an error.
    """
    log = {"toc": toc, "venue_xml_status": None, "search_api_status": None, "count": 0}
    url_xml = f"https://dblp.org/db/{toc}.xml"
    print(f"  GET {url_xml}")
    status, data = http_get(url_xml)
    log["venue_xml_status"] = status
    if status == 200 and data:
        try:
            papers = parse_venue_xml(data)
            if papers:
                log["count"] = len(papers)
                return papers, log
            print("  [info] venue XML has 0 publications; trying search API")
        except ET.ParseError as e:
            print(f"  [warn] venue XML parse error: {e}; trying search API")
    q = urllib.parse.quote(f"toc:db/{toc}.bht:")
    url_api = f"https://dblp.org/search/publ/api?q={q}&h=1000&format=json"
    print(f"  GET {url_api}")
    status, data = http_get(url_api)
    log["search_api_status"] = status
    if status == 200 and data:
        try:
            papers = parse_search_api(data)
            log["count"] = len(papers)
            return papers, log
        except json.JSONDecodeError as e:
            print(f"  [warn] search API JSON error: {e}")
    return [], log
