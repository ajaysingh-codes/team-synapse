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
from ui import seafoam, create_header
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

def show_ingest_page():
    return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)


async def show_chat_page():
    await mcp_client.connect()
    return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)


def show_live_page():
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# =============================================================================
# MAIN APP
# =============================================================================

def create_app() -> gr.Blocks:
    """Create the Gradio application."""

    css = """
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
    """

    with gr.Blocks(
        theme=seafoam,
        title="Team Synapse - Corporate Memory AI",
        css=css,
    ) as app:

        # Header
        try:
            graph_summary = neo4j_service.get_knowledge_graph_summary()
        except Exception:
            graph_summary = None
        create_header(graph_summary)

        context_state = gr.State({})

        # Navigation
        with gr.Sidebar(open=True):
            gr.Markdown("### Navigation")
            nav_ingest = gr.Button("📥 Ingest Meeting", variant="secondary", elem_classes=["nav-btn"])
            nav_chat = gr.Button("💬 Chat Copilot", variant="secondary", elem_classes=["nav-btn"])
            nav_live = gr.Button("🎙️ Live Agent", variant="secondary", elem_classes=["nav-btn"])
            gr.Markdown("---")
            gr.Markdown("**Team Synapse**\n\nCorporate Memory AI")

        # PAGE 1: INGEST
        with gr.Column(visible=True, elem_classes=["glass-panel"]) as page_ingest:
            gr.Markdown("## 📥 Ingest Meeting")
            gr.Markdown("Upload a meeting recording to analyze and store in the knowledge graph.")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 1. Meeting Context (Optional)")
                    context_file = gr.File(
                        label="Calendar invite or agenda",
                        file_types=["file"],
                        type="filepath"
                    )
                    context_text = gr.Textbox(
                        label="Or paste meeting details",
                        placeholder="Meeting title, attendees, agenda...",
                        lines=4
                    )
                    extract_btn = gr.Button("Extract Context", variant="secondary")
                    context_status = gr.Markdown("")
                    context_preview = gr.Textbox(label="Extracted Context", lines=4, interactive=False)

                with gr.Column(scale=1):
                    gr.Markdown("### 2. Upload Recording")
                    audio_input = gr.File(
                        label="Audio file (MP3, WAV, M4A)",
                        file_types=["audio"],
                        type="filepath"
                    )
                    session_type = gr.Dropdown(
                        label="Meeting Type",
                        choices=["Corporate", "Sales", "Technical"],
                        value="Corporate"
                    )
                    analyze_btn = gr.Button("Analyze Meeting", variant="primary", size="lg")
                    status_output = gr.Markdown("**Status:** Ready")

            gr.Markdown("### Analysis Results")
            graph_html = gr.HTML(value=_build_graph_html(None))

        # PAGE 2: CHAT
        with gr.Column(visible=False, elem_classes=["glass-panel"]) as page_chat:
            gr.Markdown("## 💬 Meeting Copilot")
            gr.Markdown("""
            Chat with your knowledge graph. Try:
            - "What action items are assigned to Sarah?"
            - "Find meetings about the Q4 roadmap"
            - "Show me graph statistics"
            - "Create a mind map for the last meeting" (requires Miro setup)
            """)

            chatbot = gr.Chatbot(
                value=[],
                height=500,
                show_copy_button=True,
                render_markdown=True,
                type="messages"
            )

            with gr.Row():
                msg = gr.Textbox(
                    show_label=False,
                    placeholder="Ask about your meetings...",
                    scale=8
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            clear_btn = gr.Button("Clear Chat", variant="secondary", size="sm")

        # PAGE 3: LIVE AGENT (ADK)
        with gr.Column(visible=False, elem_classes=["glass-panel"]) as page_live:
            gr.Markdown("## 🧠 Autonomous Live Agent (ADK)")
            gr.Markdown("""
            **Status:** ADK agent is configured and ready!

            The autonomous agent has been set up with:
            - **Neo4j tools**: Search meetings, get action items, historical context
            - **Miro visualization**: Create mind maps from meetings
            - **Notion integration**: Create summaries (requires NOTION_TOKEN)
            - **Storage**: Automatic meeting data persistence

            ### Text-based Testing
            Use the **Chat Copilot** tab to test the agent with text commands. The agent
            has all the same tools and capabilities as it would in live mode.

            ### Future: Real-time Audio
            Real-time audio streaming with ADK requires additional WebRTC integration.
            For now, use the **Ingest Meeting** tab to analyze recorded meetings, then
            query the knowledge graph via the **Chat Copilot**.

            **Configuration:**
            - `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Required for ADK
            - `NOTION_TOKEN`: Optional (enables Notion MCP tools)
            """)

            # Show agent configuration
            gr.Markdown("### Agent Configuration")

            with gr.Row():
                agent_api_key = gr.Textbox(
                    label="Gemini API Key Status",
                    value="✅ Configured" if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") else "❌ Not set",
                    interactive=False
                )
                agent_notion = gr.Textbox(
                    label="Notion Integration",
                    value="✅ Enabled" if os.getenv("NOTION_TOKEN") else "⚠️ Disabled (optional)",
                    interactive=False
                )

            # Test agent button
            test_agent_btn = gr.Button("🧪 Test Agent Initialization", variant="primary")
            test_agent_output = gr.Textbox(
                label="Test Results",
                lines=10,
                interactive=False
            )

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
        nav_ingest.click(show_ingest_page, outputs=[page_ingest, page_chat, page_live])
        nav_chat.click(show_chat_page, outputs=[page_ingest, page_chat, page_live])
        nav_live.click(show_live_page, outputs=[page_ingest, page_chat, page_live])

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
        share=False,
        show_error=True,
        auth=auth
    )


if __name__ == "__main__":
    main()
