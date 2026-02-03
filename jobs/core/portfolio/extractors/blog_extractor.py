
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

    async def discover_posts(self, url: str) -> List[Dict[str, str]]:
        """
        Scrapes a blog home page to find post titles and URLs.
        Supports Velog and Tistory.
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                posts = []

                if "velog.io" in url:
                    # Velog specific: posts are usually in h2 tags inside article tags
                    # Updated selector for better accuracy
                    articles = soup.find_all("div", {"class": "sc-hHTYSt"}) or soup.find_all("article")
                    for article in articles:
                        link_tag = article.find("a")
                        title_tag = article.find("h2")
                        if link_tag and title_tag and link_tag.get("href"):
                            full_url = link_tag.get("href")
                            if full_url.startswith("/"):
                                # Handle relative URL for Velog (e.g. /@username/post-title)
                                base = url.split(".io")[0] + ".io"
                                full_url = base + full_url
                            posts.append({
                                "title": title_tag.get_text(strip=True),
                                "url": full_url
                            })
                elif "tistory.com" in url:
                    # Tistory: widely varies by skin, but usually in .post-item or similar
                    # Try common selectors
                    links = soup.select("a[href*='/']")
                    for link in links:
                        # Skip pagination and category links
                        href = link.get("href", "")
                        if any(x in href for x in ["/category", "?page="]) or len(href.split("/")) < 2:
                            continue
                        
                        title = link.get_text(strip=True)
                        if title and len(title) > 2:
                            full_url = href
                            if not href.startswith("http"):
                                base = "/".join(url.split("/")[:3])
                                full_url = base + href
                            posts.append({
                                "title": title,
                                "url": full_url
                            })
                
                # Deduplicate and limit
                seen = set()
                unique_posts = []
                for p in posts:
                    if p["url"] not in seen:
                        unique_posts.append(p)
                        seen.add(p["url"])
                
                return unique_posts[:20]
        except Exception as e:
            logger.error(f"Error discovering blog posts: {e}")
            return []

    async def extract_multi(self, url: str) -> List[Dict[str, str]]:
        """
        Extract multiple posts if the URL is a profile/index page.
        Returns: List of {"title": str, "content": str, "url": str}
        """
        content = await self.extract(url)
        # Try to find title from HTML
        title = "Blog Post"
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string if soup.title else "Blog Post"
        except: pass
        
        return [{"title": title, "content": content, "url": url}]

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
