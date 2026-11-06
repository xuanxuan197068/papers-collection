"""Reproduce the local retrieval audit; semantic screening is recorded explicitly.

Run from the repository root:
    python radar/searches/2026-10-15_agent-honeypot-evaluation/search_local.py
Only writes retrieval.json beside this script. Does not modify the paper database.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("retrieval.json")
QUERIES = {
    "agent_honeypot": r"honeypot|cyber.deception|penetration.test|pentest|offensive.*agent|proactive.defens",
    "cti_forensics": r"threat.intelligence|threat.report|attack.report|incident.report|security.report|forensic|attack.reconstruction|attack.provenance|attack.investigation",
    "truth_and_faithfulness": r"fact.check|factual|hallucinat|faithful|claim.verif|verif.*claim|reference.free|ground.truth|incomplete.*label",
    "judges_and_oracles": r"llm.as.a.judge|llm.*judg|judg.*llm|evaluation.*bias|evaluat.*open.ended|open.ended.*evaluat|metamorphic|test.oracle",
    "elicitation": r"elicitation|extract.*(prompt|personal|secret|knowledge)|(prompt|personal|secret).*extract|intent.infer|plan.recogn|agent.*forensic|faithful.*(reason|explan)|chain.of.thought",
    "missing_evidence": r"capture.recapture|unknown.ground.truth|partial.ground.truth|incomplete.ground.truth|incomplete.*(evidence|observ|truth)|missing.*(evidence|truth)|open.world.*(assum|evaluat)",
    "summarization": r"(factual|semantic|reference.free|reliab).*summari|summari.*(fact|evaluat|metric|faith)|(report|claim).*verif",
    "structured_cti": r"TTP|general Indicator of Compromise|information.extract|knowledge.graph|temporal.logic",
}

# Human semantic screening after reading local abstracts, not a relevance classifier.
# Strings are regexes only to tolerate the database's existing encoding artifacts.
SELECTED = [
    ("P01", r"^MTAS:", "reference_free_evaluation"),
    ("P02", r"^Evaluating Code Summarization Techniques: A New Metric", "source_grounded_evaluation"),
    ("P03", r"^SoK: Automated TTP Extraction", "ontology_and_benchmark_ambiguity"),
    ("P04", r"^Hallucination Detection in Large Language Models with Metamorphic Relations$", "metamorphic_evidence"),
    ("P05", r"^Detecting and Reducing the Factual Hallucinations", "metamorphic_evidence"),
    ("P06", r"^KnowHow: Automatically Applying High-Level CTI", "text_to_execution_evidence"),
    ("P07", r"^POIROT: Aligning Attack Behavior", "text_to_execution_evidence"),
    ("P08", r"^Reading the Tea leaves:", "intelligence_quality"),
    ("P09", r"^A different cup of TI", "incremental_and_operational_value"),
    ("P10", r"^Sharing cyber threat intelligence: Does it really help", "intelligence_timeliness_and_actionability"),
    ("P11", r"^Can LLMs Replace Human Evaluators", "judge_validation"),
    ("P12", r"^SE-Jury:", "judge_ensemble"),
    ("P13", r"^Optimization-based Prompt Injection Attack to LLM-as-a-Judge$", "adversarial_evaluator"),
    ("P14", r"^Test oracle assessment and improvement$", "evaluator_mutation_testing"),
    ("P15", r"^APT to Disagree:", "agreement_without_truth"),
    ("P16", r"^Ground Truth for Binary Disassembly is Not Easy$", "ground_truth_quality"),
    ("P17", r"^Good-looking but Lacking Faithfulness:", "explanation_faithfulness"),
    ("P18", r"^Cloak, Honey, Trap:", "direct_agent_defense_context"),
    ("P19", r"^Into the Deep Web: Understanding E-commerce Fraud", "active_intelligence_elicitation"),
    ("P20", r"^Recovering and Rehosting Mobile Local LLM Conversations", "runtime_forensic_grounding"),
    ("P21", r"^Actively Understanding the Dynamics and Risks", "controlled_watermark_measurement"),
    ("P22", r"^Malicious LLM-Based Conversational AI Makes Users Reveal", "controlled_elicitation_comparison"),
    ("P23", r"^Evaluating LLM-based Personal Information Extraction", "bounded_extraction_reference"),
    ("P24", r"^From Texts to Rules: Generating Sigma Rules", "downstream_operational_validation"),
    ("P25", r"^High Stakes, Low Certainty:", "attribution_uncertainty"),
    ("P26", r"^Calibration of Large Language Models on Code Summarization$", "confidence_calibration"),
    ("P27", r"^Poster: Agentic Shell Honeypot Using Structured Logging$", "honeypot_state_consistency"),
    ("P28", r"^PentestGPT:", "task_completion_baseline"),
]


def compact(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def main() -> None:
    papers, sources = [], []
    for path in sorted((ROOT / "src/assets/data/meta_json").glob("*.json")):
        data = path.read_bytes()
        content = data.decode("utf-8-sig")
        rows = json.loads(content)
        title_lines = [i for i, line in enumerate(content.splitlines(), 1) if re.match(r'\s*"title"\s*:', line)]
        assert len(title_lines) == len(rows), path
        source = path.relative_to(ROOT).as_posix()
        sources.append({"path": source, "sha256": hashlib.sha256(data).hexdigest(), "records": len(rows)})
        for ordinal, (paper, line) in enumerate(zip(rows, title_lines), 1):
            papers.append({
                "id": paper.get("id"), "title": paper["title"],
                "publication": paper["publication"], "year": paper["year"],
                "paper": paper["paper"], "source": source,
                "title_line": line, "record_ordinal": ordinal,
                "_abstract": paper.get("abstract", ""),
            })

    def public(p: dict) -> dict:
        return {k: v for k, v in p.items() if not k.startswith("_")}

    query_results = {}
    candidate_keys = set()
    for name, pattern in QUERIES.items():
        hits = []
        for p in papers:
            th = len(re.findall(pattern, p["title"], re.I))
            ah = len(re.findall(pattern, p["_abstract"], re.I))
            if th or ah:
                score = 15 * th + min(10, ah)
                hits.append((score, p))
                candidate_keys.add(compact(p["title"]))
        hits.sort(key=lambda item: (-item[0], -item[1]["year"], item[1]["title"]))
        query_results[name] = {
            "regex": pattern, "record_hits": len(hits),
            "hits": [dict(public(p), retrieval_score=score) for score, p in hits],
        }

    selected = []
    for code, pattern, reason in SELECTED:
        found = [p for p in papers if re.search(pattern, p["title"], re.I)]
        assert len(found) == 1, (code, pattern, len(found))
        p = found[0]
        selected.append(dict(public(p), code=code, screening_reason=reason,
                             matched_queries=[k for k, v in QUERIES.items() if re.search(v, p["title"] + "\n" + p["_abstract"], re.I)],
                             evidence_level="local_abstract"))

    counts = Counter(compact(p["title"]) for p in papers)
    stats = {
        "files": len(sources), "paper_records": len(papers),
        "unique_compact_titles": len(counts),
        "duplicate_title_excess_records": sum(v - 1 for v in counts.values()),
        "nonempty_abstract_records": sum(p["_abstract"].strip() not in ("", "#") for p in papers),
        "years": sorted({p["year"] for p in papers}),
        "venues": dict(sorted(Counter(p["publication"] for p in papers).items())),
        "candidate_unique_titles": len(candidate_keys), "selected_papers": len(selected),
    }
    result = {
        "date": "2026-10-15", "scope": "all local meta_json files, all available years",
        "evidence_boundary": "Semantic synthesis is based on local abstracts; no full-text evaluation protocol was extracted. Candidate inclusion requires a local database match. Regex scores support retrieval, not paper-quality evaluation.",
        "statistics": stats, "source_manifest": sources,
        "queries": query_results, "selected": selected,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    for p in selected:
        print(f'{p["code"]}\t{p["publication"]} {p["year"]}\t{p["title"]}\t{p["source"]}:{p["title_line"]}')


if __name__ == "__main__":
    main()
