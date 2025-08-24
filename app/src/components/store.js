import { atom, computed } from "nanostores";
import Dexie from "dexie";

// --- 1. 数据库定义 (使用 Dexie 简化 IndexedDB 操作) ---
const db = new Dexie("RepoManagerDB");
// 定义一个表来存储我们整个 managedCollections 状态
db.version(1).stores({
  userState: "key, collections", // 使用一个固定的 key 来存储和读取
});

const UNCATEGORIZED_COLLECTION = {
  id: "system_uncategorized",
  name: "Uncategorized",
  slug: "uncategorized",
  description: "Repositories that are not in any specific collection.",
  repos: [],
  isSystem: true, // 添加一个标志，以便UI可以特殊处理（例如，禁止删除/重命名）
};

const UI_STATE_KEY = "repoManagerUiState";

/**
 * 从 localStorage 安全地加载并解析 UI 状态。
 * 如果没有存储或解析失败，则返回 null。
 * @returns {object | null}
 */
function loadUiStateFromStorage() {
  try {
    const savedState = localStorage.getItem(UI_STATE_KEY);
    return savedState ? JSON.parse(savedState) : null;
  } catch (error) {
    console.error("Failed to load UI state from localStorage:", error);
    // 如果解析出错，清除损坏的数据
    localStorage.removeItem(UI_STATE_KEY);
    return null;
  }
}

const persistedUiState = loadUiStateFromStorage();

// --- 2. 核心状态 Stores ---

// a. 原始数据：从服务器获取，作为“事实来源”，理论上在单次会话中不可变
export const originalRepos = atom([]);
export const originalCollections = atom([]);

// b. 核心托管状态：这是应用的“单一事实来源”，反映所有用户操作。
export const managedCollections = atom([]);

// c. UI 状态：用于控制视图切换等，不直接影响核心数据
export const activeView = atom(persistedUiState?.activeView || "table"); // 'card' 或 'table'
export const activeTab = atom(persistedUiState?.activeTab || "全部");
export const dataTableStore = atom(null);
export const isDataInitialized = atom(false); // 标记数据是否已加载完成
export const isSidebarVisible = atom(
  persistedUiState?.isSidebarVisible ?? true
);

export const isDraggable = computed(isSidebarVisible, (visible) => visible);

// --- 3. 派生（计算）Store ---

// “增强型”仓库列表：这是所有视图（表格、卡片）的数据基础。
// 它将原始仓库信息与当前的托管状态结合起来，为每个 repo 附加它当前所属的 collection 信息。
export const enrichedRepos = computed(
  [originalRepos, managedCollections],
  (repos, collections) => {
    if (repos.length === 0) return [];

    // 创建一个快速查找 Map：repo.full_name -> collection 对象
    const repoLocationMap = new Map();
    collections.forEach((col) => {
      // 确保 col.repos 是一个数组
      (col.repos || []).forEach((repoId) => {
        repoLocationMap.set(repoId, col);
      });
    });

    return repos.map((repo) => ({
      ...repo, // 包含所有原始 repo 信息
      // 附加当前被管理的 collection 对象
      managedCollection: repoLocationMap.get(repo.full_name) || null,
    }));
  }
);

// b. 卡片视图专用的仓库列表（根据 Tab 过滤）
export const cardViewRepos = computed(
  [enrichedRepos, activeTab],
  (repos, tab) => {
    if (tab === "全部") {
      return repos;
    }
    // 过滤始终基于原始的 list_name
    return repos.filter((repo) => repo.list_name === tab);
  }
);

// c. 卡片视图专用的 Tabs 数据 (只计算一次)
export const cardViewTabs = computed(originalRepos, (repos) => {
  if (repos.length === 0) return [];
  const repoCounts = repos.reduce((acc, repo) => {
    acc[repo.list_name] = (acc[repo.list_name] || 0) + 1;
    return acc;
  }, {});
  return ["全部", ...Object.keys(repoCounts).sort()].map((name) => ({
    name: name,
    count: name === "全部" ? repos.length : repoCounts[name],
  }));
});

// --- 4. 核心 Action 函数 (State Modifiers) ---

/**
 * 初始化应用数据，这是应用的入口。
 * 它会获取服务器数据，并尝试与本地持久化的数据进行合并。
 */
export async function initializeData() {
  try {
    const [reposRes, collectionsRes] = await Promise.all([
      fetch("/data/repos.json"),
      fetch("/data/collections.json"),
    ]);
    const serverRepos = await reposRes.json();
    const serverCollections = await collectionsRes.json();

    originalRepos.set(serverRepos);
    originalCollections.set(serverCollections);

    // 尝试从 IndexedDB 加载用户保存的状态
    const persistedState = await db.userState.get("managedCollections");

    if (persistedState) {
      // 如果有本地数据，则进行合并更新
      const mergedCollections = mergeWithServerData(
        persistedState.collections,
        serverRepos
      );
      managedCollections.set(mergedCollections);
    } else {
      // 如果没有，则根据服务器数据创建初始状态
      const initialState = buildInitialState(serverRepos, serverCollections);
      managedCollections.set(initialState);
    }
  } catch (error) {
    console.error("Failed to initialize data:", error);
    // 可选：添加错误处理逻辑
  } finally {
    isDataInitialized.set(true);
    // 启动自动保存机制
    autoSaveOnChanges();
    autoSaveUiStateOnChanges();
  }
}

