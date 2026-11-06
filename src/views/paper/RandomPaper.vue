<template>
    <div class="random-page">
        <ConfirmDialog />

        <div class="card content-card" :aria-busy="loadState === 'loading'">
            <header class="rp-header">
                <div class="rp-header-main">
                    <div class="rp-header-icon" aria-hidden="true"><i class="pi pi-calendar"></i></div>
                    <div class="rp-header-copy">
                        <h2 class="rp-title">{{ t('randomPaper.title') }}</h2>
                        <p class="rp-subtitle">{{ t('randomPaper.subtitle', { years: settings.randomYearsBack }) }}</p>
                    </div>
                </div>
                <div class="rp-read-manager">
                    <Tag :value="t('randomPaper.readManager.count', { count: readCount })" severity="secondary" />
                    <Button :label="t('randomPaper.readManager.export')" icon="pi pi-download" size="small" severity="secondary" outlined @click="exportRead" />
                    <Button :label="t('randomPaper.readManager.clear')" icon="pi pi-trash" size="small" severity="danger" outlined :disabled="readCount === 0" @click="clearRead" />
                </div>
            </header>

            <section v-if="loadState !== 'loading' && loadState !== 'error'" class="rp-toolbar">
                <div class="rp-pool-info">
                    <span>{{ t('randomPaper.poolCount', { count: poolCount }) }}</span>
                    <span v-if="showNotEnough" class="rp-not-enough">{{ t('randomPaper.notEnough', { count: poolCount }) }}</span>
                </div>
                <div class="rp-controls">
                    <label class="rp-switch-label">
                        <ToggleSwitch :model-value="settings.randomExcludeRead" @update:model-value="onExcludeReadChange" />
                        <span>{{ t('randomPaper.excludeRead') }}</span>
                    </label>
                    <Button v-if="canReshuffle" :label="t('randomPaper.reshuffle')" icon="pi pi-sync" @click="reshuffle" />
                </div>
            </section>

            <div v-if="datasetSource === 'preview' && loadState !== 'loading'" class="rp-degraded" role="alert">
                <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>
                <span>{{ t('randomPaper.degradedNotice', { count: allPapers.length }) }}</span>
                <Button :label="t('randomPaper.retry')" icon="pi pi-refresh" size="small" severity="secondary" text @click="retryDataset" />
            </div>

            <div v-if="loadState === 'loading'" class="rp-list" role="status" aria-live="polite">
                <div v-for="n in 3" :key="n" class="rp-skeleton-card">
                    <Skeleton width="70%" height="1.25rem" class="mb-3" />
                    <Skeleton width="100%" height="0.75rem" class="mb-2" />
                    <Skeleton width="100%" height="0.75rem" class="mb-2" />
                    <Skeleton width="60%" height="0.75rem" />
                </div>
            </div>

            <div v-else-if="loadState === 'error'" class="rp-state" role="alert">
                <i class="pi pi-exclamation-triangle rp-state-icon" aria-hidden="true"></i>
                <p>{{ t('randomPaper.loadFailed') }}</p>
                <Button :label="t('randomPaper.retry')" icon="pi pi-refresh" severity="secondary" @click="retryDataset" />
            </div>

            <div v-else-if="batch.length === 0" class="rp-state" role="status">
                <i class="pi pi-inbox rp-state-icon" aria-hidden="true"></i>
                <p class="rp-state-title">{{ t('randomPaper.emptyPool.title') }}</p>
                <p>{{ t('randomPaper.emptyPool.desc') }}</p>
            </div>

            <ul v-else class="rp-list">
                <li v-for="entry in batch" :key="entry.key" class="rp-item">
                    <Card class="rp-card" :class="{ 'rp-card--read': isRead(entry.key) }">
                        <template #content>
                            <div class="rp-heading">
                                <h3 class="rp-paper-title">
                                    <a v-if="entry.paper && entry.paper !== '#'" :href="entry.paper" target="_blank" rel="noopener noreferrer">
                                        <template v-for="(seg, idx) in highlightSegments(entry.title)" :key="idx">
                                            <span :class="seg.cls">{{ seg.text }}</span>
                                        </template>
                                        <i class="pi pi-external-link rp-link-icon" aria-hidden="true"></i>
                                    </a>
                                    <span v-else>
                                        <template v-for="(seg, idx) in highlightSegments(entry.title)" :key="idx">
                                            <span :class="seg.cls">{{ seg.text }}</span>
                                        </template>
                                    </span>
                                </h3>
                                <div class="rp-actions">
                                    <Tag v-if="isRead(entry.key)" :value="t('randomPaper.readBadge')" severity="success" />
                                    <Button
                                        size="small"
                                        :label="isRead(entry.key) ? t('randomPaper.markUnread') : t('randomPaper.markRead')"
                                        :icon="isRead(entry.key) ? 'pi pi-undo' : 'pi pi-check'"
                                        :severity="isRead(entry.key) ? 'secondary' : 'primary'"
                                        :outlined="isRead(entry.key)"
                                        @click="toggleRead(entry)"
                                    />
                                </div>
                            </div>

                            <div class="rp-meta">
                                <Tag :value="entry.venueYear" severity="info" />
                                <Tag :value="categoryLabel(entry.category)" severity="secondary" />
                            </div>

                            <section class="rp-block">
                                <div class="rp-block-heading">
                                    <h4>{{ t('randomPaper.abstractTitle') }}</h4>
                                    <Button
                                        v-if="entry.abstractState === 'ready'"
                                        :label="t('randomPaper.copyAbstract')"
                                        icon="pi pi-copy"
                                        size="small"
                                        severity="secondary"
                                        text
                                        @click="copyAbstract(entry)"
                                    />
                                </div>
                                <div v-if="entry.abstractState === 'loading'">
                                    <Skeleton width="100%" height="0.75rem" class="mb-2" />
                                    <Skeleton width="85%" height="0.75rem" />
                                </div>
                                <p v-else-if="entry.abstractState === 'ready'" class="rp-abstract-text">
                                    <template v-for="(seg, idx) in highlightSegments(entry.abstract)" :key="idx">
                                        <span :class="seg.cls">{{ seg.text }}</span>
                                    </template>
                                </p>
                                <p v-else class="rp-empty-text">{{ t('abstract.noAbstract') }}</p>
                            </section>

                            <section class="rp-block">
                                <h4>{{ t('randomPaper.methodTitle') }}</h4>
                                <div v-if="entry.indexState === 'loading'">
                                    <Skeleton width="60%" height="0.75rem" class="mb-2" />
                                    <Skeleton width="45%" height="0.75rem" />
                                </div>
                                <template v-else-if="entry.indexState === 'ready'">
                                    <p v-if="entry.indexRow.method" class="rp-method-text">{{ entry.indexRow.method }}</p>
                                    <ul v-if="entry.techniques.length" class="rp-atoms">
                                        <li v-for="technique in entry.techniques" :key="technique.id" class="rp-atom">
                                            <p v-if="technique.isLegacy" class="rp-atom-line">{{ technique.legacyText }}</p>
                                            <template v-else>
                                                <div class="rp-atom-head">
                                                    <Tag v-if="technique.type" :value="typeLabel(technique.type)" severity="secondary" />
                                                    <span class="rp-atom-name">{{ technique.name || t('methodIndex.unnamedTechnique', { index: technique.index + 1 }) }}</span>
                                                </div>
                                                <p v-if="technique.action || technique.effect" class="rp-atom-line">
                                                    {{ [technique.action, technique.effect].filter(Boolean).join(' → ') }}
                                                </p>
                                            </template>
                                        </li>
                                    </ul>
                                    <p v-else class="rp-empty-text">{{ t('methodIndex.emptyTechnique') }}</p>
                                    <div v-if="entry.indexRow.lens.length" class="rp-lenses">
                                        <span v-for="lens in entry.indexRow.lens" :key="lens" class="rp-lens-chip">{{ lens }}</span>
                                    </div>
                                </template>
                                <p v-else class="rp-empty-text"><i class="pi pi-inbox rp-empty-icon" aria-hidden="true"></i> {{ t('randomPaper.noIndex', { venue: entry.venueYear }) }}</p>
                            </section>
                        </template>
                    </Card>
                </li>
            </ul>
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import { usePageTitle } from '@/composables/useI18n';
import { highlightSegments } from '@/composables/useHighlight';
import { buildPool, normalizeTitleKey, rankPool, todayLocalDateStr } from '@/composables/useDailySample';
import { autoSavePreference, defaultSettings, loadReadPapers, loadSettings, saveReadPapers } from '@/service/SettingsService';
import paperDataQuickView from '@/assets/data/data-quick-view.json';

