"""
Test Notion FunctionTool Wrappers
Verify that Notion tools are now visible to the LLM as individual functions.
"""
import os
import asyncio
from dotenv import load_dotenv
from services.adk_agent_service import create_agent

load_dotenv()


def test_notion_wrapper_visibility():
    """Check that Notion wrappers are loaded as FunctionTools."""

    print("="*60)
    print("🧪 Testing Notion FunctionTool Wrappers")
    print("="*60 + "\n")

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    notion_token = os.getenv("NOTION_TOKEN")

    if not api_key:
        print("❌ No API key found")
        return

    if not notion_token:
        print("⚠️  NOTION_TOKEN not set - Notion tools won't be available")
        print("   This is expected if you haven't configured Notion integration\n")

    print("✅ Creating agent...\n")
    agent = create_agent(api_key=api_key)

    print(f"Agent: {agent.name}")
    print(f"Model: {agent.model}")
    print(f"Total Tools: {len(agent.tools)}\n")

    print("="*60)
    print("📦 Tool Breakdown:")
    print("="*60 + "\n")

    notion_tools = []
    neo4j_tools = []
    miro_tools = []
    other_tools = []

    for tool in agent.tools:
        tool_type = type(tool).__name__

        if tool_type == "FunctionTool" and hasattr(tool, 'func'):
            func_name = tool.func.__name__

            if func_name.startswith('notion_'):
                notion_tools.append(func_name)
            elif func_name in ['search_meetings', 'get_action_items',
                              'get_historical_context', 'store_meeting_data_tool']:
                neo4j_tools.append(func_name)
            elif func_name.startswith('create_meeting_'):
                miro_tools.append(func_name)
            else:
                other_tools.append(func_name)
        else:
            other_tools.append(tool_type)

    print(f"Neo4j Tools ({len(neo4j_tools)}):")
    for name in neo4j_tools:
        print(f"  ✅ {name}")

    print(f"\nMiro Tools ({len(miro_tools)}):")
    for name in miro_tools:
        print(f"  ✅ {name}")

    print(f"\nNotion Tools ({len(notion_tools)}):")
    if notion_tools:
        for name in notion_tools:
            print(f"  ✅ {name}")
        print("\n✅ SUCCESS: Notion tools are now visible as individual FunctionTools!")
    else:
        if notion_token:
            print("  ❌ No Notion tools found (check configuration)")
        else:
            print("  ⚠️  NOTION_TOKEN not set (tools not loaded)")

    if other_tools:
        print(f"\nOther Tools ({len(other_tools)}):")
        for name in other_tools:
            print(f"  - {name}")

    print("\n" + "="*60)
    print("💡 Analysis")
    print("="*60 + "\n")

    if notion_tools:
        print("✅ Notion FunctionTool wrappers are working!")
        print("✅ The LLM can now see and call:")
        for name in notion_tools:
            print(f"   - {name}")
        print("\nThe agent should now be able to create Notion pages when asked.")
    else:
        print("Expected Notion tools if NOTION_TOKEN is set:")
        print("  - notion_search_pages")
        print("  - notion_create_page")
        print("  - notion_get_workspace_info")
        print("\nIf NOTION_TOKEN is set but tools aren't loaded, check:")
        print("  1. mcp_tools/__init__.py exports Notion functions")
        print("  2. services/adk_agent_service.py imports and wraps them")
        print("  3. No errors in agent creation logs")


async def test_notion_search_wrapper():
    """Test calling the notion_search_pages wrapper directly."""

    print("\n" + "="*60)
    print("🔍 Testing notion_search_pages wrapper directly")
    print("="*60 + "\n")

    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        print("⚠️  Skipping - NOTION_TOKEN not set")
        return

    try:
        from mcp_tools.notion_tools import notion_search_pages

        print("Calling notion_search_pages('')...")
        result = await notion_search_pages("")

        print(f"\n✅ Search completed!")
        print(f"Result preview (first 500 chars):\n{result[:500]}")

        if "error" in result.lower():
            print("\n⚠️  Search returned an error - check Notion token validity")
        else:
            print("\n✅ Search successful - wrapper is working!")

    except Exception as e:
        print(f"❌ Error testing wrapper: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting Notion FunctionTool Wrapper Tests\n")

    # Test 1: Check tool visibility in agent
    test_notion_wrapper_visibility()

    # Test 2: Try calling a wrapper directly
    asyncio.run(test_notion_search_wrapper())

    print("\n" + "="*60)
    print("✅ Testing Complete")
    print("="*60)
    print("\nNext step: Test in the Live Agent chat UI")
    print("Ask the agent: 'Search my Notion workspace'")
    print("Or: 'Add my action items to Notion'\n")
