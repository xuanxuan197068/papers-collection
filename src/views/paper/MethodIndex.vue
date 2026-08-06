<template>
    <div class="method-index-page">
        <div class="card menu-card">
            <MegaMenu :model="items" />
        </div>

        <div class="card content-card" :aria-busy="loadState === 'loading'">
            <header v-if="selection" class="mi-header">
                <div class="mi-header-icon" aria-hidden="true"><i class="pi pi-sitemap"></i></div>
                <div class="mi-header-copy">
                    <h2 class="mi-title">
                        {{ selection.publication }} <span class="mi-year">{{ selection.year }}</span>
                    </h2>
                    <p v-if="loadState === 'ready'" class="mi-subtitle">
                        {{ t('methodIndex.resultCount', { filtered: filteredRows.length, total: rows.length }) }}
                    </p>
                </div>
            </header>
            <header v-else class="mi-header mi-header--placeholder">
                <h2 class="mi-title">{{ t('methodIndex.selectPublication') }}</h2>
            </header>

            <div v-if="!selection && loadState === 'idle'" class="mi-state" role="status">
                <i class="pi pi-hand-point-up mi-state-icon" aria-hidden="true"></i>
                <p>{{ t('methodIndex.emptyHint') }}</p>
            </div>

            <div v-else-if="loadState === 'loading'" class="mi-state" role="status" aria-live="polite">
                <i class="pi pi-spinner pi-spin mi-state-icon" aria-hidden="true"></i>
                <p>{{ t('methodIndex.loading') }}</p>
            </div>

            <div v-else-if="loadState === 'missing'" class="mi-state" role="status">
                <i class="pi pi-inbox mi-state-icon" aria-hidden="true"></i>
                <p>{{ t('methodIndex.notGenerated', { venue: selection.publication, year: selection.year }) }}</p>
            </div>

            <div v-else-if="loadState === 'error'" class="mi-state" role="alert">
                <i class="pi pi-exclamation-triangle mi-state-icon" aria-hidden="true"></i>
                <p>{{ t('methodIndex.loadFailed') }}</p>
                <Button :label="t('methodIndex.retry')" icon="pi pi-refresh" severity="secondary" @click="retryLoad" />
            </div>

            <template v-else-if="loadState === 'ready'">
                <section class="mi-toolbar" :aria-label="t('methodIndex.filtersLabel')">
                    <IconField class="mi-search">
                        <InputIcon><i class="pi pi-search" /></InputIcon>
                        <InputText v-model="query" :placeholder="t('methodIndex.searchPlaceholder')" :aria-label="t('methodIndex.searchPlaceholder')" />
                    </IconField>
                    <MultiSelect v-model="selectedLenses" :options="lensOptions" display="chip" :placeholder="t('methodIndex.anyLens')" :aria-label="t('methodIndex.anyLens')" :max-selected-labels="3" class="mi-filter" />
                    <MultiSelect
                        v-model="selectedTypes"
                        :options="typeOptions"
                        option-label="label"
                        option-value="value"
                        display="chip"
                        :placeholder="t('methodIndex.anyType')"
                        :aria-label="t('methodIndex.anyType')"
                        :max-selected-labels="3"
                        :disabled="typeOptions.length === 0"
                        class="mi-filter"
                    />
                    <Button v-if="hasFilters" :label="t('methodIndex.clearFilters')" icon="pi pi-filter-slash" severity="secondary" text @click="clearFilters" />
                </section>

                <div v-if="filteredRows.length === 0" class="mi-state" role="status">
                    <i class="pi pi-search mi-state-icon" aria-hidden="true"></i>
                    <p>{{ t('methodIndex.noResults') }}</p>
                    <Button v-if="hasFilters" :label="t('methodIndex.clearFilters')" icon="pi pi-filter-slash" severity="secondary" @click="clearFilters" />
                </div>

                <DataView
                    v-else
                    v-model:first="first"
                    :value="filteredRows"
                    data-key="key"
                    paginator
                    :rows="pageSize"
                    :rows-per-page-options="[12, 24, 48]"
                    paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
                    :current-page-report-template="pageReportTemplate"
                    class="mi-data-view"
                    @page="handlePage"
                >
                    <template #list="slotProps">
                        <ul class="mi-card-list">
                            <li v-for="paper in slotProps.items" :key="paper.key" class="mi-card-item">
                                <article :aria-labelledby="paperTitleId(paper)">
                                    <Card class="mi-paper-card">
                                        <template #content>
                                            <div class="mi-paper-heading">
                                                <h3 :id="paperTitleId(paper)" class="mi-paper-title">
                                                    <a v-if="paper.paper && paper.paper !== '#'" :href="paper.paper" target="_blank" rel="noopener noreferrer" :aria-label="t('methodIndex.openPaperLabel', { title: paper.title })">
                                                        {{ paper.title }}
                                                        <i class="pi pi-external-link mi-link-icon" aria-hidden="true"></i>
                                                    </a>
                                                    <span v-else>{{ paper.title }}</span>
                                                </h3>
                                                <Tag v-if="paper.evidence" :value="paper.evidence" :severity="evidenceSeverity(paper.evidence)" />
                                            </div>

                                            <section v-if="paper.method" class="mi-method-block">
                                                <h4>{{ t('methodIndex.method') }}</h4>
                                                <p>{{ paper.method }}</p>
                                            </section>

                                            <dl class="mi-paper-facts">
                                                <div v-if="paper.problem">
                                                    <dt>{{ t('methodIndex.problem') }}</dt>
                                                    <dd>{{ paper.problem }}</dd>
                                                </div>
                                                <div v-if="paper.scenario">
                                                    <dt>{{ t('methodIndex.scenario') }}</dt>
                                                    <dd>{{ paper.scenario }}</dd>
                                                </div>
                                            </dl>

                                            <div v-if="paper.lens.length" class="mi-lenses" :aria-label="t('methodIndex.lens')">
                                                <span v-for="lens in paper.lens" :key="lens" class="mi-lens-chip">{{ lens }}</span>
                                            </div>

                                            <section class="mi-techniques" :aria-labelledby="techniqueHeadingId(paper)">
                                                <h4 :id="techniqueHeadingId(paper)">{{ t('methodIndex.techniquePoints') }}</h4>
                                                <p v-if="paper.techniques.length === 0" class="mi-technique-empty">
                                                    {{ t('methodIndex.emptyTechnique') }}
                                                </p>
                                                <template v-else>
                                                    <div class="mi-technique-buttons">
                                                        <Button
                                                            v-for="technique in paper.techniques"
                                                            :id="techniqueButtonId(paper, technique)"
                                                            :key="technique.id"
                                                            type="button"
                                                            size="small"
                                                            :label="techniqueLabel(technique)"
                                                            :icon="isTechniqueExpanded(paper, technique) ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
                                                            :outlined="!isTechniqueExpanded(paper, technique)"
                                                            :severity="isTechniqueExpanded(paper, technique) ? 'primary' : 'secondary'"
                                                            :class="{ 'mi-technique-button--match': isTechniqueMatch(paper, technique) }"
                                                            :aria-expanded="isTechniqueExpanded(paper, technique) ? 'true' : 'false'"
                                                            :aria-controls="techniqueRegionId(paper, technique)"
                                                            @click="toggleTechnique(paper, technique)"
                                                        />
                                                    </div>

                                                    <section
                                                        v-for="technique in paper.techniques"
                                                        v-show="isTechniqueExpanded(paper, technique)"
                                                        :id="techniqueRegionId(paper, technique)"
                                                        :key="`${technique.id}-detail`"
                                                        class="mi-technique-detail"
                                                        role="region"
                                                        :aria-labelledby="techniqueButtonId(paper, technique)"
                                                    >
                                                        <p v-if="technique.isLegacy" class="mi-legacy-text">{{ technique.legacyText }}</p>
                                                        <dl v-else class="mi-technique-schema">
                                                            <div v-if="technique.type">
                                                                <dt>{{ t('methodIndex.fields.type') }}</dt>
                                                                <dd><Tag :value="typeLabel(technique.type)" severity="secondary" /></dd>
                                                            </div>
                                                            <div v-if="technique.target">
                                                                <dt>{{ t('methodIndex.fields.target') }}</dt>
                                                                <dd>{{ technique.target }}</dd>
                                                            </div>
                                                            <div v-if="technique.action">
                                                                <dt>{{ t('methodIndex.fields.action') }}</dt>
                                                                <dd>{{ technique.action }}</dd>
                                                            </div>
                                                            <div v-if="technique.effect">
                                                                <dt>{{ t('methodIndex.fields.effect') }}</dt>
                                                                <dd>{{ technique.effect }}</dd>
                                                            </div>
                                                            <div v-if="technique.grounding">
                                                                <dt>{{ t('methodIndex.fields.grounding') }}</dt>
                                                                <dd>{{ groundingLabel(technique.grounding) }}</dd>
                                                            </div>
                                                            <div v-if="technique.limitation" class="mi-schema-wide">
                                                                <dt>{{ t('methodIndex.fields.limitation') }}</dt>
                                                                <dd>{{ technique.limitation }}</dd>
                                                            </div>
                                                        </dl>
                                                    </section>
                                                </template>
                                            </section>
                                        </template>
                                    </Card>
                                </article>
                            </li>
                        </ul>
                    </template>
                </DataView>
            </template>
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePageTitle } from '@/composables/useI18n';
import { languageEmitter } from '@/locales';
import paperStatis from '@/assets/data/data-statistics.json';