const { t, te } = useI18n();
usePageTitle('menu.randomPaper');
const confirm = useConfirm();
const toast = useToast();

const RAW_BASE = 'https://raw.githubusercontent.com/xuanxuan197068/papers-collection/main';

const settings = ref(defaultSettings());
const readMap = ref({});
const allPapers = ref([]);
const datasetSource = ref('full');
const loadState = ref('loading');
const batch = ref([]);
const batchIndex = ref(0);
const poolCount = ref(0);

let rankedList = [];
let requestSequence = 0;
let pageController = null;
const metaCache = new Map();
const indexCache = new Map();

const CATEGORY_META = {
    'top-tier': 'abstract.topTier',
    'software-engineering': 'abstract.softwareEngineering',
    system: 'abstract.system',
    'ai-ml': 'abstract.aiMl',
    journal: 'abstract.journal'
};
const categoryLabel = (category) => (CATEGORY_META[category] ? t(CATEGORY_META[category]) : category);

const typeLabel = (type) => {
    const key = `methodIndex.types.${type}`;
    return te(key) ? t(key) : type;
};

const readCount = computed(() => Object.keys(readMap.value).length);
const isRead = (key) => Boolean(readMap.value[key]);

const clampInt = (value, min, max, fallback) => {
    const num = Number.parseInt(value, 10);
    if (!Number.isFinite(num)) return fallback;
    return Math.min(max, Math.max(min, num));
};
const sampleSize = () => clampInt(settings.value.randomSampleCount, 1, 20, 5);
const showNotEnough = computed(() => settings.value.randomExcludeRead && poolCount.value > 0 && poolCount.value < sampleSize());
const canReshuffle = computed(() => poolCount.value > sampleSize());

