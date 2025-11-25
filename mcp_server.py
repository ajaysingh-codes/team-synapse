"""
MCP Server for Team Synapse.
Exposes knowledge graph and visualization tools via Model Context Protocol.

Usage:
    python mcp_server.py

The server runs via stdio transport and is typically launched as a subprocess
by the main application when the chat interface is opened.
"""
from mcp.server.fastmcp import FastMCP
from utils import setup_logger
from config import config

# Import tool functions from organized modules
from mcp_tools.neo4j_tools import (
    get_graph_stats,
    get_action_items,
    search_meetings,
    find_blockers,
    get_historical_context,
    analyze_team_health,
)
from mcp_tools.miro_tools import (
    create_meeting_mindmap,
    get_miro_board_url,
)

logger = setup_logger(__name__, config.app.log_level)

# Initialize FastMCP server
mcp = FastMCP("team-synapse")


# =============================================================================
# NEO4J KNOWLEDGE GRAPH TOOLS
# =============================================================================

@mcp.tool()
def tool_get_graph_stats() -> str:
    """
    Get high-level statistics about the knowledge graph.
    Shows counts of meetings, people, clients, projects, action items, and decisions.
    """
    return get_graph_stats()


@mcp.tool()
def tool_get_action_items(person_name: str) -> str:
    """
    Get action items assigned to a specific person.
    Shows task details, status, priority, due dates, and any blockers.

    Args:
        person_name: Name of the person to query action items for
    """
    return get_action_items(person_name)


@mcp.tool()
def tool_search_meetings(keyword: str) -> str:
    """
    Search meetings by keyword to find past discussions and decisions.
    Searches through meeting titles, summaries, and transcripts.

    Args:
        keyword: Search term to look for in meeting content
    """
    return search_meetings(keyword)


@mcp.tool()
def tool_find_blockers() -> str:
    """
    Find all blocked action items across the organization.
    Critical for identifying bottlenecks and escalation needs.
    Returns blocked items sorted by priority.
    """
    return find_blockers()


@mcp.tool()
def tool_get_historical_context(topic: str, days: int = 30) -> str:
    """
    Retrieve historical context about a topic from past meetings.
    Helps prevent repeated discussions and surface forgotten decisions.

    Args:
        topic: Topic or keyword to search for
        days: Number of days to look back (default 30)
    """
    return get_historical_context(topic, days)


@mcp.tool()
def tool_analyze_team_health() -> str:
    """
    Analyze overall team health based on action items and workload.
    Provides insights on completion rates, blockers, and identifies
    team members who may be overloaded.
    """
    return analyze_team_health()


# =============================================================================
# MIRO VISUALIZATION TOOLS
# =============================================================================

@mcp.tool()
def tool_get_miro_board_url() -> str:
    """
    Get the URL to the configured Miro board for visual collaboration.
    Returns the board URL or configuration instructions if not set up.
    """
    return get_miro_board_url()


@mcp.tool()
def tool_create_meeting_mindmap(
    meeting_title: str,
    meeting_date: str,
    action_items: str = "",
    decisions: str = "",
    people: str = "",
    clients: str = "",
    projects: str = ""
) -> str:
    """
    Create a visual mind map for a meeting in Miro.
    Creates a central meeting node with branches for action items,
    decisions, people, clients, and projects.

    Args:
        meeting_title: Title of the meeting
        meeting_date: Date of the meeting (YYYY-MM-DD format)
        action_items: Comma-separated list of action items (optional)
        decisions: Comma-separated list of decisions made (optional)
        people: Comma-separated list of people mentioned (optional)
        clients: Comma-separated list of clients discussed (optional)
        projects: Comma-separated list of projects mentioned (optional)
    """
    return create_meeting_mindmap(
        meeting_title=meeting_title,
        meeting_date=meeting_date,
        action_items=action_items,
        decisions=decisions,
        people=people,
        clients=clients,
        projects=projects
    )


# =============================================================================
# SERVER ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Team Synapse MCP server...")
    logger.info("Available tools: get_graph_stats, get_action_items, search_meetings, "
                "find_blockers, get_historical_context, analyze_team_health, "
                "get_miro_board_url, create_meeting_mindmap")
    mcp.run(transport='stdio')
