import { managedStateStore, initializeStores } from './store.js';
import { createCollectionList } from './CollectionList.js';
import { createRepoCards } from './RepoCards.js';
import { createRepoTabs } from './RepoTabs.js';

function handleExport() {
  // 直接导出 managedStateStore 的内容
  const dataToExport = managedStateStore.get();
  
  const dataStr = JSON.stringify(dataToExport, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  
  const linkElement = document.createElement('a');
  linkElement.href = url;
  linkElement.download = 'managed-state.json';
  document.body.appendChild(linkElement);
  linkElement.click();
  document.body.removeChild(linkElement);
  URL.revokeObjectURL(url);
}

export function initApp({ allRepos, allCollections, tabData }) {
  initializeStores({ allRepos, allCollections });

  createRepoTabs(document.getElementById('repo-tabs'), { tabData });
  createRepoCards(document.getElementById('repo-cards-container'), { allRepos });
  createCollectionList(document.getElementById('collection-list-section'));

  document.getElementById('export-btn').addEventListener('click', handleExport);
}
