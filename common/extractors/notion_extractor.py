import os
import re
from typing import Optional

try:
    from notion_client import Client
except ImportError:
    Client = None

from .base import BaseExtractor
from common.config import settings
import logging

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

    def extract(self, source: str) -> str:
        """
        Extracts content from a Notion Page ID or Database ID.
        Source should be the UUID of the root page/db.
        """
        if not self.client:
            return "Error: Notion client not initialized (missing token or library)."

        self.visited_nodes.clear()

        if source.lower() == "all":
            return self._fetch_workspace_content()

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
            return self._process_node(node_id, node_type="page")
        except Exception:
            try:
                return self._process_node(node_id, node_type="database")
            except Exception as e:
                return f"Error extracting from Notion node {node_id}: {e}"

    def _process_node(self, node_id: str, node_type: str = "page") -> str:
        if node_id in self.visited_nodes:
            return ""
        self.visited_nodes.add(node_id)

        content = ""

        try:
            if node_type == "page":
                page = self.client.pages.retrieve(page_id=node_id)
                title = "Untitled"
                for prop in page.get("properties", {}).values():
                    if prop["type"] == "title":
                        title = "".join([t["plain_text"] for t in prop.get("title", [])])

                content += f"# {title}\n\n"

                blocks = self._get_all_blocks(node_id)
                for block in blocks:
                    b_type = block["type"]

                    if b_type == "child_page":
                        content += self._process_node(block["id"], "page")
                    elif b_type == "child_database":
                        content += self._process_node(block["id"], "database")
                    elif b_type in [
                        "paragraph",
                        "heading_1",
                        "heading_2",
                        "heading_3",
                        "bulleted_list_item",
                        "numbered_list_item",
                    ]:
                        rich_text = block[b_type].get("rich_text", [])
                        text = "".join([t["plain_text"] for t in rich_text])
                        if text:
                            prefix = ""
                            if b_type == "heading_1":
                                prefix = "# "
                            elif b_type == "heading_2":
                                prefix = "## "
                            elif b_type == "heading_3":
                                prefix = "### "
                            elif b_type == "bulleted_list_item":
                                prefix = "- "
                            elif b_type == "numbered_list_item":
                                prefix = "1. "  # Simplified
                            content += f"{prefix}{text}\n\n"
                    elif b_type == "image":
                        img_data = block["image"]
                        img_type = img_data["type"]
                        img_url = img_data[img_type].get("url")
                        if img_url:
                            content += f"![image]({img_url})\n\n"

            elif node_type == "database":
                db = self.client.databases.retrieve(database_id=node_id)
                db_title = "".join([t["plain_text"] for t in db.get("title", [])])
                content += f"# Database: {db_title}\n\n"

                # Check for query capabilities
                pages = self.client.databases.query(database_id=node_id).get(
                    "results", []
                )

                for page in pages:
                    content += self._process_node(page["id"], "page")

        except Exception as e:
            logger.error(f"Error processing node {node_id}: {e}")

        return content

    def _fetch_workspace_content(self) -> str:
        """Fetches content from all pages and databases accessible by the token."""
        combined_content = "# Notion Workspace Content\n\n"
        try:
            results = []
            has_more = True
            next_cursor = None

            logger.info("Searching for all accessible Notion pages and databases...")
            while has_more:
                response = self.client.search(start_cursor=next_cursor).get(
                    "results", []
                )
                results.extend(response)
                break  # Safety break for one page

            logger.info(f"Found {len(results)} items in workspace.")

            for item in results:
                item_id = item["id"]
                item_type = item["object"]  # 'page' or 'database'
                content = self._process_node(item_id, node_type=item_type)
                combined_content += f"{content}\n---\n\n"

            return combined_content
        except Exception as e:
            return f"Error searching workspace: {e}"

    def _get_all_blocks(self, parent_id):
        blocks = []
        has_more = True
        start_cursor = None
        while has_more:
            try:
                response = self.client.blocks.children.list(
                    block_id=parent_id, start_cursor=start_cursor
                )
                blocks.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response["next_cursor"]
            except:
                break
        return blocks