const { t, te, tm } = useI18n();
usePageTitle('menu.methodIndex');

const TECHNIQUE_TYPE_ORDER = [
    'algorithm',
    'model',
    'architecture',
    'protocol',
    'system-mechanism',
    'hardware-mechanism',
    'data-construction',
    'instrumentation',
    'analysis-method',
    'testing-method',
    'measurement-method',
    'formal-method',
    'user-study',
    'other',
    'legacy'
];

const paperStatisRef = ref(paperStatis);
const items = ref([]);
const selection = ref(null);
const rows = ref([]);
const loadState = ref('idle');
const query = ref('');
const selectedLenses = ref([]);
const selectedTypes = ref([]);
const first = ref(0);
const pageSize = ref(12);
const expandedTechniqueByPaper = ref({});
let activeController = null;
let requestSequence = 0;

const CATEGORY_ORDER = ['top-tier', 'software-engineering', 'system', 'ai-ml', 'journal'];
const CATEGORY_META = {
    'top-tier': { key: 'abstract.topTier', icon: 'pi pi-shield' },
    'software-engineering': { key: 'abstract.softwareEngineering', icon: 'pi pi-code' },
    system: { key: 'abstract.system', icon: 'pi pi-cog' },
    'ai-ml': { key: 'abstract.aiMl', icon: 'pi pi-sparkles' },
    journal: { key: 'abstract.journal', icon: 'pi pi-book' }
};

