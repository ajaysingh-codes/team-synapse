# Using Notion with Team Synapse

## Quick Start

### 1. Setup (One-time)

**Grant Integration Access:**
1. Go to your Notion workspace
2. Create or open a page where you want summaries/action items
3. Click `•••` (top right) → **"Add connections"**
4. Select your integration

**Important:** The integration can ONLY access pages you explicitly connect to.

### 2. Using Notion in Chat

The agent now knows how to use Notion, but it needs context. Try these prompts:

#### ✅ Good Prompts (will work):

```
"Search my Notion workspace for pages"
→ Agent uses API-post-search to find your pages

"Create a Notion page with Ajay's action items"
→ Agent will search for a parent page, get action items, create page

"Add these meeting notes to Notion: [content]"
→ Agent creates a new page with the content
```

#### ❌ Prompts that need clarification:

```
"Add to my Notion database"
→ Agent needs to know WHICH database (ID or search for it)

"Update my Notion page"
→ Agent needs to know WHICH page
```

### 3. How the Agent Uses Notion

**Workflow:**
1. User asks to add something to Notion
2. Agent uses `API-post-search` to find available pages/databases
3. Agent uses `API-post-page` to create new page (or API-patch-page to update)
4. Returns the page URL to user

### 4. Available Notion Tools

The agent has access to all 19 Notion API tools:

**Common ones:**
- `API-post-search` - Search workspace
- `API-post-page` - Create a page
- `API-patch-page` - Update a page
- `API-post-database-query` - Query a database
- `API-get-self` - Get bot info

### 5. Troubleshooting

**Agent says "I cannot add to Notion"**

Possible causes:
1. **No page access** - Grant integration access to at least one page
2. **Needs more context** - Specify which page/database
3. **Agent needs restart** - Restart the app to reload instructions

**Test Notion access:**
```bash
venv/bin/python test_notion_mcp.py
```

This will verify:
- Token is valid
- MCP server connects
- Tools are available

### 6. Example Interaction

**User:** "Get my action items and create a Notion page"

**Agent will:**
1. Call `get_action_items("Your Name")`
2. Call `API-post-search` to find a parent page
3. Call `API-post-page` with:
   - Parent page ID
   - Title: "Action Items for [Name]"
   - Content: Formatted list of action items
4. Return: "✅ Created page: [URL]"

### 7. Best Practices

**For action items:**
```
"Create a Notion page listing all my action items"
```

**For meeting summaries:**
```
"After I analyze this meeting, create a Notion summary"
```

**For databases:**
```
"Search my Notion for the Projects database, then add this project"
```

### 8. Advanced: Manual Page IDs

If you know your page/database ID, you can be explicit:

```
"Create a page in parent ID abc123 with my action items"
```

Page IDs are the UUID in the URL:
`notion.so/My-Page-abc123def456` → ID is `abc123def456`

---

## Need Help?

1. **Run diagnostic:** `venv/bin/python test_notion_mcp.py`
2. **Check integration:** https://www.notion.so/profile/integrations
3. **Grant page access:** In Notion, click `•••` → Add connections
4. **Restart app:** New instructions take effect on restart
