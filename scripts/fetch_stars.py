import os
import csv
from datetime import datetime
from collections import defaultdict
from gh_toolkit import GitHubManager

# 定义一个平台关键词配置，更易于维护和扩展
PLATFORM_KEYWORDS = {
    "iOS": {'ios', 'swift', 'swiftui', 'objective-c', 'flutter', 'dart', 'react-native'},
    "Android": {'android', 'kotlin', 'java', 'jetpack-compose', 'flutter', 'dart', 'react-native'},
    "Linux": {'linux', 'docker', 'kernel', 'ubuntu', 'debian', 'centos', 'arch'},
    "Windows": {'windows', 'wpf', '.net', 'winforms', 'c#'},
    "macOS": {'macos', 'cocoa', 'osx'},
    "Web": {'web', 'react', 'vue', 'angular', 'svelte', 'javascript', 'typescript', 'wasm'},
    "Backend": {'backend', 'server', 'api', 'go', 'golang', 'rust', 'python'}
}

# 避免一些过于通用的词产生误判
# 例如，我们不希望一个普通的 Java 库被标记为 "Android"
AMBIGUOUS_KEYWORDS = {
    "Android": {'java'} 
}

def process_and_enrich_data(manager: GitHubManager) -> list[dict]:
    """
    Processes raw repository data to add computed fields like 'platform'.
    This function takes the list of repos from the API and enriches it.
    """
    repo_to_list_map = manager.get_repo_list_mapping_hybrid()
    starred_repos = manager.get_starred_repos()

    enriched_data = []
    for repo in starred_repos:
        repo_copy = repo.copy()
        repo_full_name = repo.get('full_name')
        
        repo_copy['list_name'] = repo_to_list_map.get(repo_full_name, 'Uncategorized')
        language = repo.get('language') or "N/A"
        repo_copy['language'] = language

        analysis_tags = set([t.lower() for t in repo.get('topics', [])])
        analysis_tags.add(language.lower())

        os_tags = set()
        for platform, keywords in PLATFORM_KEYWORDS.items():
            # 检查关键词交集
            if not analysis_tags.isdisjoint(keywords):
                # 对模糊关键词进行二次判断
                ambiguous = AMBIGUOUS_KEYWORDS.get(platform, set())
                # 如果交集全都是模糊词，并且仓库描述中没有明确提示，则可以考虑跳过
                # (为简化，此处仅作基础交集判断)
                os_tags.add(platform)
        
        repo_copy['platform'] = ", ".join(sorted(list(os_tags))) if os_tags else "General"
        repo_copy['topics_str'] = ','.join(repo.get('topics', []))

        enriched_data.append(repo_copy)
        
    return enriched_data

def format_to_csv(data: list[dict], filename: str):
    """
    Formats the starred repository data into a CSV file.
    
    This function takes a list of repository data and writes it to a specified
    CSV file. Each repository becomes a row in the file.
    """
    if not data:
        print("No data to format into CSV.")
        return

    headers = ['full_name', 'list_name', 'description', 'language', 'platform', 'stars', 'url', 'topics_str']
    
    print(f"Generating CSV file: {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    print(f"Successfully generated CSV file: {filename}")

def format_to_markdown(data: list[dict], filename: str):
    """
    Formats the starred repository data into a single Markdown file.
    
    This creates a simple list of repositories without any grouping.
    """
    if not data:
        print("No data to format into Markdown.")
        return
    
    print(f"Generating Markdown file: {filename}...")
    grouped_repos = defaultdict(list)
    for repo in data:
        grouped_repos[repo['list_name']].append(repo)

    markdown_content = [
        f"---\n",
        "title: My Starred Repositories\n",
        "description: A curated list of my favorite repositories.\n",
        "---\n\n",
        "# 🌟 My Starred Repositories \n",
        f" > Update Time : {datetime.now().strftime('%Y-%m-%d')}\n"
        "A curated list of my starred repositories on GitHub, presented in a filterable table.\n",
    ]
    
    for list_name in sorted(grouped_repos.keys()):
        markdown_content.append(f"## 🗂️ {list_name}\n")
        markdown_content.append("| Repository | Description | Language | Platform | Stars |")
        markdown_content.append("|---|---|---|---|---|")
        repos_in_list = grouped_repos[list_name]

        for repo in repos_in_list:
            name_link = f"[{repo['full_name']}]({repo['url']})"
            description = (repo.get('description') or 'No description provided.').replace('\n', ' ').replace('\r', '').replace('|', '\\|')
            language = repo.get('language', 'N/A')
            platform = repo.get('platform', 'N/A')
            stars = repo.get('stars', 0)
            markdown_content.append(f"| {name_link} | {description} | {language} | {platform} | {stars} |")
        
        markdown_content.append("\n")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_content))

    print(f"Successfully generated Markdown file: {filename}")


def main():
    """
    Main function to orchestrate fetching starred repos and formatting them
    into CSV and Markdown files.
    """
    token = os.getenv("GH_TOKEN")
    if not token:
        raise ValueError("GitHub token not provided in GH_TOKEN env var.")

    manager = GitHubManager(token=token)
    
    print("Fetching all starred repositories...")

    enriched_data = process_and_enrich_data(manager)    

    if enriched_data:
        
        format_to_csv(enriched_data, "my-stars.csv")
        format_to_markdown(enriched_data, "my-stars.md")
        
        print("\nAll tasks completed successfully!")
    else:
        print("No starred repositories found.")

if __name__ == "__main__":
    main()