const categoryLabel = (category) => (CATEGORY_META[category] ? t(CATEGORY_META[category].key) : category);
const categoryIcon = (category) => (CATEGORY_META[category] ? CATEGORY_META[category].icon : 'pi pi-folder');

const normalizeText = (value) =>
    String(value ?? '')
        .trim()
        .toLocaleLowerCase();
const joinSearchText = (values) =>
    normalizeText(
        values
            .flat(Infinity)
            .filter((value) => value != null)
            .join(' ')
    );
const domSafe = (value) => String(value || 'paper').replace(/[^a-zA-Z0-9_-]/g, '-');

const normalizeTechnique = (value, paperKey, index) => {
    const id = `${paperKey}-${index}`;
    if (typeof value === 'string') {
        if (!value.trim()) return null;
        return {
            id,
            index,
            name: '',
            type: 'legacy',
            target: '',
            action: '',
            effect: '',
            grounding: '',
            limitation: '',
            legacyText: value,
            isLegacy: true,
            searchText: normalizeText(value)
        };
    }
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const technique = {
        id,
        index,
        name: typeof value.name === 'string' ? value.name : '',
        type: typeof value.type === 'string' ? value.type : '',
        target: typeof value.target === 'string' ? value.target : '',
        action: typeof value.action === 'string' ? value.action : '',
        effect: typeof value.effect === 'string' ? value.effect : '',
        grounding: typeof value.grounding === 'string' ? value.grounding : '',
        limitation: typeof value.limitation === 'string' ? value.limitation : '',
        legacyText: '',
        isLegacy: false
    };
    technique.searchText = joinSearchText([technique.name, technique.type, technique.target, technique.action, technique.effect, technique.grounding, technique.limitation]);
    return technique;
};

