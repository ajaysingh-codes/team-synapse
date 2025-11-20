"""
MCP Server for Team Synapse.
Exposes Neo4j knowledge graph capabilities as tools for the Meeting Copilot.
"""
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from services.neo4j_service import neo4j_service

# Initialize FastMCP server
mcp = FastMCP("team-synapse-neo4j")

@mcp.tool()
def search_meetings(query: str) -> str:
    """
    Search for meetings by title, summary, or content.
    
    Args:
        query: The search term to look for in meeting records.
    """
    results = neo4j_service.search_meetings(query)
    if not results:
        return "No meetings found matching that query."
    
    formatted = []
    for m in results:
        formatted.append(f"- {m['title']} ({m['meetingDate']}): {m['summary'][:150]}...")
    
    return "\n".join(formatted)

@mcp.tool()
def get_action_items(person_name: str) -> str:
    """
    Get action items assigned to a specific person.
    
    Args:
        person_name: The name of the person to look up.
    """
    items = neo4j_service.get_action_items_by_person(person_name)
    if not items:
        return f"No action items found for {person_name}."
    
    formatted = []
    for item in items:
        status_icon = "✓" if item['status'] == 'completed' else "☐"
        formatted.append(f"{status_icon} {item['task']} (Due: {item['dueDate']}, Priority: {item['priority']}) - from meeting '{item['meetingTitle']}'")
    
    return "\n".join(formatted)

@mcp.tool()
def get_project_meetings(project_name: str) -> str:
    """
    Get a list of meetings related to a specific project.
    
    Args:
        project_name: The name of the project.
    """
    meetings = neo4j_service.get_meetings_by_project(project_name)
    if not meetings:
        return f"No meetings found linked to project '{project_name}'."
    
    formatted = []
    for m in meetings:
        formatted.append(f"- {m['title']} ({m['meetingDate']})\n  Summary: {m['summary']}")
    
    return "\n\n".join(formatted)

@mcp.tool()
def get_client_history(client_name: str) -> str:
    """
    Get history and relationship details for a specific client.
    
    Args:
        client_name: The name of the client company.
    """
    # The service method returns a list, but we usually expect one record for a specific client
    results = neo4j_service.get_client_relationships(client_name)
    if not results:
        return f"No information found for client '{client_name}'."
    
    # Since we searched by specific name, we likely just want the first result or all if multiple matches
    formatted = []
    for r in results:
        recent = ", ".join(r['recentMeetings']) if r['recentMeetings'] else "None"
        formatted.append(f"Client: {r['clientName']}\nTotal Meetings: {r['meetingCount']}\nRecent Meetings: {recent}")
    
    return "\n---\n".join(formatted)

@mcp.tool()
def get_graph_stats() -> str:
    """
    Get high-level statistics about the knowledge graph (counts of meetings, people, etc.).
    """
    stats = neo4j_service.get_knowledge_graph_summary()
    if not stats:
        return "Could not retrieve graph statistics."
        
    return (
        f"Graph Statistics:\n"
        f"- Meetings: {stats.get('meetings', 0)}\n"
        f"- People: {stats.get('people', 0)}\n"
        f"- Clients: {stats.get('clients', 0)}\n"
        f"- Projects: {stats.get('projects', 0)}\n"
        f"- Action Items: {stats.get('actionItems', 0)}\n"
        f"- Decisions: {stats.get('decisions', 0)}"
    )

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport='stdio')

