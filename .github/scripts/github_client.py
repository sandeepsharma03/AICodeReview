"""
GitHub API Client
Handles interactions with GitHub API for PR operations.
"""

import os
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FileChange:
    """Represents a file change in a PR."""
    filename: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str]
    language: str


@dataclass
class PullRequest:
    """Represents a pull request."""
    number: int
    title: str
    body: str
    base_sha: str
    head_sha: str
    base_branch: str
    head_branch: str


class GitHubClient:
    """Client for GitHub API interactions."""
    
    def __init__(self, token: str, repo_owner: str, repo_name: str, api_base_url: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub API token
            repo_owner: Repository owner/organization
            repo_name: Repository name
            api_base_url: GitHub API base URL (defaults to env var or GHE instance)
        """
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        # Allow API base URL to be configurable via environment or parameter
        self.api_base_url = api_base_url or os.environ.get("GITHUB_API_URL", "https://api.github.com")
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Code-Reviewer"
        }
    
    def get_pull_request(self, pr_number: int) -> PullRequest:
        """
        Get pull request details.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            PullRequest object
        """
        url = f"{self.api_base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return PullRequest(
            number=pr_number,
            title=data["title"],
            body=data.get("body", ""),
            base_sha=data["base"]["sha"],
            head_sha=data["head"]["sha"],
            base_branch=data["base"]["ref"],
            head_branch=data["head"]["ref"]
        )
    
    def get_pr_files(self, pr_number: int) -> List[FileChange]:
        """
        Get list of changed files in a PR.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            List of FileChange objects
        """
        url = f"{self.api_base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}/files"
        
        files = []
        page = 1
        per_page = 100
        
        while True:
            response = requests.get(
                url,
                headers=self.headers,
                params={"page": page, "per_page": per_page},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if not data:
                break
            
            for file_data in data:
                language = self._detect_language(file_data["filename"])
                file_change = FileChange(
                    filename=file_data["filename"],
                    status=file_data["status"],
                    additions=file_data["additions"],
                    deletions=file_data["deletions"],
                    changes=file_data["changes"],
                    patch=file_data.get("patch"),
                    language=language
                )
                files.append(file_change)
            
            if len(data) < per_page:
                break
            
            page += 1
        
        return files
    
    def get_file_content(self, file_path: str, ref: str) -> str:
        """
        Get content of a file at a specific commit.
        
        Args:
            file_path: Path to the file
            ref: Git reference (commit SHA, branch, tag)
            
        Returns:
            File content as string
        """
        url = f"{self.api_base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
        response = requests.get(
            url,
            headers=self.headers,
            params={"ref": ref},
            timeout=10
        )
        
        if response.status_code == 404:
            return ""
        
        response.raise_for_status()
        data = response.json()
        
        # Decode base64 content
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content
    
    def create_review_comment(
        self,
        pr_number: int,
        commit_id: str,
        body: str,
        path: str,
        line: Optional[int] = None
    ) -> Dict:
        """
        Create a review comment on a specific line.
        
        Args:
            pr_number: Pull request number
            commit_id: Commit SHA
            body: Comment body
            path: File path
            line: Line number (optional)
            
        Returns:
            API response
        """
        url = f"{self.api_base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}/comments"
        
        payload = {
            "body": body,
            "commit_id": commit_id,
            "path": path
        }
        
        if line:
            payload["line"] = line
            payload["side"] = "RIGHT"
        
        response = requests.post(url, headers=self.headers, json=payload, timeout=10)
        
        if response.status_code not in [200, 201]:
            error_msg = f"Failed to create comment: {response.status_code} - {response.text}"
            print(error_msg)
            response.raise_for_status()  # Raise HTTPError
        
        return response.json()
    
    def create_review(
        self,
        pr_number: int,
        commit_id: str,
        body: str,
        event: str = "COMMENT",
        comments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create a review on the PR.
        
        Args:
            pr_number: Pull request number
            commit_id: Commit SHA
            body: Review body
            event: Review event (APPROVE, REQUEST_CHANGES, COMMENT)
            comments: List of inline comments
            
        Returns:
            API response
        """
        url = f"{self.api_base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}/reviews"
        
        payload = {
            "commit_id": commit_id,
            "body": body,
            "event": event
        }
        
        if comments:
            payload["comments"] = comments
        
        response = requests.post(url, headers=self.headers, json=payload, timeout=10)
        
        if response.status_code not in [200, 201]:
            error_msg = f"Failed to create review: {response.status_code} - {response.text}"
            print(error_msg)
            response.raise_for_status()  # Raise HTTPError
        
        return response.json()
    
    def create_issue_comment(self, pr_number: int, body: str) -> Dict:
        """
        Create a general comment on the PR.
        
        Args:
            pr_number: Pull request number
            body: Comment body
            
        Returns:
            API response
        """
        url = f"{self.api_base_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{pr_number}/comments"
        
        payload = {"body": body}
        response = requests.post(url, headers=self.headers, json=payload, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename."""
        extension_map = {
            ".java": "java",
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".xml": "xml",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".properties": "properties",
            ".json": "json",
            ".sh": "bash",
            ".sql": "sql",
            ".html": "html",
            ".css": "css"
        }
        
        for ext, lang in extension_map.items():
            if filename.endswith(ext):
                return lang
        
        return "unknown"
