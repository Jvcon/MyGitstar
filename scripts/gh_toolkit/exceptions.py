class GitHubToolkitError(Exception):
    """Base exception for the GitHub Toolkit library."""
    pass

class GitHubAPIError(GitHubToolkitError):
    """Raised when a GitHub API call fails."""
    def __init__(self, message, status_code=None, errors=None):
        # 将错误详情整合到主消息中，使其更易于阅读
        full_message = f"{message}"
        if status_code:
            full_message += f" (Status: {status_code})"
        if errors:
            # 将 errors (可能是列表或字典) 转换为格式化的 JSON 字符串
            import json
            try:
                error_details = json.dumps(errors, indent=2)
                full_message += f"\n--- GitHub API Errors ---\n{error_details}"
            except TypeError:
                full_message += f"\n--- GitHub API Errors (raw) ---\n{errors}"
        
        super().__init__(full_message)
        self.status_code = status_code
        self.errors = errors