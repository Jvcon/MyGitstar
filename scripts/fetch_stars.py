import os
import csv
from collections import defaultdict
from gh_toolkit import GitHubManager
from datetime import datetime

def format_to_csv(data: list[dict], filename: str):
    """
    Formats the repository data into a CSV file.
    """
    if not data:
        print("No data to format into CSV.")
        return

    # 包含新的 'list_name' 字段
    headers = ['full_name', 'list_name', 'description', 'language', 'stars', 'url']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
        
    print(f"Successfully generated CSV file: {filename}")

def format_to_markdown(data: list[dict], filename: str):
    """
    Formats the repository data into a Markdown file,
    grouped by list name.
    """
    if not data:
        print("No data to format into Markdown.")
        return
        
    # 按 list_name 进行分组
    grouped_repos = defaultdict(list)
    for repo in data:
        grouped_repos[repo['list_name']].append(repo)

    markdown_content = [
        f"# My Starred Repositories ({datetime.now().strftime('%Y-%m-%d')})\n"
    ]
    
    # 按照 List 名称排序，让输出更稳定
    for list_name in sorted(grouped_repos.keys()):
        markdown_content.append(f"## 🗂️ {list_name}\n")
        
        # 添加 Markdown 表格头
        markdown_content.append("| Repository | Description | Language | Stars |")
        markdown_content.append("|---|---|---|---|")
        
        repos_in_list = grouped_repos[list_name]
        for repo in repos_in_list:
            # 清理描述中的换行符和管道符，避免破坏表格
            description = (repo.get('description') or '').replace('\n', ' ').replace('\r', '').replace('|', '\|')
            name_link = f"[{repo['full_name']}]({repo['url']})"
            language = repo.get('language', 'N/A')
            stars = repo.get('stars', 0)
            
            markdown_content.append(f"| {name_link} | {description} | {language} | {stars} |")
        
        markdown_content.append("\n") # 在每个表格后增加一个空行

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_content))

    print(f"Successfully generated Markdown file: {filename}")

def main():
    token = os.getenv('GH_TOKEN')
    if not token:
        raise ValueError("GitHub token not provided in GH_TOKEN env var.")

    manager = GitHubManager(token=token)
    
    data = manager.get_starred_repos()
    
    if data:
        print("\nFormatting data into different formats...")
        format_to_csv(data, "my-stars.csv")
        format_to_markdown(data, "my-stars.md")
    else:
        print("No starred repositories found.")



if __name__ == "__main__":
    main()