const normalizeRow = (row, index) => {
    const key = typeof row?.key === 'string' && row.key ? row.key : `row-${index}`;
    const rawTechnique = row?.technique;
    const values = Array.isArray(rawTechnique) ? rawTechnique : rawTechnique == null ? [] : [rawTechnique];
    const techniques = values.map((value, techniqueIndex) => normalizeTechnique(value, key, techniqueIndex)).filter(Boolean);
    const lens = Array.isArray(row?.lens) ? row.lens.filter((value) => typeof value === 'string' && value.trim()) : [];
    const paperSearchText = joinSearchText([row?.title, row?.method, row?.problem, row?.scenario, row?.evidence, lens]);
    return {
        ...row,
        key,
        title: typeof row?.title === 'string' ? row.title : key,
        lens,
        techniques,
        paperSearchText,
        allSearchText: joinSearchText([paperSearchText, techniques.map((technique) => technique.searchText)])
    };
};

const constructPublicationItems = () => {
    const pubToCategory = {};
    (paperStatisRef.value.overview || []).forEach((entry) => {
        pubToCategory[entry.label] = entry.category;
    });
    const present = new Set(Object.values(pubToCategory));
    const categories = [...CATEGORY_ORDER.filter((category) => present.has(category)), ...[...present].filter((category) => !CATEGORY_ORDER.includes(category))];
    const groupIndex = {};
    const newItems = categories.map((category, index) => {
        groupIndex[category] = index;
        return { label: categoryLabel(category), icon: categoryIcon(category), items: [] };
    });
    for (const publication in paperStatisRef.value.byPublicationAndYear) {
        const targetIndex = groupIndex[pubToCategory[publication]];
        if (targetIndex === undefined) continue;
        const perYear = paperStatisRef.value.byPublicationAndYear[publication];
        const publicationItem = { label: publication, items: [] };
        for (const year in perYear) {
            publicationItem.items.push({
                label: year,
                command: () => selectSource(publication, year)
            });
        }
        publicationItem.items.reverse();
        newItems[targetIndex].items.push([publicationItem]);
    }
    items.value = newItems;
};

const resetViewState = ({ clearQuery = false } = {}) => {
    first.value = 0;
    expandedTechniqueByPaper.value = {};
    if (clearQuery) {
        query.value = '';
        selectedLenses.value = [];
        selectedTypes.value = [];
    }
};

const selectSource = (publication, year) => {
    selection.value = { publication, year };
    resetViewState({ clearQuery: true });
    loadIndex(publication, year);
};

