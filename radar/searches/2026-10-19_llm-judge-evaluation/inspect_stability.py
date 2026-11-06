"""Cache open paper PDFs in a temporary folder for targeted stability review."""
import io
import json
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from pypdf import PdfReader

SOURCES = {
    "code_summary": "https://arxiv.org/pdf/2407.07959v2",
    "sketches": "https://arxiv.org/pdf/2412.13386v1",
    "reconstruction": "https://www.usenix.org/system/files/usenixsecurity25-wen.pdf",
    "crescendo": "https://www.usenix.org/system/files/usenixsecurity25-russinovich.pdf",
    "papillon": "https://www.usenix.org/system/files/usenixsecurity25-gong-xueluan.pdf",
    "selfdefend": "https://www.usenix.org/system/files/usenixsecurity25-wang-xunguang.pdf",
    "refusal": "https://www.usenix.org/system/files/usenixsecurity25-song-minkyoo.pdf",
    "twinbreak": "https://www.usenix.org/system/files/usenixsecurity25-krauss.pdf",
}
CACHE = Path(tempfile.gettempdir()) / "papers-collection-20261019-judge-stability"


def cache_source(item):
    key, url = item
    pdf_path = CACHE / f"{key}.pdf"
    if not pdf_path.exists():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"Expected PDF for {key}")
        pdf_path.write_bytes(response.content)
    reader = PdfReader(io.BytesIO(pdf_path.read_bytes()))
    pages = [p.extract_text(extraction_mode="layout") for p in reader.pages]
    text = "\n\n".join(f"=== PDF PAGE {i+1} ===\n{p}" for i, p in enumerate(pages))
    (CACHE / f"{key}.txt").write_text(text, encoding="utf-8")
    normalized = [re.sub(r"\s+", " ", p) for p in pages]
    keywords = [r"temperature", r"top_p", r"repeated?", r"majority", r"determin", r"stability", r"randomness", r"do_sample", r"greedy"]
    hits = []
    for pattern in keywords:
        for page, content in enumerate(normalized, 1):
            for match in list(re.finditer(pattern, content, re.I))[:2]:
                hits.append({"keyword": pattern, "pdf_page": page,
                             "context": content[max(0, match.start()-130):match.end()+500]})
    return {"key": key, "url": url, "pages": len(pages), "hits": hits}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    CACHE.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(cache_source, SOURCES.items()))
    (CACHE / "review_search_hits.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cache_directory": str(CACHE), "papers": [{"key": r["key"], "pages": r["pages"], "hits": len(r["hits"])} for r in records]}))
