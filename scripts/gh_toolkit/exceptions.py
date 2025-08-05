class GitHubToolkitError(Exception):
    """Base exception for the GitHub Toolkit library."""
    pass

class GitHubAPIError(GitHubToolkitError):
    """Raised when a GitHub API call fails."""
    def __init__(self, message, status_code=None, errors=None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors

    def __str__(self):
        if self.errors:
            return f"GitHubAPIError: {self.message} (Status: {self.status_code}, Errors: {self.errors})"
        return f"GitHubAPIError: {self.message} (Status: {self.status_code})"
