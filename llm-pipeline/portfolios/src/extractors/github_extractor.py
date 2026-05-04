import os
import requests
import re
import httpx
import base64
from typing import Optional, List, Dict
from .base import BaseExtractor

class GitHubExtractor(BaseExtractor):
    """
    Extractor for GitHub Repositories or User Profiles.
    Supports:
    1. Single Repository URL (fetches README)
    2. User URL or ID (fetches READMEs for all public repos)
    """

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        self.client = httpx.Client(headers=self.headers, timeout=10.0)

    def extract(self, source: str) -> str:
        """
        Extracts content from GitHub.
        Source can be:
        - Full URL: https://github.com/owner/repo
        - Owner/Repo: owner/repo
        - User URL: https://github.com/owner
        - Username: owner
        """
        
        # Check if it's a URL
        if "github.com/" in source:
            parts = source.split("github.com/")[-1].strip("/").split("/")
            if len(parts) == 2:
                # Repo URL
                owner, repo = parts[0], parts[1]
                return self._fetch_repo_readme(owner, repo)
            elif len(parts) == 1:
                # User URL
                user = parts[0]
                return self._fetch_user_readmes(user)
        
        # Process as string identifier
        if "/" in source:
            # Owner/Repo
            parts = source.split("/")
            return self._fetch_repo_readme(parts[0], parts[1])
        else:
            # Username
            return self._fetch_user_readmes(source)

    def _fetch_repo_readme(self, owner: str, repo: str) -> str:
        """Fetches README for a single repository."""
        # Try raw content first (no API limit)
        branches = ['main', 'master']
        for branch in branches:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            try:
                response = httpx.get(raw_url)
                if response.status_code == 200:
                    return f"# README for {owner}/{repo}\n\n{response.text}\n\n"
            except Exception:
                continue

        # Fallback to API if raw fails
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        try:
            response = self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                content = base64.b64decode(data['content']).decode('utf-8')
                return f"# README for {owner}/{repo}\n\n{content}\n\n"
        except Exception as e:
            print(f"Error fetching README for {owner}/{repo}: {e}")

        return f"Could not fetch README for {owner}/{repo}.\n\n"

    def _fetch_user_readmes(self, user_id: str) -> str:
        """Fetches READMEs for all public repositories of a user."""
        try:
            url = f"https://api.github.com/users/{user_id}/repos"
            params = {"type": "public", "per_page": 100}
            response = self.client.get(url, params=params)
            response.raise_for_status()
            
            repos = response.json()
            combined_content = f"# Portfolio for GitHub User: {user_id}\n\n"
            
            print(f"Found {len(repos)} repositories for user {user_id}.")

            for repo in repos:
                full_name = repo['full_name']
                # owner, name = full_name.split("/")
                repo_content = self._fetch_repo_readme(repo['owner']['login'], repo['name'])
                combined_content += f"{repo_content}\n---\n\n"
            
            return combined_content

        except Exception as e:
            return f"Error fetching repositories for user {user_id}: {e}"
