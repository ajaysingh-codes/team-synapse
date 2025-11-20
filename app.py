"""
Team Synapse - Main Application
Phase 1-3: Audio Ingestion & Analysis Pipeline

A professional Gradio interface for the Team Synapse corporate memory system.
"""
import asyncio
import json
import os
from typing import Optional, Dict, Any, Union, List
import html
from contextlib import AsyncExitStack

import gradio as gr
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from vertexai.generative_models import Content, Part

from services import ingestion_pipeline
from services.gemini_service import gemini_service
from ui import (
    seafoam,
    create_header,
    format_analysis_summary,
)
from config import config
from utils import setup_logger


# Setup logging
logger = setup_logger(__name__, config.app.log_level)

# In-memory storage of the most recently extracted meeting context.
# This keeps the hackathon demo simple by letting the user first upload
# an invite/agenda, then analyze audio using the same page.
CURRENT_MEETING_CONTEXT: Optional[Dict[str, Any]] = None
LAST_ANALYSIS: Optional[Dict[str, Any]] = None


# ============================================================================
# MCP CLIENT WRAPPER
# ============================================================================

class MCPClientWrapper:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.tools: List[Any] = []
        self.is_connected = False
    
    async def connect(self, server_script: str = "mcp_server.py"):
        """Connect to the MCP server subprocess."""
        if self.is_connected:
            return "✅ Already connected to MCP server."

        try:
            logger.info(f"Connecting to MCP server: {server_script}")
            
            # Check if file exists
            if not os.path.exists(server_script):
                return f"❌ Server script not found: {server_script}"

            server_params = StdioServerParameters(
                command="python",
                args=[server_script],
                env=None
            )
            
            self.exit_stack = AsyncExitStack()
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio_transport[0], stdio_transport[1])
            )
            
            await self.session.initialize()
            
            # List available tools
            result = await self.session.list_tools()
            self.tools = result.tools
            
            self.is_connected = True
            tool_names = [t.name for t in self.tools]
            logger.info(f"Connected to MCP server. Tools: {tool_names}")
            
            return f"✅ Connected to MCP Server. Loaded tools: {', '.join(tool_names)}"
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return f"❌ Connection failed: {str(e)}"

    async def process_message(self, message: str, history: List[Dict[str, Any]]):
        """
        Process a user message through Gemini with MCP tools, showing tool calls.
        
        Args:
            message: The user's input message
            history: Gradio chat history (list of dicts with role/content)
        """
        if not message.strip():
            yield "", history
            return

        if not self.is_connected:
            # Auto-connect if not connected
            await self.connect()
            if not self.is_connected:
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": "⚠️ Error: Not connected to MCP server."})
                yield "", history
                return

        # Add user message to history
        history.append({"role": "user", "content": message})
        yield "", history

        # 1. Convert Gradio history to Gemini Content
        # Gradio 'messages' format: {"role": "user"|"assistant", "content": str}
        gemini_history = []
        
        # Note: We need to filter out metadata-only messages (like tool logs) 
        # if we want to keep the context clean for Gemini, OR we format them as tool responses.
        # For simplicity, we rebuild the history for Gemini from the 'visible' conversation
        # but we must be careful not to send raw JSON logs if Gemini doesn't expect them as Content.
        
        # Actually, simpler approach for Gemini context:
        # We construct a clean list of Content objects.
        # If we displayed a tool call to the user, we should include it in Gemini's history 
        # as a FunctionCall/Response pair if possible, or just text if we are simulating.
        # But Gemini API is strict about FunctionCall/Response pairing.
        
        # Strategy: We maintain the actual Gemini history separately or rebuild it carefully.
        # Rebuilding is safer to ensure state consistency.
        
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            metadata = msg.get("metadata", {})
            
            if role == "user":
                gemini_history.append(Content(role="user", parts=[Part.from_text(content)]))
            elif role == "assistant":
                # Check if this was a tool call visualization
                if metadata.get("title") and "Using tool" in metadata.get("title"):
                    # This is our visualization of the tool call.
                    # We don't send this literal text to Gemini as a previous turn usually, 
                    # because Gemini remembers its own function calls from the actual API history.
                    # However, since we are rebuilding history from scratch each time (stateless),
                    # we might miss the "memory" of the tool call unless we reconstruct the FunctionCall part.
                    
                    # For this MVP, we will rely on the text content for context, 
                    # or simply treat previous turns as text.
                    # To do it strictly correctly requires tracking FunctionCall objects.
                    # Let's treat previous turns as text for now to avoid complex state management,
                    # as Gemini is robust enough to understand the context from text history.
                    pass 
                else:
                    # Regular text response
                    gemini_history.append(Content(role="model", parts=[Part.from_text(str(content))]))
        
        # 2. Call Gemini
        try:
            # Initial call
            response = gemini_service.chat(gemini_history, self.tools)
            
            # Loop for tool calls
            while response.candidates[0].function_calls:
                function_call = response.candidates[0].function_calls[0]
                tool_name = function_call.name
                tool_args = dict(function_call.args)
                
                logger.info(f"Gemini requested tool execution: {tool_name} with {tool_args}")
                
                # Display tool usage to User
                history.append({
                    "role": "assistant",
                    "content": f"I'll use the `{tool_name}` tool to help answer that.",
                    "metadata": {
                        "title": f"🛠️ Using tool: {tool_name}",
                        "log": f"Parameters: {json.dumps(tool_args, indent=2)}"
                    }
                })
                yield "", history
                
                # Update Gemini history with the model's function call
                gemini_history.append(response.candidates[0].content)
                
                # Execute tool
                try:
                    result = await self.session.call_tool(tool_name, arguments=tool_args)
                    
                    # Extract text content
                    tool_output = ""
                    if result.content:
                        for c in result.content:
                            if hasattr(c, "text"):
                                tool_output += c.text
                            else:
                                tool_output += str(c)
                                
                    # Display result to User
                    # We use a collapsible detail for the result
                    history.append({
                        "role": "assistant",
                        "content": f"Tool output received.",
                        "metadata": {
                            "title": f"✅ Result: {tool_name}",
                            "log": tool_output
                        }
                    })
                    yield "", history
                    
                except Exception as tool_err:
                    logger.error(f"Tool execution failed: {tool_err}")
                    tool_output = f"Error: {str(tool_err)}"
                    history.append({
                        "role": "assistant",
                        "content": f"Error executing tool.",
                        "metadata": {
                            "title": f"❌ Error: {tool_name}",
                            "log": str(tool_err)
                        }
                    })
                    yield "", history

                # Send result back to Gemini
                part = Part.from_function_response(
                    name=tool_name,
                    response={"result": tool_output}
                )
                
                # We treat the function response as a user-role message in the API
                gemini_history.append(Content(role="user", parts=[part]))
                
                # Get next response
                response = gemini_service.chat(gemini_history, self.tools)

            # Final text response
            final_text = response.text if response.text else "(No text response)"
            history.append({"role": "assistant", "content": final_text})
            yield "", history

        except Exception as e:
            logger.error(f"Error in chat loop: {e}")
            history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
            yield "", history

