"""Fetch a venue's paper list from DBLP.

Primary source:  venue TOC XML   https://dblp.org/db/<toc>.xml
Mirror fallback: official Trier/Dagstuhl venue TOC XML mirrors
Fallback source: search API, then the daily-synchronised DBLP SPARQL service

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
VENUE_XML_BASES = (
    "https://dblp.org",
    "https://dblp.uni-trier.de",
    "https://dblp.dagstuhl.de",
)
SPARQL_ENDPOINT = "https://sparql.dblp.org/sparql"
SPARQL_PAGE_SIZE = 1000
MIRROR_RETRY_STATUS = {-1, 429, 500, 502, 503, 504}

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


def http_post(url, body, timeout=60, accept="application/sparql-results+json"):
    _throttle()
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={
            "User-Agent": UA,
            "Content-Type": "application/sparql-query; charset=utf-8",
            "Accept": accept,
        },
        method="POST",
    )
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


def _is_anubis_challenge(data):
    """Recognise DBLP's HTTP-200 HTML proof-of-work page."""
    prefix = data[:16384].lower()
    return b"anubis" in prefix and (b"<!doctype html" in prefix or b"<html" in prefix)


def _binding_value(row, name, default=""):
    return row.get(name, {}).get("value", default)


def fetch_toc_sparql(toc):
    """Fetch one exact TOC from DBLP's daily-synchronised knowledge graph.

    The regular XML and search endpoints may be protected by an interactive
    Anubis challenge.  ``listedOnTocPage`` keeps this fallback equivalent to
    the XML TOC (rather than mixing in workshops from the same stream/year).
    """
    toc_uri = f"https://dblp.org/db/{toc}"
    offset = 0
    rows = []
    last_status = None
    while True:
        query = f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?publ ?title ?ordinal ?author ?link WHERE {{
  VALUES ?type {{ dblp:Inproceedings dblp:Article }}
  ?publ rdf:type ?type ;
        dblp:listedOnTocPage <{toc_uri}> ;
        dblp:title ?title .
  OPTIONAL {{ ?publ dblp:primaryDocumentPage ?link }}
  OPTIONAL {{
    ?publ dblp:hasSignature ?signature .
    ?signature dblp:signatureDblpName ?author ;
               dblp:signatureOrdinal ?ordinal .
  }}
}}
ORDER BY ?publ ?ordinal
LIMIT {SPARQL_PAGE_SIZE}
OFFSET {offset}
"""
        print(f"  POST {SPARQL_ENDPOINT} (TOC {toc}, offset {offset})")
        last_status, data = http_post(SPARQL_ENDPOINT, query)
        if last_status != 200 or not data:
            return [], last_status
        try:
            page = json.loads(data).get("results", {}).get("bindings", [])
        except json.JSONDecodeError as e:
            print(f"  [warn] SPARQL JSON error: {e}")
            return [], last_status
        rows.extend(page)
        if len(page) < SPARQL_PAGE_SIZE:
            break
        offset += SPARQL_PAGE_SIZE

    by_key = {}
    for row in rows:
        uri = _binding_value(row, "publ")
        if not uri:
            continue
        key = urllib.parse.unquote(uri.split("/rec/", 1)[-1])
        paper = by_key.setdefault(key, {
            "dblp_key": key,
            "title": clean_title(_binding_value(row, "title")),
            "authors": [],
            "links": [],
            "source": "dblp_sparql",
            "_authors": {},
        })
        author = _binding_value(row, "author")
        ordinal = _binding_value(row, "ordinal")
        if author:
            try:
                ordinal = int(ordinal)
            except (TypeError, ValueError):
                ordinal = len(paper["_authors"]) + 1
            paper["_authors"][ordinal] = author
        link = _binding_value(row, "link")
        if link and link not in paper["links"]:
            paper["links"].append(link)

    papers = []
    for paper in by_key.values():
        paper["authors"] = [name for _, name in sorted(paper.pop("_authors").items())]
        if paper["title"]:
            papers.append(paper)
    return papers, last_status


def fetch_toc(toc):
    """Return (papers, log) for a DBLP TOC key like 'conf/uss/uss2025'.

    papers is [] when DBLP has no data for that TOC yet (e.g. proceedings
    not published); callers must treat that as "nothing to do", not an error.
    """
    log = {
        "toc": toc,
        "venue_xml_status": None,
        "search_api_status": None,
        "sparql_status": None,
        "count": 0,
    }
    status, data = None, b""
    anubis_challenge = False
    for base in VENUE_XML_BASES:
        url_xml = f"{base}/db/{toc}.xml"
        print(f"  GET {url_xml}")
        status, data = http_get(url_xml)
        log["venue_xml_status"] = status
        if status == 200 and data:
            try:
                papers = parse_venue_xml(data)
            except ET.ParseError as e:
                # DBLP can return an HTML challenge/error body with HTTP 200.
                # A known Anubis challenge goes directly to DBLP's official
                # SPARQL service; other invalid responses still try mirrors.
                print(f"  [warn] venue XML parse error from {base}: {e}; trying mirror/fallback")
                if _is_anubis_challenge(data):
                    print("  [info] DBLP Anubis challenge detected; using official SPARQL fallback")
                    anubis_challenge = True
                    break
                continue
            if papers:
                log["count"] = len(papers)
                return papers, log
            print("  [info] venue XML has 0 publications; trying search API")
            break
        if status not in MIRROR_RETRY_STATUS:
            break
    if not anubis_challenge:
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

    papers, status = fetch_toc_sparql(toc)
    log["sparql_status"] = status
    log["count"] = len(papers)
    if papers:
        return papers, log
    return [], log
