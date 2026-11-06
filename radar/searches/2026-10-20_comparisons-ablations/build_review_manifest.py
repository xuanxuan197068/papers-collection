"""Join the reviewed report to the local selection and source-access audit."""
import json
import re
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
selection = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
sources = {
    row["key"]: row
    for row in json.loads((OUT / "source_manifest.json").read_text(encoding="utf-8"))
}
report = (OUT / "report.md").read_text(encoding="utf-8")
sections = list(re.finditer(r"^\*\*.+ID (\d+)；([FSA])）\*\*", report, re.M))
assert len(sections) == len(selection["selected"]) == 23
by_id = {row["id"]: row for row in selection["selected"]}
reviewed = []
for index, match in enumerate(sections):
    paper_id, level = int(match[1]), match[2]
    row = by_id[paper_id]
    end = sections[index + 1].start() if index + 1 < len(sections) else report.index("## 3.")
    block = report[match.end():end].strip()
    fields = dict(re.findall(r"^- \*\*(.+?)：\*\*\s*(.+)$", block, re.M))
    source = sources[row["key"]]
    if level in {"F", "S"}:
        assert source["status"] == "ok", row["key"]
        cache = json.loads((OUT / "sources" / f"{row['key']}.json").read_text(encoding="utf-8"))
        assert sum(len(page["text"]) for page in cache["pages"]) > 1000, row["key"]
    reviewed.append({
        "key": row["key"],
        "local_id": paper_id,
        "local_title": row["title"],
        "publication": row["publication"],
        "year": row["year"],
        "local_metadata_file": row["source"],
        "evidence_level": level,
        "access_result": source,
        "report_heading": match[0],
        "review_fields": fields,
        "source_links": re.findall(r"\]\((https?://[^)]+)\)", block),
        "report": "report.md",
    })

assert len({row["local_id"] for row in reviewed}) == len(reviewed)
assert {row["publication"] for row in reviewed} == set(selection["venue_counts"])
result = {
    "date": selection["date"],
    "interest": selection["interest"],
    "scope": "Purposeful selection from every locally represented venue; not exhaustive.",
    "records_in_local_library": selection["record_count"],
    "venue_count": len(selection["venue_counts"]),
    "selected_count": len(reviewed),
    "evidence_counts": dict(Counter(row["evidence_level"] for row in reviewed)),
    "evidence_levels": {
        "F": "Full-text experimental sections reviewed; no reproduction performed.",
        "S": "Author slides reviewed; full paper not verified.",
        "A": "Only abstract/metadata verified; experimental details unresolved.",
    },
    "papers": reviewed,
}
(OUT / "reviewed_papers.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps({k: v for k, v in result.items() if k != "papers"}, ensure_ascii=True, indent=2))
