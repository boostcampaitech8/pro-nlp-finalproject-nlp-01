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
            return await self._process_node(node_id, node_type="page")
        except Exception:
            try:
                return await self._process_node(node_id, node_type="database")
            except Exception as e:
                return f"Error extracting from Notion node {node_id}: {e}"

    async def _process_node(self, node_id: str, node_type: str = "page") -> str:
        if node_id in self.visited_nodes:
            return ""
        self.visited_nodes.add(node_id)

        content = ""
        max_retries = 3
        base_delay = 1.0

        try:
            if node_type == "page":
                # Retry for page retrieval
                page = None
                for attempt in range(max_retries + 1):
                    try:
                        page = self.client.pages.retrieve(page_id=node_id)
                        break
                    except Exception as e:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                            await asyncio.sleep(delay)
                        else: raise

                title = "Untitled"
                for prop in page.get("properties", {}).values():
                    if prop["type"] == "title":
                        title = "".join([t["plain_text"] for t in prop.get("title", [])])

                content += f"# {title}\n\n"

                blocks = await self._get_all_blocks(node_id)
                content += await self._process_blocks(blocks)

            elif node_type == "database":
                # Retry for database retrieval
                db = None
                for attempt in range(max_retries + 1):
                    try:
                        db = self.client.databases.retrieve(database_id=node_id)
                        break
                    except Exception as e:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                            await asyncio.sleep(delay)
                        else: raise

                db_title = "".join([t["plain_text"] for t in db.get("title", [])])
                content += f"# Database: {db_title}\n\n"

                # Retry for database query
                pages = []
                for attempt in range(max_retries + 1):
                    try:
                        pages = self.client.databases.query(database_id=node_id).get("results", [])
                        break
                    except Exception as e:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                            await asyncio.sleep(delay)
                        else: raise

                for page in pages:
                    content += await self._process_node(page["id"], "page")

        except Exception as e:
            logger.error(f"Error processing node {node_id}: {e}")

        return content

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
                response = None
                for attempt in range(3):
                    try:
                        response = self.client.search(start_cursor=next_cursor)
                        break
                    except Exception as e:
                        if attempt < 2:
                            await asyncio.sleep(1.0 * (2**attempt))
                        else: raise

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
                    
                content = await self._process_node(item_id, node_type=item_type)
                if content.strip():
                    combined_content += f"{content}\n---\n\n"

            return combined_content
        except Exception as e:
            return f"Error searching workspace: {e}"

    async def _get_all_blocks(self, parent_id):
        blocks = []
        has_more = True
        start_cursor = None
        max_retries = 3
        base_delay = 1.0

        while has_more:
            attempt_success = False
            for attempt in range(max_retries + 1):
                try:
                    response = self.client.blocks.children.list(
                        block_id=parent_id, start_cursor=start_cursor
                    )
                    blocks.extend(response["results"])
                    has_more = response["has_more"]
                    start_cursor = response["next_cursor"]
                    attempt_success = True
                    break
                except Exception as e:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                        logger.warning(f"Notion API error for {parent_id}: {e}. Retrying in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Notion API final failure for {parent_id}: {e}")
                        has_more = False 
                        break
            if not attempt_success:
                break
        return blocks