// The visible batch is an imperative snapshot: marking a paper read keeps its
// card in place; the shrunken pool only applies on the next draw/reshuffle.
const drawBatch = ({ reset = false, advance = false } = {}) => {
    const current = settings.value;
    const yearsBack = clampInt(current.randomYearsBack, 1, 10, 3);
    const minYear = new Date().getFullYear() - yearsBack + 1;
    rankedList = rankPool(
        buildPool(allPapers.value, {
            minYear,
            readMap: readMap.value,
            excludeRead: current.randomExcludeRead !== false
        }),
        todayLocalDateStr(),
        current
    );
    poolCount.value = rankedList.length;
    const size = sampleSize();
    const pageCount = Math.max(1, Math.ceil(rankedList.length / size));
    if (reset) batchIndex.value = 0;
    else if (advance) batchIndex.value = (batchIndex.value + 1) % pageCount;
    if (batchIndex.value >= pageCount) batchIndex.value = 0;
    const start = batchIndex.value * size;
    batch.value = rankedList.slice(start, start + size).map((paper) => ({
        ...paper,
        venueYear: `${paper.publication} - ${paper.year}`,
        abstract: '',
        abstractState: 'loading',
        indexRow: null,
        techniques: [],
        indexState: 'loading'
    }));
};

// Trimmed-down copy of MethodIndex.vue's normalizeTechnique: accepts both
// technique-v2 atom objects and legacy strings still awaiting migration.
const normalizeTechnique = (value, paperKey, index) => {
    const id = `${paperKey}-${index}`;
    if (typeof value === 'string') {
        if (!value.trim()) return null;
        return { id, index, isLegacy: true, legacyText: value, name: '', type: '', action: '', effect: '' };
    }
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    return {
        id,
        index,
        isLegacy: false,
        legacyText: '',
        name: typeof value.name === 'string' ? value.name : '',
        type: typeof value.type === 'string' ? value.type : '',
        action: typeof value.action === 'string' ? value.action : '',
        effect: typeof value.effect === 'string' ? value.effect : ''
    };
};

