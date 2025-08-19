import { activeTabStore } from './store.js';

export function createRepoTabs(element, { tabData }) {
  function render() {
    const activeTab = activeTabStore.get();
    element.innerHTML = tabData.map(tab => `
      <button class="tab-btn ${tab.name === activeTab ? 'active' : ''}" data-collection-name="${tab.name}">
        ${tab.name} (${tab.count})
      </button>
    `).join('');
  }

  element.addEventListener('click', (e) => {
    if (e.target.tagName === 'BUTTON') {
      activeTabStore.set(e.target.dataset.collectionName);
    }
  });

  activeTabStore.subscribe(render);
}
