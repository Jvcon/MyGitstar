import requests

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

    def __init__(self, token: str):
        if not token:
            raise ValueError("GitHub token cannot be empty.")
            
        self._headers = {
            "Authorization": f"bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.session = requests.Session()
        self.session.headers.update(self._headers)

    def _execute_graphql(self, query: str, variables: dict = None) -> dict:
        """Helper function to execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        response = self.session.post(self._GRAPHQL_API_URL, json=payload)
        
        if response.status_code != 200:
            raise GitHubAPIError(f"GraphQL query failed.", status_code=response.status_code, errors=response.text)
            
        data = response.json()
        if "errors" in data:
            raise GitHubAPIError("GraphQL query returned errors.", errors=data["errors"])
            
        return data.get("data", {})

    _authenticated_user_id = None

    # --- REST API Methods for Stars and Repos ---

    def get_authenticated_user_id(self) -> str:
        """
        Fetches and returns the user ID (login) of the authenticated user.
        Caches the result to avoid repeated API calls.
        """
        if self._authenticated_user_id:
            return self._authenticated_user_id
            
        url = f"{self._REST_API_URL}/user"
        response = self.session.get(url)
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
            response = self.session.get(url, params=params)
            response.raise_for_status() # Raises an HTTPError for bad responses
            
            data = response.json()
            if not data:
                break
            
            for item in data:
                repo_info = item.get('repo', {})
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
        response = self.session.put(url)
        return response.status_code == 204

    def unstar_repo(self, owner: str, repo: str) -> bool:
        """Unstars a repository for the authenticated user."""
        url = f"{self._REST_API_URL}/user/starred/{owner}/{repo}"
        response = self.session.delete(url)
        return response.status_code == 204

    # --- GraphQL API Methods for Lists ---

    def get_repo_list_mapping(self) -> dict[str, str]:
        """
        Fetches all user lists and the repositories within them,
        then returns a mapping from a repo's full name to its list's name.

        Returns:
            A dictionary like: {'user/repo1': 'List A', 'user/repo2': 'List B'}
        """
        repo_to_list_map = {}
        query = """
        query GetListsWithRepos($cursor: String) {
          viewer {
            lists(first: 20, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                name
                entries(first: 100) { # Assuming a list won't have more than 100 repos
                  nodes {
                    ... on Repository {
                      nameWithOwner
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        has_next_page = True
        cursor = None
        
        print("Building repository-to-list mapping...")
        while has_next_page:
            variables = {"cursor": cursor}
            data = self._execute_graphql(query, variables)
            
            lists_data = data.get("viewer", {}).get("lists", {})
            for list_node in lists_data.get("nodes", []):
                list_name = list_node.get("name")
                for entry_node in list_node.get("entries", {}).get("nodes", []):
                    if repo_name := entry_node.get("nameWithOwner"):
                        repo_to_list_map[repo_name] = list_name
            
            page_info = lists_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        print("Mapping built successfully.")
        return repo_to_list_map

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
        return data.get("viewer", {}).get("lists", {}).get("nodes", [])

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
