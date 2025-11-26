"""
Team Synapse - Corporate Memory AI
A Gradio app for meeting analysis, knowledge graph storage, and AI chat.

Optimized for Hugging Face Spaces deployment.
"""
import asyncio
import json
import os
from typing import Optional, Dict, Any, List
import html
from contextlib import AsyncExitStack
from datetime import datetime

import gradio as gr
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from vertexai.generative_models import Content, Part

from services import ingestion_pipeline, neo4j_service
from services.gemini_service import gemini_service
from services.adk_agent_service import create_agent
from ui import (
    team_synapse_theme,
    create_homepage_hero,
    create_problem_section,
    create_how_it_works_section,
    create_features_grid,
    create_use_cases_section,
    create_cta_section,
)
from ui.design_system import get_design_system_css
from config import config
from utils import setup_logger

logger = setup_logger(__name__, config.app.log_level)

# Global state
CURRENT_MEETING_CONTEXT: Optional[Dict[str, Any]] = None
LAST_ANALYSIS: Optional[Dict[str, Any]] = None


# =============================================================================
# MCP CLIENT
# =============================================================================

class MCPClientWrapper:
    """Manages MCP server connection and tool execution."""

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.tools: List[Any] = []
        self.is_connected = False

    async def connect(self, server_script: str = "mcp_server.py"):
        """Connect to the MCP server subprocess."""
        if self.is_connected:
            return "Already connected to MCP server."

        try:
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
            result = await self.session.list_tools()
            self.tools = result.tools
            self.is_connected = True

            tool_names = [t.name for t in self.tools]
            logger.info(f"Connected to MCP server. Tools: {tool_names}")
            return f"Connected. Tools: {', '.join(tool_names)}"

        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            return f"Connection failed: {str(e)}"

    async def process_message(self, message: str, history: List[Dict[str, Any]]):
        """Process a user message with Gemini and MCP tools."""
        if not message.strip():
            yield "", history
            return

        if not self.is_connected:
            await self.connect()
            if not self.is_connected:
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": "Error: Not connected to MCP server."})
                yield "", history
                return

        history.append({"role": "user", "content": message})
        yield "", history

        # Build Gemini history
        gemini_history = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            metadata = msg.get("metadata") or {}

            if role == "user":
                gemini_history.append(Content(role="user", parts=[Part.from_text(content)]))
            elif role == "assistant" and not metadata.get("title"):
                gemini_history.append(Content(role="model", parts=[Part.from_text(str(content))]))

        try:
            response = gemini_service.chat(gemini_history, self.tools)

            # Handle tool calls
            while response.candidates[0].function_calls:
                func_call = response.candidates[0].function_calls[0]
                tool_name = func_call.name
                tool_args = dict(func_call.args)

                logger.info(f"Tool call: {tool_name}({tool_args})")

                history.append({
                    "role": "assistant",
                    "content": f"Using `{tool_name}` tool...",
                    "metadata": {"title": f"Tool: {tool_name}"}
                })
                yield "", history

                gemini_history.append(response.candidates[0].content)

                try:
                    result = await self.session.call_tool(tool_name, arguments=tool_args)
                    tool_output = ""
                    if result.content:
                        for c in result.content:
                            tool_output += c.text if hasattr(c, "text") else str(c)

                    history.append({
                        "role": "assistant",
                        "content": f"```\n{tool_output[:500]}{'...' if len(tool_output) > 500 else ''}\n```",
                        "metadata": {"title": f"Result: {tool_name}"}
                    })
                    yield "", history

                except Exception as e:
                    tool_output = f"Error: {str(e)}"
                    history.append({"role": "assistant", "content": tool_output})
                    yield "", history

                part = Part.from_function_response(name=tool_name, response={"result": tool_output})
                gemini_history.append(Content(role="user", parts=[part]))
                response = gemini_service.chat(gemini_history, self.tools)

            # Final response
            final_text = response.text if response.text else "No response generated."
            history.append({"role": "assistant", "content": final_text})
            yield "", history

        except Exception as e:
            logger.error(f"Chat error: {e}")
            history.append({"role": "assistant", "content": f"Error: {str(e)}"})
            yield "", history


mcp_client = MCPClientWrapper()