# Initialize global client
mcp_client = MCPClientWrapper()


# ============================================================================
# EVENT HANDLERS
# ============================================================================

def handle_audio_upload(audio_file: Optional[str], context_file: Optional[str]) -> tuple:
    """
    Handle uploaded audio file processing with optional context.
    """
    global CURRENT_MEETING_CONTEXT, LAST_ANALYSIS

    if audio_file is None:
        return "⚠️ Please upload an audio file.", "", "", _build_graph_html(None)
    
    logger.info(f"Processing uploaded file: {audio_file}")
    
    if context_file:
        try:
            with open(context_file, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            if raw_text.strip():
                CURRENT_MEETING_CONTEXT = gemini_service.extract_meeting_context(raw_text)
                logger.info("Extracted meeting context from uploaded file")
        except Exception as e:
            logger.warning(f"Could not extract context: {e}")
    
    final_status = ""
    final_analysis: Optional[Dict[str, Any]] = None
    
    for status, analysis in ingestion_pipeline.process_audio_file(
        audio_file,
        meeting_context=CURRENT_MEETING_CONTEXT,
    ):
        final_status = status
        if analysis:
            final_analysis = analysis
    
    if final_analysis:
        LAST_ANALYSIS = final_analysis
        clean_status = _simplify_status_message(final_status, had_analysis=True)
        action_items_md = _format_action_items(final_analysis)
        summary_md = format_analysis_summary(final_analysis)
        graph_html = _build_graph_html(final_analysis)
        return clean_status, summary_md, action_items_md, graph_html
    
    return _simplify_status_message(final_status, had_analysis=False), "", "", _build_graph_html(None)


def handle_audio_recording(audio_file: Optional[Any], context_file: Optional[str]) -> tuple:
    """
    Handle live audio recording processing with optional context.
    """
    import os
    global CURRENT_MEETING_CONTEXT, LAST_ANALYSIS
    
    if audio_file is None:
        return "⚠️ Please record some audio first.", "", "", _build_graph_html(None)
    
    audio_path = None
    if isinstance(audio_file, tuple):
        audio_path = audio_file[1] if len(audio_file) > 1 and isinstance(audio_file[1], str) else audio_file[0]
    elif isinstance(audio_file, str):
        audio_path = audio_file
    else:
        return "⚠️ Invalid audio format. Please try recording again.", "", "", _build_graph_html(None)
    
    if not audio_path or not os.path.exists(audio_path):
        return "⚠️ Audio file not found. Please record again.", "", "", _build_graph_html(None)
    
    logger.info(f"Processing recorded audio: {audio_path}")
    
    if context_file:
        try:
            with open(context_file, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            if raw_text.strip():
                CURRENT_MEETING_CONTEXT = gemini_service.extract_meeting_context(raw_text)
                logger.info("Extracted meeting context from uploaded file")
        except Exception as e:
            logger.warning(f"Could not extract context: {e}")
    
    final_status = ""
    final_analysis: Optional[Dict[str, Any]] = None
    
    try:
        for status, analysis in ingestion_pipeline.process_audio_file(
            audio_path,
            meeting_context=CURRENT_MEETING_CONTEXT,
        ):
            final_status = status
            if analysis:
                final_analysis = analysis
        
        if final_analysis:
            LAST_ANALYSIS = final_analysis
            clean_status = _simplify_status_message(final_status, had_analysis=True)
            action_items_md = _format_action_items(final_analysis)
            summary_md = format_analysis_summary(final_analysis)
            graph_html = _build_graph_html(final_analysis)
            return clean_status, summary_md, action_items_md, graph_html
        
        return _simplify_status_message(final_status, had_analysis=False), "", "", _build_graph_html(None)
    except Exception as e:
        logger.error(f"Error processing recorded audio: {e}", exc_info=True)
        return f"❌ Error processing audio: {str(e)}", "", "", _build_graph_html(None)


def _format_action_items(analysis: Dict[str, Any]) -> str:
    """Format action items from analysis as clean Markdown."""
    if not analysis:
        return ""
    
    parts = []
    title = analysis.get("meetingTitle", "Meeting")
    parts.append(f"## 📋 {title}\n")
    
    action_items = analysis.get("actionItems", [])
    if action_items:
        parts.append("### ✅ Action Items\n")
        for idx, item in enumerate(action_items, 1):
            task = item.get("task", "")
            assignee = item.get("assignee", "unassigned")
            due = item.get("dueDate", "none")
            priority = item.get("priority", "unspecified")
            
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority.lower(), "⚪")
            
            parts.append(f"{idx}. {priority_emoji} **{task}**")
            if assignee != "unassigned":
                parts.append(f"   - Assignee: {assignee}")
            if due != "none":
                parts.append(f"   - Due: {due}")
            parts.append("")
    else:
        parts.append("_No action items detected._\n")
    
    decisions = analysis.get("keyDecisions", [])
    if decisions:
        parts.append("### 🎯 Key Decisions\n")
        for decision in decisions:
            parts.append(f"- {decision}")
        parts.append("")
    
    stats = []
    if "mentionedPeople" in analysis:
        stats.append(f"👥 {len(analysis['mentionedPeople'])} people")
    if "mentionedClients" in analysis:
        stats.append(f"🏢 {len(analysis['mentionedClients'])} clients")
    if "mentionedProjects" in analysis:
        stats.append(f"📊 {len(analysis['mentionedProjects'])} projects")
    
    if stats:
        parts.append(f"\n**Detected:** {' • '.join(stats)}")
    
    return "\n".join(parts)


def _simplify_status_message(raw_status: str, had_analysis: bool) -> str:
    """Collapse the verbose pipeline status down to a compact, UX-friendly string."""
    if not raw_status:
        return "**Status:** Ready"
    
    if "❌" in raw_status or "Error" in raw_status:
        return raw_status
    
    if "Neo4j storage failed" in raw_status or "Neo4j storage error" in raw_status:
        if had_analysis:
            return "✅ Analysis complete (graph storage had a non-critical issue)."
        return "⚠️ Graph storage encountered an issue."
    
    if had_analysis:
        if "Stored in Neo4j knowledge graph" in raw_status:
            return "✅ Analysis complete and linked into the knowledge graph."
        return "✅ Analysis complete."
    
    return raw_status


def _build_graph_html(analysis: Optional[Dict[str, Any]]) -> str:
    """Build a lightweight, static 'graph snapshot'."""
    if not analysis:
        return """
        <div class="ts-graph-empty">
            <div><strong>No graph yet.</strong> Run an analysis to see how this meeting links to people, clients, and projects.</div>
            <div class="ts-graph-hint">We’ll render a small topology-style snapshot of the knowledge graph here.</div>
        </div>
        """
    
    meeting_title = html.escape(analysis.get("meetingTitle", "Meeting"))
    meeting_date = html.escape(analysis.get("meetingDate", "unknown"))
    sentiment = html.escape(analysis.get("sentiment", "neutral"))
    
    action_items = analysis.get("actionItems", []) or []
    mentioned_clients = analysis.get("mentionedClients", []) or []
    mentioned_projects = analysis.get("mentionedProjects", []) or []
    
    people = sorted(
        {
            html.escape(str(item.get("assignee")))
            for item in action_items
            if item.get("assignee") and str(item.get("assignee")).lower() != "unassigned"
        }
    )
    
    def _render_pills(values, empty_label: str) -> str:
        if not values:
            return f'<span class="ts-pill ts-pill-muted">{empty_label}</span>'
        return "".join(f'<span class="ts-pill">{html.escape(str(v))}</span>' for v in values)
    
    if action_items:
        ai_items_html = []
        for item in action_items[:8]:
            task = html.escape(item.get("task", ""))
            assignee = item.get("assignee")
            assignee_label = f" · {html.escape(str(assignee))}" if assignee and str(assignee).lower() != "unassigned" else ""
            ai_items_html.append(
                f'<li><span class="ts-dot"></span><span class="ts-ai-task">{task}</span><span class="ts-ai-meta">{assignee_label}</span></li>'
            )
        if len(action_items) > 8:
            remaining = len(action_items) - 8
            ai_items_html.append(f'<li class="ts-ai-more">+{remaining} more…</li>')
        action_items_html = "<ul class=\"ts-ai-list\">" + "".join(ai_items_html) + "</ul>"
    else:
        action_items_html = '<div class="ts-pill ts-pill-muted">No action items detected</div>'
    
    clients_html = _render_pills(mentioned_clients, "No clients detected")
    projects_html = _render_pills(mentioned_projects, "No projects detected")
    people_html = _render_pills(people, "No owners detected")
    
    return f"""
    <div class="ts-graph-grid">
        <div class="ts-graph-card ts-graph-card-meeting">
            <div class="ts-graph-title">Meeting</div>
            <div class="ts-graph-body">
                <div class="ts-graph-meeting-title">{meeting_title}</div>
                <div class="ts-graph-meta">
                    <span class="ts-pill">📅 {meeting_date}</span>
                    <span class="ts-pill">💬 {sentiment.title()}</span>
                </div>
            </div>
        </div>
        <div class="ts-graph-card ts-graph-card-actions">
            <div class="ts-graph-title">Action Items</div>
            <div class="ts-graph-body">
                {action_items_html}
            </div>
        </div>
        <div class="ts-graph-card ts-graph-card-entities">
            <div class="ts-graph-title">Entities</div>
            <div class="ts-graph-subtitle">People (owners)</div>
            <div class="ts-graph-row">
                {people_html}
            </div>
            <div class="ts-graph-subtitle">Clients</div>
            <div class="ts-graph-row">
                {clients_html}
            </div>
            <div class="ts-graph-subtitle">Projects</div>
            <div class="ts-graph-row">
                {projects_html}
            </div>
        </div>
    </div>
    """


def _show_home_page() -> tuple:
    """Helper: show ingestion page, hide chatbot page."""
    return gr.update(visible=True), gr.update(visible=False)


async def _show_chat_page() -> tuple:
    """Helper: hide ingestion page, show chatbot page."""
    # Connect to MCP when switching to chat
    # We check connection first to avoid redundant await if possible,
    # but connect() handles idempotency.
    await mcp_client.connect()
    return gr.update(visible=False), gr.update(visible=True)


# ============================================================================
# UI CONSTRUCTION
# ============================================================================

def create_app() -> gr.Blocks:
    """Create the main Gradio application."""
    
    custom_css = """
    .header-title {
        font-size: 3rem !important;
        font-weight: 700 !important;
        color: #e5e7eb !important;
        letter-spacing: 0.03em;
        text-shadow: 0 0 40px rgba(79, 70, 229, 0.45);
        margin-bottom: 0.5rem !important;
    }
    .header-subtitle {
        font-size: 1.1rem !important;
        color: #9ca3af !important;
        font-weight: 400 !important;
    }
    .main-card {
        padding: 2rem !important;
        border-radius: 1rem !important;
        background: rgba(15, 23, 42, 0.98) !important;
        border: 1px solid rgba(31, 41, 55, 0.9) !important;
        box-shadow: 0 22px 55px rgba(15, 23, 42, 0.85) !important;
    }
    .output-card {
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
    }
    .status-text {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.95rem !important;
    }
    /* Glass-style containers */
    .glass-panel {
        background: rgba(17, 24, 39, 0.96) !important;
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        border-radius: 18px !important;
        border: 1px solid rgba(55, 65, 81, 0.85) !important;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.9) !important;
        padding: 1.5rem !important;
    }
    .action-card {
        background: rgba(22, 163, 74, 0.09);
        border-left: 4px solid #22c55e;
        padding: 0.75rem 0.9rem;
        margin-bottom: 0.5rem;
        border-radius: 0.5rem;
    }
    .action-card h4 {
        margin: 0;
        color: #bbf7d0;
    }
    .action-card p {
        margin: 0.15rem 0 0;
        font-size: 0.85rem;
        color: #e5e7eb;
    }
    /* Static graph snapshot */
    .ts-graph-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
        gap: 0.9rem;
        font-size: 0.9rem;
        color: #e5e7eb;
    }
    .ts-graph-card {
        padding: 0.9rem 1rem;
        border-radius: 0.9rem;
        background: rgba(15, 23, 42, 0.96);
        border: 1px solid rgba(55, 65, 81, 0.9);
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.9);
    }
    .ts-graph-card-actions {
        border-color: rgba(34, 197, 94, 0.7);
    }
    .ts-graph-card-entities {
        border-color: rgba(56, 189, 248, 0.7);
    }
    .ts-graph-title {
        font-weight: 600;
        letter-spacing: 0.02em;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
        font-size: 0.78rem;
        color: #c7d2fe;
    }
    .ts-graph-subtitle {
        margin-top: 0.5rem;
        margin-bottom: 0.25rem;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #a5b4fc;
    }
    .ts-graph-meeting-title {
        font-size: 0.98rem;
        font-weight: 600;
        color: #e5e7eb;
        margin-bottom: 0.4rem;
    }
    .ts-graph-meta {
        margin-top: 0.25rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
    }
    .ts-graph-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.2rem;
    }
    .ts-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.16rem 0.55rem;
        border-radius: 9999px;
        background: rgba(15, 23, 42, 0.86);
        border: 1px solid rgba(148, 163, 184, 0.5);
        font-size: 0.75rem;
        color: #e5e7eb;
        margin: 0.08rem 0.1rem 0.08rem 0;
        white-space: nowrap;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .ts-pill-muted {
        opacity: 0.7;
        border-style: dashed;
    }
    .ts-ai-list {
        list-style: none;
        padding-left: 0;
        margin: 0;
    }
    .ts-ai-list li {
        display: flex;
        align-items: baseline;
        font-size: 0.86rem;
        margin-bottom: 0.25rem;
        color: #e5e7eb;
    }
    .ts-dot {
        width: 0.4rem;
        height: 0.4rem;
        border-radius: 50%;
        background: #22c55e;
        margin-right: 0.4rem;
        margin-top: 0.28rem;
        flex-shrink: 0;
    }
    .ts-ai-task {
        font-weight: 500;
    }
    .ts-ai-meta {
        font-size: 0.78rem;
        color: #9ca3af;
        margin-left: 0.25rem;
    }
    .ts-ai-more {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 0.15rem;
    }
    .ts-graph-empty {
        padding: 0.85rem 1rem;
        border-radius: 0.9rem;
        background: rgba(15, 23, 42, 0.75);
        border: 1px dashed rgba(148, 163, 184, 0.6);
        color: #9ca3af;
        font-size: 0.88rem;
    }
    .ts-graph-hint {
        margin-top: 0.25rem;
        font-size: 0.78rem;
        color: #6b7280;
    }
    /* Page background */
    .gradio-container {
        background: #020617;
    }
    /* Better button styling */
    button {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 0.75rem !important;
        transition: all 0.18s ease !important;
    }
    button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.65) !important;
    }
    """
    
    with gr.Blocks(
        theme=seafoam,
        title="Team Synapse - Corporate Memory AI",
        analytics_enabled=False,
        css=custom_css,
    ) as app:
        
        # HEADER
        create_header()
        
        # MAIN LAYOUT
        with gr.Row():
            # LEFT SIDEBAR MENU
            with gr.Column(scale=1, min_width=200):
                gr.Markdown("### Menu")
                nav_ingest = gr.Button("🎙️ Ingest Meeting", variant="secondary", size="lg")
                nav_chat = gr.Button("💬 Meeting Copilot", variant="secondary", size="lg")
                
                # Add some spacing or other menu items if needed
                gr.Markdown("---")
                
            # RIGHT CONTENT AREA
            with gr.Column(scale=4):
                # PAGE 1: INGESTION
                with gr.Column(visible=True, elem_classes=["main-card"]) as page_ingest:
                    gr.Markdown("## 🎙️ Upload or Record Meeting")
                    with gr.Row():
                        # LEFT: Ingest
                        with gr.Column(scale=1, elem_classes=["glass-panel"]):
                            gr.Markdown("### 📥 Ingest Stream")
                            with gr.Tabs():
                                with gr.TabItem("📁 Upload Recording"):
                                    audio_input = gr.File(label="Meeting Recording", file_types=["audio"], type="filepath")
                                    context_input_upload = gr.File(label="Calendar Invite / Agenda (optional)", file_types=["text"], type="filepath", file_count="single")
                                    analyze_btn = gr.Button("✨ Analyze with Gemini", variant="primary", size="lg")
                                    gr.Markdown("""<p style="font-size: 0.9rem; color: #94a3b8; margin-top: 1rem;"><strong>Supported audio:</strong> MP3, WAV, M4A, OGG (max 100 MB)<br/><strong>Optional context:</strong> Upload a calendar invite (.ics) to auto-fill attendees.</p>""")
                                
                                with gr.TabItem("🎤 Record Live"):
                                    audio_record = gr.Audio(sources=["microphone"], type="filepath", label="Record Your Meeting", show_download_button=True)
                                    context_input_record = gr.File(label="Calendar Invite / Agenda (optional)", file_types=["text"], type="filepath", file_count="single")
                                    record_btn = gr.Button("✨ Analyze Recording", variant="primary", size="lg")
                                    gr.Markdown("""<p style="font-size: 0.9rem; color: #94a3b8; margin-top: 1rem;"><strong>Record your meeting</strong> directly in the browser.<br/><strong>Optional context:</strong> Upload a calendar invite (.ics) to auto-fill attendees.</p>""")
                            
                            status_output = gr.Markdown("**Status:** Ready", elem_classes=["status-text"])
                        
                        # RIGHT: Intelligence
                        with gr.Column(scale=2):
                            with gr.Row():
                                with gr.Column(elem_classes=["glass-panel"]):
                                    gr.Markdown("### 📝 Executive Summary")
                                    summary_output = gr.Markdown(value="", elem_classes=["output-card"])
                                with gr.Column(elem_classes=["glass-panel"]):
                                    gr.Markdown("### 🕸️ Knowledge Graph")
                                    graph_html = gr.HTML(value=_build_graph_html(None), label="Graph Preview")
                            with gr.Row():
                                with gr.Column(elem_classes=["glass-panel"]):
                                    gr.Markdown("### ⚡ Action Items")
                                    results_output = gr.Markdown(value="", elem_classes=["output-card"])
                    
                    gr.Markdown("""---<p style="text-align: center; color: #64748b; font-size: 0.9rem;">💡 <strong>Tip:</strong> For best results, upload a calendar invite first, then your recording.</p>""")
                
                # PAGE 2: CHATBOT
                with gr.Column(visible=False, elem_classes=["main-card"]) as page_chat:
                    gr.Markdown("## 💬 Meeting Copilot")
                    gr.Markdown(
                        """
                        <p style="font-size: 1.05rem; color: #94a3b8; margin-bottom: 1rem;">
                        Chat with your knowledge graph. Ask questions like:
                        </p>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
                            <span class="ts-pill">"What action items are assigned to Sarah?"</span>
                            <span class="ts-pill">"Find meetings about the Q4 roadmap."</span>
                            <span class="ts-pill">"What did we discuss with Acme Corp?"</span>
                            <span class="ts-pill">"Show me graph statistics."</span>
                        </div>
                        """
                    )
                    
                    with gr.Row():
                        # Chat Interface
                        with gr.Column(elem_classes=["glass-panel"]):
                            chatbot = gr.Chatbot(
                                value=[],
                                height=600,
                                avatar_images=(
                                    "https://api.dicebear.com/7.x/avataaars/svg?seed=User123",
                                    "https://api.dicebear.com/7.x/bottts/svg?seed=SynapseBot"
                                ),
                                show_copy_button=True,
                                render_markdown=True,
                                type="messages"
                            )
                            
                            with gr.Row():
                                msg = gr.Textbox(
                                    show_label=False,
                                    placeholder="Ask a question about your meetings...",
                                    scale=8,
                                    container=False
                                )
                                submit_btn = gr.Button("Send", variant="primary", scale=1)
                                
                            clear_btn = gr.Button("Clear Chat", variant="secondary", size="sm")
                    
                    # Chat Event Handlers
                    
            
        # EVENT BINDINGS
        nav_ingest.click(fn=_show_home_page, outputs=[page_ingest, page_chat])
        nav_chat.click(fn=_show_chat_page, outputs=[page_ingest, page_chat])
        
        analyze_btn.click(handle_audio_upload, inputs=[audio_input, context_input_upload], outputs=[status_output, summary_output, results_output, graph_html])
        record_btn.click(handle_audio_recording, inputs=[audio_record, context_input_record], outputs=[status_output, summary_output, results_output, graph_html])
        
        # Chat bindings
        msg.submit(mcp_client.process_message, [msg, chatbot], [msg, chatbot])
        submit_btn.click(mcp_client.process_message, [msg, chatbot], [msg, chatbot])
        clear_btn.click(lambda: [], None, chatbot)
    
    return app

def main():
    """Main entry point."""
    logger.info("Starting Team Synapse application...")
    
    if not config.validate():
        logger.error("Configuration validation failed. Please check your settings.")
        return
    
    logger.info("Configuration validated successfully")
    app = create_app()
    logger.info("Launching Gradio interface...")
    app.launch(server_name="0.0.0.0", server_port=7860, share=True, show_error=True)

if __name__ == "__main__":
    main()