const fetchComboFile = async (url, signal, buildEntry) => {
    try {
        const response = await fetch(url, { signal });
        if (response.status === 404) return { status: 'missing', byKey: new Map() };
        if (!response.ok) return { status: 'missing', byKey: new Map() };
        // Vite's dev SPA fallback answers missing JSON files with index.html + 200.
        if ((response.headers.get('content-type') || '').includes('text/html')) return { status: 'missing', byKey: new Map() };
        const payload = await response.json();
        if (!Array.isArray(payload)) return { status: 'missing', byKey: new Map() };
        const byKey = new Map();
        payload.forEach((row) => {
            const entry = buildEntry(row);
            if (entry) byKey.set(entry.key, entry.value);
        });
        return { status: 'ready', byKey };
    } catch (error) {
        if (error?.name !== 'AbortError') console.error('Failed to load', url, error);
        return { status: 'missing', byKey: new Map() };
    }
};

const ensureComboLoaded = async (combo, signal) => {
    const file = encodeURIComponent(`${combo}.json`);
    const jobs = [];
    if (!metaCache.has(combo)) {
        const url = import.meta.env.PROD ? `${RAW_BASE}/src/assets/data/meta_json/${file}` : `/src/assets/data/meta_json/${file}`;
        jobs.push(
            fetchComboFile(url, signal, (row) => {
                if (typeof row?.title !== 'string') return null;
                return { key: normalizeTitleKey(row.title), value: row };
            }).then((result) => metaCache.set(combo, result))
        );
    }
    if (!indexCache.has(combo)) {
        const url = import.meta.env.PROD ? `${RAW_BASE}/radar/index/${file}` : `/radar/index/${file}`;
        jobs.push(
            fetchComboFile(url, signal, (row) => {
                const key = typeof row?.key === 'string' && row.key ? row.key : normalizeTitleKey(row?.title);
                if (!key) return null;
                return { key, value: row };
            }).then((result) => indexCache.set(combo, result))
        );
    }
    await Promise.all(jobs);
};

const enrichBatch = async () => {
    const sequence = ++requestSequence;
    const signal = pageController?.signal;
    const combos = [...new Set(batch.value.map((entry) => entry.venueYear))];
    await Promise.all(combos.map((combo) => ensureComboLoaded(combo, signal)));
    if (sequence !== requestSequence) return;
    batch.value.forEach((entry) => {
        const meta = metaCache.get(entry.venueYear);
        const metaRow = meta?.status === 'ready' ? meta.byKey.get(entry.key) : null;
        const abstract = typeof metaRow?.abstract === 'string' ? metaRow.abstract.trim() : '';
        entry.abstract = abstract && abstract !== '#' ? abstract : '';
        entry.abstractState = entry.abstract ? 'ready' : 'missing';

        const index = indexCache.get(entry.venueYear);
        const indexRow = index?.status === 'ready' ? index.byKey.get(entry.key) : null;
        if (indexRow) {
            const rawTechnique = indexRow.technique;
            const values = Array.isArray(rawTechnique) ? rawTechnique : rawTechnique == null ? [] : [rawTechnique];
            entry.techniques = values.map((value, idx) => normalizeTechnique(value, entry.key, idx)).filter(Boolean);
            entry.indexRow = {
                method: typeof indexRow.method === 'string' ? indexRow.method : '',
                lens: Array.isArray(indexRow.lens) ? indexRow.lens.filter((lens) => typeof lens === 'string' && lens.trim()) : []
            };
            entry.indexState = 'ready';
        } else {
            entry.indexState = 'missing';
        }
    });
};

const redraw = (options) => {
    drawBatch(options);
    enrichBatch();
};

