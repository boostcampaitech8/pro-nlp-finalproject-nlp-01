import os
import httpx
import base64
from typing import Optional
import logging
from .base import BaseExtractor
from common.config import settings

logger = logging.getLogger(__name__)

class GitHubExtractor(BaseExtractor):
    """
    Extractor for GitHub Repositories or User Profiles.
    Supports:
    1. Single Repository URL (fetches README)
    2. User URL or ID (fetches READMEs for all public repos)
    """

    def __init__(self):
        self.github_token = settings.GITHUB_TOKEN
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
        text_content = ""
        branches = ['main', 'master', 'develop']
        base_url_for_images = ""
        
        for branch in branches:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            try:
                response = httpx.get(raw_url)
                if response.status_code == 200:
                    text_content = response.text
                    base_url_for_images = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"
                    break
            except Exception:
                continue

        # Fallback to API
        if not text_content:
            url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    text_content = base64.b64decode(data['content']).decode('utf-8')
                    # API result doesn't give easy base url for relative images, 
                    # but usually it's default branch. Let's try main/master logic for images later.
                    base_url_for_images = f"https://raw.githubusercontent.com/{owner}/{repo}/main/" 
            except Exception as e:
                logger.error(f"Error fetching README for {owner}/{repo}: {e}")

        if text_content:
            # Run OCR on images found in README
            ocr_content = self._process_images_in_markdown(text_content, base_url_for_images)
            return f"# README for {owner}/{repo}\n\n{text_content}\n\n{ocr_content}\n\n"

        return f"Could not fetch README for {owner}/{repo}.\n\n"

    def _process_images_in_markdown(self, markdown_text: str, base_url: str) -> str:
        """Finds images in markdown, downloads them, and runs OCR."""
        import re
        from .google_vision_extractor import GoogleVisionExtractor

        vision = GoogleVisionExtractor()
        ocr_results = []
        
        # 1. Regex for Markdown images: ![alt](url)
        md_images = re.findall(r'!\[.*?\]\((.*?)\)', markdown_text)
        
        # 2. Regex for HTML images: <img src="url">
        html_images = re.findall(r'<img.*?src=["\'](.*?)["\']', markdown_text)
        
        all_images = list(set(md_images + html_images))
        
        # Limit to avoid processing too many (e.g., badges)
        # Filter for likely content images (png, jpg, jpeg) and ignore common badges (shields.io)
        valid_images = [
            img for img in all_images 
            if not "shields.io" in img and not "badge" in img
            and any(ext in img.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp'])
        ][:5] # Max 5 images to prevent timeout
        
        for img_url in valid_images:
            # Handle relative URLs
            if not img_url.startswith("http"):
                # Clean path (./assets/img.png -> assets/img.png)
                clean_path = img_url.lstrip("./")
                full_url = f"{base_url}{clean_path}"
            else:
                full_url = img_url
            
            try:
                # Download image
                # Use longer timeout for images
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(full_url)
                    if resp.status_code == 200:
                        img_bytes = resp.content
                        if len(img_bytes) < 5000: continue # Skip tiny icons (< 5KB)

                        ocr_text = vision.extract_bytes(img_bytes)
                        if ocr_text:
                            ocr_results.append(f"[Image OCR ({img_url})]:\n{ocr_text}")
            except Exception as e:
                logger.warning(f"Failed to process image {full_url}: {e}")
                continue
                
        return "\n\n".join(ocr_results)

    def _fetch_user_readmes(self, user_id: str) -> str:
        """Fetches READMEs for all public repositories of a user."""
        try:
            url = f"https://api.github.com/users/{user_id}/repos"
            params = {"type": "public", "per_page": 100}
            response = self.client.get(url, params=params)
            response.raise_for_status()
            
            repos = response.json()
            combined_content = f"# Portfolio for GitHub User: {user_id}\n\n"
            
            logger.info(f"Found {len(repos)} repositories for user {user_id}.")

            for repo in repos:
                # owner, name = full_name.split("/")
                repo_content = self._fetch_repo_readme(repo['owner']['login'], repo['name'])
                combined_content += f"{repo_content}\n---\n\n"
            
            return combined_content

        except Exception as e:
            return f"Error fetching repositories for user {user_id}: {e}"
