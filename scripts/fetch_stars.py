import os
from github_toolkit import GitHubManager
from datetime import datetime

def main():
    token = os.getenv('GH_TOKEN')
    user_id = os.getenv("GH_USER_ID")
    if not token:
        raise ValueError("GitHub token not provided in GH_TOKEN env var.")

    manager = GitHubManager(token=token)

    print("Fetching starred repositories...")
    starred_repos = manager.get_starred_repos(user_id=user_id)
    print(f"Found {len(starred_repos)} starred repos.")

    print("\nCurrent lists:")
    all_lists = manager.get_lists()
    for l in all_lists:
        print(f"- {l['name']} ({l['description']})")

    # 用于存储Markdown内容的列表
    markdown_content = [
        f"# My Starred Repositories ({datetime.now().strftime('%Y-%m-%d')})\n",
        "A curated list of my starred repositories on GitHub.\n"
        ]

    # 分析和格式化每个仓库
    for repo in starred_repos:
         # 1. 名称
        name = f"[{repo.full_name}]({repo.url})"
        
        # 2. 功能描述
        description = repo.description or "No description provided."
        
        # 3. 主要语言
        language = repo.language or "N/A"
        
        # 4. 适合的系统（这是一个推断性分析，可以根据关键词或topic来判断）
        # 这是一个简化的例子，您可以根据需要扩展这个逻辑
        topics = repo.topics or []
        os_tags = []
        if any(t in ['ios', 'swift', 'objective-c'] for t in topics):
            os_tags.append("iOS")
        if any(t in ['android', 'kotlin', 'java'] for t in topics if 'javascript' not in t):
            os_tags.append("Android")
        if any(t in ['linux', 'docker', 'kernel'] for t in topics):
            os_tags.append("Linux")
        if any(t in ['windows', 'wpf', '.net'] for t in topics):
            os_tags.append("Windows")
        if any(t in ['web', 'react', 'vue', 'angular'] for t in topics):
            os_tags.append("Web")
        
        os_compatibility = ", ".join(os_tags) if os_tags else "General"

        # 组合成Markdown格式
        markdown_content.append(f"## {name}\n")
        markdown_content.append(f"> {description}\n")
        markdown_content.append(f"- **Language:** {language}")
        markdown_content.append(f"- **Platform:** {os_compatibility}")
        markdown_content.append(f"- **Stars:** {repo.stars}\n")

    # 将内容写入文件
    with open("my-stars.md", "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_content))

    print("Successfully generated my-stars.md")



if __name__ == "__main__":
    main()