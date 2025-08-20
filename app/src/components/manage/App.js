import { managedStateStore, initializeStores } from "./store.js";
import { createCollectionList } from "./CollectionList.js";
import { createRepoCards } from "./RepoCards.js";
import { createRepoTabs } from "./RepoTabs.js";

function handleExport() {
  // 直接导出 managedStateStore 的内容
  const dataToExport = managedStateStore.get();

  const dataStr = JSON.stringify(dataToExport, null, 2);
  const blob = new Blob([dataStr], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const linkElement = document.createElement("a");
  linkElement.href = url;
  linkElement.download = "managed-state.json";
  document.body.appendChild(linkElement);
  linkElement.click();
  document.body.removeChild(linkElement);
  URL.revokeObjectURL(url);
}

export async function initApp() {
  try {
    const [reposResponse, collectionsResponse] = await Promise.all([
      fetch("/data/repos.json"),
      fetch("/data/collections.json"),
    ]);

    if (!reposResponse.ok || !collectionsResponse.ok) {
      throw new Error("Failed to fetch initial data.");
    }

    const allRepos = await reposResponse.json();
    const allCollections = await collectionsResponse.json();

    const repoCounts = allRepos.reduce((acc, repo) => {
      acc[repo.list_name] = (acc[repo.list_name] || 0) + 1;
      return acc;
    }, {});

    const tabData = ["全部", ...Object.keys(repoCounts).sort()].map((name) => ({
      name: name,
      count: name === "全部" ? allRepos.length : repoCounts[name],
    }));

    // 4. 使用获取并处理好的数据来初始化各个模块
    initializeStores({ allRepos, allCollections });

    createRepoTabs(document.getElementById("repo-tabs"), { tabData });
    createRepoCards(document.getElementById("repo-cards-container"), {
      allRepos,
    });
    createCollectionList(document.getElementById("collection-list-section"));

    document
      .getElementById("export-btn")
      .addEventListener("click", handleExport);
  } catch (error) {
    console.error("Error initializing the RepoManager app:", error);
    // 可以在这里向用户显示一个错误信息
    const container = document.getElementById("repo-manager-container");
    if (container) {
      container.innerHTML =
        '<p style="color: red; text-align: center;">Failed to load repository data. Please try again later.</p>';
    }
  }
}
