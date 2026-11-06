// Pure helpers for the Daily Random page: deterministic date-seeded weighted
// sampling (Efraimidis–Spirakis) over the paper corpus. No Vue state here.

const WEIGHT_MIN = 0.5;
const WEIGHT_MAX = 3;
const BOOST_MIN = 1;
const BOOST_MAX = 3;

// 53-bit string hash (cyrb53). Deterministic across sessions/platforms.
export function cyrb53(str, seed = 0) {
    let h1 = 0xdeadbeef ^ seed;
    let h2 = 0x41c6ce57 ^ seed;
    for (let i = 0; i < str.length; i++) {
        const ch = str.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return 4294967296 * (2097151 & h2) + (h1 >>> 0);
}

// Same normalization as tools/radar_index_merge.py `paper_key`. Note: Python
// str.isalnum() keeps Unicode letters while this regex is ASCII-only — fine
// while the corpus is English-titled; revisit if non-ASCII titles appear.
export function normalizeTitleKey(title) {
    return String(title ?? '')
        .replace(/[^a-zA-Z0-9]/g, '')
        .toLowerCase();
}

// Local-timezone YYYY-MM-DD (toISOString would flip the batch at UTC midnight).
export function todayLocalDateStr(date = new Date()) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function clamp(value, min, max) {
    const num = Number(value);
    if (!Number.isFinite(num)) return 1;
    return Math.min(max, Math.max(min, num));
}

// Filter to the sampling pool: recent years, no embargo placeholders,
// deduplicated by normalized key (USENIX 2026 ships 4 identical
// "Paper Title Under Embargo" rows), optionally minus read papers.
export function buildPool(papers, { minYear, readMap = {}, excludeRead = true } = {}) {
    const seen = new Set();
    const pool = [];
    for (const paper of papers || []) {
        if (!paper || typeof paper.title !== 'string') continue;
        if (Number(paper.year) < minYear) continue;
        if (/under embargo/i.test(paper.title)) continue;
        const key = normalizeTitleKey(paper.title);
        if (!key || seen.has(key)) continue;
        seen.add(key);
        if (excludeRead && readMap[key]) continue;
        pool.push({ ...paper, key });
    }
    return pool;
}

// Clamped weights keep the radar wide: max advantage between any two papers
// is (3*3)/0.5, so every pooled paper keeps a floor probability.
export function weightOf(paper, settings = {}) {
    const categoryWeights = settings.randomCategoryWeights || {};
    const base = clamp(categoryWeights[paper.category] ?? 1, WEIGHT_MIN, WEIGHT_MAX);
    const keywords = (settings.keywords || []).filter((kw) => typeof kw === 'string' && kw.trim());
    let boost = 1;
    if (keywords.length) {
        const title = paper.title.toLowerCase();
        if (keywords.some((kw) => title.includes(kw.trim().toLowerCase()))) {
            boost = clamp(settings.randomKeywordBoost ?? 1.5, BOOST_MIN, BOOST_MAX);
        }
    }
    return base * boost;
}

// Efraimidis–Spirakis ranking: score = u^(1/w) with u derived only from
// (dateStr, paper.key), so each paper's score is independent of the pool
// composition — removing read papers shifts the cut line without reshuffling
// the survivors. "Next batch" is a further slice of this same ranking.
export function rankPool(pool, dateStr, settings = {}) {
    return pool
        .map((paper) => {
            const u = (cyrb53(`${dateStr}|${paper.key}`) + 0.5) / 2 ** 53;
            return { paper, score: Math.pow(u, 1 / weightOf(paper, settings)) };
        })
        .sort((a, b) => b.score - a.score || (a.paper.key < b.paper.key ? -1 : 1))
        .map((entry) => entry.paper);
}
