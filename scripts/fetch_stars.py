import os
import csv
import json
from datetime import datetime
from collections import defaultdict
from gh_toolkit import GitHubManager
from utils.data_loader import load_dict_fr_txt,get_filtered

# 定义一个平台关键词配置，更易于维护和扩展
PLATFORM_MAPPING = {
    "Windows": {
        'keywords': {'windows', 'win32', 'win64', 'wpf', 'winforms', 'winui', 'uwp'},
        'languages': {'c#', 'visual basic .net'}
    },
    "macOS": {
        'keywords': {'macos', 'osx', 'mac', 'cocoa', 'mac-app-store'},
        'languages': {'swift', 'objective-c'}
    },
    "Linux": {
        'keywords': {'linux', 'ubuntu', 'debian', 'fedora', 'arch', 'centos', 'gnome', 'kde'},
        'languages': {} 
    },
     "iOS": {
        'keywords': {'ios', 'iphone', 'ipad', 'swiftui', 'uikit'},
        'languages': {'swift', 'objective-c'}
    },
    "Android": {
        'keywords': {'android', 'jetpack-compose', 'wear-os'},
        'languages': {'kotlin', 'java'} 
    },
    "Web": {
        'keywords': {
            'web', 'website', 'webapp', 'web-app', 'backend', 'server', 'api', 'rest-api', 
            'frontend', 'react', 'vue', 'angular', 'svelte', 'django', 'flask', 'fastapi',
            'rails', 'asp.net', 'nodejs', 'express', 'nginx', 'apache', 'serverless', 'lambda'
        },
        'languages': {'javascript', 'typescript', 'php', 'ruby', 'go'}
    },
    "Cross-platform": {
        'keywords': {'cross-platform', 'electron', 'react-native', 'flutter', 'maui', 'xamarin', 'qt', 'ionic'},
        'languages': {'dart'}
    }
}

CROSS_PLATFORM_TARGETS = {
    'electron': {'Windows', 'macOS', 'Linux'},
    'react-native': {'iOS', 'Android'},
    'flutter': {'iOS', 'Android', 'Windows', 'macOS', 'Linux', 'Web'},
    'dart': {'iOS', 'Android', 'Windows', 'macOS', 'Linux', 'Web'},
    'maui': {'iOS', 'Android', 'Windows', 'macOS'},
    'xamarin': {'iOS', 'Android', 'Windows'},
    'qt': {'Windows', 'macOS', 'Linux'},
    'ionic': {'iOS', 'Android', 'Web'}
}

def analyze_platform_from_repo(repo: dict) -> list[str]:
    """
    Analyzes a repository's topics, description, and language to determine its platform(s).
    This function uses a structured mapping inspired by AlternativeTo.net's categorization.
    
    Args:
        repo: A dictionary representing a single repository from the GitHub API.

    Returns:
        A string of comma-separated platform names.
    """
    # 1. Aggregate all text sources for analysis
    language = (repo.get('language') or "").lower()
    topics = {t.lower() for t in repo.get('topics', [])}
    description_text = (repo.get('description') or "").lower()
    
    # Combine topics and language into a single set of tags for efficient lookup
    analysis_tags = topics.union({language})

    # Also create a combined string for regex-based keyword searching in the description
    full_text = " ".join(list(topics)) + " " + description_text

    detected_platforms = set()

    # 2. Check for Cross-Platform technologies first
    cross_platform_tech_found = set()
    for tech, targets in CROSS_PLATFORM_TARGETS.items():
        if tech in analysis_tags or tech in full_text:
            detected_platforms.update(targets)
            cross_platform_tech_found.add(tech)

    # 3. Check for native platforms
    for platform, data in PLATFORM_MAPPING.items():
        if platform == "Cross-platform":
            continue

        # Check keywords and languages
        if not analysis_tags.isdisjoint(data['keywords']) or language in data['languages']:
            # Special handling for ambiguous 'java'
            if platform == 'Android' and language == 'java' and not any(kw in analysis_tags for kw in ['android', 'jetpack-compose']):
                # If language is Java but no other Android keyword is present, be cautious.
                # We can add more logic here, e.g., checking description for 'android app'. For now, we skip if ambiguous.
                if 'android' not in full_text:
                    continue
            
            detected_platforms.add(platform)

    # 4. Final Cleanup and Formatting
    if not detected_platforms:
        # If no specific platform is detected, but it's a known backend language/framework, classify as Web.
        if not analysis_tags.isdisjoint(PLATFORM_MAPPING['Web']['keywords']):
             detected_platforms.add('Web')
        elif cross_platform_tech_found:
             # Already handled by the initial update
             pass
        else:
            return ["General"]

    return sorted(list(detected_platforms))