/**
 * 初始化一个 Collection 选择器 (TomSelect 实例).
 * @param {HTMLSelectElement} selectElement - 要初始化的 <select> DOM 元素。
 * @param {Map<string, any>} tomSelectInstances - 用于存储和管理 TomSelect 实例的 Map 对象。
 */
export function initializeCollectionSelector(
  selectElement,
  tomSelectInstances,
  TomSelect
) {
  if (!TomSelect) {
    console.error(
      "TomSelect class was not provided to initializeCollectionSelector."
    );
    return;
  }

  const repoFullName = selectElement.dataset.repoFullname;
  if (!repoFullName) return;

  // 如果已存在此 repo 的实例，先销毁以防内存泄漏
  if (tomSelectInstances.has(repoFullName)) {
    tomSelectInstances.get(repoFullName).destroy();
  }

  // 1. 从 store 获取数据
  const collections = managedCollections.get();
  const allRepos = enrichedRepos.get();

  // 2. 准备 TomSelect 的选项
  const options = collections.map((c) => ({
    value: c.slug,
    text: c.name,
  }));

  // 3. 找到当前 repo 以确定其默认选中的值
  const currentRepo = allRepos.find((r) => r.full_name === repoFullName);
  const currentSlug = currentRepo?.managedCollection?.slug;

  // 4. 初始化 TomSelect
  const tomSelectInstance = new TomSelect(selectElement, {
    options: options,
    items: currentSlug ? [currentSlug] : [],
    create: false,
    placeholder: "Assign collection...",
    // 确保下拉菜单在表格滚动时不会被遮挡
    dropdownParent: "body",
    onChange: (newCollectionSlug) => {
      // 5. 当选择变化时，调用 store 的 action 更新状态
      if (newCollectionSlug && newCollectionSlug !== currentSlug) {
        moveRepoToCollection(repoFullName, newCollectionSlug);
      }
    },
  });

  // 6. 存储新创建的实例
  tomSelectInstances.set(repoFullName, tomSelectInstance);
}

/**
 * 将仓库移动到新的集合中
 * @param {string} repoFullName - 仓库的 full_name
 * @param {string} newCollectionSlug - 目标集合的 slug
 */
export function moveRepoToCollection(repoFullName, newCollectionSlug) {
  const currentState = managedCollections.get();
  // 使用 map 来创建一个新的状态数组，确保不可变性
  const newState = currentState.map((collection) => {
    // 从所有集合中过滤掉该仓库
    const updatedRepos = (collection.repos || []).filter(
      (r) => r !== repoFullName
    );
    return { ...collection, repos: updatedRepos };
  });

  // 在目标集合中找到并添加该仓库
  const targetCollection = newState.find((c) => c.slug === newCollectionSlug);
  if (targetCollection && !targetCollection.repos.includes(repoFullName)) {
    targetCollection.repos.push(repoFullName);
  }

  managedCollections.set(newState);
}

/**
 * 新增一个 Collection
 * @param {string} name - 新集合的名称
 */
export function addCollection(name) {
  const currentState = managedCollections.get();
  const newSlug = name.toLowerCase().replace(/\s+/g, "-");
  if (!newSlug) {
    alert("Collection name cannot be empty.");
    return;
  }
  if (currentState.some((c) => c.name.toLowerCase() === name.toLowerCase())) {
    alert("Collection with this name already exists.");
    return;
  }
  const newCollection = {
    id: `col_${Date.now()}`,
    name: name,
    slug: newSlug,
    description: "",
    repos: [], // 新集合初始为空
  };
  managedCollections.set([...currentState, newCollection]);
}

/**
 * 更新一个 Collection 的元数据 (如名称、描述)
 * @param {string} collectionSlug
 * @param {object} updates - e.g., { name: "New Name", description: "..." }
 */
export function updateCollection(collectionSlug, updates) {
  const collectionToUpdate = managedCollections
    .get()
    .find((c) => c.slug === collectionSlug);
  if (collectionToUpdate?.isSystem) {
    alert("The Uncategorized collection cannot be modified.");
    return;
  }
  delete updates.slug;
  const currentState = managedCollections.get();
  const newState = currentState.map((c) =>
    c.slug === collectionSlug ? { ...c, ...updates } : c
  );
  managedCollections.set(newState);
}

/**
 * 删除一个 Collection
 * @param {string} collectionSlug
 */
