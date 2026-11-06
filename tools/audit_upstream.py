"""Read the author's published CDN data and produce a data-only sync audit.

Never modifies data.yml, official_cache, src/assets/data or the git worktree
state. Downloaded evidence lives under cache/; review reports under radar/.
"""
import argparse
import collections
import datetime as dt
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://cdn.c01dkit.com/sec-papers"
REFERER = "https://sec.c01dkit.com/"
META = ROOT / "src/assets/data/meta_json"
URL_ALIASES = {}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def compact(value):
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())


def text_norm(value):
    return " ".join(unicodedata.normalize("NFKC", value or "").split())


def doi(value):
    value = urllib.parse.unquote(value or "").lower().rstrip("/.")
    found = re.search(r"10\.\d{4,9}/[^?#\s]+", value)
    return found.group(0) if found else ""


def document_url(value):
    if not value or not value.startswith("http"):
        return ""
    value = URL_ALIASES.get(value, value)
    parts = urllib.parse.urlsplit(value)
    return parts.netloc.lower().removeprefix("www.") + urllib.parse.unquote(parts.path).rstrip("/")


def usable(value):
    return len(text_norm(value)) >= 50 and text_norm(value) != "#"


def group(rows):
    out = collections.defaultdict(list)
    for row in rows:
        out[(row["publication"], int(row["year"]))].append(row)
    return out


def title_preview(row):
    return {k: row.get(k) for k in ("id", "publication", "year", "title", "paper")}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def duplicates(rows):
    index = collections.defaultdict(list)
    for row in rows:
        index[(row["publication"], int(row["year"]), compact(row["title"]))].append(row)
    return [list(map(title_preview, items)) for items in index.values() if len(items) > 1]


def changes(local, upstream):
    result = {}
    for field in ("title", "paper", "category", "status"):
        a, b = local.get(field), upstream.get(field)
        if a == b:
            continue
        if field == "title":
            kind = "format_only" if compact(a or "") == compact(b or "") else "title_variant"
        elif field == "paper":
            da, db = doi(a), doi(b)
            kind = "same_doi" if da and da == db else "different_doi" if da and db else "alternate_url"
        else:
            kind = "value_changed"
        result[field] = {"kind": kind, "local": a, "upstream": b}
    a, b = text_norm(local.get("abstract")), text_norm(upstream.get("abstract"))
    if a != b:
        if "under embargo" in a.casefold() and usable(b) and "under embargo" not in b.casefold():
            kind = "upstream_releases_embargo"
        elif not usable(a) and usable(b):
            kind = "upstream_fills_missing"
        elif usable(a) and not usable(b):
            kind = "local_has_abstract"
        elif not usable(a) and not usable(b):
            kind = "both_missing"
        else:
            kind = "both_present_different"
        result["abstract"] = {
            "kind": kind, "local_chars": len(a), "upstream_chars": len(b),
            "similarity": round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 4),
            "local_preview": a[:240], "upstream_preview": b[:240],
            "local_sha256": hashlib.sha256(a.encode()).hexdigest(),
            "upstream_sha256": hashlib.sha256(b.encode()).hexdigest(),
        }
    return result


