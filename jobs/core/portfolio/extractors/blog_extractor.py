
import httpx
import logging
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import BaseExtractor

logger = logging.getLogger(__name__)

class BlogExtractor(BaseExtractor):
    def __init__(self):
        self.timeout = 20.0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def extract(self, url: str) -> str:
        """
        BaseExtractor interface usually returns a single string.
        But for our new batch logic, we might call this differently.
        For now, let's implement a method that returns a list of posts.
        """
        if "velog.io" in url:
            return await self._extract_velog(url)
        elif "tistory.com" in url:
            return await self._extract_tistory(url)
        else:
            # Fallback to general HTML extraction
            return await self._extract_general(url)

    async def extract_multi(self, url: str) -> List[Dict[str, str]]:
        """
        Extract multiple posts if the URL is a profile/index page.
        Returns: List of {"title": str, "content": str, "url": str}
        """
        # For MVC, we focus on extracting the main content of the provided URL.
        # If it's a list page, we could crawl, but let's start with single page or top post.
        content = await self.extract(url)
        return [{"title": "Blog Post", "content": content, "url": url}]

    async def _extract_velog(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Velog specific: usually the content is in a specific div
                # Look for the main article content
                content_div = soup.find("div", {"class": "atom-one-light"}) or \
                              soup.find("div", {"id": "root"}) # Fallback
                
                if content_div:
                    # Remove unwanted elements (scripts, styles, nav)
                    for tag in content_div.find_all(["script", "style", "nav", "header", "footer"]):
                        tag.decompose()
                    return content_div.get_text(separator="\n", strip=True)
                
                return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            logger.error(f"Error extracting Velog: {e}")
            return f"Error extracting Velog content: {str(e)}"

    async def _extract_tistory(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Tistory specific: content is usually in .entry-content or .tt_article_usr
                content_div = soup.select_one(".entry-content") or \
                              soup.select_one(".tt_article_us") or \
                              soup.select_one(".article-view")
                
                if content_div:
                    for tag in content_div.find_all(["script", "style"]):
                        tag.decompose()
                    return content_div.get_text(separator="\n", strip=True)
                
                return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            logger.error(f"Error extracting Tistory: {e}")
            return f"Error extracting Tistory content: {str(e)}"

    async def _extract_general(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                
                for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
                    tag.decompose()
                    
                # Try to find the main body
                body = soup.find("main") or soup.find("article") or soup.find("body")
                return body.get_text(separator="\n", strip=True) if body else ""
        except Exception as e:
            logger.error(f"Error in general extraction: {e}")
            return ""
