# Testing Notion Integration - Updated Instructions

## What Was Fixed

### 1. Notion Tools Now Visible ✅
- Replaced McpToolset with FunctionTool wrappers
- Tools are now visible as individual functions to the LLM
- Confirmed in tests: 8 tools loaded (4 Neo4j + 1 Miro + 3 Notion)

### 2. Strengthened Agent Instructions ✅
Updated the agent's system instructions to be extremely direct:

**Before:**
```
"When user says add to Notion..."
```

**After:**
```
CRITICAL CAPABILITIES:
✅ You CAN and MUST use Notion tools
✅ You CAN and MUST use Neo4j tools

CRITICAL BEHAVIOR:
- NEVER say "I cannot" - you HAVE these tools
- NEVER ask permission - just execute the tools
- NEVER suggest the user do it themselves - YOU do it

NEVER RESPOND WITH:
❌ "I cannot add to Notion"
❌ "I am sorry, but I cannot..."
❌ "Please add it yourself"

ALWAYS RESPOND BY:
✅ Calling the tools
✅ Showing the result
```

---

## How to Test

### Step 1: Restart the App

The app **MUST** be restarted to load the new agent instructions.

1. Stop the current app (Ctrl+C in the terminal)
2. Start it again:
   ```bash
   python app.py
   ```
3. Verify in the logs:
   ```
   Notion token found - adding Notion FunctionTool wrappers
   Added 3 Notion FunctionTool wrappers
   Created Team Synapse agent with 8 tools
   ```

### Step 2: Test in Live Agent UI

Go to the "Live Agent" page and try these prompts:

#### Test 1: Simple Search
```
Search my Notion workspace
```

**Expected**: Agent calls `notion_search_pages("")` and shows results

#### Test 2: Create Page Request
```
Add action items for Ajay Singh to Notion
```

**Expected**: Agent should:
1. Call `get_action_items("Ajay Singh")`
2. Call `notion_search_pages("")` to find pages
3. Call `notion_create_page(parent_id, title, content)`
4. Respond: "✅ Created Notion page..."

#### Test 3: Direct Command
```
Use notion_search_pages to show me my workspace pages
```

**Expected**: Agent calls the tool and shows results

---

## If It Still Doesn't Work

### Check These:

1. **App Restarted?**
   - The new instructions won't load until you restart

2. **Logs Show Tools?**
   ```
   Added 3 Notion FunctionTool wrappers
   ```

3. **NOTION_TOKEN Set?**
   - Check `.env` has `NOTION_TOKEN=your_token`

4. **Try Simpler Prompt:**
   ```
   Call notion_search_pages
   ```

### Debug Steps:

If the agent still refuses:

1. **Check what the agent says** - copy the exact response
2. **Check the logs** - any errors when tools are called?
3. **Test wrapper directly:**
   ```bash
   python test_notion_wrappers.py
   ```

---

## Technical Summary

**Root Cause**: McpToolset doesn't expose individual MCP tools to the LLM for function calling

**Solution**:
1. Created async wrapper functions in `mcp_tools/notion_tools.py`
2. Wrapped them as FunctionTools instead of using McpToolset
3. Strengthened agent instructions to be extremely directive

**Files Changed**:
- `mcp_tools/notion_tools.py` - Created async wrappers
- `mcp_tools/__init__.py` - Exported wrappers
- `services/adk_agent_service.py` - Replaced McpToolset + updated instructions

**Status**: Tools are loaded ✅, Instructions updated ✅, Ready to test!

---

## Next Step

**→ Restart the app and test with: "Search my Notion workspace"**

If it works, you should see the agent actually calling `notion_search_pages` and showing results!
