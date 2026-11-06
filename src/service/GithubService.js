const repoURL = 'https://api.github.com/repos/xuanxuan197068/papers-collection'

async function getRepoStatistics() {
    try {
        let response = await fetch(repoURL);
        if (!response.ok) return null;
        return await response.json();
    } catch (error) {
        console.error(error);
        return null;
    }
}

export const GithubService = {
    getRepoStatisticsData() {
        return getRepoStatistics();
    }
}
