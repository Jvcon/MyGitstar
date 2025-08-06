import requests
import re
import time

from .exceptions import GitHubAPIError, GitHubToolkitError

class GitHubManager:
    """
    A toolkit for managing GitHub Stars and Lists via REST and GraphQL APIs.

    This class requires a Personal Access Token (PAT) with the following scopes:
    - 'repo': For accessing repository details.
    - 'read:user': For reading user profile information.
    - 'write:lists': For creating, updating, and deleting star lists.
    """

    _REST_API_URL = "https://api.github.com"
    _GRAPHQL_API_URL = "https://api.github.com/graphql"

    def __init__(self, token: str,username: str = None):
        if not token:
            raise ValueError("GitHub token cannot be empty.")
            
        self.token = token
        self._authenticated_user_id = username
        
        # Session for API calls
        self._api_headers = {
            "Authorization": f"bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.api_session = requests.Session()
        self.api_session.headers.update(self._api_headers)

        # Session for Web Scraping
        self.scrape_session = requests.Session()
        self.scrape_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        self.repo_list_mapping_cache = None
        

    def _execute_graphql(self, query: str, variables: dict = None, headers: dict = None) -> dict:
        """Helper function to execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        request_headers = self._api_headers.copy()
        if headers:
            request_headers.update(headers)
            
        response = self.api_session.post(self._GRAPHQL_API_URL, json=payload, headers=request_headers)

        if response.status_code != 200:
            raise GitHubAPIError(f"GraphQL query failed.", status_code=response.status_code, errors=response.text)
            
        data = response.json()
        if "errors" in data:
            raise GitHubAPIError("GraphQL query returned errors.", errors=data["errors"])
            
        return data.get("data", {})


    # --- REST API Methods for Stars and Repos ---

    def get_authenticated_user_id(self) -> str:
        """
        Fetches and returns the user ID (login) of the authenticated user.
        Caches the result to avoid repeated API calls.
        """
        if self._authenticated_user_id:
            return self._authenticated_user_id
            
        url = f"{self._REST_API_URL}/user"
        response = self.api_session.get(url)
        response.raise_for_status()
        
        user_data = response.json()
        self._authenticated_user_id = user_data['login']
        return self._authenticated_user_id

    def get_starred_repos(self, user_id: str = None) -> list[dict]:
        """
        Fetches all starred repositories for a given user.
        See: https://docs.github.com/en/rest/activity/starring
        """
        if not user_id:
            user_id = self.get_authenticated_user_id()
            
        repos = []
        page = 1
        per_page = 100
        url = f"{self._REST_API_URL}/users/{user_id}/starred"
         
        while True:
            params = {"per_page": per_page, "page": page}
            response = self.api_session.get(url, params=params)
            response.raise_for_status() # Raises an HTTPError for bad responses
            
            data = response.json()

            if not data:
                break
            
            for item in data:
                repo_info = item
                repos.append({
                    'full_name': repo_info.get('full_name'),
                    'description': repo_info.get('description'),
                    'language': repo_info.get('language'),
                    'stars': repo_info.get('stargazers_count'),
                    'topics': repo_info.get('topics', []),
                    'url': repo_info.get('html_url'),
                })
            page += 1
            
        return repos

    def star_repo(self, owner: str, repo: str) -> bool:
        """Stars a repository for the authenticated user."""
        url = f"{self._REST_API_URL}/user/starred/{owner}/{repo}"
        response = self.api_session.put(url)
        return response.status_code == 204

    def unstar_repo(self, owner: str, repo: str) -> bool:
        """Unstars a repository for the authenticated user."""
        url = f"{self._REST_API_URL}/user/starred/{owner}/{repo}"
        response = self.api_session.delete(url)
        return response.status_code == 204

    # --- GraphQL API Methods for Lists ---
    
    def get_lists(self) -> list[dict]:
        """Fetches all star lists for the authenticated user."""
        query = """
        query {
          viewer {
            lists(first: 50) {
              nodes {
                id
                name
                description
              }
            }
          }
        }
        """
        data = self._execute_graphql(query)
        lists = data.get("viewer", {}).get("lists", {}).get("nodes", [])
        
        # 我们需要从 list 的 name 生成 slug，以便用于 URL
        for lst in lists:
            # 简单地将名字转为小写并用连字符替换空格，这通常是 GitHub 的做法
            lst['slug'] = lst['name'].lower().replace(' ', '-')
            
        return lists
    
    def create_list(self, name: str, description: str = "") -> str | None:
        """Creates a new star list and returns its node ID."""
        query = """
        mutation CreateList($name: String!, $description: String) {
          createLists(input: {lists: [{name: $name, description: $description}]}) {
            lists {
              id
              name
            }
          }
        }
        """
        variables = {"name": name, "description": description}
        data = self._execute_graphql(query, variables)
        new_list = data.get("createLists", {}).get("lists", [])
        return new_list[0]['id'] if new_list else None

    def delete_list(self, list_name: str) -> bool:
        """Deletes a star list by its name."""
        lists = self.get_lists()
        list_to_delete = next((l for l in lists if l['name'] == list_name), None)
        
        if not list_to_delete:
            raise GitHubToolkitError(f"List '{list_name}' not found.")
            
        query = """
        mutation DeleteList($listId: ID!) {
          deleteLists(input: {listIds: [$listId]}) {
            clientMutationId
          }
        }
        """
        variables = {"listId": list_to_delete['id']}
        self._execute_graphql(query, variables)
        return True

    def _get_node_id(self, item_type: str, owner: str, name: str) -> str:
        """Helper to get the global node ID for a repo."""
        if item_type == 'repo':
            query = """
            query GetRepoId($owner: String!, $name: String!) {
              repository(owner: $owner, name: $name) {
                id
              }
            }
            """
            data = self._execute_graphql(query, {"owner": owner, "name": name})
            return data.get("repository", {}).get("id")
        raise ValueError("Unsupported item type for node ID lookup.")

    def add_repo_to_list(self, repo_full_name: str, list_name: str) -> bool:
        """Adds a repository to a specified list."""
        owner, name = repo_full_name.split('/')
        repo_id = self._get_node_id('repo', owner, name)
        
        lists = self.get_lists()
        target_list = next((l for l in lists if l['name'] == list_name), None)

        if not repo_id or not target_list:
            raise GitHubToolkitError(f"Repository '{repo_full_name}' or List '{list_name}' not found.")

        query = """
        mutation AddToList($listId: ID!, $subjectId: ID!) {
          addListEntry(input: {listId: $listId, listEntry: {subjectId: $subjectId}}) {
            clientMutationId
          }
        }
        """
        variables = {"listId": target_list['id'], "subjectId": repo_id}
        self._execute_graphql(query, variables)
        return True
    
    # --- Web Scraping-based method (The "Missing Piece") ---

    def _get_repos_in_list_from_page(self, list_slug: str,user_id:str = None ) -> list[str]:
        """
        [WARNING: WEB SCRAPING]
        Fetches all repository names from a specific star list page.
        This method is fragile and used only because no official API exists.
        """
        repos_in_list = []
        page = 1
        
        if not user_id:
            user_id = self.get_authenticated_user_id() 
            
        print(f"  Scraping repositories for list slug: '{list_slug}'...")
        while True:
            url = f"https://github.com/stars/{user_id}/lists/{list_slug}?page={page}"
            try:
                response = self.scrape_session.get(url, timeout=10)
                response.raise_for_status()

                pattern = r'<span class="text-normal">([^/]+) / </span>([^<]+)</a>'
                matches = re.findall(pattern, response.text)

                if not matches:
                    break
                
                current_page_repos = [f"{owner.strip()}/{repo.strip()}" for owner, repo in matches]
                repos_in_list.extend(current_page_repos)
                
                page += 1
                time.sleep(1) # Polite scraping
            except requests.RequestException as e:
                print(f"  - Error scraping page {page} for list {list_slug}: {e}")
                break
        return repos_in_list

    # --- The Hybrid Method ---

    def get_repo_list_mapping_hybrid(self) -> dict[str, str]:
        """
        [HYBRID METHOD]
        Builds a mapping from a repository to its list by combining a reliable
        GraphQL API call with a web scraping fallback.
        1. Uses GraphQL to get all list names and slugs.
        2. Uses web scraping to get repos within each list.
        """
        if self.repo_list_mapping_cache is not None:
            return self.repo_list_mapping_cache

        repo_to_list_map = {}
        # 步骤 1: 使用可靠的 API 获取所有 lists
        lists = self.get_lists()
        
        if not lists:
            print("No star lists found via API.")
            return {}

        print(f"Found {len(lists)} lists. Now fetching repos for each via scraping...")
        for lst in lists:
            list_name = lst['name']
            list_slug = lst['slug']
            # 步骤 2: 使用网页抓取来补充缺失的仓库信息
            repos = self._get_repos_in_list_from_page(list_slug)
            for repo_full_name in repos:
                repo_to_list_map[repo_full_name] = list_name
        
        self.repo_list_mapping_cache = repo_to_list_map
        return self.repo_list_mapping_cache
