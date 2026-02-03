import os
import re
import asyncio
import random
from typing import Optional
import logging

try:
    from notion_client import Client
except ImportError:
    Client = None

from .base import BaseExtractor
from common.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class NotionExtractor(BaseExtractor):
    """
    Extractor for Notion pages or databases via API.
    Recursively crawls child pages and databases.
    """

    def __init__(self):
        self.access_token = settings.NOTION_TOKEN
        if not self.access_token:
            # Main service should handle this check if needed
            logger.warning("Warning: NOTION_TOKEN not set.")
            self.client = None
        else:
            if Client is None:
                raise ImportError("notion-client library is not installed.")
            self.client = Client(auth=self.access_token, notion_version="2022-06-28")

        self.visited_nodes = set()

    async def extract(self, source: str) -> str:
        """
        Extracts content from a Notion Page ID or Database ID.
        Source should be the UUID of the root page/db.
        """
        if not self.client:
            return "Error: Notion client not initialized (missing token or library)."

        self.visited_nodes.clear()

        if source.lower() == "all":
            return await self._fetch_workspace_content()

        # Clean source ID
        node_id = source
        if "notion.site" in source or "notion.so" in source:
            # Simple regex for UUID
            match = re.search(r"([0-9a-f]{32})", source.replace("-", ""))
            if match:
                node_id = match.group(1)

        # Determine if it's a page or database (try retrieval)
        try:
            # Try as page first
            title, content = await self._process_node(node_id, node_type="page")
            return content
        except Exception:
            try:
                title, content = await self._process_node(node_id, node_type="database")
                return content
            except Exception as e:
                return f"Error extracting from Notion node {node_id}: {e}"

    async def _process_node(self, node_id: str, node_type: str = "page") -> tuple[str, str]:
        if node_id in self.visited_nodes:
            return "", ""
        self.visited_nodes.add(node_id)

        content = ""
        node_title = "Untitled"
        max_retries = 3
        base_delay = 1.0

        try:
            if node_type == "page":
                page = await self._retrieve_page(node_id)
                for prop in page.get("properties", {}).values():
                    if prop["type"] == "title":
                        node_title = "".join([t["plain_text"] for t in prop.get("title", [])])

                content += f"# {node_title}\n\n"

                blocks = await self._get_all_blocks(node_id)
                content += await self._process_blocks(blocks)

            elif node_type == "database":
                db = await self._retrieve_database(node_id)
                node_title = "".join([t["plain_text"] for t in db.get("title", [])])
                content += f"# Database: {node_title}\n\n"

                pages = await self._query_database_results(node_id)
                for page in pages:
                    _, child_content = await self._process_node(page["id"], "page")
                    content += child_content

        except Exception as e:
            logger.error(f"Error processing node {node_id}: {e}")

        return node_title, content

    async def _process_blocks(self, blocks, depth=0) -> str:
        content = ""
        for block in blocks:
            content += await self._process_single_block(block, depth)
        return content

    async def _process_single_block(self, block, depth=0) -> str:
        b_type = block["type"]
        indent = "  " * depth
        content = ""

        if b_type == "child_page":
            # Recursively process child pages
            content += await self._process_node(block["id"], "page")
        elif b_type == "child_database":
            # Recursively process child databases
            content += await self._process_node(block["id"], "database")
        elif b_type in [
            "paragraph", "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item", "quote", "code", "to_do"
        ]:
            rich_text = block[b_type].get("rich_text", [])
            text = "".join([t["plain_text"] for t in rich_text])
            if text:
                prefix = ""
                if b_type == "heading_1": prefix = "# "
                elif b_type == "heading_2": prefix = "## "
                elif b_type == "heading_3": prefix = "### "
                elif b_type == "bulleted_list_item": prefix = "- "
                elif b_type == "numbered_list_item": prefix = "1. "
                elif b_type == "quote": prefix = "> "
                elif b_type == "code": 
                    lang = block[b_type].get("language", "")
                    content += f"{indent}```{lang}\n{text}\n{indent}```\n\n"
                    return content
                elif b_type == "to_do":
                    checked = " [x] " if block[b_type].get("checked") else " [ ] "
                    prefix = checked
                
                content += f"{indent}{prefix}{text}\n\n"
        
        elif b_type == "image":
            img_data = block["image"]
            img_type = img_data["type"]
            img_url = img_data[img_type].get("url")
            if img_url:
                content += f"{indent}![image]({img_url})\n\n"
        
        # Process children if any (recursive blocks)
        if block.get("has_children") and depth < 5: # Limit depth
             child_blocks = await self._get_all_blocks(block["id"])
             content += await self._process_blocks(child_blocks, depth + 1)
             
        return content

    async def _fetch_workspace_content(self) -> str:
        """Fetches content from all pages and databases accessible by the token."""
        combined_content = "# Notion Workspace Content\n\n"
        try:
            results = []
            has_more = True
            next_cursor = None

            logger.info("Searching for all accessible Notion pages and databases...")
            while has_more:
                # Retry for search
                @retry(
                    retry=retry_if_exception_type(Exception),
                    stop=stop_after_attempt(3),
                    wait=wait_exponential(multiplier=1, min=1, max=10)
                )
                def _do_search(cursor):
                    return self.client.search(start_cursor=cursor)

                response = _do_search(next_cursor)

                results.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                
                if len(results) > 500:
                    logger.warning("Reached search limit (500 items).")
                    break

            logger.info(f"Found {len(results)} items in workspace.")

            for item in results:
                item_id = item["id"]
                item_type = item["object"]  # 'page' or 'database'
                
                if item_id in self.visited_nodes:
                    continue
                    
                _, content = await self._process_node(item_id, node_type=item_type)
                if content.strip():
                    combined_content += f"{content}\n---\n\n"

            return combined_content
        except Exception as e:
            return f"Error searching workspace: {e}"

    
    @retry(
        retry=retry_if_exception_type(Exception), 
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _retrieve_page(self, page_id: str):
        return self.client.pages.retrieve(page_id=page_id)

    @retry(
        retry=retry_if_exception_type(Exception), 
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _retrieve_database(self, database_id: str):
        return self.client.databases.retrieve(database_id=database_id)

    @retry(
        retry=retry_if_exception_type(Exception), 
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _query_database_results(self, database_id: str):
        return self.client.databases.query(database_id=database_id).get("results", [])

    async def _get_all_blocks(self, parent_id):
        blocks = []
        has_more = True
        start_cursor = None
        
        @retry(
            retry=retry_if_exception_type(Exception), 
            stop=stop_after_attempt(3), 
            wait=wait_exponential(multiplier=1, min=1, max=10)
        )
        def _fetch_children(pid, cursor):
            # client.blocks.children.list is synchronous or async? notion-client is synchronous by default but we used it in async context previously?
            # Creating a wrapper to be safe. Actually the library is sync unless async client used. 
            # In previous code "self.client.pages.retrieve" was called without await?
            # Wait, line 84: page = self.client.pages.retrieve(page_id=node_id)
            # Line 3: import asyncio.
            # It seems the previous code treated notion-client as sync blocking code inside async def?
            # 'notion-client' is synchronous by default. There is AsyncClient too.
            # But line 34: Client(auth=...) suggests synchronous client.
            # If so, we should not await inside _retrieve_page unless we run in executor.
            # However, the previous code had `await asyncio.sleep` which suggests this was running in an event loop.
            # If the client is sync, these calls block the loop.
            # For now, I will keep the call usage as is (sync call) but wrapping in async def helper is fine, 
            # but I should remove `await` if the library returns dict immediately.
            # Wait, looking at lines 38 async def extract...
            # The previous code lines 84: page = self.client.pages.retrieve... NO await.
            # So it is synchronous.
            return self.client.blocks.children.list(block_id=pid, start_cursor=cursor)

        while has_more:
            try:
                response = _fetch_children(parent_id, start_cursor)
                blocks.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response["next_cursor"]
            except Exception as e:
                logger.error(f"Notion API final failure for {parent_id}: {e}")
                break
                
        return blocks