export function deleteCollection(collectionSlug) {
  if (collectionSlug === UNCATEGORIZED_COLLECTION.slug) {
    alert("The Uncategorized collection cannot be deleted.");
    return;
  }
  const currentState = managedCollections.get();
  const collectionToDelete = currentState.find(
    (c) => c.slug === collectionSlug
  );
  const uncategorized = currentState.find(
    (c) => c.slug === UNCATEGORIZED_COLLECTION.slug
  );

  if (!collectionToDelete || !uncategorized) return;

  const reposToMove = collectionToDelete.repos || [];
  uncategorized.repos = [...new Set([...uncategorized.repos, ...reposToMove])];

  // 过滤掉被删除的集合
  const newState = currentState.filter((c) => c.slug !== collectionSlug);
  managedCollections.set(newState);
}

// --- 5. 持久化逻辑 ---

let isAutoSaveInitialized = false;
let isUiAutoSaveInitialized = false;

function autoSaveUiStateOnChanges() {
  if (isUiAutoSaveInitialized) return;

  // 创建一个组合 store，监听所有 UI 状态的变化
  const uiState = computed(
    [activeView, activeTab, isSidebarVisible],
    (view, tab, sidebar) => ({
      activeView: view,
      activeTab: tab,
      isSidebarVisible: sidebar,
    })
  );

  // 订阅这个组合 store 的变化
  uiState.subscribe((currentState) => {
    // 确保只在数据初始化后才执行保存，避免不必要地写入
    if (!isDataInitialized.get()) return;

    try {
      localStorage.setItem(UI_STATE_KEY, JSON.stringify(currentState));
    } catch (error) {
      console.error("Failed to save UI state to localStorage:", error);
    }
  });

  isUiAutoSaveInitialized = true;
}

function autoSaveOnChanges() {
  if (isAutoSaveInitialized) return;
  // 监听 managedCollections 的变化，并自动保存到 IndexedDB
  managedCollections.subscribe(async (collections) => {
    // 确保只在数据初始化后才执行保存，防止初始空状态覆盖已有数据
    if (!isDataInitialized.get() || collections.length === 0) return;

    try {
      await db.userState.put({
        key: "managedCollections",
        collections: collections,
      });
      console.log("State saved to IndexedDB.");
    } catch (error) {
      console.error("Failed to save state to IndexedDB:", error);
    }
  });
  isAutoSaveInitialized = true;
}

// --- 6. 辅助函数 ---

/**
 * 在首次启动或无本地数据时，根据服务器数据构建初始状态
 */
function buildInitialState(repos, collections) {
  const userCollections = collections.map((c) => ({ ...c, repos: [] }));
  const state = [...userCollections, { ...UNCATEGORIZED_COLLECTION }];
  const collectionMap = new Map(state.map((c) => [c.name, c]));
  const uncategorizedCollection = state.find(
    (c) => c.slug === UNCATEGORIZED_COLLECTION.slug
  );

  repos.forEach((repo) => {
    const targetCollection = collectionMap.get(repo.list_name);
    if (targetCollection) {
      targetCollection.repos.push(repo.full_name);
    } else {
      // 如果 repo 的 list_name 不在任何已知集合中，则放入“未分类”
      uncategorizedCollection.repos.push(repo.full_name);
    }
  });
  return state;
}

/**
 * 当应用重新加载时，将本地保存的状态与最新的服务器数据进行合并
 */
function mergeWithServerData(persistedCollections, serverRepos) {
  // 这个过程类似于库存管理，persistedCollections 是我们的“现有库存”，serverRepos 是“新到的货品清单”
  // 我们需要添加新商品，并移除已下架的商品。
  // [Stochastic inventory models for a single item at a single location](https://research.tue.nl/files/3784301/708391088818209.pdf){target="_blank" class="gpt-web-url"}

  const serverRepoSet = new Set(serverRepos.map((r) => r.full_name));
  let collectionsToMerge = [...persistedCollections];
  if (
    !collectionsToMerge.some((c) => c.slug === UNCATEGORIZED_COLLECTION.slug)
  ) {
    collectionsToMerge.push({ ...UNCATEGORIZED_COLLECTION });
  }

  // 1. 过滤掉用户集合中已经不存在于服务器的 repo
  const updatedCollections = persistedCollections.map((col) => ({
    ...col,
    repos: (col.repos || []).filter((repoId) => serverRepoSet.has(repoId)),
  }));

  const managedRepoSet = new Set(
    updatedCollections.flatMap((col) => col.repos)
  );
  const collectionMap = new Map(updatedCollections.map((c) => [c.name, c]));
  const uncategorizedCollection = updatedCollections.find(
    (c) => c.slug === UNCATEGORIZED_COLLECTION.slug
  );

  // 2. 找出服务器上新增的、且未被用户管理的 repo，并将它们添加到其原始 collection 中
  serverRepos.forEach((repo) => {
    if (!managedRepoSet.has(repo.full_name)) {
      const targetCol = collectionMap.get(repo.list_name);
      if (targetCol) {
        targetCol.repos.push(repo.full_name);
      } else {
        // <-- 核心修正点 5: 如果其原始集合已被用户删除，则放入“未分类” -->
        uncategorizedCollection.repos.push(repo.full_name);
      }
    }
  });

  return updatedCollections;
}
