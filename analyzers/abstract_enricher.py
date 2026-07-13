"""Fill missing abstracts for fetched paper records.

Fallback chain, each layer only touching records the previous ones missed:
  1. arXiv title match   (exact phrase, then distinctive-keyword AND, fuzzy >= 0.75)
  2. Semantic Scholar    (/graph/v1/paper/search/match, fuzzy >= 0.75)
  3. open-access PDF     (paper page -> citation_pdf_url or first .pdf link
                          -> pypdf first 2 pages -> Abstract..Introduction regex)

Records are dicts with at least {title, paper, abstract}; a record needs
enrichment when its abstract is '#' or shorter than 50 chars. On success the
record gets `abstract` plus an `abstract_source` provenance tag.
"""
import difflib
import json
import random
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pypdf is only needed for the PDF layer
    PdfReader = None

UA = "papers-collection-radar/0.1 (academic paper radar; personal use)"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_RATE_S = 3.2
S2_RATE_S = 1.2
WEB_RATE_S = 2.0
MATCH_RATIO = 0.75

STOPWORDS = {"the", "and", "with", "from", "against", "using", "via", "for",
             "towards", "toward", "your", "into", "over", "under", "their"}

JITTER_FRAC = 0.5  # add up to +50% random wait so intervals aren't fixed

_last = {}


def _throttle(source, seconds):
    # base gap + random jitter -> non-constant cadence, avoids tripping
    # rate limiters during long unattended (24h loop) runs.
    target = seconds + random.uniform(0, JITTER_FRAC * seconds)
    wait = target - (time.time() - _last.get(source, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last[source] = time.time()


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        print(f"    [warn] {url[:90]} -> {type(e).__name__}: {e}")
        return -1, b""


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def _ratio(a, b):
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def needs_abstract(record):
    abstract = record.get("abstract") or "#"
    return abstract == "#" or len(abstract) < 50


# --- layer 1: arXiv ---------------------------------------------------------

def _arxiv_query(search_query):
    _throttle("arxiv", ARXIV_RATE_S)
    q = urllib.parse.quote(search_query)
    status, data = _get(f"http://export.arxiv.org/api/query?search_query={q}&max_results=5")
    return data if status == 200 and data else None


def _arxiv_best(data, clean_title):
    root = ET.fromstring(data)
    best, best_ratio = None, 0.0
    for entry in root.iter(f"{ATOM}entry"):
        et = entry.findtext(f"{ATOM}title", "").replace("\n", " ").strip()
        r = _ratio(clean_title, et)
        if r > best_ratio:
            best_ratio = r
            best = re.sub(r"\s+", " ", entry.findtext(f"{ATOM}summary", "")).strip()
    return best, best_ratio


def arxiv_lookup(title):
    clean = title.rstrip(".")
    data = _arxiv_query(f'ti:"{clean}"')
    if data:
        try:
            abstract, r = _arxiv_best(data, clean)
            if abstract and r >= MATCH_RATIO:
                return abstract
        except ET.ParseError:
            pass
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", clean)
             if w.lower() not in STOPWORDS][:6]
    if not words:
        return None
    data = _arxiv_query(" AND ".join(f"ti:{w}" for w in words))
    if data:
        try:
            abstract, r = _arxiv_best(data, clean)
            if abstract and r >= MATCH_RATIO:
                return abstract
        except ET.ParseError:
            pass
    return None


# --- layer 2: Semantic Scholar ----------------------------------------------

def s2_lookup(title):
    _throttle("s2", S2_RATE_S)
    q = urllib.parse.quote(title.rstrip("."))
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search/match"
           f"?query={q}&fields=title,abstract")
    status, data = _get(url)
    if status == 429:
        print("    [info] S2 rate-limited, backing off 10s")
        time.sleep(10)
        status, data = _get(url)
    if status != 200 or not data:
        return None
    try:
        hits = json.loads(data).get("data", [])
    except json.JSONDecodeError:
        return None
    for hit in hits[:1]:
        abstract = (hit.get("abstract") or "").strip()
        if abstract and _ratio(title, hit.get("title", "")) >= MATCH_RATIO:
            return re.sub(r"\s+", " ", abstract)
    return None


# --- layer 3: open-access PDF ------------------------------------------------

def _pdf_url_from_page(page_url):
    _throttle("web", WEB_RATE_S)
    status, data = _get(page_url)
    if status != 200 or not data:
        return None
    html = data.decode("utf-8", errors="replace")
    m = re.search(r'<meta name="citation_pdf_url" content="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'href="(https?://[^"]+\.pdf)"', html)
    return m.group(1) if m else None


def _abstract_from_pdf(pdf_path):
    if PdfReader is None:
        return None
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join((reader.pages[i].extract_text() or "")
                         for i in range(min(2, len(reader.pages))))
    except Exception as e:
        print(f"    [warn] pdf parse: {type(e).__name__}: {e}")
        return None
    m = re.search(r"Abstract\s*[—:-]?\s*(.+?)\s*1\.?\s+Introduction", text, re.S | re.I)
    if not m:
        m = re.search(r"Abstract\s*[—:-]?\s*(.+?)\s*Introduction", text, re.S | re.I)
    if not m:
        return None
    abstract = re.sub(r"-\s*\n\s*", "", m.group(1))
    abstract = re.sub(r"\s+", " ", abstract).strip()
    if not (200 <= len(abstract) <= 4000):
        return None
    return abstract


def pdf_lookup(paper_url, pdf_cache_dir):
    if not paper_url or paper_url == "#" or not paper_url.startswith("http"):
        return None
    if paper_url.lower().endswith(".pdf"):
        pdf_url = paper_url
    else:
        pdf_url = _pdf_url_from_page(paper_url)
    if not pdf_url:
        return None
    cache_dir = Path(pdf_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", pdf_url.rsplit("/", 1)[-1])[:120] or "paper.pdf"
    pdf_path = cache_dir / name
    if not pdf_path.exists():
        _throttle("web", WEB_RATE_S)
        status, data = _get(pdf_url, timeout=60)
        if status != 200 or not data:
            return None
        pdf_path.write_bytes(data)
    return _abstract_from_pdf(pdf_path)


# --- driver -------------------------------------------------------------------

def enrich_records(records, pdf_cache_dir="cache_pdf", max_records=None):
    """Enrich records missing abstracts in place; return per-layer stats."""
    todo = [r for r in records if needs_abstract(r)]
    if max_records is not None:
        todo = todo[:max_records]
    stats = {"todo": len(todo), "arxiv": 0, "semantic_scholar": 0, "pdf": 0, "failed": 0}
    for i, r in enumerate(todo):
        print(f"  [{i + 1}/{len(todo)}] {r['title'][:70]}")
        for source, lookup in (
            ("arxiv", lambda rec: arxiv_lookup(rec["title"])),
            ("semantic_scholar", lambda rec: s2_lookup(rec["title"])),
            ("pdf", lambda rec: pdf_lookup(rec.get("paper"), pdf_cache_dir)),
        ):
            abstract = lookup(r)
            if abstract:
                r["abstract"] = abstract
                r["abstract_source"] = source
                stats[source] += 1
                print(f"    -> {source} ok ({len(abstract)} chars)")
                break
        else:
            stats["failed"] += 1
            print("    -> no abstract found")
    return stats
