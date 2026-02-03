
import os
import httpx
import base64
import logging
from typing import Optional, List, Dict
from .base import BaseExtractor
from common.config import settings

logger = logging.getLogger(__name__)

class GitHubExtractor(BaseExtractor):
    """
    Extractor for GitHub Repositories or User Profiles.
    Enhanced with Gitingest for deep code analysis.
    """

    def __init__(self, token: Optional[str] = None):
        self.github_token = token or settings.GH_API_TOKEN
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
            logger.info("GitHub API: Using authenticated requests")
        else:
            logger.warning("GitHub API: No token provided, using unauthenticated requests (rate limited to 60/hour)")
        self.client = httpx.Client(headers=self.headers, timeout=10.0)

    def extract(self, source: str, token: Optional[str] = None) -> str:
        """
        Legacy support: returns a single combined string.
        """
        if token:
            self.__init__(token) # Refresh with user token
        results = self.extract_multi(source)
        combined = ""
        for res in results:
            combined += f"{res['content']}\n\n---\n\n"
        return combined

    def extract_multi(self, source: str, token: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Extracts multiple projects/repositories.
        Returns: List of {"title": str, "content": str, "url": str}
        """
        if token:
            self.__init__(token)
        source = source.strip()
        
        # 1. URL Case
        if "github.com/" in source:
            parts = source.split("github.com/")[-1].strip("/").split("/")
            if len(parts) >= 2:
                # Repo URL
                owner, repo = parts[0], parts[1]
                content = self._fetch_repo_deep(owner, repo)
                return [{"title": f"{owner}/{repo}", "content": content, "url": source}]
            elif len(parts) == 1:
                # User URL
                return self._fetch_user_repos(parts[0])
        
        # 2. String identifier
        if "/" in source:
            parts = source.split("/")
            content = self._fetch_repo_deep(parts[0], parts[1])
            return [{"title": source, "content": content, "url": f"https://github.com/{source}"}]
        else:
            return self._fetch_user_repos(source)

    def _fetch_repo_deep(self, owner: str, repo: str) -> str:
        """
        Fetches README and deep code summary using Gitingest.
        Enforces a 10KB budget for cost efficiency.
        """
        logger.info(f"Deep fetching repo: {owner}/{repo}")
        
        # 1. Fetch README first (as it's often the best summary)
        readme = self._fetch_repo_readme(owner, repo)
        
        # 2. Try Gitingest for code analysis (Low-cost mode)
        code_summary = ""
        try:
            from gitingest import ingest
            # Aggressive exclusion for cost saving
            exclude_patterns = [
                "node_modules", "venv", "env", "dist", "build", "target",
                "*.lock", "*.log", "*.svg", "*.png", "*.jpg", "*.jpeg", "*.pdf",
                "test", "tests", "spec", "*.test.*", "*.spec.*",
                ".git", ".github", ".vscode", ".idea"
            ]
            
            # ingest(url, max_size=..., exclude_patterns=...)
            ingest_url = f"https://github.com/{owner}/{repo}"
            if self.github_token:
                # Gitingest might support token directly or via URL. 
                # Assuming it needs token for private repo if passed in URL or if it uses env (it doesn't seem to have a token param in API)
                # Let's use the token in URL if possible, or just depend on the fact that if it's private, 
                # we might need to handle it differently.
                # Actually, many libraries use GITHUB_TOKEN env.
                os.environ["GITHUB_TOKEN"] = self.github_token
            
            res_summary, res_tree, res_content = ingest(
                ingest_url,
                max_file_size=10240, # 10KB Limit for cost efficiency
                exclude_patterns=exclude_patterns
            )
            
            code_summary = f"\n### File Structure\n{res_tree}\n\n### Core Snippets\n{res_content}"
            
        except Exception as e:
            logger.warning(f"Gitingest failed for {owner}/{repo}: {e}. Falling back to README only.")
            code_summary = "\n(Source code analysis failed or skipped)"

        return f"# {owner}/{repo}\n\n{readme}\n\n## Deep Code Analysis (10KB Limit)\n{code_summary}"

    def _fetch_repo_readme(self, owner: str, repo: str) -> str:
        """Original README fetching logic with image OCR."""
        text_content = ""
        branches = ['main', 'master', 'develop']
        base_url_for_images = ""
        
        for branch in branches:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            try:
                response = httpx.get(raw_url, timeout=5.0)
                if response.status_code == 200:
                    text_content = response.text
                    base_url_for_images = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"
                    break
            except Exception:
                continue

        if not text_content:
            url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    text_content = base64.b64decode(data['content']).decode('utf-8')
                    base_url_for_images = f"https://raw.githubusercontent.com/{owner}/{repo}/main/" 
            except Exception:
                pass

        if text_content:
            ocr_content = self._process_images_in_markdown(text_content, base_url_for_images)
            return f"## README\n\n{text_content}\n\n{ocr_content}"

        return "No README found."

    def _process_images_in_markdown(self, markdown_text: str, base_url: str) -> str:
        """Same as original, but kept for integration."""
        import re
        from .google_vision_extractor import GoogleVisionExtractor

        vision = GoogleVisionExtractor()
        ocr_results = []
        md_images = re.findall(r'!\[.*?\]\((.*?)\)', markdown_text)
        html_images = re.findall(r'<img.*?src=["\'](.*?)["\']', markdown_text)
        all_images = list(set(md_images + html_images))
        
        valid_images = [img for img in all_images if any(ext in img.lower() for ext in ['.png', '.jpg', '.jpeg'])][:3]
        
        for img_url in valid_images:
            url = f"{base_url}{img_url.lstrip('./')}" if not img_url.startswith("http") else img_url
            try:
                resp = httpx.get(url, timeout=5.0)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    text = vision.extract_bytes(resp.content)
                    if text: ocr_results.append(f"[OCR: {img_url}]: {text}")
            except Exception: continue
        return "\n".join(ocr_results)

    def _fetch_user_repos(self, user_id: str) -> List[Dict[str, str]]:
        """
        Fetches up to 5 most active/recent public repos for a user.
        Uses unauthenticated API to avoid token issues for public repos.
        """
        logger.info(f"Fetching public repos for user: {user_id} (without authentication)")
        
        try:
            # Use unauthenticated client for public repos
            headers = {"Accept": "application/vnd.github.v3+json"}
            unauthenticated_client = httpx.Client(headers=headers, timeout=10.0)
            
            url = f"https://api.github.com/users/{user_id}/repos"
            params = {"type": "public", "sort": "pushed", "direction": "desc", "per_page": 5}
            
            response = unauthenticated_client.get(url, params=params)
            response.raise_for_status()
            
            repos = response.json()
            results = []
            for repo in repos:
                content = self._fetch_repo_deep_unauthenticated(user_id, repo['name'], unauthenticated_client)
                results.append({
                    "title": f"{user_id}/{repo['name']}",
                    "content": content,
                    "url": repo['html_url']
                })
            
            unauthenticated_client.close()
            logger.info(f"Successfully fetched {len(results)} public repos")
            return results
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"GitHub user '{user_id}' not found")
                raise ValueError(f"GitHub 사용자 '{user_id}'를 찾을 수 없습니다.")
            else:
                logger.error(f"GitHub API error: {e}")
                raise ValueError(f"GitHub API 오류: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching user repos: {e}")
            return []

    
    def _fetch_repo_deep_unauthenticated(self, owner: str, repo: str, client: httpx.Client) -> str:
        """Fetch repo content without authentication (for public repos only)."""
        logger.info(f"Fetching repo (unauthenticated): {owner}/{repo}")
        
        # 1. Fetch README
        readme = ""
        try:
            readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            resp = client.get(readme_url)
            if resp.status_code == 200:
                data = resp.json()
                import base64
                readme = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Could not fetch README: {e}")
        
        # 2. Try Gitingest (same as authenticated version)
        code_summary = ""
        try:
            from gitingest import ingest
            exclude_patterns = [
                "node_modules", "venv", "env", "dist", "build", "target",
                "*.lock", "*.log", "*.svg", "*.png", "*.jpg", "*.jpeg", "*.pdf",
                "test", "tests", "spec", "*.test.*", "*.spec.*",
                ".git", ".github", ".vscode", ".idea"
            ]
            
            ingest_url = f"https://github.com/{owner}/{repo}"
            summary, tree, content = ingest(
                ingest_url,
                max_file_size=10_000,
                include_patterns=None,
                exclude_patterns=exclude_patterns
            )
            code_summary = content[:10_000]
        except Exception as e:
            logger.warning(f"Gitingest failed (unauthenticated): {e}")
        
        combined = f"# {owner}/{repo}\n\n"
        if readme:
            combined += f"## README\n{readme[:5000]}\n\n"
        if code_summary:
            combined += f"## Code Summary\n{code_summary}\n"
        
        return combined if combined.strip() else f"Repository: {owner}/{repo} (No content available)"