const loadIndex = async (publication, year) => {
    activeController?.abort();
    const controller = new AbortController();
    activeController = controller;
    const requestId = ++requestSequence;
    loadState.value = 'loading';
    rows.value = [];
    const file = `${publication} - ${year}.json`;
    const url = import.meta.env.PROD ? `https://raw.githubusercontent.com/xuanxuan197068/papers-collection/main/radar/index/${encodeURIComponent(file)}` : `/radar/index/${encodeURIComponent(file)}`;
    try {
        const response = await fetch(url, { signal: controller.signal });
        if (requestId !== requestSequence) return;
        if (response.status === 404) {
            loadState.value = 'missing';
            return;
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        // Vite's development SPA fallback returns index.html with HTTP 200 for
        // an absent JSON file; treat that response as a missing index as well.
        if ((response.headers.get('content-type') || '').includes('text/html')) {
            loadState.value = 'missing';
            return;
        }
        const payload = await response.json();
        if (!Array.isArray(payload)) throw new Error('Method index must be a JSON array');
        rows.value = payload.map(normalizeRow);
        loadState.value = 'ready';
    } catch (error) {
        if (error?.name === 'AbortError' || requestId !== requestSequence) return;
        console.error('Failed to load method index:', error);
        loadState.value = 'error';
    } finally {
        if (requestId === requestSequence && activeController === controller) activeController = null;
    }
};

const retryLoad = () => {
    if (selection.value) loadIndex(selection.value.publication, selection.value.year);
};

const lensOptions = computed(() => {
    const values = new Set();
    rows.value.forEach((row) => row.lens.forEach((lens) => values.add(lens)));
    return [...values].sort((left, right) => left.localeCompare(right));
});

const typeLabel = (type) => {
    const key = `methodIndex.types.${type}`;
    return te(key) ? t(key) : type;
};

const groundingLabel = (grounding) => {
    const key = `methodIndex.grounding.${grounding}`;
    return te(key) ? t(key) : grounding;
};

const pageReportTemplate = computed(() => String(tm('methodIndex.pageReport')));

const typeOptions = computed(() => {
    const available = new Set();
    rows.value.forEach((row) => row.techniques.forEach((technique) => technique.type && available.add(technique.type)));
    return [...available]
        .sort((left, right) => {
            const leftIndex = TECHNIQUE_TYPE_ORDER.indexOf(left);
            const rightIndex = TECHNIQUE_TYPE_ORDER.indexOf(right);
            return (leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex) - (rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex) || left.localeCompare(right);
        })
        .map((value) => ({ value, label: typeLabel(value) }));
});

const normalizedQuery = computed(() => normalizeText(query.value));
const filteredRows = computed(() => {
    const search = normalizedQuery.value;
    return rows.value.filter((row) => {
        const matchesQuery = !search || row.allSearchText.includes(search);
        const matchesLens = selectedLenses.value.length === 0 || row.lens.some((lens) => selectedLenses.value.includes(lens));
        const matchesType = selectedTypes.value.length === 0 || row.techniques.some((technique) => selectedTypes.value.includes(technique.type));
        return matchesQuery && matchesLens && matchesType;
    });
});

const hasFilters = computed(() => Boolean(query.value.trim()) || selectedLenses.value.length > 0 || selectedTypes.value.length > 0);

watch([query, selectedLenses, selectedTypes], () => resetViewState(), { deep: true });

const clearFilters = () => {
    query.value = '';
    selectedLenses.value = [];
    selectedTypes.value = [];
    resetViewState();
};

const handlePage = (event) => {
    first.value = event.first;
    pageSize.value = event.rows;
};

const techniqueLabel = (technique) => {
    if (technique.isLegacy) return t('methodIndex.legacyTechnique');
    return technique.name || t('methodIndex.unnamedTechnique', { index: technique.index + 1 });
};

const paperTitleId = (paper) => `mi-paper-title-${domSafe(paper.key)}`;
const techniqueHeadingId = (paper) => `mi-techniques-${domSafe(paper.key)}`;
const techniqueButtonId = (paper, technique) => `mi-technique-button-${domSafe(paper.key)}-${technique.index}`;
const techniqueRegionId = (paper, technique) => `mi-technique-region-${domSafe(paper.key)}-${technique.index}`;

const isTechniqueExpanded = (paper, technique) => expandedTechniqueByPaper.value[paper.key] === technique.id;
const toggleTechnique = (paper, technique) => {
    const current = expandedTechniqueByPaper.value[paper.key];
    expandedTechniqueByPaper.value = {
        ...expandedTechniqueByPaper.value,
        [paper.key]: current === technique.id ? null : technique.id
    };
};

const isTechniqueMatch = (_paper, technique) => Boolean(normalizedQuery.value) && technique.searchText.includes(normalizedQuery.value);

const evidenceSeverity = (evidence) => {
    switch (normalizeText(evidence)) {
        case 'real-world':
        case 'real system':
        case '真实系统':
            return 'success';
        case 'benchmark':
        case '基准测试':
            return 'info';
        case 'user study':
        case '用户研究':
            return 'warn';
        case 'simulation':
        case '仿真':
            return 'secondary';
        case 'unknown':
            return 'contrast';
        default:
            return 'info';
    }
};

const handleLanguageChange = () => constructPublicationItems();

onMounted(() => {
    constructPublicationItems();
    languageEmitter.on(handleLanguageChange);
});

onUnmounted(() => {
    requestSequence += 1;
    activeController?.abort();
    languageEmitter.off(handleLanguageChange);
});
</script>

<style scoped>
.method-index-page {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.menu-card {
    padding: 0.5rem 0.75rem;
}

.menu-card :deep(.p-megamenu) {
    border: none;
    background: transparent;
}

.content-card {
    padding: 1.5rem 1.75rem 1.75rem;
}

.mi-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.25rem;
}

.mi-header--placeholder {
    color: var(--text-color-secondary);
}

.mi-header-copy {
    min-width: 0;
}

.mi-header-icon {
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

.mi-title {
    margin: 0;
    font-size: 1.3rem;
    font-weight: 600;
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    overflow-wrap: anywhere;
}

.mi-year {
    color: var(--primary-color);
    font-weight: 700;
}

.mi-subtitle {
    margin: 0.15rem 0 0;
    color: var(--text-color-secondary);
    font-size: 0.9rem;
}

.mi-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 3rem 1rem;
    color: var(--text-color-secondary);
    text-align: center;
}

.mi-state p {
    margin: 0;
}

.mi-state-icon {
    font-size: 2rem;
}

.mi-toolbar {
    display: grid;
    grid-template-columns: minmax(15rem, 1fr) minmax(12rem, auto) minmax(12rem, auto) auto;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.mi-search,
.mi-search :deep(.p-inputtext),
.mi-filter {
    width: 100%;
}

.mi-data-view :deep(.p-dataview-content),
.mi-data-view :deep(.p-paginator) {
    border: none;
    background: transparent;
}

.mi-card-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

.mi-card-item {
    min-width: 0;
}

.mi-paper-card {
    border: 1px solid var(--surface-border);
    box-shadow: none;
}

.mi-paper-card :deep(.p-card-body),
.mi-paper-card :deep(.p-card-content) {
    padding: 0;
}

.mi-paper-card :deep(.p-card-body) {
    padding: 1.25rem;
}

.mi-paper-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
}

.mi-paper-title {
    min-width: 0;
    margin: 0;
    font-size: 1.05rem;
    font-weight: 650;
    line-height: 1.45;
    overflow-wrap: anywhere;
}

.mi-paper-title a {
    color: inherit;
    text-decoration: none;
}

.mi-paper-title a:hover {
    color: var(--primary-color);
}

.mi-link-icon {
    margin-left: 0.35rem;
    font-size: 0.72rem;
    opacity: 0.65;
}

.mi-method-block,
.mi-techniques {
    margin-top: 1rem;
}

.mi-method-block h4,
.mi-techniques h4 {
    margin: 0 0 0.4rem;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--text-color-secondary);
}

