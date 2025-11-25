"""
MCP Tools for Team Synapse.
Organized tool modules for the MCP server.
"""
from .neo4j_tools import (
    get_graph_stats,
    get_action_items,
    search_meetings,
    find_blockers,
    get_historical_context,
    analyze_team_health,
    store_meeting_data_tool,
)
from .miro_tools import (
    create_meeting_mindmap,
    get_miro_board_url,
)
from .notion_tools import (
    notion_search_pages,
    notion_create_page,
    notion_get_workspace_info,
    add_to_notion,
)

__all__ = [
    # Neo4j tools
    "get_graph_stats",
    "get_action_items",
    "search_meetings",
    "find_blockers",
    "get_historical_context",
    "analyze_team_health",
    "store_meeting_data_tool",
    # Miro tools
    "create_meeting_mindmap",
    "get_miro_board_url",
    # Notion tools
    "notion_search_pages",
    "notion_create_page",
    "notion_get_workspace_info",
    "add_to_notion",
]