# =============================================================================
# EVENT HANDLERS
# =============================================================================

def handle_audio_upload(
    audio_file: Optional[str],
    context_state: Optional[Dict[str, Any]],
    session_type: str
) -> tuple:
    """Process uploaded audio file."""
    global CURRENT_MEETING_CONTEXT, LAST_ANALYSIS

    if not audio_file or not os.path.exists(audio_file):
        return "Please upload an audio file.", _build_graph_html(None)

    if context_state:
        CURRENT_MEETING_CONTEXT = context_state

    mode = (session_type or "corporate").lower()
    final_status = ""
    final_analysis = None

    try:
        for status, analysis in ingestion_pipeline.process_audio_file(
            audio_file,
            meeting_context=CURRENT_MEETING_CONTEXT,
            analysis_mode=mode,
        ):
            final_status = status
            if analysis:
                final_analysis = analysis

        if final_analysis:
            LAST_ANALYSIS = final_analysis
            return "Analysis complete!", _build_graph_html(final_analysis)

        return final_status, _build_graph_html(None)

    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        return f"Error: {str(e)}", _build_graph_html(None)


def handle_extract_context(context_file: Optional[str], context_text: str) -> tuple:
    """Extract meeting context from file/text."""
    global CURRENT_MEETING_CONTEXT

    sources = []
    if context_file and os.path.exists(context_file):
        try:
            with open(context_file, "r", encoding="utf-8", errors="ignore") as f:
                sources.append(f.read())
        except Exception as e:
            return f"Failed to read file: {e}", "{}", {}

    if context_text and context_text.strip():
        sources.append(context_text.strip())

    if not sources:
        return "Upload a file or paste text first.", "{}", {}

    try:
        combined = "\n\n".join(sources)
        extracted = gemini_service.extract_meeting_context(combined)
        CURRENT_MEETING_CONTEXT = extracted
        return "Context extracted!", json.dumps(extracted, indent=2), extracted
    except Exception as e:
        logger.error(f"Context extraction failed: {e}")
        return f"Failed: {e}", "{}", {}


