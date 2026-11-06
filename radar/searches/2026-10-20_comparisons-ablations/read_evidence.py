"""Print cached full pages, or nonoverlapping contexts around a regex."""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
key, pattern = sys.argv[1:3]
data = json.loads((Path(__file__).parent / "sources" / f"{key}.json").read_text(encoding="utf-8"))
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
count = 0
for page in data["pages"]:
    if pattern.startswith("page:"):
        if str(page["pdf_page"]) in pattern[5:].split(","):
            print("PDF PAGE", page["pdf_page"], page["text"])
        continue
    text = re.sub(r"\s+", " ", page["text"])
    end = -1
    for match in re.finditer(pattern, text, re.I):
        if match.start() < end:
            continue
        print("PDF PAGE", page["pdf_page"], text[max(0, match.start()-100):match.end()+2000])
        end = match.end() + 2000
        count += 1
        if count >= limit:
            sys.exit()
