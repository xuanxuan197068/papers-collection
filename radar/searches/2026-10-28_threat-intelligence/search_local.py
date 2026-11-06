"""Reproducible retrieval over local titles and abstracts; no network calls."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
QUERIES = {
    "explicit_cti": r"threat[ -]?intelligence|\bCTI\b|\bOSINT\b|open.source intelligence|intelligence (?:gathering|collection)|\bIOCs?\b|indicators? of compromise|TTP extraction|threat reports?|attack reports?|APT reports?",
    "underground_sources": r"dark[ -]?(?:web|net)|underground|hacker forums?|cybercrim\w*|cyber.crim\w*|criminal (?:forums?|market\w*|communit\w*)",
    "active_collection": r"honeypot|honeyfarm|honeytoken|honeytrap|network telescope|darknet telescope|sinkhol\w*|intelligence (?:gathering|collection)|threat information|attacker engagement",
    "threat_knowledge": r"(?:attack|threat|security|cybersecurity|cyber.security|malware|vulnerability|APT).{0,45}(?:knowledge graphs?|information extraction|entity extraction|relation extraction)|(?:knowledge graphs?|information extraction|entity extraction|relation extraction).{0,45}(?:attack|threat|security|malware|vulnerability)|attack attribution|threat attribution|APT attribution",
    "infrastructure_discovery": r"malicious infrastructure|attack infrastructure|attacker infrastructure|cybercriminal infrastructure|passive DNS|Internet.wide scann\w*|Internet.wide measur\w*|Internet.scann\w*|security intelligence|threat hunting|threat discovery",
    "social_and_behavioral_intelligence": r"\bTTPs?\b|threat information|threat data|security blogs?|intelligence feeds?|(?:tweets?|Twitter|Telegram|social media).{0,100}(?:security events?|threat|exploits?|malicious|cybercriminal|spam)|(?:security events?|threat|exploits?|malicious|cybercriminal|spam).{0,100}(?:tweets?|Twitter|Telegram|social media)",
}


def compact(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum())


def main() -> None:
    papers, sources = [], []
    for path in sorted((ROOT / "src/assets/data/meta_json").glob("*.json")):
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")
        rows = json.loads(content)
        lines = [i for i, line in enumerate(content.splitlines(), 1)
                 if re.match(r'\s*"title"\s*:', line)]
        assert len(rows) == len(lines), path
        source = path.relative_to(ROOT).as_posix()
        sources.append({"path": source, "sha256": hashlib.sha256(raw).hexdigest(), "records": len(rows)})
        for ordinal, (row, line) in enumerate(zip(rows, lines), 1):
            p = {k: row.get(k) for k in ("id", "title", "publication", "year", "paper", "abstract")}
            p.update(source=source, title_line=line, record_ordinal=ordinal)
            p["matches"] = {}
            for name, pattern in QUERIES.items():
                title_hits = re.findall(pattern, p["title"], re.I)
                abstract_hits = re.findall(pattern, p.get("abstract") or "", re.I)
                if title_hits or abstract_hits:
                    p["matches"][name] = {"title": title_hits, "abstract": abstract_hits}
            papers.append(p)
    candidates = [p for p in papers if p["matches"]]
    stats = {
        "files": len(sources), "records": len(papers),
        "unique_compact_titles": len({compact(p["title"]) for p in papers}),
        "years": [min(p["year"] for p in papers), max(p["year"] for p in papers)],
        "venues": dict(sorted(Counter(p["publication"] for p in papers).items())),
        "with_abstract": sum((p.get("abstract") or "").strip() not in ("", "#") for p in papers),
        "candidate_records": len(candidates),
        "candidate_unique_titles": len({compact(p["title"]) for p in candidates}),
        "query_counts": {q: sum(q in p["matches"] for p in candidates) for q in QUERIES},
    }
    result = {"date": "2026-10-28", "scope": "All current local meta_json files and available years",
              "evidence_boundary": "Retrieval and semantic screening use local titles and abstracts only. Keyword matches are candidates, not relevance decisions or a completeness guarantee.",
              "statistics": stats, "queries": QUERIES, "source_manifest": sources,
              "candidates": candidates}
    screening_path = OUT / "screening.json"
    if screening_path.exists():
        screening = json.loads(screening_path.read_text(encoding="utf-8"))
        by_id = {p["id"]: p for p in candidates}
        assert len(by_id) == len(candidates), "Duplicate candidate IDs"
        assert len({s["id"] for s in screening}) == len(screening), "Duplicate selections"
        selected = []
        for s in screening:
            assert s["id"] in by_id, s
            p = by_id[s["id"]]
            assert (p.get("abstract") or "").strip() not in ("", "#"), s
            if "expected_title" in s:
                assert p["title"] == s["expected_title"], s
            selected.append(dict(p, **{k: v for k, v in s.items() if k != "id"}))
        result["selected"] = selected
        stats["selected_core"] = sum(p["tier"] == "重点相关" for p in selected)
        stats["selected_extended"] = sum(p["tier"] != "重点相关" for p in selected)
        report = [
            "# 本地论文检索：威胁情报、情报收集与威胁信息获取",
            "", "检索日期：2026-10-28（Asia/Shanghai）。", "",
            f"范围：本地 `src/assets/data/meta_json/` 的 {stats['files']} 个文件、{stats['records']:,} 条记录"
            f"（{stats['unique_compact_titles']:,} 个去重标题），覆盖 {stats['years'][0]}–{stats['years'][1]} 年、{len(stats['venues'])} 个会议/期刊。",
            f"检索 {len(QUERIES)} 组标题与摘要关键词得到 {stats['candidate_records']} 篇候选。经标题筛选和重点候选摘要核对，整理"
            f" {stats['selected_core']} 篇重点相关论文及 {stats['selected_extended']} 篇方法或场景延伸材料。", "",
            "依据为本地标题和摘要，并参考已有方法索引与阅读状态；没有联网补充或核对全文。年份、题名和论文链接均来自本地元数据。"
            "相关性分组是本次人工语义判断，不代表论文质量排名或所有相关论文的完整清单。"
            f"库内有 {stats['records']-stats['with_abstract']} 条记录缺少有效摘要；关键词召回也可能漏掉未使用这些表达的论文。", "",
            "## 优先阅读路线", "",
            "- **主动获取新的威胁信息**：S01（自动聊天）→ S06（诱饵账号）→ H04（响应式网络望远镜）→ H02（协同蜜罐）。",
            "- **发现和利用新的情报源**：S02（地下市场鉴定评论）→ S03（Twitter 安全事件）→ S04 / S05（Telegram）。",
            "- **从报告中提取可用知识**：E01（IOC）→ E02（TTP 提取综述）→ E04（Sigma 规则）；E05 / E06 衔接到日志分析。",
            "- **验证收集是否有价值**：Q02（评估指标）→ Q05（公开 STIX 数据质量）→ Q01（传播链测量）→ Q06（IOC 发布时效）；地下市场采集另读 Q10。", "",
            "IOC 指失陷指标，如恶意 IP、域名或文件哈希；TTP 指攻击者的战术、技术与过程。", "",
        ]
        for group in dict.fromkeys(p["group"] for p in selected):
            report.extend([f"## {group}", "", "| 编号 | 论文与出处 | 信息来源 | 方法及相关性 |", "|---|---|---|---|"])
            for p in selected:
                if p["group"] != group:
                    continue
                source_path = (ROOT / p["source"]).as_posix()
                local = f"[本地摘要](<{source_path}:{p['title_line']}>)"
                title = p["title"].replace("|", "\\|")
                paper = f"[{title}]({p['paper']})<br>{p['publication']} {p['year']} · {local}"
                desc = p["summary_cn"] + "<br>**相关性：**" + p["fit_cn"]
                report.append(f"| {p['code']} | {paper} | {p['source_cn']} | {desc} |")
            report.append("")
        report.extend([
            "## 检索与排除说明", "",
            "覆盖显式 CTI / IOC、地下情报源、主动采集、安全知识提取、基础设施发现、社交平台及 TTP 等六组表达；具体正则、命中位置、全部候选摘要和源文件 SHA-256 见同目录 retrieval.json。",
            "排除仅泛泛提到 cyber threats / cybercrime、通用知识图攻击、普通网络流量分类等弱命中。智能合约中以诈骗为目的的 honeypot 未当作防御型采集蜜罐纳入。",
            "E04–E09 中多篇重点在情报应用、关联或推理，Q09 重点在共享协议；均在相关性说明中作了区分。X03 是 Poster，X06 是 dissertation research description。",
            "H02 已有方法卡：[Cyber-Physical Deception Through Coordinated IoT Honeypots](<" + (ROOT / "radar/cards/coordinated-iot-honeypots.md").as_posix() + ">)。本次没有新增勾选、已读或方法卡状态。", "",
            "检索材料保存在 radar/searches/，没有修改论文数据或已有方法索引。", "",
            "复现关键词召回与报告生成：", "",
            "```powershell", "python radar/searches/2026-10-28_threat-intelligence/search_local.py", "```", "",
            "screening.json 保存本次人工选择及摘要依据下的中文说明；重跑只复现召回和组装，不会自动执行新的语义筛选。", "",
        ])
        (OUT / "report.md").write_text("\n".join(report), encoding="utf-8")
    (OUT / "retrieval.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    for q in QUERIES:
        hits = [p for p in candidates if q in p["matches"]]
        hits.sort(key=lambda p: (-bool(p["matches"][q]["title"]), -p["year"], p["title"]))
        print("\nQUERY", q)
        for p in hits:
            if q == "explicit_cti" or p["matches"][q]["title"]:
                print(f'{p["id"]}\t{p["publication"]} {p["year"]}\t{p["title"]}')


if __name__ == "__main__":
    main()
