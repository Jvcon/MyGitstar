import os
from github import Github
from datetime import datetime

# 从环境变量中获取 GitHub Token
token = os.getenv('GH_TOKEN')
if not token:
    raise ValueError("GitHub token not provided in GH_TOKEN env var.")

g = Github(token)
user = g.get_user()

# 获取所有加星的仓库（这是一个分页对象，PyGithub会自动处理分页）
starred_repos = user.get_starred()

# 用于存储Markdown内容的列表
markdown_content = [
    f"# My Starred Repositories ({datetime.now().strftime('%Y-%m-%d')})\n",
    "A curated list of my starred repositories on GitHub.\n"
]

# 分析和格式化每个仓库
for repo in starred_repos:
    # 1. 名称
    name = f"[{repo.full_name}]({repo.html_url})"
    
    # 2. 功能描述
    description = repo.description or "No description provided."
    
    # 3. 主要语言
    language = repo.language or "N/A"
    
    # 4. 适合的系统（这是一个推断性分析，可以根据关键词或topic来判断）
    # 这是一个简化的例子，您可以根据需要扩展这个逻辑
    topics = repo.get_topics()
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
    markdown_content.append(f"- **Stars:** {repo.stargazers_count}\n")

# 将内容写入文件
with open("my-stars.md", "w", encoding="utf-8") as f:
    f.write("\n".join(markdown_content))

print("Successfully generated my-stars.md")