def _build_graph_html(analysis: Optional[Dict[str, Any]]) -> str:
    """Build HTML visualization of analysis results."""
    if not analysis:
        return """
        <div style="padding: 2rem; text-align: center; color: #64748b; border: 2px dashed #e2e8f0; border-radius: 12px;">
            <p><strong>No analysis yet.</strong></p>
            <p>Upload and analyze a meeting to see results here.</p>
        </div>
        """

    title = html.escape(analysis.get("meetingTitle", "Meeting"))
    date = html.escape(analysis.get("meetingDate", "unknown"))
    sentiment = html.escape(analysis.get("sentiment", "neutral"))

    action_items = analysis.get("actionItems", []) or []
    clients = analysis.get("mentionedClients", []) or []
    projects = analysis.get("mentionedProjects", []) or []

    # Build action items list
    ai_html = ""
    if action_items:
        items = []
        for item in action_items[:5]:
            task = html.escape(item.get("task", ""))
            assignee = item.get("assignee", "")
            items.append(f"<li><strong>{task}</strong> - {html.escape(str(assignee))}</li>")
        if len(action_items) > 5:
            items.append(f"<li><em>+{len(action_items) - 5} more...</em></li>")
        ai_html = "<ul>" + "".join(items) + "</ul>"
    else:
        ai_html = "<p><em>No action items detected</em></p>"

    # Build entity pills
    def pills(items, label):
        if not items:
            return f"<span style='color: #94a3b8;'><em>No {label}</em></span>"
        return " ".join(
            f"<span style='background: #f1f5f9; padding: 2px 8px; border-radius: 12px; font-size: 0.85rem;'>{html.escape(str(i))}</span>"
            for i in items[:5]
        )

    return f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div style="padding: 1rem; border: 1px solid #e2e8f0; border-radius: 12px;">
            <h4 style="margin: 0 0 0.5rem 0; color: #3b82f6;">Meeting</h4>
            <p style="margin: 0; font-weight: 600;">{title}</p>
            <p style="margin: 0.25rem 0; color: #64748b;">{date} • {sentiment}</p>
        </div>
        <div style="padding: 1rem; border: 1px solid #e2e8f0; border-radius: 12px;">
            <h4 style="margin: 0 0 0.5rem 0; color: #f97316;">Action Items ({len(action_items)})</h4>
            {ai_html}
        </div>
        <div style="padding: 1rem; border: 1px solid #e2e8f0; border-radius: 12px; grid-column: span 2;">
            <h4 style="margin: 0 0 0.5rem 0; color: #10b981;">Entities</h4>
            <p><strong>Clients:</strong> {pills(clients, 'clients')}</p>
            <p><strong>Projects:</strong> {pills(projects, 'projects')}</p>
        </div>
    </div>
    """


# =============================================================================
# PAGE NAVIGATION
# =============================================================================

def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format.

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    import re

    if not username:
        return False, "Username cannot be empty"
    if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', username):
        return False, "Username must be 3-50 characters (letters, numbers, -, _ only)"
    return True, ""


def handle_username_entry(username: str):
    """
    Process username entry and enter app.

    Args:
        username: Entered username

    Returns:
        Tuple of updates for UI components
    """
    is_valid, error_msg = validate_username(username)

    if not is_valid:
        return (
            gr.update(value=f"❌ {error_msg}"),  # error_display
            gr.update(visible=True),   # landing page
            gr.update(visible=False),  # home page
            gr.update(visible=False),  # ingest page
            gr.update(visible=False),  # chat page
            gr.update(visible=False),  # live page
            gr.update(value=f"**User:** `demo`")  # username display
        )

    # Set tenant_id
    config.app.tenant_id = username
    logger.info(f"User '{username}' entered app with tenant_id: {username}")

    return (
        gr.update(value=""),  # clear error message
        gr.update(visible=False),  # hide landing
        gr.update(visible=True),   # show home
        gr.update(visible=False),  # hide ingest
        gr.update(visible=False),  # hide chat
        gr.update(visible=False),  # hide live
        gr.update(value=f"**User:** `{username}`")  # update display
    )


def show_home_page():
    """Show homepage and hide all other pages."""
    return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def show_ingest_page():
    """Show ingest page and hide all others."""
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)


async def show_chat_page():
    """Show chat page and hide all others."""
    await mcp_client.connect()
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)


def show_live_page():
    """Show live agent page and hide all others."""
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# =============================================================================
# MAIN APP
# =============================================================================

def create_app() -> gr.Blocks:
    """Create the Gradio application."""

    # Combine design system CSS with custom CSS
    design_system_css = get_design_system_css()

    custom_css = """
    /* Glass panel styling */
    .glass-panel {
        background: #ffffff;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .nav-btn { margin-bottom: 0.5rem; }

    /* Hero header styling */
    .ts-hero {
        display: flex;
        gap: 2rem;
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid rgba(148, 163, 184, 0.4);
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(59, 130, 246, 0.08) 100%);
        color: #0f172a;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }

    .ts-hero-content {
        flex: 2;
        min-width: 280px;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .ts-hero-kicker {
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-size: 0.75rem;
        color: #10b981;
        font-weight: 600;
        margin: 0;
    }

    .ts-hero-headline {
        font-size: 1.75rem;
        line-height: 1.3;
        margin: 0;
        font-weight: 700;
        color: #0f172a;
    }

    .ts-hero-subhead {
        font-size: 0.95rem;
        color: #64748b;
        margin: 0;
        line-height: 1.5;
    }

    .ts-hero-cta-group {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-top: 0.5rem;
    }

    .ts-hero-cta {
        text-decoration: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.2s;
    }

    .ts-hero-cta.primary {
        background: #10b981;
        color: white;
    }

    .ts-hero-cta.primary:hover {
        background: #059669;
    }

    .ts-hero-cta.ghost {
        background: transparent;
        color: #0f172a;
        border: 1px solid #e2e8f0;
    }

    .ts-hero-cta.ghost:hover {
        background: #f1f5f9;
    }

    .ts-hero-link {
        font-size: 0.875rem;
        color: #3b82f6;
        text-decoration: none;
        font-weight: 500;
    }

    .ts-hero-link:hover {
        text-decoration: underline;
    }

    .ts-hero-stats {
        flex: 1;
        min-width: 200px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 0.75rem;
    }

    .ts-hero-card {
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.3);
        background: rgba(255, 255, 255, 0.9);
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        text-align: center;
    }

    .ts-hero-card .label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
    }

    .ts-hero-card .value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .ts-hero {
            flex-direction: column;
        }
        .ts-hero-headline {
            font-size: 1.5rem;
        }
    }

    /* ===== POLISH & ANIMATIONS ===== */

    /* Smooth page transitions */
    .gradio-column {
        animation: fadeInPage 0.4s ease-out;
    }

    @keyframes fadeInPage {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Enhanced sidebar styling */
    .gradio-container .sidebar {
        background: linear-gradient(180deg, var(--color-neutral-50), white) !important;
        border-right: 2px solid var(--color-neutral-200) !important;
        box-shadow: var(--shadow-lg) !important;
    }

    /* Navigation button hover effects */
    .nav-btn {
        transition: all 0.3s ease !important;
        border-radius: var(--radius-lg) !important;
    }

    .nav-btn:hover {
        transform: translateX(4px) !important;
        box-shadow: var(--shadow-md) !important;
    }

    /* Button enhancements */
    button {
        transition: all 0.2s ease !important;
        border-radius: var(--radius-lg) !important;
    }

    button:hover {
        transform: translateY(-1px) !important;
        box-shadow: var(--shadow-md) !important;
    }

    button:active {
        transform: translateY(0) !important;
    }

    /* Input field polish */
    input[type="text"],
    textarea {
        border-radius: var(--radius-md) !important;
        border: 2px solid var(--color-neutral-200) !important;
        transition: all 0.2s ease !important;
    }

    input[type="text"]:focus,
    textarea:focus {
        border-color: var(--color-primary-500) !important;
        box-shadow: 0 0 0 3px var(--color-primary-100) !important;
    }

    /* File upload area enhancement */
    .file-preview {
        border-radius: var(--radius-lg) !important;
        border: 2px dashed var(--color-neutral-300) !important;
        transition: all 0.3s ease !important;
    }

    .file-preview:hover {
        border-color: var(--color-primary-400) !important;
        background: var(--color-primary-50) !important;
    }

    /* Chat interface polish */
    .chat-interface {
        border-radius: var(--radius-xl) !important;
        box-shadow: var(--shadow-lg) !important;
    }

    /* Markdown content spacing */
    .markdown-body {
        line-height: 1.6 !important;
    }

    .markdown-body h1,
    .markdown-body h2,
    .markdown-body h3 {
        margin-top: var(--space-lg) !important;
        margin-bottom: var(--space-md) !important;
    }

    /* Status messages */
    .status-box {
        padding: var(--space-md) !important;
        border-radius: var(--radius-lg) !important;
        margin: var(--space-md) 0 !important;
        animation: slideIn 0.3s ease-out !important;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    /* Loading states */
    .loading {
        animation: pulse 1.5s ease-in-out infinite !important;
    }

    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }

    /* Scroll behavior */
    * {
        scroll-behavior: smooth !important;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--color-neutral-100);
        border-radius: var(--radius-md);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--color-neutral-400);
        border-radius: var(--radius-md);
        transition: background 0.2s ease;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--color-primary-500);
    }

    /* Tooltip-style labels */
    label {
        font-weight: 600 !important;
        color: var(--color-neutral-700) !important;
        margin-bottom: var(--space-xs) !important;
    }

    /* Card hover effects for interactive elements */
    .card:hover,
    .card-feature:hover {
        transform: translateY(-2px) !important;
        transition: all 0.3s ease !important;
    }

    /* Badge animations */
    .badge {
        transition: all 0.2s ease !important;
    }

    .badge:hover {
        transform: scale(1.05) !important;
    }

    /* Focus visible for accessibility */
    *:focus-visible {
        outline: 3px solid var(--color-primary-500) !important;
        outline-offset: 2px !important;
        border-radius: var(--radius-sm) !important;
    }

    /* Gradient text effect for headings */
    .gradient-text {
        background: linear-gradient(135deg, var(--color-primary-600), var(--color-accent-500));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    """

    # Combine design system CSS with custom CSS
    css = design_system_css + custom_css

    with gr.Blocks(
        theme=team_synapse_theme,
        title="Team Synapse - Corporate Memory AI",
        css=css,
    ) as app:

        context_state = gr.State({})

        # Fetch graph summary for homepage
        try:
            graph_summary = neo4j_service.get_knowledge_graph_summary()
        except Exception:
            graph_summary = None

        # Navigation
        with gr.Sidebar(open=True):
            gr.Markdown("### Navigation")
            nav_home = gr.Button("🏠 Home", variant="primary", elem_classes=["nav-btn"])
            nav_ingest = gr.Button("📥 Analyze Meeting", variant="secondary", elem_classes=["nav-btn"])
            nav_chat = gr.Button("💬 Chat Copilot", variant="secondary", elem_classes=["nav-btn"])
            nav_live = gr.Button("🎙️ Live Agent", variant="secondary", elem_classes=["nav-btn"])
            gr.Markdown("---")
            username_display = gr.Markdown(f"**User:** `{config.app.tenant_id}`")
            gr.Markdown("---")
            gr.Markdown("**Team Synapse**\n\nCorporate Memory AI")

        # PAGE 0: LANDING (Username Entry)
        with gr.Column(visible=True) as page_landing:
            gr.Markdown("""
            <div style="text-align: center; padding: 4rem 2rem;">
                <h1 style="font-size: 3rem; margin-bottom: 1rem; color: #4F46E5;">Team Synapse</h1>
                <p style="font-size: 1.25rem; color: #64748b; margin-bottom: 2rem;">
                    Corporate Memory AI
                </p>
                <p style="font-size: 1rem; margin-bottom: 2rem; color: #475569;">
                    Enter your username to get started and access your private knowledge graph:
                </p>
            </div>
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    pass  # Spacer
                with gr.Column(scale=2):
                    username_input = gr.Textbox(
                        label="Username",
                        placeholder="your-username",
                        max_lines=1,
                        elem_classes=["username-input"]
                    )
                    error_display = gr.Markdown("", elem_classes=["error-message"])
                    enter_btn = gr.Button("Enter App →", variant="primary", size="lg")
                with gr.Column(scale=1):
                    pass  # Spacer

            gr.Markdown("""
            <div style="text-align: center; padding: 2rem; color: #94a3b8;">
                <p style="margin-bottom: 0.5rem;">✓ Your data is completely isolated and private</p>
                <p style="margin-bottom: 0.5rem;">✓ No password needed - perfect for demos!</p>
                <p>✓ Start testing GraphRAG queries immediately</p>
            </div>
            """)

        # PAGE 1: HOMEPAGE
        with gr.Column(visible=False) as page_home:
            create_homepage_hero(graph_summary)
            create_problem_section()
            create_how_it_works_section()
            create_features_grid()
            create_use_cases_section()
            create_cta_section()

        # PAGE 1: INGEST
        with gr.Column(visible=False) as page_ingest:
            # Page Header
            gr.Markdown("""
            <div class="container-narrow">
                <div style="text-align: center; margin-bottom: var(--space-xl);">
                    <span class="badge badge-primary">Step-by-Step Analysis</span>
                    <h1 class="text-display-lg mt-md mb-md">📥 Analyze Meeting</h1>
                    <p class="text-body-lg text-neutral">
                        Upload your meeting recording and get AI-powered insights. We'll extract action items,
                        decisions, and key entities, then store everything in your knowledge graph.
                    </p>
                </div>
            </div>
            """)

            with gr.Row():
                # LEFT COLUMN: Context
                with gr.Column(scale=1):
                    gr.Markdown("""
                    <div class="card">
                        <div style="display: flex; align-items: center; gap: var(--space-md); margin-bottom: var(--space-lg);">
                            <div style="
                                width: 40px;
                                height: 40px;
                                border-radius: var(--radius-lg);
                                background: var(--color-primary-100);
                                color: var(--color-primary-600);
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: 700;
                                font-size: 1.25rem;
                            ">1</div>
                            <div>
                                <h3 class="text-heading-md" style="margin: 0;">Meeting Context</h3>
                                <p class="text-body-sm text-muted" style="margin: 0;">Optional but helpful</p>
                            </div>
                        </div>
                    </div>
                    """)

                    context_file = gr.File(
                        label="📅 Calendar invite or agenda",
                        file_types=["file"],
                        type="filepath"
                    )
                    context_text = gr.Textbox(
                        label="Or paste meeting details",
                        placeholder="Meeting title, attendees, agenda...",
                        lines=4
                    )
                    extract_btn = gr.Button("Extract Context", variant="secondary", size="lg")
                    context_status = gr.Markdown("")
                    context_preview = gr.Textbox(label="Extracted Context", lines=4, interactive=False)

                # RIGHT COLUMN: Audio Upload
                with gr.Column(scale=1):
                    gr.Markdown("""
                    <div class="card">
                        <div style="display: flex; align-items: center; gap: var(--space-md); margin-bottom: var(--space-lg);">
                            <div style="
                                width: 40px;
                                height: 40px;
                                border-radius: var(--radius-lg);
                                background: var(--color-primary-500);
                                color: white;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: 700;
                                font-size: 1.25rem;
                            ">2</div>
                            <div>
                                <h3 class="text-heading-md" style="margin: 0;">Upload Recording</h3>
                                <p class="text-body-sm text-muted" style="margin: 0;">MP3, WAV, or M4A</p>
                            </div>
                        </div>
                    </div>
                    """)

                    audio_input = gr.File(
                        label="🎙️ Audio file",
                        file_types=["audio"],
                        type="filepath"
                    )
                    session_type = gr.Dropdown(
                        label="Meeting Type",
                        choices=["Corporate", "Sales", "Technical"],
                        value="Corporate"
                    )
                    analyze_btn = gr.Button("🚀 Analyze Meeting", variant="primary", size="lg")
                    status_output = gr.Markdown("**Status:** Ready to analyze")

            # Results Section
            gr.Markdown("""
            <div style="margin-top: var(--space-3xl); padding-top: var(--space-xl); border-top: 2px solid var(--color-neutral-200);">
                <div style="text-align: center; margin-bottom: var(--space-xl);">
                    <h2 class="text-heading-xl">📊 Analysis Results</h2>
                    <p class="text-body-md text-muted">Results will appear here after analysis</p>
                </div>
            </div>
            """)
            graph_html = gr.HTML(value=_build_graph_html(None))

        # PAGE 2: CHAT
        with gr.Column(visible=False) as page_chat:
            # Page Header
            gr.Markdown("""
            <div class="container-narrow">
                <div style="text-align: center; margin-bottom: var(--space-xl);">
                    <span class="badge badge-success">AI-Powered Assistant</span>
                    <h1 class="text-display-lg mt-md mb-md">💬 Meeting Copilot</h1>
                    <p class="text-body-lg text-neutral">
                        Chat with your entire meeting history. Ask questions, find action items, and query your knowledge graph using natural language.
                    </p>
                </div>
            </div>
            """)

            # Example queries
            gr.Markdown("""
            <div class="container-narrow mb-xl">
                <div class="card" style="background: var(--color-primary-50); border: 1px solid var(--color-primary-200);">
                    <h3 class="text-heading-sm mb-md">Try asking:</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: var(--space-sm);">
                        <span class="badge badge-primary">"What action items are assigned to Sarah?"</span>
                        <span class="badge badge-primary">"Find meetings about the Q4 roadmap"</span>
                        <span class="badge badge-primary">"Show me graph statistics"</span>
                        <span class="badge badge-primary">"Create a mind map for the last meeting"</span>
                    </div>
                </div>
            </div>
            """)

            # Chat interface
            chatbot = gr.Chatbot(
                value=[],
                height=500,
                show_copy_button=True,
                render_markdown=True,
                type="messages",
                elem_classes=["chat-interface"]
            )

            with gr.Row():
                msg = gr.Textbox(
                    show_label=False,
                    placeholder="Ask me anything about your meetings...",
                    scale=8,
                    container=False
                )
                send_btn = gr.Button("Send 🚀", variant="primary", scale=1, size="lg")

            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary", size="sm")

        # PAGE 3: LIVE AGENT (ADK)
        with gr.Column(visible=False) as page_live:
            # Page Header
            gr.Markdown("""
            <div class="container-narrow">
                <div style="text-align: center; margin-bottom: var(--space-xl);">
                    <span class="badge badge-accent">Autonomous Agent</span>
                    <h1 class="text-display-lg mt-md mb-md">🧠 Live Agent (ADK)</h1>
                    <p class="text-body-lg text-neutral">
                        Powered by Google's Agent Development Kit, this autonomous agent can proactively assist during meetings with real-time insights.
                    </p>
                </div>
            </div>
            """)

            # Status card
            gr.Markdown("""
            <div class="container-narrow mb-xl">
                <div class="card" style="background: linear-gradient(135deg, var(--color-success-light), var(--color-info-light)); border: 2px solid var(--color-success);">
                    <div style="display: flex; align-items: center; gap: var(--space-md); margin-bottom: var(--space-md);">
                        <div style="font-size: 2rem;">✅</div>
                        <div>
                            <h3 class="text-heading-md" style="margin: 0;">Agent Ready</h3>
                            <p class="text-body-sm text-muted" style="margin: 0;">Configured with full tool access</p>
                        </div>
                    </div>
                </div>
            </div>
            """)

            # Capabilities section
            gr.Markdown("""
            <div class="container-narrow mb-2xl">
                <h2 class="text-heading-xl mb-lg" style="text-align: center;">Agent Capabilities</h2>
                <div class="grid-2 gap-lg">
                    <div class="card-feature">
                        <div class="icon-md icon-primary">🔍</div>
                        <h3 class="text-heading-sm mb-sm">Neo4j Tools</h3>
                        <p class="text-body-sm text-muted">
                            Search meetings, get action items, retrieve historical context from your knowledge graph.
                        </p>
                    </div>
                    <div class="card-feature">
                        <div class="icon-md icon-accent">🎨</div>
                        <h3 class="text-heading-sm mb-sm">Miro Visualization</h3>
                        <p class="text-body-sm text-muted">
                            Automatically create mind maps and visual summaries of meeting insights.
                        </p>
                    </div>
                    <div class="card-feature">
                        <div class="icon-md icon-primary">📄</div>
                        <h3 class="text-heading-sm mb-sm">Notion Integration</h3>
                        <p class="text-body-sm text-muted">
                            Create pages with action items and summaries (requires NOTION_TOKEN).
                        </p>
                    </div>
                    <div class="card-feature">
                        <div class="icon-md icon-accent">💾</div>
                        <h3 class="text-heading-sm mb-sm">Auto Storage</h3>
                        <p class="text-body-sm text-muted">
                            Automatically persist meeting data to your knowledge graph.
                        </p>
                    </div>
                </div>
            </div>
            """)

            # How to use section
            gr.Markdown("""
            <div class="container-narrow mb-2xl">
                <div class="card" style="background: var(--color-neutral-50);">
                    <h3 class="text-heading-md mb-lg">How to Use the Agent</h3>
                    <div style="display: flex; flex-direction: column; gap: var(--space-md);">
                        <div style="display: flex; gap: var(--space-md);">
                            <div class="badge badge-primary" style="width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">1</div>
                            <div>
                                <h4 class="text-heading-sm" style="margin: 0 0 4px 0;">Text Testing</h4>
                                <p class="text-body-sm text-muted" style="margin: 0;">Use the <strong>Chat Copilot</strong> tab to interact with the agent via text. All tools are available.</p>
                            </div>
                        </div>
                        <div style="display: flex; gap: var(--space-md);">
                            <div class="badge badge-primary" style="width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">2</div>
                            <div>
                                <h4 class="text-heading-sm" style="margin: 0 0 4px 0;">Analyze Meetings</h4>
                                <p class="text-body-sm text-muted" style="margin: 0;">Upload recordings via <strong>Analyze Meeting</strong>, then query insights through the agent.</p>
                            </div>
                        </div>
                        <div style="display: flex; gap: var(--space-md);">
                            <div class="badge badge-info" style="width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">💡</div>
                            <div>
                                <h4 class="text-heading-sm" style="margin: 0 0 4px 0;">Future: Real-time Audio</h4>
                                <p class="text-body-sm text-muted" style="margin: 0;">Live audio streaming requires WebRTC integration (coming soon).</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """)

            # Configuration section
            gr.Markdown("""
            <div class="container-narrow">
                <h2 class="text-heading-xl mb-lg" style="text-align: center;">Configuration Status</h2>
            </div>
            """)

            with gr.Row():
                with gr.Column():
                    agent_api_key = gr.Textbox(
                        label="🔑 Gemini API Key",
                        value="✅ Configured" if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") else "❌ Not set",
                        interactive=False
                    )
                with gr.Column():
                    agent_notion = gr.Textbox(
                        label="📝 Notion Integration",
                        value="✅ Enabled" if os.getenv("NOTION_TOKEN") else "⚠️ Disabled (optional)",
                        interactive=False
                    )

            # Test section
            gr.Markdown("""
            <div class="container-narrow mt-xl">
                <div class="card" style="background: var(--color-primary-50); border: 1px solid var(--color-primary-200);">
                    <h3 class="text-heading-sm mb-md">🧪 Test Agent Initialization</h3>
                    <p class="text-body-sm text-muted mb-md">
                        Click below to verify the agent is properly configured with all tools.
                    </p>
            """)

            test_agent_btn = gr.Button("Run Test", variant="primary", size="lg")
            test_agent_output = gr.Textbox(
                label="Test Results",
                lines=10,
                interactive=False
            )

            gr.Markdown("""
                </div>
            </div>
            """)

            def test_agent_init():
                """Test that the ADK agent initializes correctly."""
                try:
                    import os
                    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                    if not api_key:
                        return "❌ No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable."

                    # Try to create agent
                    agent = create_agent(api_key=api_key)

                    result = [
                        "✅ Agent created successfully!",
                        f"",
                        f"**Model:** {agent.model}",
                        f"**Name:** {agent.name}",
                        f"**Tools:** {len(agent.tools)} tools loaded",
                        f"",
                        "**Available Tools:**"
                    ]

                    # List tools
                    for i, tool in enumerate(agent.tools[:10], 1):  # Show first 10
                        tool_name = getattr(tool, 'name', str(type(tool).__name__))
                        result.append(f"{i}. {tool_name}")

                    if len(agent.tools) > 10:
                        result.append(f"... and {len(agent.tools) - 10} more")

                    return "\n".join(result)

                except Exception as e:
                    return f"❌ Error initializing agent:\n\n{str(e)}\n\nCheck your API key and dependencies."

            test_agent_btn.click(test_agent_init, outputs=[test_agent_output])

        # EVENT BINDINGS
        # Username entry
        enter_btn.click(
            handle_username_entry,
            inputs=[username_input],
            outputs=[
                error_display,
                page_landing,
                page_home,
                page_ingest,
                page_chat,
                page_live,
                username_display
            ]
        )

        # Navigation
        nav_home.click(show_home_page, outputs=[page_landing, page_home, page_ingest, page_chat, page_live])
        nav_ingest.click(show_ingest_page, outputs=[page_landing, page_home, page_ingest, page_chat, page_live])
        nav_chat.click(show_chat_page, outputs=[page_landing, page_home, page_ingest, page_chat, page_live])
        nav_live.click(show_live_page, outputs=[page_landing, page_home, page_ingest, page_chat, page_live])

        extract_btn.click(
            handle_extract_context,
            inputs=[context_file, context_text],
            outputs=[context_status, context_preview, context_state]
        )

        analyze_btn.click(
            handle_audio_upload,
            inputs=[audio_input, context_state, session_type],
            outputs=[status_output, graph_html]
        )

        msg.submit(mcp_client.process_message, [msg, chatbot], [msg, chatbot])
        send_btn.click(mcp_client.process_message, [msg, chatbot], [msg, chatbot])
        clear_btn.click(lambda: [], None, chatbot)

    return app


def main():
    """Main entry point."""
    logger.info("Starting Team Synapse...")

    if not config.validate():
        logger.error("Configuration validation failed.")
        return

    app = create_app()

    # Auth (optional)
    username = os.getenv("GRADIO_USERNAME")
    password = os.getenv("GRADIO_PASSWORD")
    auth = [(username, password)] if username and password else None

    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=True,
        show_error=True,
        auth=auth
    )


if __name__ == "__main__":
    main()
