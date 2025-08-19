import {
  managedStateStore,
  repoDisplayStore,
  moveRepoToCollection,
} from "./store.js";
import Sortable from "sortablejs";

let container = null;
let allRepos = [];
let sortableInstance = null;

function unfavoriteRepo(repoId) {
  const currentState = JSON.parse(JSON.stringify(managedStateStore.get()));

  currentState.manage.forEach((c) => {
    const repoIndex = c.repos.indexOf(repoId);
    if (repoIndex > -1) c.repos.splice(repoIndex, 1);
  });

  if (!currentState.removed.includes(repoId)) {
    currentState.removed.push(repoId);
  }

  managedStateStore.set(currentState);
}

// 渲染函数
function render(reposToShow) {
  const managedState = managedStateStore.get();

  if (sortableInstance) {
    sortableInstance.destroy();
  }
  container.innerHTML = reposToShow
    .map((repo) => {
      const collectionOptions = managedState.manage
        .map(
          (c) =>
            `<option value="${c.id}" ${
              repo.targetCollectionId === c.id ? "selected" : ""
            }>${c.name}</option>`
        )
        .join("");

      return `
      <div class="repo-card ${
        repo.isUnfavorited ? "is-unfavorited" : ""
      }" data-repo-id="${repo.full_name}">
        <div class="card-header" style="cursor: grab;">
          <h4 class="repo-name">${repo.full_name}</h4>
          <a href="${
            repo.url
          }" target="_blank" rel="noopener noreferrer" class="repo-link-btn" title="Open Repo" onclick="event.stopPropagation()">🔗</a>
        </div>
        
        <p class="repo-collection">Original: ${repo.list_name}</p>
        <p class="repo-description">${
          repo.description || "No description provided."
        }</p>
        <div class="card-actions">
          <div class="target-collection-selector">
            <span style="font-size: 0.8rem; color: var(--color-gray-400);">Target: </span>
 <select class="repo-target-select" data-repo-id="${repo.full_name}" ${
        repo.isUnfavorited ? "disabled" : ""
      }>
              ${collectionOptions}
            </select>
          </div>
          <div class="card-buttons">
            <button title="恢复" class="adopt-btn" data-original-list-name="${
              repo.list_name
            }" ${repo.isUnfavorited ? "disabled" : ""}>&#x21BA;</button>

            <button title="${
              repo.isUnfavorited ? "收藏" : "取消收藏"
            }" class="favorite-btn" data-is-favorited="${!repo.isUnfavorited}">
              ${repo.isUnfavorited ? "✩" : "★"}
            </button>
          </div>
        </div>
      </div>
    `;
    })
    .join("");

  $(".repo-target-select")
    .select2({
      width: "150px",
    })
    .on("change", function () {
      const repoId = $(this).data("repo-id");
      const newCollectionId = $(this).val();
      moveRepoToCollection(repoId, newCollectionId);
    });

  sortableInstance = new Sortable(container, {
    group: {
      name: "shared-repos",
      pull: "clone",
      put: false,
    },
    sort: false,
    animation: 150,
    handle: ".card-header", // 指定拖拽手柄
    dragClass: "repo-card-drag-proxy", 
    ghostClass: "is-unfavorited", // 拖拽时的占位符样式
    onEnd: function (evt) {
      // 拖拽结束后的逻辑（暂不处理，因为我们主要是拖到右侧列表）
    },
  });
}

// 事件处理器
function handleCardEvents(e) {
  const card = e.target.closest(".repo-card");
  if (!card) return;
  const repoId = card.dataset.repoId;
  if (e.target.tagName === "BUTTON") {
    if (e.target.classList.contains("adopt-btn")) {
      const originalListName = e.target.dataset.originalListName;
      const targetCollection = managedStateStore
        .get()
        .manage.find((c) => c.name === originalListName);
      if (targetCollection) {
        moveRepoToCollection(repoId, targetCollection.id);
      }
    }

    if (e.target.classList.contains("favorite-btn")) {
      const isFavorited = e.target.dataset.isFavorited === "true";
      if (isFavorited) {
        unfavoriteRepo(repoId);
      } else {
        const originalRepo = allRepos.find((r) => r.full_name === repoId);
        const originalCollection = managedStateStore
          .get()
          .manage.find((c) => c.name === originalRepo.list_name);
        moveRepoToCollection(repoId, originalCollection.id);
      }
    }
  }
}

// 初始化函数
export function createRepoCards(element, initialData) {
  container = element;
  allRepos = initialData.allRepos;
  container.addEventListener("click", handleCardEvents);
  repoDisplayStore.subscribe(render);
}
