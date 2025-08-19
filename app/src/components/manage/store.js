import { atom, computed } from 'nanostores';

// --- 基础 Stores ---
// 1. 数据层：原始、不可变的仓库列表
export const originalReposStore = atom([]); 

// 2. 状态管理层：用户可修改的管理状态，包含 manage 和 removed 两个部分
export const managedStateStore = atom({
    manage: [],
    removed: []
});

// 3. UI状态：当前激活的Tab
export const activeTabStore = atom('全部');


// --- 派生/计算 Store (用于表示层) ---
// 这个 store 是连接数据和UI的桥梁，它根据原始数据和管理状态生成用于显示的“视图模型”
export const repoDisplayStore = computed(
  [originalReposStore, managedStateStore, activeTabStore],
  (allRepos, managedState, activeTab) => {
    // 创建一个快速查找 repo 当前所在 collection 的 map
    const repoLocationMap = new Map();
    managedState.manage.forEach(col => {
      col.repos.forEach(repoId => {
        repoLocationMap.set(repoId, col);
      });
    });

    // 1. 生成“增强”后的仓库列表
    const enrichedRepos = allRepos.map(repo => {
      const currentCollection = repoLocationMap.get(repo.full_name);
      // 判断是否在 removed 数组中
      const isUnfavorited = managedState.removed.includes(repo.full_name);
      
      return {
        ...repo, // 包含所有原始 repo 信息
        targetCollectionId: isUnfavorited ? null : currentCollection?.id,
        isUnfavorited: isUnfavorited,
      };
    });

    // 2. 根据 activeTab 过滤要显示的仓库
    if (activeTab === '全部') {
      return enrichedRepos;
    }
    // 过滤始终基于原始的 list_name
    return enrichedRepos.filter(repo => repo.list_name === activeTab);
  }
);


// --- 初始化函数 ---
export function initializeStores({ allRepos, allCollections }) {

    originalReposStore.set(allRepos);

    // 深拷贝以创建可修改的副本
    const initialManage = JSON.parse(JSON.stringify(allCollections));
    const collectionMap = new Map(initialManage.map(col => [col.name, col]));

    // 根据原始 list_name 分配 repo 到初始的管理集合中
    allRepos.forEach(repo => {
        const collection = collectionMap.get(repo.list_name);
        if (collection) {
            collection.repos = collection.repos || [];
            if (!collection.repos.includes(repo.full_name)) {
                collection.repos.push(repo.full_name);
            }
        }
    });

    // 设置初始状态
    managedStateStore.set({
        manage: initialManage,
        removed: []
    });
    
    activeTabStore.set('全部');
}

export function moveRepoToCollection(repoId, newCollectionId) {
  const currentState = JSON.parse(JSON.stringify(managedStateStore.get()));

  const removedIndex = currentState.removed.indexOf(repoId);
  if (removedIndex > -1) currentState.removed.splice(removedIndex, 1);

  currentState.manage.forEach((c) => {
    const repoIndex = c.repos.indexOf(repoId);
    if (repoIndex > -1) c.repos.splice(repoIndex, 1);
  });

  const targetCollection = currentState.manage.find(
    (c) => c.id === newCollectionId
  );
  if (targetCollection && !targetCollection.repos.includes(repoId)) {
    targetCollection.repos.push(repoId);
  }

  managedStateStore.set(currentState);
}