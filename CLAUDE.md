# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Vue 3 + Vite web app displaying curated academic security papers from top-tier conferences (IEEE S&P, USENIX Security, ACM CCS, NDSS) and related venues (ICSE, ISSTA, FSE, ASPLOS, SOSP).

**This is a fork** (xuanxuan197068/papers-collection) of c01dkit/sec-papers-collection, extended into a personal "paper radar": an own DBLP-based update chain plus an in-session semantic digest workflow. See "Fork-specific notes" below.

## Fork-specific notes

### Two update chains

- **Own chain (primary)**: `uv run tools/fetch_new.py` pulls venue TOCs from DBLP and fills abstracts via arXiv / Semantic Scholar / open-access PDFs (rate limits carry random jitter; `--loop <min>` runs unattended for 24h abstract backfill). Driven by the `dblp_toc_template` / `source: dblp` fields in `data.yml`. See `.claude/skills/fetch-papers/`.
- **Upstream chain (backup)**: the author's manual bib/csv + XPath-crawl flow still works untouched. Pull author updates with `git fetch upstream && git merge upstream/main` (remote `upstream` = c01dkit/sec-papers-collection). Keep meta_json field sets unchanged so merges stay clean.
- **Completeness audit**: `uv run tools/audit_completeness.py [--venue KEY] [--recent N]` compares local vs DBLP vs upstream paper counts per venue-year (fuzzy-matched gaps) and suggests fetch/merge actions.

### Rebuilding official_cache

Upstream ships original bib/csv sources in an AES-encrypted `private_source.zip` (password not available to this fork). `official_cache/*.json` intermediates are instead reconstructed from the committed meta_json files:

```bash
uv run tools/rebuild_official_cache.py   # one-time after fresh clone
```

`cache.zip` (crawl HTML cache) is a plain zip; unzip it into the repo root so USENIX/NDSS crawl-path years reproduce offline.

### Environment

No `.env` is needed for this fork's flows (`--llm-analyze` and `--zip`/`--unzip` are upstream-only; `PRIVATE_ZIP_PASSWD` is unknown anyway).

### Radar semantic layer

`radar/` holds the semantic outputs produced in-session via `.claude/skills/radar-digest/`:
- `radar/index/<Pub> - <Year>.json` — per-paper method index (method/technique/problem/scenario/evidence/lens), built by subagent map-reduce (`tools/radar_shard.py` → haiku/sonnet subagents → `tools/radar_index_merge.py`, which prunes extraction-drift keys and reports coverage). `method` = one-line "what's new"; `technique` = concrete algorithm/pipeline ("how it's done"). Longer `technique` text is JSON-fragile, so use `model: sonnet` when re-filling gaps.
- `radar/maps/` — direction maps (Stage 1, two-part: neutral + lens-combined). `radar/cards/` — method cards (Stage 2). `radar/state/` — read/pick status + missing-abstracts log.

Extra information never goes into `src/assets/data/` files — those keep the upstream schema.

### Frontend notes (fork)

- **Method Index page** (`/paper/method-index`, `src/views/paper/MethodIndex.vue`) browses `radar/index/` files with search + lens filter; shows a "not generated yet" prompt when a venue-year has no index.
- Venue→category grouping in `ViewAbstract.vue` / `MethodIndex.vue` and the `Trends.vue` category labels are **data-driven** (from `data-statistics.json` overview) with fallbacks, so adding a new venue/category (e.g. `ai-ml`, `journal`) doesn't break the menu or charts; `main.py`'s trend palette cycles, so a category may hold >6 venues.
- **Journals** use `category: journal` (grouped under "安全期刊" / "Security Journals"). DBLP indexes journals by volume not year, so each journal site needs a per-year `dblp_toc` override (e.g. TIFS: `journals/tifs/tifs21` = vol 21 = 2026). The fetcher already parses both `<inproceedings>` (confs) and `<article>` (journals). UI wording on shared pages is venue-neutral ("会议/期刊").
- Prod data URLs (`ViewAbstract.vue`, `Search.vue`) point at this fork's raw GitHub, not upstream.
- Adding a venue: append to the **end** of `data.yml` (never reorder — paper `id` is a running index).

## Commands

### Frontend (JavaScript/Vue)
```bash
npm run dev           # Start Vite dev server
npm run build         # Production build to dist/
npm run preview       # Preview production build
npm run lint          # ESLint with auto-fix
npm run format        # Prettier formatting
npm run deploy        # Deploy dist/ to GitHub Pages
npm run deploy:build  # Build then deploy
```

Frontend is designed with PrimeVue UI. The usage of components is documented in primevue-document.md

### Backend (Python data processing)
```bash
uv sync                             # Install Python deps
uv run main.py --analyze            # Crawl/parse papers and generate JSON data files
uv run main.py --llm-analyze        # Analyze abstracts with LLM (requires .env)
uv run main.py --zip                # Create encrypted zip of crawl cache
uv run main.py --unzip              # Unzip crawl cache
```

### Full publish cycle
```bash
uv run main.py --analyze --zip && npm run build && npm run deploy
```

## Architecture

**Data flow:** `data.yml` (conference config) → `main.py` (Python processing) → JSON files in `src/assets/data/` → Vue frontend

### Python backend (`analyzers/`)
- `main.py` — orchestrates scraping, parsing, and JSON generation
- `data.yml` — master config defining conferences with XPath selectors for web scraping, or references to official CSV/BIB files
- Crawl results cached in `cache/` (pickle files, SHA256-keyed); official data in `official_cache/`
- `llm_analyzer.py` — uses OpenAI API (configurable via `.env`) to classify paper topics; results cached in JSONL

### Generated JSON assets (`src/assets/data/`)
- `data.json` — full paper list (no abstracts for size)
- `data-quick-view.json` — 100 latest papers per publication
- `data-statistics.json` — aggregated stats by publication/year/category
- `meta_json/[Publication - Year].json` — full per-conference details with abstracts

### Vue frontend (`src/`)
- **Router:** `src/router/index.js`
- **Layout:** `src/layout/` — AppLayout wrapping AppTopbar, AppSidebar, AppFooter; layout state via `composables/layout.js`
- **Views:** `src/views/` — Dashboard, paper/Search, paper/Trends, paper/ViewAbstract, paper/SubmissionTimeline, reputation/Awards, misc/About, misc/Settings
- **Services:** `src/service/` — pure JS modules for data loading (SettingsService uses IndexedDB for theme/language persistence)
- **i18n:** English/Chinese via `src/locales/`; locale persisted in localStorage

### Key tech
- Vue 3 Composition API, Vue Router 4, Vue-i18n
- PrimeVue 4 + Tailwind CSS 3 for UI
- Chart.js for trend visualizations
- IndexedDB for user settings (theme, dark mode, language, LLM config)

## Paper Status Values

Papers in the data pipeline have a `status` field: `notchecked` → `inprogress` → `done` → `advanced` (LLM-analyzed with topics).

## Environment

Copy `.env.example` to `.env` for LLM analysis and cache encryption:
- `OPENAI_API_KEY`, `MODEL`, `BASE_URL` — for `--llm-analyze`
- `PRIVATE_ZIP_PASSWD` — for cache zip encryption

## Adding a New Conference/Year

Edit `data.yml` to add the conference entry (with XPath selectors or official file references), place any official CSV/BIB files in `official_cache/`, then run `uv run main.py --analyze`.
