"""Read open primary sources for a manual review of experimental LLM judges."""
import io
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from lxml import html
from pypdf import PdfReader

SOURCES = {
    "reconstruction": ("https://www.usenix.org/system/files/usenixsecurity25-wen.pdf", r"6\.1|five times|InternVL|human"),
    "refusal": ("https://www.usenix.org/system/files/usenixsecurity25-song-minkyoo.pdf", r"5\.1\.3|LLaMA.Guard.8B|Broken responses"),
    "twinbreak": ("https://www.usenix.org/system/files/usenixsecurity25-krauss.pdf", r"[Ee]valuation.*[Mm]etric|[Aa]ttack [Ss]uccess [Rr]ate|Llama.Guard|LLaMA.Guard"),
    "papillon": ("https://www.usenix.org/system/files/usenixsecurity25-gong-xueluan.pdf", r"4\.3 Two.level|Experimental metrics|default jailbreak score"),
    "selfdefend": ("https://www.usenix.org/system/files/usenixsecurity25-wang-xunguang.pdf", r"Metrics\. We|unsafe rate uses|5\.2"),
    "sketches": ("https://arxiv.org/html/2412.13386", r"IV.E|LLM-as-a-Judge|Judge Validation"),
    "seval": ("https://arxiv.org/html/2405.14191", r"3\.4\.|riskiness score|4\.1\.|4\.2\.|based on|maximum score"),
    "sejury": ("https://arxiv.org/html/2505.20854", r"IV-C|Kappa|III-C|five evaluation|dynamic|score aggregation"),
    "diting": ("https://arxiv.org/html/2505.19502", r"IV-B|IV-C|Majority Voting|correctness labels|functional consistency|R1-Distill"),
}


def inspect_source(item):
    key, (url, pattern) = item
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    if url.endswith(".pdf"):
        pages = [(i + 1, p.extract_text()) for i, p in enumerate(PdfReader(io.BytesIO(response.content)).pages)]
    else:
        tree = html.fromstring(response.content)
        for e in tree.xpath("//script|//style|//nav|//header|//footer"):
            e.drop_tree()
        pages = [(None, " ".join(tree.itertext()))]
    hits = []
    for page, text in pages:
        normalized = re.sub(r"\s+", " ", text)
        matches = list(re.finditer(pattern, normalized, re.I))
        for m in matches[:6]:
            hits.append({"pdf_page": page, "excerpt": normalized[max(0, m.start()-100):m.end()+1000]})
    return {"key": key, "url": url, "hits": hits}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # Full text and snippets are used in memory; save source locators only.
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(inspect_source, SOURCES.items()))
    target = Path(__file__).parent / "source_evidence.json"
    locators = [{"key": r["key"], "url": r["url"],
                 "matched_pages": sorted({h["pdf_page"] for h in r["hits"] if h["pdf_page"] is not None}),
                 "match_count": len(r["hits"])} for r in records]
    target.write_text(json.dumps(locators, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in records:
        print(json.dumps({"key": r["key"], "hits": r["hits"][:4]}, ensure_ascii=False))