def md_title(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="user-facing report date, YYYY-MM-DD")
    ap.add_argument("--offline", action="store_true", help="reuse the downloaded snapshot")
    ap.add_argument("--check-usenix", action="store_true", help="verify research/talk markers on official schedules")
    args = ap.parse_args()
    revision = git("rev-parse", "upstream/main")
    cache = ROOT / "cache/upstream-audit" / f"{args.date}-{revision[:7]}"
    report_dir = ROOT / "radar/sync" / f"upstream-{args.date}"
    cache.mkdir(parents=True, exist_ok=True)
    manifest = []
    review_path = report_dir / "review.json"
    decisions = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
    URL_ALIASES.update(decisions.get("document_aliases", {}))

    def download(relative):
        target = cache / relative
        if args.offline:
            payload = target.read_bytes()
        else:
            request = urllib.request.Request(
                BASE + "/" + urllib.parse.quote(relative, safe="/"),
                headers={"User-Agent": "papers-collection-sync-audit/1.0", "Referer": REFERER},
            )
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(request, timeout=60) as response:
                        if urllib.parse.urlparse(response.geturl()).hostname != "cdn.c01dkit.com":
                            raise ValueError("CDN redirected away from the author's data host")
                        payload = response.read()
                        entry = {"path": relative, "url": request.full_url,
                                 "last_modified": response.headers.get("Last-Modified"),
                                 "etag": response.headers.get("ETag")}
                    parsed = json.loads(payload)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
                    manifest.append({**entry, "sha256": hashlib.sha256(payload).hexdigest()})
                    time.sleep(0.15)
                    return parsed
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2 * (attempt + 1))
        return json.loads(payload)

    local_files = sorted(META.glob("*.json"))
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in local_files}
    local_rows = [row for path in local_files for row in json.loads(path.read_text(encoding="utf-8"))]
    upstream_list = download("data.json")
    upstream_stats = download("data-statistics.json")
    expected = group(upstream_list)
    upstream_rows = []
    for number, (edition, listed) in enumerate(sorted(expected.items()), 1):
        publication, year = edition
        relative = f"meta_json/{publication} - {year}.json"
        rows = download(relative)
        # Fail on a stale/incomplete mixture of CDN objects, even when counts agree.
        if len(rows) != len(listed) or collections.Counter((r["id"], r["title"]) for r in rows) != collections.Counter((r["id"], r["title"]) for r in listed):
            raise ValueError(f"CDN list/meta disagree for {edition}")
        if any((r["publication"], int(r["year"])) != edition for r in rows):
            raise ValueError(f"CDN meta contains records from another edition: {edition}")
        upstream_rows.extend(rows)
        if not args.offline:
            print(f"snapshot {number}/{len(expected)}: {publication} {year} ({len(rows)})", flush=True)
    if len(upstream_rows) != upstream_stats["total"]:
        raise ValueError("CDN statistics total disagrees with list/meta")
    if not args.offline:
        final_list = download("data.json")
        if final_list != upstream_list:
            raise ValueError("CDN data changed during audit; rerun for a consistent snapshot")
        (cache / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    local_groups, upstream_groups = group(local_rows), group(upstream_rows)
    additions, local_only, matches, review, conflicts, editions = [], [], [], [], [], []
    for edition in sorted(set(local_groups) | set(upstream_groups)):
        local, upstream = local_groups[edition], upstream_groups[edition]
        used = set()
        pairs = []
        unmatched = []
        local_title = collections.defaultdict(list)
        local_doi = collections.defaultdict(list)
        local_url = collections.defaultdict(list)
        for index, row in enumerate(local):
            local_title[compact(row["title"])].append(index)
            if doi(row.get("paper")):
                local_doi[doi(row["paper"])].append(index)
            if document_url(row.get("paper")):
                local_url[document_url(row["paper"])].append(index)
        for remote in upstream:
            candidates = [i for i in local_title[compact(remote["title"])] if i not in used]
            method = "normalized_title"
            # URLs resolve duplicate titles and embargo placeholders. Same
            # presentation URL remains the same paper after its title changes.
            if len(candidates) != 1 and document_url(remote.get("paper")):
                candidates = [i for i in local_url[document_url(remote["paper"])] if i not in used]
                method = "document_url"
            if len(candidates) != 1 and doi(remote.get("paper")):
                candidates = [i for i in local_doi[doi(remote["paper"])] if i not in used]
                method = "doi"
            if len(candidates) == 1:
                index = candidates[0]
                used.add(index)
                pairs.append((local[index], remote, method))
            else:
                unmatched.append(remote)
        for remote in unmatched:
            scored = sorted(((difflib.SequenceMatcher(None, compact(remote["title"]), compact(row["title"]), autojunk=False).ratio(), i)
                             for i, row in enumerate(local) if i not in used), reverse=True)
            if scored and scored[0][0] >= 0.9:
                score, index = scored[0]
                # Similar titles are not proof of identity; retain both in the
                # set differences and explicitly flag for human review.
                review.append({"upstream": title_preview(remote), "local": title_preview(local[index]),
                               "similarity": round(score, 4)})
        new = unmatched
        own = [row for i, row in enumerate(local) if i not in used]
        additions.extend(new)
        local_only.extend(own)
        for own_row, remote, method in pairs:
            delta = changes(own_row, remote)
            match = {"local": title_preview(own_row), "upstream": title_preview(remote),
                     "match_method": method, "changes": delta}
            matches.append(match)
            if delta:
                conflicts.append(match)
        editions.append({"publication": edition[0], "year": edition[1], "local": len(local),
                         "upstream": len(upstream), "matched": len(pairs), "upstream_only": len(new),
                         "local_only": len(own)})

    global_local_doi = collections.defaultdict(list)
    for row in local_rows:
        if doi(row.get("paper")):
            global_local_doi[doi(row["paper"])].append(row)
    cross_edition = []
    for row in additions:
        candidates = global_local_doi.get(doi(row.get("paper")), [])
        if candidates:
            cross_edition.append({"upstream": title_preview(row), "local": list(map(title_preview, candidates))})
    field_counts = collections.Counter()
    for match in matches:
        for field, delta in match["changes"].items():
            field_counts[f"{field}:{delta['kind']}"] += 1
    local_schema = sorted({key for row in local_rows for key in row})
    upstream_schema = sorted({key for row in upstream_rows for key in row})
    evidence_path = cache / "schedule-evidence.json"
    schedule_evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    if args.check_usenix:
        from lxml import html
        schedule_evidence = {}
        for event in ("usenixsecurity25", "usenixsecurity26", "osdi26"):
            url = f"https://www.usenix.org/conference/{event}/technical-sessions"
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            print(f"Check official schedule: {url}", flush=True)
            schedule_path = cache / f"{event}-technical-sessions.html"
            if args.offline and schedule_path.exists():
                payload = schedule_path.read_bytes()
            else:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = response.read()
                schedule_path.write_bytes(payload)
            tree = html.fromstring(payload)
            records = {}
            for article in tree.xpath('//article[.//h2/a]'):
                anchor = article.xpath('.//h2/a')[0]
                link = urllib.parse.urljoin(url, anchor.get("href"))
                if f"/conference/{event}/" not in urllib.parse.urlsplit(link).path:
                    continue
                research = bool(article.xpath('.//*[contains(@class,"field-name-field-paper-people-text")]'))
                speaker = bool(article.xpath('.//*[contains(@class,"field-name-field-presented-by")]'))
                records[document_url(link)] = {
                    "url": link, "title": text_norm(anchor.text_content()),
                    "research_author_field": research, "speaker_field": speaker,
                    "pdf_media": bool(article.xpath('.//span[contains(@class,"usenix-schedule-media pdf")]')),
                    "kind": "research_paper" if research else "talk" if speaker else "unresolved",
                }
            schedule_evidence[event] = {"source": url, "sha256": hashlib.sha256(payload).hexdigest(), "records": records}
        evidence_path.write_text(json.dumps(schedule_evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    schedule_records = {key: value for page in schedule_evidence.values() for key, value in page["records"].items()}
    excluded, import_candidates, unresolved = [], [], []
    front_matter = {"Author Index", "Proceedings", "Copyright Page", "Table of Contents",
                    "Message from the Program Chairs", "Organizing Committee", "Program Committee"}
    for row in additions:
        marker = schedule_records.get(document_url(row.get("paper")))
        reason = None
        if row["publication"] == "IEEE S&P" and row["year"] == 2026 and row["title"] in front_matter:
            reason = "proceedings_front_matter"
        elif marker and marker["kind"] == "talk":
            reason = "official_schedule_speaker_field"
        if reason:
            excluded.append({**title_preview(row), "reason": reason, "evidence": marker})
        else:
            import_candidates.append(row)
            checked_editions = {("USENIX Sec", 2025), ("USENIX Sec", 2026), ("OSDI", 2026)}
            if (row["publication"], row["year"]) in checked_editions and schedule_evidence and not (marker and marker["kind"] == "research_paper"):
                unresolved.append(title_preview(row))
    summary = {
        "date": args.date, "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "upstream_git_revision": revision, "upstream_git_commit": git("log", "-1", "--format=%cI %s", revision),
        "cdn": BASE, "snapshot_dir": str(cache.relative_to(ROOT)),
        "local_total": len(local_rows), "upstream_total": len(upstream_rows),
        "matched": len(matches), "upstream_only_candidates": len(additions), "local_only": len(local_only),
        "fuzzy_review_pairs": len(review), "cross_edition_doi_pairs": len(cross_edition),
        "local_schema": local_schema, "upstream_schema": upstream_schema,
        "field_differences": dict(field_counts),
        "excluded_nonpapers": len(excluded), "import_candidates": len(import_candidates),
        "unresolved_schedule_records": len(unresolved),
        "local_duplicate_title_groups": duplicates(local_rows),
        "upstream_duplicate_title_groups": duplicates(upstream_rows),
    }
    if len(matches) + len(additions) != len(upstream_rows) or len(matches) + len(local_only) != len(local_rows):
        raise AssertionError("comparison counts do not reconcile")
    for relative, digest in before.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"local data changed during audit: {relative}")
    report = {"summary": summary, "editions": editions, "upstream_only": additions,
              "local_only": local_only, "matched_field_differences": conflicts,
              "fuzzy_review": review, "cross_edition_doi": cross_edition,
              "excluded_nonpapers": excluded, "import_candidates": import_candidates,
              "unresolved_schedule_records": unresolved, "review_decisions": decisions,
              "local_files_sha256": before}
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 作者数据同步前审计（{args.date}）", "", f"- 作者 Git 提交：`{revision}`（{summary['upstream_git_commit']}）",
             f"- 数据来源：{BASE}；逐届 meta 与全量清单 ID/标题/数量已核对，下载前后 data.json 一致。",
             f"- 本地 {len(local_rows)} 篇；作者 {len(upstream_rows)} 篇；已确定匹配 {len(matches)} 篇。",
             f"- 作者独有候选 {len(additions)} 篇；本地独有 {len(local_only)} 篇；近似标题待核对 {len(review)} 对。",
             f"- 排除前言/报告 {len(excluded)} 条后，可同步候选 {len(import_candidates)} 篇；官方场次类型未核实 {len(unresolved)} 条。",
             "- 本次只生成审计报告和下载快照；未改数据、配置或合并仓库。", "",
             "## 分会议/年份差异", "", "| 会议/期刊 | 年份 | 本地 | 作者 | 匹配 | 作者独有候选 | 本地独有 |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for e in editions:
        if e["upstream_only"] or e["local_only"]:
            lines.append(f"| {md_title(e['publication'])} | {e['year']} | {e['local']} | {e['upstream']} | {e['matched']} | {e['upstream_only']} | {e['local_only']} |")
    lines += ["", "## 已匹配论文的字段差异", ""]
    lines += [f"- {key}: {count}" for key, count in sorted(field_counts.items())]
    lines += ["", "## 可补齐的缺失摘要与解密论文", ""]
    for match in conflicts:
        delta = match["changes"].get("abstract", {})
        if delta.get("kind") in ("upstream_fills_missing", "upstream_releases_embargo"):
            row = match["upstream"]
            lines.append(f"- {row['publication']} {row['year']}: [{row['title']}]({URL_ALIASES.get(row['paper'], row['paper'])}) ({delta['kind']})")
    lines += ["", "上游新增字段：" + ", ".join(sorted(set(upstream_schema) - set(local_schema))),
              "", "ID 属于不同方案，不能跨库直接比较或覆盖；语义标签、中文摘要和奖项应放 radar 扩展层。",
              "", "## 近似标题待核对", ""]
    for item in review:
        lines.append(f"- {item['upstream']['publication']} {item['upstream']['year']} ({item['similarity']}): 作者「{item['upstream']['title']}」 ↔ 本地「{item['local']['title']}」")
    lines += ["", "## 应排除的非论文条目", ""]
    lines += [f"- {r['publication']} {r['year']}: {r['title']} ({r['reason']})" for r in excluded]
    lines += ["", "## 可同步候选论文清单", ""]
    for edition, rows in sorted(group(import_candidates).items()):
        lines += [f"### {edition[0]} - {edition[1]}（{len(rows)} 篇）", ""]
        for row in rows:
            link = URL_ALIASES.get(row.get("paper"), row.get("paper", "#"))
            lines.append(f"- [{row['title']}]({link})" if link.startswith("http") else f"- {row['title']}")
        lines.append("")
    lines += ["", "## 作者独有候选原始清单（含上述排除条目）", ""]
    for edition, rows in sorted(group(additions).items()):
        lines += [f"### {edition[0]} - {edition[1]}（{len(rows)} 篇）", ""]
        for row in rows:
            link = row.get("paper", "#")
            lines.append(f"- [{row['title']}]({link})" if link.startswith("http") else f"- {row['title']}")
        lines.append("")
    (report_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"Report: {report_dir}", flush=True)


if __name__ == "__main__":
    main()