const loadDataset = async () => {
    loadState.value = 'loading';
    try {
        if (import.meta.env.PROD) {
            const response = await fetch(`${RAW_BASE}/src/assets/data/data.json`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (!Array.isArray(data)) throw new Error('data.json must be a JSON array');
            allPapers.value = data;
        } else {
            const module = await import('@/assets/data/data.json');
            allPapers.value = module.default;
        }
        datasetSource.value = 'full';
        loadState.value = 'ready';
    } catch (error) {
        console.error('Failed to load full dataset, falling back to preview:', error);
        allPapers.value = paperDataQuickView;
        datasetSource.value = 'preview';
        loadState.value = 'degraded';
    }
};

const retryDataset = async () => {
    await loadDataset();
    redraw({ reset: true });
};

const reshuffle = () => redraw({ advance: true });

const onExcludeReadChange = (value) => {
    settings.value.randomExcludeRead = value;
    autoSavePreference('randomExcludeRead', value);
    redraw({ reset: true });
};

const copyAbstract = async (entry) => {
    if (!entry.abstract) return;
    try {
        await navigator.clipboard.writeText(entry.abstract);
        toast.add({ severity: 'success', summary: t('common.notice'), detail: t('randomPaper.toast.abstractCopied'), life: 2500 });
    } catch (error) {
        console.error('Failed to copy abstract:', error);
        toast.add({ severity: 'error', summary: t('common.notice'), detail: t('randomPaper.toast.copyFailed'), life: 3000 });
    }
};

const toggleRead = async (entry) => {
    const previous = readMap.value;
    const next = { ...previous };
    if (next[entry.key]) delete next[entry.key];
    else next[entry.key] = { title: entry.title, venue: entry.venueYear, date: todayLocalDateStr() };
    readMap.value = next;
    try {
        await saveReadPapers(next);
    } catch (error) {
        console.error('Failed to save read status:', error);
        readMap.value = previous;
        toast.add({ severity: 'error', summary: t('common.notice'), detail: t('randomPaper.toast.saveFailed'), life: 3000 });
    }
};

const exportRead = () => {
    if (readCount.value === 0) {
        toast.add({ severity: 'info', summary: t('common.notice'), detail: t('randomPaper.readManager.exportEmpty'), life: 3000 });
        return;
    }
    const blob = new Blob([JSON.stringify(readMap.value, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `read-papers-${todayLocalDateStr().replaceAll('-', '')}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
};

const clearRead = () => {
    confirm.require({
        header: t('randomPaper.readManager.clearTitle'),
        message: t('randomPaper.readManager.clearMessage', { count: readCount.value }),
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: t('common.confirm'),
        rejectLabel: t('common.cancel'),
        acceptProps: { severity: 'danger' },
        rejectProps: { severity: 'secondary', outlined: true },
        accept: async () => {
            const previous = readMap.value;
            readMap.value = {};
            try {
                await saveReadPapers({});
                toast.add({ severity: 'success', summary: t('common.notice'), detail: t('randomPaper.readManager.cleared'), life: 3000 });
                redraw({ reset: true });
            } catch (error) {
                console.error('Failed to clear read status:', error);
                readMap.value = previous;
                toast.add({ severity: 'error', summary: t('common.notice'), detail: t('randomPaper.toast.saveFailed'), life: 3000 });
            }
        }
    });
};

onMounted(async () => {
    pageController = new AbortController();
    try {
        const stored = await loadSettings();
        settings.value = { ...defaultSettings(), ...(stored || {}) };
    } catch (error) {
        console.error('Failed to load settings, using defaults:', error);
    }
    try {
        readMap.value = (await loadReadPapers()) || {};
    } catch (error) {
        console.error('Failed to load read papers:', error);
    }
    await loadDataset();
    redraw({ reset: true });
});

onUnmounted(() => {
    requestSequence += 1;
    pageController?.abort();
    pageController = null;
});
</script>

<style scoped>
.random-page {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.content-card {
    padding: 1.5rem 1.75rem 1.75rem;
}

.rp-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}

.rp-header-main {
    display: flex;
    align-items: center;
    gap: 1rem;
    min-width: 0;
}

.rp-header-icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--primary-color) 12%, transparent);
    color: var(--primary-color);
    font-size: 1.25rem;
    flex-shrink: 0;
}

.rp-title {
    margin: 0;
    font-size: 1.3rem;
    font-weight: 600;
}

.rp-subtitle {
    margin: 0.15rem 0 0;
    color: var(--text-color-secondary);
    font-size: 0.9rem;
}

.rp-read-manager {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.rp-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
    padding: 0.75rem 1rem;
    border: 1px solid var(--surface-border);
    border-radius: 0.75rem;
    background: color-mix(in srgb, var(--primary-color) 4%, transparent);
}

.rp-pool-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    color: var(--text-color-secondary);
    font-size: 0.9rem;
}

.rp-not-enough {
    color: var(--p-orange-500, #f97316);
}

.rp-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}

.rp-switch-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    color: var(--text-color-secondary);
    cursor: pointer;
}

.rp-degraded {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
    padding: 0.6rem 1rem;
    border-radius: 0.75rem;
    border: 1px solid color-mix(in srgb, var(--p-orange-500, #f97316) 40%, var(--surface-border));
    background: color-mix(in srgb, var(--p-orange-500, #f97316) 8%, transparent);
    font-size: 0.9rem;
}

.rp-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 3rem 1rem;
    color: var(--text-color-secondary);
    text-align: center;
}

.rp-state p {
    margin: 0;
}

.rp-state-title {
    font-weight: 600;
    color: var(--text-color);
}

.rp-state-icon {
    font-size: 2rem;
}

.rp-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

.rp-skeleton-card {
    border: 1px solid var(--surface-border);
    border-radius: 0.75rem;
    padding: 1.25rem;
}

.rp-item {
    min-width: 0;
}

.rp-card {
    border: 1px solid var(--surface-border);
    box-shadow: none;
}

.rp-card--read {
    opacity: 0.72;
}

.rp-card :deep(.p-card-body) {
    padding: 1.25rem;
}

.rp-card :deep(.p-card-content) {
    padding: 0;
}

.rp-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
}

.rp-paper-title {
    min-width: 0;
    margin: 0;
    font-size: 1.05rem;
    font-weight: 650;
    line-height: 1.45;
    overflow-wrap: anywhere;
}

.rp-paper-title a {
    color: inherit;
    text-decoration: none;
}

.rp-paper-title a:hover {
    color: var(--primary-color);
}

.rp-link-icon {
    margin-left: 0.35rem;
    font-size: 0.72rem;
    opacity: 0.65;
}

.rp-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
}

.rp-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 0.75rem;
}

.rp-block {
    margin-top: 1rem;
}

.rp-block-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.4rem;
}

.rp-block h4 {
    margin: 0;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--text-color-secondary);
}

.rp-abstract-text,
.rp-method-text {
    margin: 0;
    line-height: 1.65;
    overflow-wrap: anywhere;
}

.rp-method-text {
    margin-bottom: 0.6rem;
}

.rp-empty-text {
    margin: 0;
    color: var(--text-color-secondary);
    font-size: 0.9rem;
}

.rp-empty-icon {
    margin-right: 0.3rem;
}

.rp-atoms {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

.rp-atom {
    padding: 0.6rem 0.8rem;
    border: 1px solid color-mix(in srgb, var(--primary-color) 18%, var(--surface-border));
    border-radius: 0.6rem;
    background: color-mix(in srgb, var(--primary-color) 4%, transparent);
}

.rp-atom-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.rp-atom-name {
    font-weight: 600;
    overflow-wrap: anywhere;
}

.rp-atom-line {
    margin: 0.35rem 0 0;
    font-size: 0.9rem;
    line-height: 1.55;
    color: var(--text-color-secondary);
    overflow-wrap: anywhere;
}

.rp-lenses {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.75rem;
}

.rp-lens-chip {
    display: inline-block;
    padding: 0.12rem 0.55rem;
    border-radius: 999px;
    font-size: 0.75rem;
    background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    color: var(--primary-color);
}

@media (max-width: 768px) {
    .content-card {
        padding: 1rem;
    }

    .rp-heading {
        flex-direction: column;
        gap: 0.6rem;
    }

    .rp-toolbar {
        flex-direction: column;
        align-items: stretch;
    }

    .rp-controls {
        justify-content: space-between;
    }
}
</style>
