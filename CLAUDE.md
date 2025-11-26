# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Team Synapse** is a corporate memory AI system that transforms meeting recordings into structured, actionable intelligence. It uses Google Gemini AI for audio transcription/analysis and Neo4j for knowledge graph storage.

**Key Features:**
- **Multi-tenant architecture** - Each user gets isolated knowledge graph (username-based)
- Batch audio analysis (upload → transcribe → extract entities → store)
- MCP chat interface with knowledge graph tools
- Live agent with real-time audio via FastRTC + Gemini Live API
- Miro integration for visual mind maps

**Hackathon Status:** 5 days remaining - Multi-tenancy v1 complete ✅

## Commands

```bash
# Run the main application
python app.py

# Verify GCP setup
python verify_gcp_setup.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture

```
app.py                          # Main Gradio app (5 pages: Landing, Home, Ingest, Chat, Live)
    ├── validate_username()     # Username format validation
    ├── handle_username_entry() # Sets tenant_id and grants access
    ├── MCPClientWrapper        # MCP client for tool execution
    ├── handle_audio_upload()   # Batch analysis handler
    └── create_live_stream()    # FastRTC live agent

mcp_server.py                   # MCP server entry point (FastMCP)
    └── imports from mcp_tools/

mcp_tools/                      # Organized MCP tool modules
    ├── __init__.py             # Exports all tools
    ├── neo4j_tools.py          # Knowledge graph query tools (tenant-scoped)
    └── miro_tools.py           # Miro visualization tools

services/
    ├── gemini_service.py       # Gemini AI (transcription, chat, entity extraction)
    ├── neo4j_service.py        # Neo4j graph operations (tenant-aware)
    ├── gcs_service.py          # Google Cloud Storage (temp audio files)
    ├── ingestion_pipeline.py   # Orchestrates audio → analysis → storage
    └── realtime_service.py     # FastRTC WebRTC handler for live agent

ui/
    ├── theme.py                # Gradio theme (blue/indigo)
    └── components.py           # UI components (homepage sections)

config.py                       # Configuration (tenant_id is mutable)
```

## MCP Tools

The MCP server exposes these tools to the chat interface:

**Neo4j Tools** (`mcp_tools/neo4j_tools.py`):
- `tool_get_graph_stats` - Knowledge graph statistics
- `tool_get_action_items` - Action items by person
- `tool_search_meetings` - Search past meetings
- `tool_find_blockers` - Find blocked action items
- `tool_get_historical_context` - Past context on a topic
- `tool_analyze_team_health` - Team workload analysis

**Miro Tools** (`mcp_tools/miro_tools.py`):
- `tool_get_miro_board_url` - Get configured board URL
- `tool_create_meeting_mindmap` - Create visual mind map

## Neo4j Graph Schema

```
Nodes: Meeting, ActionItem, Decision, Person, Client, Project
Relationships:
  (Meeting)-[:HAS_ACTION_ITEM]->(ActionItem)
  (Meeting)-[:HAS_DECISION]->(Decision)
  (Person)-[:ASSIGNED_TO]->(ActionItem)
  (Meeting)-[:DISCUSSED_CLIENT]->(Client)
  (Meeting)-[:RELATES_TO_PROJECT]->(Project)
```

## Environment Variables

Required in `.env`:
```bash
# Google Cloud (for batch analysis via Vertex AI)
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_LOCATION=us-central1
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Live Agent (uses Google AI Studio, not Vertex)
GEMINI_API_KEY=your-api-key

# Optional: Miro integration
MIRO_API_TOKEN=your-miro-token
MIRO_BOARD_ID=your-board-id

# Optional: HF Spaces
HF_TOKEN=your-hf-token  # For TURN server credentials
```

## Key Patterns

### Service Singletons
```python
# services/neo4j_service.py
class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(...)

neo4j_service = Neo4jService()  # Global instance
```

### MCP Tool Definition
```python
# mcp_tools/neo4j_tools.py
def get_action_items(person_name: str) -> str:
    """Tool implementation (plain function)."""
    results = neo4j_service.get_action_items_by_person(person_name)
    return formatted_string

# mcp_server.py
@mcp.tool()
def tool_get_action_items(person_name: str) -> str:
    """MCP tool wrapper with docstring."""
    return get_action_items(person_name)
```

### Generator Pattern for Progress
```python
for status, analysis in ingestion_pipeline.process_audio_file(path):
    if analysis:
        # Final result available
```

## Data Flow

**Batch Analysis:**
1. User uploads audio → `handle_audio_upload()`
2. Upload to GCS → `gcs_service.upload_file()`
3. Analyze with Gemini → `gemini_service.analyze_audio()`
4. Store in Neo4j → `neo4j_service.store_meeting_data()`
5. Delete from GCS → `gcs_service.delete_file()`

**Live Agent:**
1. User speaks → FastRTC captures audio
2. Audio sent to Gemini Live API
3. Gemini extracts entities, calls tools
4. Neo4j queries return context
5. Gemini responds with audio

## Important Notes

- **GCS files are temporary** - deleted after Gemini processes them
- **Person nodes** - only created for action item assignees
- **Transcripts truncated** - max 10,000 chars in Neo4j
- **MCP server** - runs as subprocess when chat page opens
- **Live agent** - requires `GEMINI_API_KEY` (not Vertex AI)
- **Multi-tenancy** - all nodes include `tenantId` from `config.app.tenant_id`
  - Set dynamically via landing page username entry
  - All queries are tenant-scoped for complete data isolation
  - Username format: 3-50 chars, alphanumeric + `-` and `_` only

## Recent Changes (2025-11-25)

### ✅ Multi-Tenancy Implementation
**Goal:** Enable hackathon judges to test with isolated knowledge graphs

**Changes Made:**
1. **Landing Page (app.py:759-794)**
   - Added username entry form before app access
   - Validation: 3-50 chars, alphanumeric + `-_` only
   - Sets `config.app.tenant_id = username` on entry
   - Username displayed in sidebar

2. **Security Fixes (mcp_tools/neo4j_tools.py)**
   - Fixed 3 unscoped tools that leaked data between tenants:
     - `find_blockers()` - Now filters by tenantId
     - `get_historical_context()` - Now tenant-scoped
     - `analyze_team_health()` - Now isolated per tenant
   - All queries now include `{tenantId: $tenantId}` in MATCH clauses

3. **Mutable tenant_id (config.py:81)**
   - Changed from static default to `field(default="demo")`
   - Allows runtime modification per user session

4. **UI Cleanup**
   - Removed redundant `create_header()` component
   - Kept homepage hero with live stats
   - Updated navigation to handle 5 pages (added landing)

**Testing Status:** ✅ All files compile, awaiting live testing

## HuggingFace Spaces Deployment

1. Set secrets in Space settings:
   - `VERTEX_PROJECT_ID`, `VERTEX_LOCATION`, `GCS_BUCKET_NAME`
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
   - `GEMINI_API_KEY` (for live agent)
   - `HF_TOKEN` (for TURN credentials)

2. Upload `service-account-key.json` content as a secret

3. The app runs on port 7860 by default
