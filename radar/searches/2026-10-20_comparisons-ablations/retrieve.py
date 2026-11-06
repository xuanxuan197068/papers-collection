"""Reproducible local selection and open-primary-source reading cache.

Run: uv run python radar/searches/2026-10-20_comparisons-ablations/retrieve.py
Only writes beside this script; never modifies the paper database.
"""
import hashlib
import io
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from lxml import html
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
# Selection is manual after reviewing all venue-specific ranked candidate lists.
SELECTED = {
    "cpds": 4147, "cheat": 4535,
    "honeyplc": 3153, "subplay": 2089,
    "incalmo": 244, "depcomm": 997,
    "chimera": 6598, "honeysat": 6653,
    "marg": 8269, "sejury": 8084,
    "autoresttest": 9757, "codesummary": 10110,
    "mastest": 11675, "judge": 11535,
    "pwn": 12919, "mtas": 12736,
    "fleetio": 14722, "mulberry": 14945,
    "potemkin": 14444, "backtracker": 14514,
    "cdsmg": 15928, "disguise": 15830,
    "automaltool": 16116,
}
SOURCES = {
    "cpds": "https://www.usenix.org/system/files/usenixsecurity25-guan.pdf",
    "cheat": "https://www.usenix.org/system/files/usenixsecurity25-ayzenshteyn.pdf",
    "honeyplc": "https://carlosrubiomedrano.com/publications/honeyPLC-next-generation-ccs2020.pdf",
    "subplay": "https://arxiv.org/html/2402.03741",
    "incalmo": "https://arxiv.org/html/2501.16466v4",
    "depcomm": "https://par.nsf.gov/servlets/purl/10287251",
    "chimera": "https://www.ndss-symposium.org/wp-content/uploads/2026-f375-paper.pdf",
    "honeysat": "https://www.ndss-symposium.org/wp-content/uploads/2026-f537-paper.pdf",
    "marg": "https://yepangliu.github.io/files/ASE2024-MARG.pdf",
    "sejury": "https://arxiv.org/html/2505.20854",
    "autoresttest": "https://arxiv.org/html/2411.07098",
    "judge": "https://arxiv.org/html/2502.06193",
    "pwn": "https://arxiv.org/pdf/2308.00121",
    "fleetio": "https://snir.cs.illinois.edu/listed/fleetIO.pdf",
    "potemkin": "https://web.stanford.edu/class/archive/cs/cs240/cs240.1086/readings/potemkin.pdf",
    "backtracker": "https://www.cs.rochester.edu/meetings/sosp2003/papers/p190-king.pdf",
    "codesummary": "https://arxiv.org/html/2312.15475",
    "mulberry": "https://zishenwan.github.io/publication/ASPLOS24_mulberry_slide.pdf",
    "mtas": "https://dl.acm.org/doi/pdf/10.1145/3660820",
    "mastest": "https://is.cas.cn/ztzl2016/2024xsnh/2024hbzs/202408/P020240828564827483868.pdf",
    "disguise": "https://ieeexplore.ieee.org/document/11218933/",
    "cdsmg": "https://doi.org/10.1109/TIFS.2026.3664334",
    "automaltool": "https://nesa.zju.edu.cn/download/auto_20260505_T-IFS-23770_CameraReady.pdf",
}


def inventory():
    records, files = [], []
    for path in sorted((ROOT / "src/assets/data/meta_json").glob("*.json")):
        raw = path.read_bytes()
        rows = json.loads(raw.decode("utf-8-sig"))
        files.append({"path": path.relative_to(ROOT).as_posix(),
                      "sha256": hashlib.sha256(raw).hexdigest(), "count": len(rows)})
        for row in rows:
            records.append({**row, "source": path.relative_to(ROOT).as_posix()})
    selected = []
    for key, paper_id in SELECTED.items():
        matches = [p for p in records if p["id"] == paper_id]
        assert len(matches) == 1, (key, paper_id)
        selected.append({"key": key, **matches[0]})
    result = {"date": "2026-10-20", "interest": "智能体蜜罐、欺骗与情报获取",
              "record_count": len(records), "file_count": len(files),
              "venue_counts": dict(Counter(p["publication"] for p in records)),
              "files": files, "selected": selected}
    (OUT / "selection.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def retrieve(item):
    key, url = item
    cache = OUT / "sources" / f"{key}.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data.get("status") == "ok" and data.get("url") == url:
            return {k: v for k, v in data.items() if k != "pages"}
    try:
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        raw = response.content
        if raw.lstrip().startswith(b"%PDF"):
            pages = [{"pdf_page": i + 1, "text": page.extract_text()}
                     for i, page in enumerate(PdfReader(io.BytesIO(raw)).pages)]
            kind = "pdf"
        else:
            tree = html.fromstring(raw)
            for element in tree.xpath("//script|//style|//nav|//header|//footer"):
                element.drop_tree()
            pages = [{"pdf_page": None, "text": " ".join(tree.itertext())}]
            kind = "html"
        data = {"key": key, "url": url, "resolved_url": response.url,
                "status": "ok", "kind": kind,
                "sha256": hashlib.sha256(raw).hexdigest(), "pages": pages}
    except Exception as exc:
        data = {"key": key, "url": url, "status": "error", "error": str(exc)}
    cache.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {k: v for k, v in data.items() if k != "pages"}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    (OUT / "sources").mkdir(exist_ok=True)
    inventory()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(retrieve, SOURCES.items()))
    (OUT / "source_manifest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for result in results:
        print(result["key"], result["status"], result.get("error", ""))
