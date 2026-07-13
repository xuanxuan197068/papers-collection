<template>
    <div class="method-index-page">
        <div class="card menu-card">
            <MegaMenu :model="items" />
        </div>

        <div class="card content-card">
            <!-- Header -->
            <header v-if="selection" class="mi-header">
                <div class="mi-header-icon"><i class="pi pi-sitemap"></i></div>
                <div>
                    <h2 class="mi-title">
                        {{ selection.publication }} <span class="mi-year">{{ selection.year }}</span>
                    </h2>
                    <p class="mi-subtitle" v-if="!loading && !notGenerated">
                        {{ rows.length }} {{ t('methodIndex.papers') }}
                    </p>
                </div>
            </header>
            <header v-else class="mi-header mi-header--placeholder">
                <h2 class="mi-title">{{ t('methodIndex.selectPublication') }}</h2>
            </header>

            <!-- Empty state -->
            <div v-if="!selection && !loading" class="mi-empty">
                <i class="pi pi-hand-point-up mi-empty-icon"></i>
                <p>{{ t('methodIndex.emptyHint') }}</p>
            </div>

            <!-- Loading -->
            <div v-else-if="loading" class="mi-empty">
                <i class="pi pi-spinner pi-spin mi-empty-icon"></i>
                <p>{{ t('methodIndex.loading') }}</p>
            </div>

            <!-- Not generated -->
            <div v-else-if="notGenerated" class="mi-empty">
                <i class="pi pi-inbox mi-empty-icon"></i>
                <p>{{ t('methodIndex.notGenerated', { venue: selection.publication, year: selection.year }) }}</p>
            </div>

            <!-- Index table -->
            <DataTable
                v-else
                class="borderless-table"
                :value="displayedRows"
                v-model:filters="filters"
                size="small"
                data-key="key"
                paginator :rows="15"
                :globalFilterFields="['title', 'method', 'problem', 'scenario']"
                :rows-per-page-options="[15, 30, 50, 100]"
                paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
            >
                <template #header>
                    <div class="flex flex-wrap justify-between gap-2">
                        <MultiSelect
                            v-model="selectedLenses"
                            :options="lensOptions"
                            display="chip"
                            :placeholder="t('methodIndex.anyLens')"
                            :max-selected-labels="4"
                            class="min-w-64"
                        />
                        <IconField>
                            <InputIcon><i class="pi pi-search" /></InputIcon>
                            <InputText v-model="filters['global'].value" :placeholder="t('methodIndex.searchPlaceholder')" />
                        </IconField>
                    </div>
                </template>

                <template #empty>{{ t('methodIndex.notGenerated', { venue: selection.publication, year: selection.year }) }}</template>

                <Column :header="t('methodIndex.title')" style="min-width: 16rem">
                    <template #body="{ data }">
                        <a v-if="data.paper && data.paper !== '#'" :href="data.paper" target="_blank" rel="noopener" class="mi-paper-title">
                            {{ data.title }}<i class="pi pi-external-link mi-link-icon"></i>
                        </a>
                        <span v-else>{{ data.title }}</span>
                    </template>
                </Column>
                <Column :header="t('methodIndex.scenario')" field="scenario" style="min-width: 10rem" />
                <Column :header="t('methodIndex.problem')" field="problem" style="min-width: 12rem" />
                <Column :header="t('methodIndex.method')" field="method" style="min-width: 14rem" />
                <Column :header="t('methodIndex.evidence')" style="min-width: 8rem">
                    <template #body="{ data }">
                        <Tag :value="data.evidence" :severity="evidenceSeverity(data.evidence)" />
                    </template>
                </Column>
                <Column :header="t('methodIndex.lens')" style="min-width: 10rem">
                    <template #body="{ data }">
                        <span v-for="l in (data.lens || [])" :key="l" class="mi-lens-chip">{{ l }}</span>
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { FilterMatchMode } from '@primevue/core/api';
import { usePageTitle } from '@/composables/useI18n';
import { languageEmitter } from '@/locales';
import paperStatis from '@/assets/data/data-statistics.json';

const { t } = useI18n();
usePageTitle('menu.methodIndex');

const paperStatisRef = ref(paperStatis);
const items = ref([]);
const selection = ref(null);
const rows = ref([]);
const loading = ref(false);
const notGenerated = ref(false);
const selectedLenses = ref([]);
const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });

