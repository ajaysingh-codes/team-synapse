"""
Notion MCP Tool Wrappers for Team Synapse.
Manual wrappers to expose Notion MCP tools as ADK FunctionTools.
"""
import os
import asyncio
from typing import Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from utils import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# Global MCP session management
_notion_session: Optional[ClientSession] = None
_exit_stack: Optional[AsyncExitStack] = None


async def _get_notion_session() -> ClientSession:
    """Get or create Notion MCP session."""
    global _notion_session, _exit_stack

    if _notion_session is not None:
        return _notion_session

    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        raise ValueError("NOTION_TOKEN not set")

    try:
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={"NOTION_TOKEN": notion_token}
        )

        _exit_stack = AsyncExitStack()
        stdio_transport = await _exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        _notion_session = await _exit_stack.enter_async_context(
            ClientSession(stdio_transport[0], stdio_transport[1])
        )

        await _notion_session.initialize()
        logger.info("Connected to Notion MCP server")
        return _notion_session

    except Exception as e:
        logger.error(f"Failed to connect to Notion MCP: {e}")
        raise


async def notion_search_pages(query: str = "") -> str:
    """
    Search Notion workspace for pages and databases.

    Args:
        query: Search query (empty string searches all)

    Returns:
        List of pages/databases found
    """
    try:
        session = await _get_notion_session()

        result = await session.call_tool(
            "API-post-search",
            arguments={"query": query} if query else {}
        )

        if result.content:
            output = []
            for content in result.content:
                if hasattr(content, 'text'):
                    output.append(content.text)
            return "\n".join(output) if output else "No results found"

        return "No results found"

    except Exception as e:
        logger.error(f"Notion search failed: {e}")
        return f"Error searching Notion: {str(e)}"


async def notion_create_page(
    parent_page_id: str,
    title: str,
    content: str
) -> str:
    """
    Create a new Notion page.

    Args:
        parent_page_id: ID of parent page (use notion_search_pages to find)
        title: Page title
        content: Page content (markdown or plain text)

    Returns:
        Success message with page URL
    """
    try:
        session = await _get_notion_session()

        # Format content as Notion blocks
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            }
        ]

        result = await session.call_tool(
            "API-post-page",
            arguments={
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [{"text": {"content": title}}]
                    }
                },
                "children": blocks
            }
        )

        if result.content:
            for content_item in result.content:
                if hasattr(content_item, 'text'):
                    return f"✅ Created Notion page: {title}\n{content_item.text}"

        return f"✅ Created Notion page: {title}"

    except Exception as e:
        logger.error(f"Notion page creation failed: {e}")
        return f"Error creating Notion page: {str(e)}"


async def notion_get_workspace_info() -> str:
    """
    Get information about the Notion workspace and bot.

    Returns:
        Workspace and bot information
    """
    try:
        session = await _get_notion_session()

        result = await session.call_tool(
            "API-get-self",
            arguments={}
        )

        if result.content:
            output = []
            for content in result.content:
                if hasattr(content, 'text'):
                    output.append(content.text)
            return "\n".join(output) if output else "No workspace info available"

        return "No workspace info available"

    except Exception as e:
        logger.error(f"Failed to get Notion workspace info: {e}")
        return f"Error: {str(e)}"


# Simplified wrapper for common use case
async def add_to_notion(title: str, content: str, search_query: str = "") -> str:
    """
    Simplified function to add content to Notion.
    Searches for a parent page and creates a new page.

    Args:
        title: Title for the new page
        content: Content to add
        search_query: Optional query to find specific parent page

    Returns:
        Success or error message
    """
    try:
        # First, search for pages
        logger.info(f"Searching Notion workspace with query: '{search_query}'")
        search_results = await notion_search_pages(search_query)

        # For now, we need the user to provide a parent page ID
        # A production version would parse search results to get IDs
        return (
            f"Found Notion pages:\n{search_results}\n\n"
            f"To create a page, I need a parent page ID from the search results.\n"
            f"Please use notion_create_page with a specific parent_page_id."
        )

    except Exception as e:
        logger.error(f"Add to Notion failed: {e}")
        return f"Error: {str(e)}"
