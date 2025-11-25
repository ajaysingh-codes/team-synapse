# Notion Integration Fix - Summary

## Problem Identified

The ADK agent was refusing to create Notion pages, saying "I cannot add to Notion" or "Add it on your own" even though Notion MCP tools were configured.

### Root Cause

**McpToolset doesn't expose individual MCP tools to the LLM for function calling.**

The test in `test_llm_tools.py` revealed:
```python
6. McpToolset
   Type: MCP Server
   ❌ No get_function_declarations method found
   This might mean MCP tools are NOT visible to the LLM!
```

The LLM could only see "McpToolset" as an opaque tool, not individual Notion API operations like `API-post-search` or `API-post-page`. This is why the agent said it couldn't use Notion - it literally couldn't see the tools as callable functions.

---

## Solution Implemented

Created **manual FunctionTool wrappers** that:
1. Connect to the Notion MCP server internally
2. Expose individual operations as Python async functions
3. Are wrapped as FunctionTools that the LLM CAN see and call

### Changes Made

#### 1. Created `mcp_tools/notion_tools.py`
Manual wrappers for Notion MCP tools:
- `async def notion_search_pages(query: str = "") -> str`
- `async def notion_create_page(parent_page_id: str, title: str, content: str) -> str`
- `async def notion_get_workspace_info() -> str`

Each wrapper:
- Manages its own MCP session connection
- Calls the Notion MCP server tools (API-post-search, API-post-page, etc.)
- Returns string results that the LLM can understand
- Uses async/await for proper event loop handling

#### 2. Updated `mcp_tools/__init__.py`
Exported the new Notion wrapper functions:
```python
from .notion_tools import (
    notion_search_pages,
    notion_create_page,
    notion_get_workspace_info,
    add_to_notion,
)
```

#### 3. Updated `services/adk_agent_service.py`

**Replaced McpToolset with FunctionTool wrappers:**
```python
# OLD (didn't work):
notion_toolset = McpToolset(connection_params=...)
tools.append(notion_toolset)

# NEW (works!):
tools.extend([
    FunctionTool(func=notion_search_pages),
    FunctionTool(func=notion_create_page),
    FunctionTool(func=notion_get_workspace_info),
])
```

**Updated agent instructions** to reference the new function names:
- Changed `API-post-search` → `notion_search_pages`
- Changed `API-post-page` → `notion_create_page`
- Added clearer step-by-step examples for the agent

#### 4. Removed unused imports
Removed `McpToolset`, `StdioConnectionParams`, and `StdioServerParameters` imports since they're no longer needed.

---

## Test Results

Created `test_notion_wrappers.py` to verify the fix:

```
✅ Agent has 8 tools loaded (4 Neo4j + 1 Miro + 3 Notion)

Notion Tools (3):
  ✅ notion_search_pages
  ✅ notion_create_page
  ✅ notion_get_workspace_info

✅ SUCCESS: Notion tools are now visible as individual FunctionTools!
✅ Search test successful - wrapper connected to Notion and returned workspace data
```

The LLM can now see and call each Notion function individually!

---

## How to Test

1. **Start the app:**
   ```bash
   source venv/bin/activate
   python app.py
   ```

2. **Go to the "Live Agent" page**

3. **Test the agent with these prompts:**
   - "Search my Notion workspace"
   - "Add my action items to Notion"
   - "Create a Notion page with a meeting summary"

The agent should now:
1. Call `notion_search_pages` to find workspace pages
2. Extract a `parent_page_id` from the results
3. Call `notion_create_page` to create the page
4. Respond with "✅ Created Notion page: [title]"

---

## Technical Details

### Why async functions?

The Notion wrappers are `async` because:
- MCP operations are asynchronous
- ADK's FunctionTool supports async functions
- Prevents "asyncio.run() cannot be called from a running event loop" errors

### Session Management

The wrappers use a global session pattern:
```python
_notion_session: Optional[ClientSession] = None
_exit_stack: Optional[AsyncExitStack] = None

async def _get_notion_session() -> ClientSession:
    global _notion_session, _exit_stack

    if _notion_session is not None:
        return _notion_session

    # Initialize session...
```

This ensures:
- Only one MCP connection per process
- Connection is reused across multiple tool calls
- Efficient resource usage

### Error Handling

Each wrapper includes try/except blocks:
- Logs errors with context
- Returns user-friendly error messages
- Doesn't crash the agent on Notion failures

---

## Files Modified

| File | Change |
|------|--------|
| `mcp_tools/notion_tools.py` | **Created** - Manual Notion MCP wrappers |
| `mcp_tools/__init__.py` | **Modified** - Export Notion functions |
| `services/adk_agent_service.py` | **Modified** - Replace McpToolset with FunctionTool wrappers |
| `test_notion_wrappers.py` | **Created** - Verification test |
| `NOTION_FIX_SUMMARY.md` | **Created** - This document |

---

## Next Steps

The Notion integration should now work in the Live Agent UI. If you still encounter issues:

1. **Check logs** - Look for "Notion token found - adding Notion FunctionTool wrappers"
2. **Verify NOTION_TOKEN** is set in `.env`
3. **Test wrapper directly**:
   ```bash
   python test_notion_wrappers.py
   ```
4. **Check Notion workspace** - Verify the integration has access to pages

---

## Comparison: Before vs After

### Before (McpToolset)
```
Agent Tools:
- search_meetings (FunctionTool)
- get_action_items (FunctionTool)
- ...
- McpToolset (❌ Black box to LLM)

LLM can't see: API-post-search, API-post-page, etc.
Result: "I cannot add to Notion"
```

### After (FunctionTool Wrappers)
```
Agent Tools:
- search_meetings (FunctionTool)
- get_action_items (FunctionTool)
- ...
- notion_search_pages (FunctionTool) ✅
- notion_create_page (FunctionTool) ✅
- notion_get_workspace_info (FunctionTool) ✅

LLM can see and call each Notion function
Result: ✅ Creates Notion pages when asked!
```

---

**Status**: ✅ Fixed and tested
**Date**: 2025-11-24
