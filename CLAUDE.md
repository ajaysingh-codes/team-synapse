# CLAUDE.md - Team Synapse Codebase Guide

> **For AI Assistants:** This document provides comprehensive context about the Team Synapse codebase structure, architecture, development workflows, and key conventions to follow when assisting with this project.

## Table of Contents
- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Directory Structure](#directory-structure)
- [Key Components](#key-components)
- [Data Flow](#data-flow)
- [Development Setup](#development-setup)
- [Coding Conventions](#coding-conventions)
- [Common Development Tasks](#common-development-tasks)
- [External Dependencies](#external-dependencies)
- [Testing & Debugging](#testing--debugging)
- [Known Issues & Gotchas](#known-issues--gotchas)

---

## Project Overview

**Team Synapse** is a corporate memory AI system that transforms meeting recordings into structured, actionable intelligence using Google Gemini AI and stores the knowledge in a Neo4j graph database.

### Key Capabilities
- **Audio transcription and analysis** using Google Gemini 2.5 Pro via Vertex AI
- **Structured data extraction**: action items, decisions, people, clients, projects
- **Knowledge graph storage** using Neo4j for relationship mapping
- **MCP (Model Context Protocol) integration** for AI agent access to the knowledge graph
- **Interactive Gradio UI** with two modes:
  - Meeting ingestion and analysis
  - AI copilot chat interface with MCP tools

### Project Phase
Currently implementing **Phase 1-3**:
- Phase 1: Audio ingestion pipeline
- Phase 2: Gemini AI analysis
- Phase 3: Neo4j knowledge graph + MCP server

### Tech Stack
- **Python 3.9+**
- **Gradio 4.30+** - Web UI framework
- **Google Cloud Platform**:
  - Vertex AI (Gemini API)
  - Cloud Storage (temporary audio storage)
- **Neo4j** - Graph database for knowledge storage
- **MCP (Model Context Protocol)** - Tool integration for AI agents
- **FastMCP** - MCP server framework

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Gradio Web UI                           │
│  ┌────────────────────┐         ┌─────────────────────────┐   │
│  │  Ingest Meeting    │         │   Meeting Copilot       │   │
│  │  - Upload/Record   │         │   - Chat with AI        │   │
│  │  - Analyze Audio   │         │   - Query Knowledge     │   │
│  └────────┬───────────┘         └───────────┬─────────────┘   │
└───────────┼─────────────────────────────────┼─────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────┐      ┌────────────────────────────┐
│  Ingestion Pipeline     │      │   MCP Client Wrapper       │
│  - Upload to GCS        │      │   - Manages MCP session    │
│  - Call Gemini API      │      │   - Tool execution         │
│  - Store in Neo4j       │      └────────────┬───────────────┘
└───────┬─────────────────┘                   │
        │                                     │
        ▼                                     ▼
┌─────────────────────────┐      ┌────────────────────────────┐
│   Gemini Service        │◄─────│   MCP Server (subprocess)  │
│   - Audio transcription │      │   - Neo4j query tools      │
│   - Structured analysis │      │   - search_meetings        │
│   - Chat completions    │      │   - get_action_items       │
└───────┬─────────────────┘      │   - get_project_meetings   │
        │                        │   - get_client_history     │
        ▼                        │   - get_graph_stats        │
┌─────────────────────────┐      └────────────┬───────────────┘
│   Neo4j Service         │◄──────────────────┘
│   - Graph storage       │
│   - Cypher queries      │
│   - Relationship mapping│
└─────────────────────────┘

External Services:
┌─────────────────────────┐
│   Google Cloud Storage  │  (Temporary audio file storage)
└─────────────────────────┘
┌─────────────────────────┐
│   Vertex AI (Gemini)    │  (Audio analysis and chat)
└─────────────────────────┘
┌─────────────────────────┐
│   Neo4j AuraDB          │  (Knowledge graph database)
└─────────────────────────┘
```

---

## Directory Structure

```
team-synapse/
├── app.py                      # Main Gradio application entry point
├── config.py                   # Configuration management (env vars, dataclasses)
├── mcp_server.py               # MCP server exposing Neo4j tools
├── requirements.txt            # Python dependencies
├── verify_gcp_setup.py         # GCP setup verification script
├── README.md                   # User-facing documentation
├── CLAUDE.md                   # This file (AI assistant guide)
│
├── services/                   # Core business logic
│   ├── __init__.py
│   ├── gcs_service.py         # Google Cloud Storage operations
│   ├── gemini_service.py      # Gemini AI interactions
│   ├── neo4j_service.py       # Neo4j graph database operations
│   └── ingestion_pipeline.py # Orchestrates end-to-end processing
│
├── ui/                         # UI components and theme
│   ├── __init__.py
│   ├── theme.py               # Custom Gradio theme (AuroraCollab)
│   └── components.py          # Reusable UI components
│
└── utils/                      # Shared utilities
    ├── __init__.py
    └── logger.py              # Logging configuration

Configuration Files (gitignored):
├── .env                        # Environment variables (create from example)
├── service-account-key.json   # GCP credentials (download from console)
```

---

## Key Components

### 1. **app.py** - Main Application (app.py:1-867)

**Purpose**: Gradio web interface and application orchestration

**Key Classes/Functions**:
- `MCPClientWrapper` (app.py:44-248): Manages MCP client connection and tool execution
  - `connect()`: Establishes connection to MCP server subprocess
  - `process_message()`: Handles chat messages with MCP tool calling
- `create_app()` (app.py:536-851): Builds the Gradio UI
- Event handlers:
  - `handle_audio_upload()` (app.py:257-297): Processes uploaded files
  - `handle_audio_recording()` (app.py:300-356): Processes live recordings

**Important Notes**:
- Uses async/await for MCP operations
- Maintains in-memory state: `CURRENT_MEETING_CONTEXT` and `LAST_ANALYSIS`
- Two-page UI: ingestion page and chat page
- Chat interface supports Gemini function calling with MCP tools

### 2. **config.py** - Configuration Management (config.py:1-111)

**Purpose**: Centralized configuration using environment variables

**Key Classes**:
- `GoogleCloudConfig`: GCP project, location, bucket, credentials
- `GeminiConfig`: Model name, temperature, max tokens
- `Neo4jConfig`: Database connection details
- `AppConfig`: Application settings (file size, formats, etc.)
- `Config`: Main config aggregator

**Environment Variables**:
```bash
# Google Cloud
VERTEX_PROJECT_ID=your-project-id
VERTEX_LOCATION=us-central1
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Gemini
GEMINI_MODEL=gemini-2.5-pro
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_TOKENS=8192

# Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
NEO4J_ENABLED=True

# App
MAX_FILE_SIZE_MB=100
LOG_LEVEL=INFO
```

**Important**: Config validates on initialization and raises errors for missing required fields.

### 3. **services/gemini_service.py** - AI Analysis (gemini_service.py:1-398)

**Purpose**: Handles all Gemini AI interactions

**Key Methods**:
- `analyze_audio()` (gemini_service.py:148-244): **CORE METHOD**
  - Takes GCS URI and optional meeting context
  - Returns structured JSON with transcript, action items, decisions, entities
  - Uses detailed prompt engineering (see `ANALYSIS_PROMPT` at line 30)
- `extract_meeting_context()` (gemini_service.py:246-294):
  - Extracts metadata from calendar invites/agendas
  - Supports .ics files and plaintext
- `chat()` (gemini_service.py:296-323):
  - Generates chat responses with MCP tool support
  - Converts MCP tool definitions to Gemini FunctionDeclarations

**Prompt Engineering**:
- `ANALYSIS_PROMPT` (gemini_service.py:30-77): Detailed JSON schema for meeting analysis
- `CONTEXT_PROMPT` (gemini_service.py:80-113): Schema for calendar invite parsing
- `CHAT_SYSTEM_INSTRUCTION` (gemini_service.py:116-122): Chatbot persona

**Important**: Always returns pure JSON (no markdown code blocks)

### 4. **services/neo4j_service.py** - Knowledge Graph (neo4j_service.py:1-509)

**Purpose**: Manages Neo4j graph database operations

**Graph Schema**:
```cypher
Nodes:
- Meeting (meetingId, title, summary, meetingDate, sentiment, transcript, processingTimestamp)
- ActionItem (actionId, task, assignee, dueDate, priority, status)
- Decision (decisionId, description)
- Person (name, email) - only created when they own action items
- Client (name)
- Project (name)

Relationships:
- (Meeting)-[:HAS_ACTION_ITEM]->(ActionItem)
- (Meeting)-[:HAS_DECISION]->(Decision)
- (Person)-[:ASSIGNED_TO]->(ActionItem)
- (Meeting)-[:DISCUSSED_CLIENT]->(Client)
- (Meeting)-[:RELATES_TO_PROJECT]->(Project)
```

**Key Methods**:
- `store_meeting_data()` (neo4j_service.py:62-94): Main entry point for storage
- `_store_meeting_transaction()` (neo4j_service.py:96-133): ACID transaction
- Query methods (used by MCP tools):
  - `search_meetings()` (neo4j_service.py:471-505)
  - `get_action_items_by_person()` (neo4j_service.py:319-353)
  - `get_meetings_by_project()` (neo4j_service.py:355-384)
  - `get_client_relationships()` (neo4j_service.py:386-424)
  - `get_knowledge_graph_summary()` (neo4j_service.py:426-469)

**Important Design Decision**: Only creates Person nodes for action item assignees (not all meeting participants). This keeps the graph focused on actionable relationships.

### 5. **services/ingestion_pipeline.py** - Orchestration (ingestion_pipeline.py:1-276)

**Purpose**: Orchestrates the complete ingestion workflow

**Main Flow** (`process_audio_file()` at line 71-206):
1. Validate file and generate meeting ID
2. Upload to GCS (temporary storage)
3. Call Gemini AI for analysis
4. Merge optional meeting context (from calendar invite)
5. Store in Neo4j knowledge graph
6. Cleanup (delete GCS file and temp files)

**Generator Pattern**: Yields status updates for real-time UI feedback:
```python
for status, analysis in ingestion_pipeline.process_audio_file(audio_path):
    # Update UI with status
    if analysis:
        # Display final results
```

**Important**: All GCS files are temporary and deleted after processing.

### 6. **mcp_server.py** - MCP Tool Server (mcp_server.py:1-111)

**Purpose**: Exposes Neo4j query capabilities as MCP tools

**Available Tools**:
1. `search_meetings` (mcp_server.py:13-28): Full-text search
2. `get_action_items` (mcp_server.py:31-47): Action items by person
3. `get_project_meetings` (mcp_server.py:50-65): Meetings by project
4. `get_client_history` (mcp_server.py:68-86): Client relationships
5. `get_graph_stats` (mcp_server.py:89-105): Knowledge graph statistics

**Implementation**: Uses `FastMCP` framework with `@mcp.tool()` decorator

**Important**: Runs as a subprocess launched by the main app when user switches to chat mode.

### 7. **ui/theme.py** - Custom Theme (ui/theme.py:1-55)

**Purpose**: Custom Gradio theme for professional appearance

**Theme**: `AuroraCollab` - Indigo primary, teal accent, slate neutral
**Fonts**:
- UI: Quicksand (Google Font)
- Mono: IBM Plex Mono (Google Font)

---

## Data Flow

### Meeting Ingestion Flow

```
User uploads audio
    ↓
[app.py: handle_audio_upload()]
    ↓
[ingestion_pipeline.process_audio_file()]
    ↓
1. Upload to GCS → [gcs_service.upload_file()]
    ↓
2. Analyze with Gemini → [gemini_service.analyze_audio()]
   - Transcribes audio
   - Extracts structured data (JSON)
    ↓
3. Store in Neo4j → [neo4j_service.store_meeting_data()]
   - Creates Meeting node
   - Creates ActionItem, Decision nodes
   - Links to Person, Client, Project nodes
    ↓
4. Cleanup → [gcs_service.delete_file()]
    ↓
Return analysis JSON to UI
```

### Chat/Query Flow

```
User asks question
    ↓
[app.py: MCPClientWrapper.process_message()]
    ↓
1. Convert Gradio history to Gemini Content
    ↓
2. Call Gemini with MCP tools → [gemini_service.chat()]
    ↓
3. If Gemini requests tool:
   - Execute via MCP → [mcp_server.py: tool function]
   - Query Neo4j → [neo4j_service: query method]
   - Return result to Gemini
    ↓
4. Gemini generates final response
    ↓
Display to user
```

---

## Development Setup

### Prerequisites
1. **Google Cloud Account** with billing enabled
2. **Neo4j AuraDB** account (free tier works)
3. **Python 3.9+**
4. **Git**

### Step-by-Step Setup

```bash
# 1. Clone and create virtual environment
git clone <repo-url>
cd team-synapse
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up Google Cloud
# Enable APIs: Vertex AI, Cloud Storage
gcloud services enable aiplatform.googleapis.com storage.googleapis.com

# Create GCS bucket
gsutil mb -l us-central1 gs://your-unique-bucket-name

# Create service account and download key
gcloud iam service-accounts create team-synapse
# Grant roles: aiplatform.user, storage.objectAdmin
# Download key as service-account-key.json

# 4. Set up Neo4j
# Create free AuraDB instance at: https://console.neo4j.io
# Note URI, username, password

# 5. Configure environment variables
# Create .env file with all required variables (see config.py section above)

# 6. Verify setup
python verify_gcp_setup.py

# 7. Run application
python app.py
```

---

## Coding Conventions

### Python Style
- **PEP 8** compliance
- **Type hints** throughout (using `typing` module)
- **Docstrings** for all public functions/methods (Google style)
- **Dataclasses** for configuration and data structures

### Error Handling
- Use **try-except** blocks with specific exception types
- **Log errors** before raising or returning error states
- **Non-critical failures** (e.g., Neo4j storage) should not block the main workflow

Example from ingestion_pipeline.py:180-183:
```python
except Exception as neo4j_error:
    logger.error(f"Neo4j storage error: {neo4j_error}", exc_info=True)
    yield f"⚠️ Neo4j storage error (non-critical): {str(neo4j_error)}", analysis
```

### Logging
- Use the centralized logger from `utils/logger.py`
- Levels: DEBUG (verbose), INFO (progress), WARNING (recoverable issues), ERROR (failures)
- Include context in log messages: `logger.info(f"Processing meeting: {meeting_id}")`

### Configuration
- **ALL** configurable values go in `config.py` or environment variables
- **NO** hardcoded credentials, endpoints, or magic numbers
- Validate configuration on startup

### Service Pattern
- Each external dependency has a **service class** in `services/`
- Services are **singletons** (instantiated once at module level)
- Services handle their own initialization and connection management

Example pattern:
```python
class MyService:
    def __init__(self):
        # Initialize connections
        logger.info("Service initialized")

    def operation(self, params):
        try:
            # Do work
            return result
        except Exception as e:
            logger.error(f"Error: {e}")
            raise

# Global instance
my_service = MyService()
```

### UI/UX Patterns
- Use **generators** for long-running operations to provide progress updates
- Return **user-friendly messages** (not raw exceptions)
- Use **emoji** sparingly for visual clarity: ✅ ❌ ⚠️ 🧠 📊

---

## Common Development Tasks

### Adding a New MCP Tool

1. **Add query method to Neo4j service** (services/neo4j_service.py):
```python
def get_my_data(self, param: str) -> List[Dict[str, Any]]:
    query = """
    MATCH (n:Node {property: $param})
    RETURN n.data AS data
    """
    with self.driver.session(database=self.database) as session:
        result = session.run(query, {"param": param})
        return [dict(record) for record in result]
```

2. **Add MCP tool** (mcp_server.py):
```python
@mcp.tool()
def my_tool(param: str) -> str:
    """
    Description of what this tool does.

    Args:
        param: Description of parameter
    """
    results = neo4j_service.get_my_data(param)
    if not results:
        return "No data found."

    # Format results as string
    return "\n".join([r['data'] for r in results])
```

3. **Test the tool** in the chat interface after restarting the app.

### Modifying the Analysis Schema

1. **Update the prompt** in `services/gemini_service.py`:
   - Modify `ANALYSIS_PROMPT` (gemini_service.py:30-77)
   - Add new fields to the JSON schema

2. **Update validation** if adding required fields:
   - Modify `_validate_analysis()` (gemini_service.py:368-393)

3. **Update Neo4j storage** if persisting new fields:
   - Modify `_create_meeting_node()` or add new node creation methods
   - Update the graph schema documentation in this file

4. **Test thoroughly** with sample audio files

### Adding a UI Component

1. **Create component function** in `ui/components.py`:
```python
def my_component(data: Dict[str, Any]) -> str:
    """Generate HTML/Markdown for component."""
    return f"<div>{data['field']}</div>"
```

2. **Use in app.py** in the relevant event handler or output

3. **Add custom CSS** in `create_app()` if needed (app.py:539-730)

### Changing the Gemini Model

1. **Update environment variable**: `GEMINI_MODEL=gemini-1.5-flash-002`
2. **Or modify default** in config.py:40
3. **Adjust temperature/tokens** based on model capabilities
4. **Test thoroughly** - different models have different behaviors

---

## External Dependencies

### Google Cloud Platform

**Required APIs**:
- Vertex AI API (`aiplatform.googleapis.com`)
- Cloud Storage API (`storage.googleapis.com`)

**Required IAM Roles**:
- `roles/aiplatform.user` - For Gemini API calls
- `roles/storage.objectAdmin` - For GCS bucket operations

**Cost Considerations**:
- Gemini 2.5 Pro: ~$3.50 per 1M input tokens, ~$10.50 per 1M output tokens
- Cloud Storage: Minimal (files are temporary)
- Audio analysis of 30-minute meeting: ~$0.10-0.30

**Region**: Default is `us-central1` for optimal Vertex AI availability

### Neo4j AuraDB

**Recommended Tier**: Free tier is sufficient for development/demo
- 50k nodes, 175k relationships
- Shared compute

**Connection**:
- Uses official `neo4j` Python driver
- Connection string format: `neo4j+s://xxxxx.databases.neo4j.io`
- Default database: `neo4j`

**Indexes**: Automatically created on startup (neo4j_service.py:44-60)

**Backup**: AuraDB provides automated backups on paid tiers

### Model Context Protocol (MCP)

**Framework**: FastMCP (simplified MCP server implementation)
- GitHub: https://github.com/jlowin/fastmcp
- Documentation: https://docs.mcp.ai

**Communication**: Uses stdio transport (subprocess)
- Server runs as child process of main app
- JSON-RPC protocol over stdin/stdout

**Tool Schema**: MCP tools are automatically converted to Gemini FunctionDeclarations

### Gradio

**Version**: 4.30+
**Key Features Used**:
- `gr.Blocks` for custom layouts
- `gr.Chatbot` with `type="messages"` for structured chat
- `gr.Audio` for recording
- Custom themes via `gradio.themes`
- Async event handlers

**Ports**: Default is 7860
**Share**: `share=True` creates temporary public URL via Gradio tunneling

---

## Testing & Debugging

### Manual Testing

**Test Audio Files**:
- Use 30-60 second recordings for quick testing
- Record yourself saying the sample script from README.md:155-163
- Test with different formats: MP3, WAV, M4A

**Test Queries**:
```
"What action items are assigned to Sarah?"
"Find meetings about Project Phoenix"
"Show me graph statistics"
"What did we discuss with Acme Corp?"
```

### Logging

**Enable DEBUG logging**:
```bash
export LOG_LEVEL=DEBUG
python app.py
```

**Key log messages**:
- `"Processing meeting: {meeting_id}"` - Start of ingestion
- `"Gemini analysis completed successfully"` - Analysis done
- `"Stored meeting in Neo4j: {meeting_id}"` - Graph storage success
- `"Connected to MCP server"` - MCP tools available

### Common Issues

**Issue**: "GCS_BUCKET_NAME must be set"
- **Cause**: Missing or invalid bucket name in .env
- **Solution**: Create GCS bucket and update .env

**Issue**: "Authentication failed"
- **Cause**: Invalid service account credentials
- **Solution**: Verify GOOGLE_APPLICATION_CREDENTIALS path, check IAM roles

**Issue**: "Neo4j connection failed"
- **Cause**: Invalid URI, username, or password
- **Solution**: Check Neo4j console for correct credentials, verify network access

**Issue**: MCP tools not working
- **Cause**: MCP server failed to start or connect
- **Solution**: Check logs for MCP server errors, verify mcp_server.py runs standalone

**Issue**: Gemini returns invalid JSON
- **Cause**: Model hallucination or prompt ambiguity
- **Solution**: Check raw response in logs, adjust ANALYSIS_PROMPT if needed

### Debugging Tools

**Verify GCP Setup**:
```bash
python verify_gcp_setup.py
```

**Test Neo4j Connection**:
```python
from services.neo4j_service import neo4j_service
stats = neo4j_service.get_knowledge_graph_summary()
print(stats)
```

**Test MCP Server Standalone**:
```bash
python mcp_server.py
# Should start and wait for stdin
```

**Query Neo4j Browser**:
- Go to Neo4j console → Open Neo4j Browser
- Run: `MATCH (n) RETURN n LIMIT 25`

---

## Known Issues & Gotchas

### 1. Temporary File Cleanup
- Files in `/tmp/gradio/` are automatically deleted after processing
- Don't rely on file paths persisting after ingestion

### 2. Neo4j Transaction Size
- Transcripts are truncated to 10,000 characters (neo4j_service.py:159)
- Neo4j free tier has memory limits for large transactions

### 3. Gemini Rate Limits
- Vertex AI has quota limits (default: 5 req/minute for Gemini Pro)
- For high volume, request quota increase in GCP console

### 4. MCP Server Lifecycle
- MCP server is started when user switches to chat page
- Server runs as subprocess - if main app crashes, orphan processes may remain
- Use `ps aux | grep mcp_server` to check for orphans

### 5. Person Node Creation
- Only creates Person nodes for action item assignees (not all participants)
- This is intentional to keep graph focused
- Calendar invite attendees are stored in Meeting node metadata

### 6. Audio File Size
- Default limit: 100MB (configurable via MAX_FILE_SIZE_MB)
- Vertex AI has limits on audio duration (check docs for current limits)

### 7. GCS Bucket Region
- GCS bucket should be in same region as Vertex AI (us-central1)
- Cross-region transfers may incur egress costs

### 8. Chat History
- Chat history is in-memory only (lost on page refresh)
- Gradio chatbot uses `type="messages"` format

### 9. Meeting Context Merging
- If both calendar invite and audio are provided:
  - Calendar metadata takes precedence for title/date
  - Gemini analysis provides transcript and entities
- Attendee name matching is fuzzy (case-insensitive substring)

### 10. Neo4j Indexes
- Indexes are created on first run
- If database is reset, restart app to recreate indexes

---

## Key Files Reference

### Critical Files (Do Not Break!)
- `config.py` - All services depend on this
- `services/gemini_service.py` - Core AI functionality
- `services/neo4j_service.py` - Knowledge graph schema
- `mcp_server.py` - Tools for AI copilot

### Configuration Files
- `.env` - Environment variables (gitignored, required)
- `requirements.txt` - Python dependencies
- `service-account-key.json` - GCP credentials (gitignored, required)

### Entry Points
- `app.py:main()` - Start Gradio UI
- `mcp_server.py:main()` - Start MCP server (called by app)

### Documentation
- `README.md` - User-facing setup and usage guide
- `CLAUDE.md` - This file (developer/AI assistant guide)

---

## Best Practices for AI Assistants

When working on this codebase:

1. **Always read config.py first** to understand available configuration options
2. **Check the logs** when debugging - they are comprehensive
3. **Test with small audio files** (30 seconds) during development
4. **Validate JSON** when modifying Gemini prompts
5. **Use transactions** for Neo4j writes (see `_store_meeting_transaction`)
6. **Handle errors gracefully** - don't let Neo4j failures block analysis
7. **Update this file** when making significant architectural changes
8. **Test MCP tools** after modifying neo4j_service query methods
9. **Preserve type hints** when modifying function signatures
10. **Follow the service pattern** when adding new integrations

---

## Future Roadmap (Not Yet Implemented)

**Phase 4**: Enhanced Knowledge Graph
- Relationship inference (e.g., Person→Client)
- Temporal tracking (meeting series)

**Phase 5**: Additional MCP Servers
- Miro integration (visual collaboration)
- Notion integration (documentation)
- ElevenLabs integration (text-to-speech)

**Phase 6**: Context-Aware Dashboard
- Google ADK integration
- Proactive action item reminders
- Meeting preparation summaries

---

## Version History

- **2025-01**: Phase 1-3 complete (audio ingestion, Gemini analysis, Neo4j + MCP)
- **Initial Commit**: Hackathon submission (MCP 1-Year Anniversary)

---

## Contact & Support

**Project**: Team Synapse - Corporate Memory AI
**Hackathon**: MCP 1-Year Anniversary
**Track**: Agent App - Productivity

For issues or questions, refer to README.md troubleshooting section.

---

**Last Updated**: 2025-11-20
**Document Version**: 1.0.0
