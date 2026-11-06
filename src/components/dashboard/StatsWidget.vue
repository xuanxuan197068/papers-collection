<script setup>
import { useI18n } from 'vue-i18n';
import { languageEmitter } from '@/locales';
import paperStatistics from '@/assets/data/data-statistics.json'
import { GithubService } from '@/service/GithubService.js';
import { computed, onMounted, onUnmounted, ref } from 'vue';

const { t } = useI18n();
const paperStatis = ref(paperStatistics);
const githubData = ref({ stars: '—', forks: '' });

// byPublication keys are one entry per venue; overview is (category, venue)
// pairs and can double-count a venue that spans two categories.
const totalPublications = computed(() => Object.keys(paperStatis.value.byPublication || {}).length);
// Written by main.py when the data files are regenerated; '—' before that.
const generatedAt = computed(() => (paperStatis.value.generated_at || '').slice(0, 10) || '—');

// 语言切换处理
const handleLanguageChange = () => {
    // 当语言切换时，可以在这里处理特定的逻辑
    // 目前大部分内容会自动更新
};

onMounted(() => {
    GithubService.getRepoStatisticsData().then((res) => {
        if (!res || typeof res.stargazers_count !== 'number') return;
        githubData.value = {
            stars: res.stargazers_count,
            forks: ' / ' + res.forks_count,
        }
    })
    languageEmitter.on(handleLanguageChange);
});

onUnmounted(() => {
    languageEmitter.off(handleLanguageChange);
});
</script>

<template>
    <div class="grid grid-cols-12 gap-8 mb-8">
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">{{ t('dashboard.totalPapers') }}</span>
                        <div class="font-medium text-xl">{{ paperStatis.total }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-blue-100 dark:bg-blue-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-file text-blue-500 !text-xl"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">{{ t('dashboard.totalPublications') }}</span>
                        <div class="font-medium text-xl">{{ totalPublications }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-indigo-100 dark:bg-indigo-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-book text-indigo-500 !text-xl"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">{{ t('dashboard.projectStars') }}</span>
                        <div class="font-medium text-xl">{{ githubData.stars }} {{ githubData.forks }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-yellow-100 dark:bg-yellow-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-star text-yellow-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-span-12 lg:col-span-6 xl:col-span-3">
            <div class="card mb-0">
                <div class="flex justify-between mb-4">
                    <div>
                        <span class="block text-muted-color font-medium mb-4">{{ t('dashboard.recentUpdate') }}</span>
                        <span class="text-900 font-medium text-xl"> {{ generatedAt }} </span>
                    </div>
                    <div class="flex items-center justify-center bg-orange-100 dark:bg-orange-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-sparkles text-orange-500 !text-xl"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

</template>

<style scoped>
h1 {
    @apply font-semibold text-xl ;
}
</style>