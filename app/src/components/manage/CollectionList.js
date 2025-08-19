import { managedStateStore, moveRepoToCollection } from "./store.js";
import Sortable from 'sortablejs'; 

let listContainerElement = null;
const sortableInstances = [];

function render(managedState) {

  sortableInstances.forEach((instance) => instance.destroy());
  sortableInstances.length = 0;

  if (listContainerElement) {
    listContainerElement.innerHTML = managedState.manage
      .map(
        (collection) => `
                <div class="collection-item" data-collection-id="${collection.id}">
                    <div class="collection-details">
                        <span class="collection-name">${collection.name}</span>
                        <span class="repo-count">${collection.repos.length}</span>
                    </div>
                    <button class="delete-collection-btn" data-collection-id="${collection.id}">🗑️</button>
                </div>
                `
      )
      .join("");
  }
  
  document.querySelectorAll("#collection-list-container .collection-item").forEach((item) => {
        const instance = new Sortable(item, {
            group: "shared-repos",
            animation: 150,
            ghostClass: "repo-item-ghost", 
            onAdd: function (evt) {
                const itemEl = evt.item;
                const toCollectionEl = evt.to;
                const collectionId = toCollectionEl.dataset.collectionId;
                const repoId = itemEl.dataset.repoId;

                if (repoId && collectionId) {
                    moveRepoToCollection(repoId, collectionId);
                }
                itemEl.parentNode.removeChild(itemEl);
            },
        });
        sortableInstances.push(instance);
    });
}

function handleNewCollection(e) {
  if (e.key === "Enter" && e.target.value.trim() !== "") {
    const newName = e.target.value.trim();
    const currentState = managedStateStore.get();
    if (!currentState.manage.some((c) => c.name === newName)) {
      const newCollection = {
        id: `col_${Date.now()}`,
        name: newName,
        slug: newName.toLowerCase().replace(/\s+/g, "-"),
        description: "",
        repos: [],
      };
      managedStateStore.set({
        ...currentState,
        manage: [...currentState.manage, newCollection],
      });
    }
    e.target.value = "";
  }
}

function handleDeleteCollection(e) {
  if (e.target.classList.contains("delete-collection-btn")) {
    const collectionId = e.target.dataset.collectionId;
    const currentState = managedStateStore.get();
    // 此处可以添加逻辑，例如将集合内的 repo 移到某个默认集合
    const updatedManage = currentState.manage.filter(
      (c) => c.id !== collectionId
    );
    managedStateStore.set({ ...currentState, manage: updatedManage });
  }
}

export function createCollectionList(rootElement) {
  const newCollectionInput = rootElement.querySelector("#new-collection-input");
  listContainerElement = rootElement.querySelector(
    "#collection-list-container"
  );
  if (!newCollectionInput || !listContainerElement) {
    console.error("CollectionList container elements not found!");
    return;
  }
  newCollectionInput.addEventListener("keydown", handleNewCollection);
  listContainerElement.addEventListener("click", handleDeleteCollection); // 使用事件委托

  managedStateStore.subscribe(render);

  render(managedStateStore.get());
}
