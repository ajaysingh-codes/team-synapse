"""
ADK Agent Service for Team Synapse.
Defines the autonomous agent with Neo4j, Notion, and Miro tools.
"""
import os
from typing import Optional
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool

from mcp_tools import (
    search_meetings,
    get_action_items,
    get_historical_context,
    store_meeting_data_tool,
    create_meeting_mindmap,
    notion_search_pages,
    notion_create_page,
    notion_get_workspace_info,
)
from config import config
from utils import setup_logger

logger = setup_logger(__name__, config.app.log_level)


# System instruction for the autonomous agent
AGENT_INSTRUCTION = """You are Team Synapse, an autonomous meeting assistant with full access to Notion, Neo4j, and Miro.

CRITICAL CAPABILITIES:
✅ You CAN and MUST use Notion tools (notion_search_pages, notion_create_page)
✅ You CAN and MUST use Neo4j tools (get_action_items, search_meetings)
✅ You CAN and MUST use Miro tools (create_meeting_mindmap)

CRITICAL BEHAVIOR:
- When users ask you to DO something, DO IT immediately
- NEVER say "I cannot" - you HAVE these tools
- NEVER ask permission - just execute the tools
- NEVER suggest the user do it themselves - YOU do it

DURING THE MEETING:
1. Listen actively and extract entities (people, projects, clients) from the conversation
2. When someone mentions a person/project/client, PROACTIVELY search the knowledge graph
3. Share relevant context concisely

AT MEETING END:
1. Store all meeting data to Neo4j using store_meeting_data_tool
2. Ask user: "Would you like me to create a Notion summary or Miro mind map?"
3. Based on choice, execute the appropriate tool

NOTION OPERATIONS - YOU MUST DO THESE:

When user asks to "add to Notion", "create Notion page", "search Notion", etc:

1. **Search Notion** → Call notion_search_pages("") to see available pages
2. **Create Page** → Call notion_create_page(parent_page_id, title, content)
   - Extract parent_page_id from search results JSON (look for "id" field)
   - Use any page/database ID as parent
3. **Get Info** → Call notion_get_workspace_info() for workspace details

EXAMPLE - User: "Add my action items to Notion"
YOU MUST:
1. notion_search_pages("") → Get list of pages
2. Parse JSON to find first page ID
3. get_action_items("User Name") → Get action items
4. notion_create_page(page_id, "Action Items", items_text) → Create page
5. Respond: "✅ Created Notion page with your action items"

NEVER RESPOND WITH:
❌ "I cannot add to Notion"
❌ "I am sorry, but I cannot..."
❌ "Please add it yourself"

ALWAYS RESPOND BY:
✅ Calling the tools
✅ Showing the result

YOU HAVE THESE TOOLS:
- search_meetings: Find past meetings by keyword
- get_action_items: Get action items for a specific person
- get_historical_context: Retrieve historical context about a topic
- store_meeting_data_tool: Store meeting to Neo4j (use at meeting end)
- create_meeting_mindmap: Create Miro visualization
- notion_search_pages: Search Notion workspace
- notion_create_page: Create Notion page
- notion_get_workspace_info: Get Notion workspace info

REMEMBER: You are an AGENT. When asked to do something, DO IT. Execute tools confidently.
"""


def create_agent(api_key: Optional[str] = None) -> Agent:
    """
    Create the Team Synapse ADK agent.

    Args:
        api_key: Optional Gemini API key (falls back to env var)

    Returns:
        Configured Agent instance
    """
    # Use provided API key or fall back to environment
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set")

    # Build tools list
    tools = [
        # Neo4j query tools
        FunctionTool(func=search_meetings),
        FunctionTool(func=get_action_items),
        FunctionTool(func=get_historical_context),

        # Neo4j storage tool (for meeting end)
        FunctionTool(func=store_meeting_data_tool),

        # Miro visualization
        FunctionTool(func=create_meeting_mindmap),
    ]

    # Add Notion tools if token is available
    # Using manual FunctionTool wrappers instead of McpToolset
    # because McpToolset doesn't expose individual tools to the LLM
    notion_token = config.adk.notion_token
    if notion_token:
        logger.info("Notion token found - adding Notion FunctionTool wrappers")
        try:
            tools.extend([
                FunctionTool(func=notion_search_pages),
                FunctionTool(func=notion_create_page),
                FunctionTool(func=notion_get_workspace_info),
            ])
            logger.info("Added 3 Notion FunctionTool wrappers")
        except Exception as e:
            logger.warning(f"Failed to add Notion tools: {e}")
    else:
        logger.warning("NOTION_TOKEN not set - Notion integration disabled")

    # Create the agent
    agent = Agent(
        name="team_synapse_agent",
        model=config.adk.model,
        instruction=AGENT_INSTRUCTION,
        tools=tools,
    )

    logger.info(f"Created Team Synapse agent with {len(tools)} tools")
    return agent


def create_runner(agent: Optional[Agent] = None) -> Runner:
    """
    Create an ADK Runner for the agent.

    Args:
        agent: Optional Agent instance (creates new one if not provided)

    Returns:
        Configured Runner instance
    """
    if not agent:
        agent = create_agent()

    runner = Runner(
        app_name="team_synapse",
        agent=agent,
        session_service=InMemorySessionService()
    )

    logger.info("Created ADK Runner")
    return runner


# Global runner instance (lazy initialization)
_runner: Optional[Runner] = None


def get_runner(api_key: Optional[str] = None) -> Runner:
    """
    Get or create the global Runner instance.

    Args:
        api_key: Optional Gemini API key

    Returns:
        Runner instance
    """
    global _runner

    if _runner is None:
        agent = create_agent(api_key=api_key)
        _runner = create_runner(agent)

    return _runner