// --- venue -> category grouping (data-driven, same approach as ViewAbstract) ---
const CATEGORY_ORDER = ['top-tier', 'software-engineering', 'system', 'ai-ml'];
const CATEGORY_META = {
    'top-tier': { key: 'abstract.topTier', icon: 'pi pi-shield' },
    'software-engineering': { key: 'abstract.softwareEngineering', icon: 'pi pi-code' },
    'system': { key: 'abstract.system', icon: 'pi pi-cog' },
    'ai-ml': { key: 'abstract.aiMl', icon: 'pi pi-sparkles' }
};
const categoryLabel = (c) => (CATEGORY_META[c] ? t(CATEGORY_META[c].key) : c);
const categoryIcon = (c) => (CATEGORY_META[c] ? CATEGORY_META[c].icon : 'pi pi-folder');

const constructPublicationItems = () => {
    const pubToCategory = {};
    (paperStatisRef.value.overview || []).forEach((el) => {
        pubToCategory[el.label] = el.category;
    });
    const present = new Set(Object.values(pubToCategory));
    const categories = [
        ...CATEGORY_ORDER.filter((c) => present.has(c)),
        ...[...present].filter((c) => !CATEGORY_ORDER.includes(c))
    ];
    const groupIndex = {};
    const newItems = categories.map((category, i) => {
        groupIndex[category] = i;
        return { label: categoryLabel(category), icon: categoryIcon(category), items: [] };
    });
    for (let publication in paperStatisRef.value.byPublicationAndYear) {
        const targetIndex = groupIndex[pubToCategory[publication]];
        if (targetIndex === undefined) continue;
        const perYear = paperStatisRef.value.byPublicationAndYear[publication];
        const tempPublicationItem = { label: publication, items: [] };
        for (let year in perYear) {
            tempPublicationItem.items.push({
                label: year,
                command: () => {
                    selection.value = { publication, year };
                    loadIndex(publication, year);
                }
            });
        }
        tempPublicationItem.items = tempPublicationItem.items.reverse();
        newItems[targetIndex].items.push([tempPublicationItem]);
    }
    items.value = newItems;
};

// --- load a per-venue-year index file from radar/index/ ---
const loadIndex = async (publication, year) => {
    loading.value = true;
    notGenerated.value = false;
    rows.value = [];
    selectedLenses.value = [];
    const file = `${publication} - ${year}.json`;
    const url = import.meta.env.PROD
        ? 'https://raw.githubusercontent.com/xuanxuan197068/papers-collection/main/radar/index/' + encodeURIComponent(file)
        : '/radar/index/' + encodeURIComponent(file);
    try {
        const res = await fetch(url);
        if (res.ok) {
            rows.value = await res.json();
        } else {
            notGenerated.value = true;
        }
    } catch (e) {
        console.log(e);
        notGenerated.value = true;
    } finally {
        loading.value = false;
    }
};

const lensOptions = computed(() => {
    const s = new Set();
    rows.value.forEach((r) => (r.lens || []).forEach((l) => s.add(l)));
    return [...s].sort();
});

const displayedRows = computed(() => {
    if (!selectedLenses.value.length) return rows.value;
    return rows.value.filter((r) => (r.lens || []).some((l) => selectedLenses.value.includes(l)));
});

const evidenceSeverity = (evidence) => {
    switch ((evidence || '').toLowerCase()) {
        case 'real-world':
        case 'real system':
        case '真实系统': return 'success';
        case 'benchmark':
        case '基准测试': return 'info';
        case 'user study':
        case '用户研究': return 'warn';
        case 'simulation':
        case '仿真': return 'secondary';
        case 'unknown': return 'contrast';
        default: return 'info';
    }
};

const handleLanguageChange = () => constructPublicationItems();

onMounted(() => {
    constructPublicationItems();
    languageEmitter.on(handleLanguageChange);
});
onUnmounted(() => {
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
.mi-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 3rem 1rem;
    color: var(--text-color-secondary);
    text-align: center;
}
.mi-empty-icon {
    font-size: 2rem;
}
.mi-paper-title {
    text-decoration: none;
    color: inherit;
    font-weight: 500;
}
.mi-paper-title:hover {
    color: var(--primary-color);
}
.mi-link-icon {
    font-size: 0.7rem;
    margin-left: 0.35rem;
    opacity: 0.6;
}
.mi-lens-chip {
    display: inline-block;
    padding: 0.05rem 0.5rem;
    margin: 0.1rem 0.15rem 0.1rem 0;
    border-radius: 999px;
    font-size: 0.75rem;
    background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    color: var(--primary-color);
}
.borderless-table :deep(.p-datatable-table-container),
.borderless-table :deep(.p-datatable-header),
.borderless-table :deep(.p-datatable-paginator-bottom) {
    border: none;
    background: transparent;
}
.borderless-table :deep(.p-datatable-thead > tr > th),
.borderless-table :deep(.p-datatable-tbody > tr > td) {
    border-left: none;
    border-right: none;
    vertical-align: top;
}
.borderless-table :deep(.p-datatable-thead > tr > th) {
    background: transparent;
}
</style>
