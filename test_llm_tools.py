"""
Test what function declarations the LLM sees.
This checks if MCP tools are exposed to the LLM for function calling.
"""
import os
import asyncio
from dotenv import load_dotenv
from services.adk_agent_service import create_agent

load_dotenv()

async def test_llm_tool_visibility():
    """Check what tools the LLM can actually see."""

    print("="*60)
    print("🔍 Testing LLM Tool Visibility")
    print("="*60 + "\n")

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    agent = create_agent(api_key=api_key)

    print(f"Agent has {len(agent.tools)} tools loaded\n")

    # Try to access the model's tool configuration
    print("Checking what gets passed to the LLM...\n")

    # In ADK, tools should be converted to function declarations
    # Let's see if we can inspect that

    for i, tool in enumerate(agent.tools, 1):
        tool_type = type(tool).__name__
        print(f"{i}. {tool_type}")

        if tool_type == "FunctionTool":
            # Function tools should have a name and description
            if hasattr(tool, 'name'):
                print(f"   Name: {tool.name}")
            if hasattr(tool, 'description'):
                print(f"   Description: {tool.description[:60]}...")

        elif tool_type == "McpToolset":
            print("   Type: MCP Server")

            # The critical question: Does McpToolset expose individual tools to the LLM?
            # Or does it appear as a single "McpToolset" tool?

            # Check if it has a get_function_declarations method
            if hasattr(tool, 'get_function_declarations'):
                print("   ✅ Has get_function_declarations method")
                try:
                    declarations = await tool.get_function_declarations()
                    print(f"   ✅ Exposes {len(declarations)} function declarations to LLM:")
                    for decl in declarations[:5]:
                        print(f"      - {decl.name}")
                    if len(declarations) > 5:
                        print(f"      ... and {len(declarations) - 5} more")
                except Exception as e:
                    print(f"   ❌ Error getting declarations: {e}")
            else:
                print("   ❌ No get_function_declarations method found")
                print("   This might mean MCP tools are NOT visible to the LLM!")

            # Check for other relevant methods
            if hasattr(tool, 'to_function_declarations'):
                print("   ✅ Has to_function_declarations method")

            # List all methods to understand the interface
            print("\n   Available methods:")
            methods = [m for m in dir(tool) if not m.startswith('_')]
            for method in methods[:10]:
                print(f"      - {method}")

        print()

    print("="*60)
    print("💡 Analysis")
    print("="*60 + "\n")

    print("For MCP tools to work with the LLM:")
    print("1. McpToolset must expose individual tool declarations")
    print("2. Each Notion tool (API-post-search, etc.) must be a separate function")
    print("3. The LLM must receive these as callable functions")
    print("\nIf McpToolset doesn't expose declarations:")
    print("→ The LLM can't call the Notion tools")
    print("→ We need a different approach (manual wrapping)")

if __name__ == "__main__":
    asyncio.run(test_llm_tool_visibility())