def fetch_and_process_all_data(manager: GitHubManager) -> tuple[list[dict],list[dict]]:
    """
    Processes raw repository data to add computed fields like 'platform'.
    This function takes the list of repos from the API and enriches it.
    """
    collections = get_filtered(manager.get_lists(),load_dict_fr_txt("../data/.listignore"),"name")
    repo_to_list_map = manager.get_repo_list_mapping_hybrid()
    starred_repos = get_filtered(manager.get_starred_repos(),load_dict_fr_txt("../data/.repoignore"),"full_name")

    enriched_data = []
    for repo in starred_repos:
        repo_copy = repo.copy()
        repo_full_name = repo.get('full_name')
        
        repo_copy['list_name'] = repo_to_list_map.get(repo_full_name, 'Uncategorized')
        language = repo.get('language') or "N/A"
        repo_copy['language'] = language
        
        repo_copy['platform'] = analyze_platform_from_repo(repo)
        repo_copy['topics'] = repo.get('topics', [])

        enriched_data.append(repo_copy)
        
    return enriched_data, collections

def format_to_csv(data: list[dict], filename: str):
    """
    Formats the starred repository data into a CSV file.
    
    This function takes a list of repository data and writes it to a specified
    CSV file. Each repository becomes a row in the file.
    """
    if not data:
        print("No data to format into CSV.")
        return

    headers = ['full_name', 'list_name', 'description', 'language', 'platform', 'stars', 'url', 'topics']
    processed_data = []
    for repo in data:
        repo_copy = repo.copy()
        if isinstance(repo_copy.get('platform'), list):
                    repo_copy['platform'] = ', '.join(repo_copy['platform'])
        if isinstance(repo_copy.get('topics'), list):
            repo_copy['topics'] = ', '.join(repo_copy['topics'])
        processed_data.append(repo_copy)
    print(f"Generating CSV file: {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(processed_data)
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
            stars = repo.get('stars', 0)
            platform = repo.get('platform',[])
            platform_str = ', '.join(platform) if isinstance(platform, list) else (platform or 'N/A')
            markdown_content.append(f"| {name_link} | {description} | {language} | {platform_str} | {stars} |")
        
        markdown_content.append("\n")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_content))

    print(f"Successfully generated Markdown file: {filename}")

def format_to_json(data: list[dict], filename: str):
    """
    Formats the starred repository data into a single JSON file.
    
    This function takes a list of repository data and writes it to a specified
    JSON file, suitable for consumption by web frontends like Astro.
    """
    if not data:
        print("No data to format into JSON.")
        return

    print(f"Generating JSON file: {filename}...")
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=2)
    print(f"Successfully generated JSON file: {filename}")

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

    enriched_repo_data,collections_data = fetch_and_process_all_data(manager)    

    output_dir = "dist"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    if enriched_repo_data:
        print("\n[Step 1/2] Formatting and writing repository data files...")
        format_to_csv(enriched_repo_data, os.path.join(output_dir, "repos.csv"))
        format_to_markdown(enriched_repo_data, os.path.join(output_dir, "starred-repos.md"))
        format_to_json(enriched_repo_data, os.path.join(output_dir, "repos.json"))
    else:
        print("\n[Step 1/2] No starred repositories found to process.")

    if collections_data:
        print("\n[Step 2/2] Formatting and writing collection data file (list.json)...")
        format_to_json(collections_data, os.path.join(output_dir, "collections.json"))
    else:
        print("\n[Step 2/2] No collections (lists) found to process.")
        
if __name__ == "__main__":
    main()