.mi-method-block p,
.mi-technique-empty,
.mi-legacy-text {
    margin: 0;
    line-height: 1.65;
    overflow-wrap: anywhere;
}

.mi-paper-facts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem 1.25rem;
    margin: 1rem 0 0;
}

.mi-paper-facts div,
.mi-technique-schema div {
    min-width: 0;
}

.mi-paper-facts dt,
.mi-technique-schema dt {
    margin-bottom: 0.25rem;
    color: var(--text-color-secondary);
    font-size: 0.78rem;
    font-weight: 700;
}

.mi-paper-facts dd,
.mi-technique-schema dd {
    margin: 0;
    line-height: 1.55;
    overflow-wrap: anywhere;
}

.mi-lenses {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.9rem;
}

.mi-lens-chip {
    display: inline-block;
    padding: 0.12rem 0.55rem;
    border-radius: 999px;
    font-size: 0.75rem;
    background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    color: var(--primary-color);
}

.mi-technique-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.mi-technique-buttons :deep(.p-button) {
    min-height: 2.5rem;
    max-width: 100%;
}

.mi-technique-buttons :deep(.p-button-label) {
    white-space: normal;
    overflow-wrap: anywhere;
}

.mi-technique-button--match {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 38%, transparent);
}

.mi-technique-detail {
    margin-top: 0.8rem;
    padding: 1rem;
    border: 1px solid color-mix(in srgb, var(--primary-color) 24%, var(--surface-border));
    border-radius: 0.75rem;
    background: color-mix(in srgb, var(--primary-color) 5%, var(--surface-card));
}

.mi-technique-schema {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem 1.25rem;
    margin: 0;
}

.mi-schema-wide {
    grid-column: 1 / -1;
}

@media (max-width: 1024px) {
    .mi-toolbar {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
    .content-card {
        padding: 1rem;
    }

    .mi-toolbar,
    .mi-paper-facts,
    .mi-technique-schema {
        grid-template-columns: minmax(0, 1fr);
    }

    .mi-schema-wide {
        grid-column: auto;
    }

    .mi-toolbar :deep(.p-button) {
        width: 100%;
    }

    .mi-paper-heading {
        flex-direction: column;
        gap: 0.6rem;
    }

    .mi-technique-buttons :deep(.p-button) {
        flex: 1 1 100%;
        justify-content: center;
    }
}
</style>
