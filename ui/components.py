"""
Reusable UI components for Team Synapse.
"""
import gradio as gr
from typing import Dict, Any, Optional


def create_info_banner() -> gr.Markdown:
    """
    Create an informational banner about the app.
    
    Returns:
        Gradio Markdown component with info content
    """
    return gr.Markdown(
        """
        ### 🎯 How it works
        
        1. **Record or Upload** a meeting audio file (MP3, WAV, M4A)
        2. **AI Analysis** extracts key information with Google Gemini
        3. **Structured Output** ready for knowledge graph integration
        
        ---
        
        **Phase 1-3 Demo:** This interface demonstrates the ingestion pipeline. 
        The full system will include Neo4j knowledge graph and contextual action dashboard.
        """,
        elem_classes=["info-banner"]
    )


def create_features_section() -> gr.Markdown:
    """
    Create a section highlighting key features.
    
    Returns:
        Gradio Markdown component with features
    """
    return gr.Markdown(
        """
        ### ✨ What gets extracted
        
        <div style="
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
            gap: 1rem; 
            margin: 1rem 0;
        ">
            <div style="
                padding: 1rem 1.25rem; 
                background: linear-gradient(135deg, #0f172a 0%, #020617 100%); 
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.35);
                box-shadow: 0 10px 25px rgba(15, 23, 42, 0.35);
                color: #e5e7eb;
            ">
                <strong>📝 Transcript</strong><br/>
                Complete verbatim text
            </div>
            <div style="
                padding: 1rem 1.25rem; 
                background: radial-gradient(circle at top left, #22c55e 0%, #0f172a 55%, #020617 100%); 
                border-radius: 12px;
                border: 1px solid rgba(45, 212, 191, 0.6);
                box-shadow: 0 10px 25px rgba(34, 197, 94, 0.25);
                color: #ecfdf5;
            ">
                <strong>✅ Action Items</strong><br/>
                Tasks with assignees
            </div>
            <div style="
                padding: 1rem 1.25rem; 
                background: radial-gradient(circle at top left, #6366f1 0%, #0b1120 60%, #020617 100%); 
                border-radius: 12px;
                border: 1px solid rgba(129, 140, 248, 0.7);
                box-shadow: 0 10px 25px rgba(79, 70, 229, 0.25);
                color: #e0e7ff;
            ">
                <strong>🎯 Decisions</strong><br/>
                Key outcomes
            </div>
            <div style="
                padding: 1rem 1.25rem; 
                background: linear-gradient(145deg, #020617 0%, #0b1120 45%, #111827 100%); 
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.35);
                box-shadow: 0 10px 25px rgba(15, 23, 42, 0.35);
                color: #e5e7eb;
            ">
                <strong>👥 People</strong><br/>
                All participants
            </div>
            <div style="
                padding: 1rem 1.25rem; 
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #020617 100%); 
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.35);
                box-shadow: 0 10px 25px rgba(15, 23, 42, 0.35);
                color: #e5e7eb;
            ">
                <strong>🏢 Clients</strong><br/>
                Mentioned companies
            </div>
            <div style="
                padding: 1rem 1.25rem; 
                background: radial-gradient(circle at top left, #22d3ee 0%, #0f172a 55%, #020617 100%); 
                border-radius: 12px;
                border: 1px solid rgba(45, 212, 191, 0.6);
                box-shadow: 0 10px 25px rgba(8, 145, 178, 0.3);
                color: #ecfeff;
            ">
                <strong>📊 Projects</strong><br/>
                Related initiatives
            </div>
        </div>
        """
    )


def create_status_display(status: str, status_type: str = "info") -> str:
    """
    Format a status message with appropriate styling.
    
    Args:
        status: Status message
        status_type: Type of status (success, error, processing, info)
    
    Returns:
        HTML-formatted status message
    """
    class_map = {
        "success": "status-success",
        "error": "status-error",
        "processing": "status-processing",
        "info": "status-processing"
    }
    
    css_class = class_map.get(status_type, "status-processing")
    
    return f'<div class="status-box {css_class}">{status}</div>'


def format_analysis_summary(analysis: Optional[Dict[str, Any]]) -> str:
    """
    Create a formatted summary of the analysis results.
    
    Args:
        analysis: Analysis dictionary from Gemini
    
    Returns:
        Formatted HTML summary
    """
    if not analysis:
        return ""
    
    summary_parts = []
    
    # Meeting title
    if "meetingTitle" in analysis:
        summary_parts.append(f"### 📋 {analysis['meetingTitle']}")
    
    # Quick stats
    stats = []
    if "actionItems" in analysis:
        stats.append(f"✅ {len(analysis['actionItems'])} action items")
    if "keyDecisions" in analysis:
        stats.append(f"🎯 {len(analysis['keyDecisions'])} decisions")
    if "mentionedPeople" in analysis:
        stats.append(f"👥 {len(analysis['mentionedPeople'])} people")
    if "mentionedClients" in analysis:
        stats.append(f"🏢 {len(analysis['mentionedClients'])} clients")
    
    if stats:
        summary_parts.append(f"**Quick Stats:** {' • '.join(stats)}")
    
    # Summary
    if "summary" in analysis:
        summary_parts.append(f"\n**Summary:**\n{analysis['summary']}")
    
    # Sentiment
    if "sentiment" in analysis:
        sentiment_emoji = {
            "positive": "😊",
            "negative": "😟",
            "neutral": "😐",
            "mixed": "🤔"
        }
        emoji = sentiment_emoji.get(analysis.get("sentiment", "").lower(), "")
        summary_parts.append(f"\n**Sentiment:** {emoji} {analysis['sentiment'].title()}")
    
    return "\n\n".join(summary_parts)


def create_tips_section() -> gr.Markdown:
    """
    Create helpful tips for users.
    
    Returns:
        Gradio Markdown component with tips
    """
    return gr.Markdown(
        """
        ### 💡 Tips for best results
        
        - **Clear audio** works best (minimize background noise)
        - **Mention names** explicitly for better person extraction
        - **State action items** clearly (e.g., "Sarah will complete X by Friday")
        - **Name projects/clients** when discussing them
        - Test with a **30-60 second recording** for quick results
        """,
        elem_classes=["tips-section"]
    )


def create_footer() -> gr.Markdown:
    """
    Create the application footer.
    
    Returns:
        Gradio Markdown component with footer content
    """
    return gr.Markdown(
        """
        ---
        
        <div style="text-align: center; padding: 1rem; color: #9ca3af;">
            <p>
                <strong>Team Synapse</strong> · Meeting Intelligence Workspace<br/>
                Powered by Google Gemini & Vertex AI
            </p>
        </div>
        """,
        elem_classes=["footer"]
    )


def create_example_recordings_info() -> gr.Markdown:
    """
    Create information about example recordings.

    Returns:
        Gradio Markdown component
    """
    return gr.Markdown(
        """
        ### 🎬 Example Recordings

        Try these sample scenarios:
        - **Project Kickoff:** "This is our Project Phoenix kickoff. Sarah will handle design by next week..."
        - **Client Call:** "Meeting with Acme Corp. They need the proposal by Friday. John is the contact..."
        - **Team Standup:** "Quick update: I finished the API integration. Next, I'll work on testing..."
        """
    )


# =============================================================================
# HOMEPAGE COMPONENTS
# =============================================================================

def create_homepage_hero(graph_summary: Optional[Dict[str, Any]] = None) -> gr.Markdown:
    """
    Create the homepage hero section with headline and CTA.

    Args:
        graph_summary: Optional dictionary with knowledge graph statistics

    Returns:
        Gradio Markdown component with hero content
    """
    meetings = graph_summary.get("meetings", "0") if graph_summary else "0"
    action_items = graph_summary.get("actionItems", "0") if graph_summary else "0"

    return gr.Markdown(
        f"""
        <div class="container-hero animate-fade-in">
            <div style="margin-bottom: var(--space-md);">
                <span class="badge badge-primary">Corporate Memory Engine</span>
            </div>
            <h1 class="text-display-xl" style="margin-bottom: var(--space-lg); color: var(--color-neutral-900);">
                Never forget what<br/>happened in a meeting
            </h1>
            <p class="text-body-lg text-neutral" style="max-width: 700px; margin: 0 auto var(--space-xl);">
                Team Synapse transforms meeting recordings into a live knowledge graph.
                Ask questions, track action items, and connect insights across your entire portfolio—before you walk into the room.
            </p>
            <div class="flex-center gap-md" style="margin-bottom: var(--space-2xl);">
                <div class="btn-primary" style="cursor: default;">
                    👈 Use sidebar navigation
                </div>
            </div>
            <div class="grid-4 gap-lg" style="margin-top: var(--space-3xl);">
                <div class="card-stat">
                    <span class="text-caption">Meetings Indexed</span>
                    <span class="text-heading-xl text-primary">{meetings}</span>
                </div>
                <div class="card-stat">
                    <span class="text-caption">Action Items Tracked</span>
                    <span class="text-heading-xl text-primary">{action_items}</span>
                </div>
                <div class="card-stat">
                    <span class="text-caption">AI-Powered Analysis</span>
                    <span class="text-heading-xl text-accent">100%</span>
                </div>
                <div class="card-stat">
                    <span class="text-caption">Real-Time Updates</span>
                    <span class="text-heading-xl text-accent">Live</span>
                </div>
            </div>
        </div>
        """,
        elem_classes=["homepage-hero"]
    )


def create_problem_section() -> gr.Markdown:
    """
    Create the problem statement section.

    Returns:
        Gradio Markdown component with problem statement
    """
    return gr.Markdown(
        """
        <div class="container-section">
            <div style="text-align: center; margin-bottom: var(--space-2xl);">
                <span class="badge badge-error">The Problem</span>
                <h2 class="text-display-md mt-md mb-lg">
                    Important details slip through the cracks
                </h2>
                <p class="text-body-lg text-neutral" style="max-width: 600px; margin: 0 auto;">
                    You're managing multiple projects, clients, and meetings.
                    Critical action items get buried in notes, decisions are forgotten,
                    and context is lost between calls.
                </p>
            </div>
            <div class="grid-3 gap-xl">
                <div class="card-feature">
                    <div class="icon-lg icon-primary">📝</div>
                    <h3 class="text-heading-sm mb-sm">Notes Scattered</h3>
                    <p class="text-body-sm text-muted">
                        Meeting notes live in different docs, emails, and tools. Finding what you need takes forever.
                    </p>
                </div>
                <div class="card-feature">
                    <div class="icon-lg icon-primary">🔍</div>
                    <h3 class="text-heading-sm mb-sm">Context Lost</h3>
                    <p class="text-body-sm text-muted">
                        "What did we decide last time?" becomes an archaeology project through old recordings.
                    </p>
                </div>
                <div class="card-feature">
                    <div class="icon-lg icon-primary">⏱️</div>
                    <h3 class="text-heading-sm mb-sm">Time Wasted</h3>
                    <p class="text-body-sm text-muted">
                        Team members spend hours re-listening to recordings or searching through transcripts.
                    </p>
                </div>
            </div>
        </div>
        """,
        elem_classes=["problem-section"]
    )


def create_how_it_works_section() -> gr.Markdown:
    """
    Create the "How It Works" section.

    Returns:
        Gradio Markdown component with process explanation
    """
    return gr.Markdown(
        """
        <div class="container-section bg-gradient-hero">
            <div style="text-align: center; margin-bottom: var(--space-3xl);">
                <span class="badge badge-success">The Solution</span>
                <h2 class="text-display-md mt-md">
                    How Team Synapse Works
                </h2>
            </div>
            <div class="grid-2 gap-2xl" style="align-items: center;">
                <div>
                    <div style="margin-bottom: var(--space-2xl);">
                        <div style="display: flex; align-items: flex-start; gap: var(--space-lg);">
                            <div style="
                                width: 48px;
                                height: 48px;
                                border-radius: var(--radius-lg);
                                background: var(--color-primary-500);
                                color: white;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: 700;
                                font-size: 1.5rem;
                                flex-shrink: 0;
                            ">1</div>
                            <div>
                                <h3 class="text-heading-md mb-sm">Upload or Record</h3>
                                <p class="text-body-md text-neutral">
                                    Drop your meeting audio file or record live. Supports MP3, WAV, M4A formats.
                                </p>
                            </div>
                        </div>
                    </div>
                    <div style="margin-bottom: var(--space-2xl);">
                        <div style="display: flex; align-items: flex-start; gap: var(--space-lg);">
                            <div style="
                                width: 48px;
                                height: 48px;
                                border-radius: var(--radius-lg);
                                background: var(--color-primary-500);
                                color: white;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: 700;
                                font-size: 1.5rem;
                                flex-shrink: 0;
                            ">2</div>
                            <div>
                                <h3 class="text-heading-md mb-sm">AI Analysis</h3>
                                <p class="text-body-md text-neutral">
                                    Google Gemini 2.5 Pro extracts transcript, action items, decisions, people, clients, and projects.
                                </p>
                            </div>
                        </div>
                    </div>
                    <div>
                        <div style="display: flex; align-items: flex-start; gap: var(--space-lg);">
                            <div style="
                                width: 48px;
                                height: 48px;
                                border-radius: var(--radius-lg);
                                background: var(--color-primary-500);
                                color: white;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: 700;
                                font-size: 1.5rem;
                                flex-shrink: 0;
                            ">3</div>
                            <div>
                                <h3 class="text-heading-md mb-sm">Knowledge Graph</h3>
                                <p class="text-body-md text-neutral">
                                    Data stored in Neo4j connects meetings, people, projects, and clients. Query instantly.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="card" style="padding: var(--space-2xl);">
                    <h4 class="text-heading-sm mb-lg text-center">What Gets Extracted</h4>
                    <div style="display: flex; flex-direction: column; gap: var(--space-sm);">
                        <div class="badge badge-primary" style="display: block; text-align: left;">📝 Complete Transcript</div>
                        <div class="badge badge-success" style="display: block; text-align: left;">✅ Action Items with Assignees</div>
                        <div class="badge badge-info" style="display: block; text-align: left;">🎯 Key Decisions</div>
                        <div class="badge badge-primary" style="display: block; text-align: left;">👥 Meeting Participants</div>
                        <div class="badge badge-primary" style="display: block; text-align: left;">🏢 Client Mentions</div>
                        <div class="badge badge-primary" style="display: block; text-align: left;">📊 Project References</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        elem_classes=["how-it-works"]
    )


def create_features_grid() -> gr.Markdown:
    """
    Create the features grid section.

    Returns:
        Gradio Markdown component with features
    """
    return gr.Markdown(
        """
        <div class="container-section">
            <div style="text-align: center; margin-bottom: var(--space-3xl);">
                <h2 class="text-display-md mb-lg">
                    Powerful Features
                </h2>
                <p class="text-body-lg text-neutral" style="max-width: 600px; margin: 0 auto;">
                    Everything you need to capture, organize, and query meeting intelligence.
                </p>
            </div>
            <div class="grid-3 gap-xl">
                <div class="card">
                    <div class="icon-md icon-accent">🤖</div>
                    <h3 class="text-heading-sm mb-sm">AI-Powered Agent</h3>
                    <p class="text-body-sm text-muted">
                        Chat with your meeting history. Ask natural questions and get instant answers from your knowledge graph.
                    </p>
                </div>
                <div class="card">
                    <div class="icon-md icon-accent">🔗</div>
                    <h3 class="text-heading-sm mb-sm">Neo4j Integration</h3>
                    <p class="text-body-sm text-muted">
                        Relationships between meetings, people, projects, and clients are automatically mapped and queryable.
                    </p>
                </div>
                <div class="card">
                    <div class="icon-md icon-accent">🎨</div>
                    <h3 class="text-heading-sm mb-sm">Miro Mind Maps</h3>
                    <p class="text-body-sm text-muted">
                        Visualize meeting insights as interactive mind maps. Export directly to your Miro board.
                    </p>
                </div>
                <div class="card">
                    <div class="icon-md icon-accent">📄</div>
                    <h3 class="text-heading-sm mb-sm">Notion Sync</h3>
                    <p class="text-body-sm text-muted">
                        Automatically create Notion pages with action items, decisions, and meeting summaries.
                    </p>
                </div>
                <div class="card">
                    <div class="icon-md icon-accent">⚡</div>
                    <h3 class="text-heading-sm mb-sm">Real-Time Analysis</h3>
                    <p class="text-body-sm text-muted">
                        Live agent monitors meetings in real-time, providing context and insights as discussions happen.
                    </p>
                </div>
                <div class="card">
                    <div class="icon-md icon-accent">🔍</div>
                    <h3 class="text-heading-sm mb-sm">Smart Search</h3>
                    <p class="text-body-sm text-muted">
                        Find past discussions by person, project, client, or topic. Full-text search across all meetings.
                    </p>
                </div>
            </div>
        </div>
        """,
        elem_classes=["features-grid"]
    )


def create_use_cases_section() -> gr.Markdown:
    """
    Create the use cases section.

    Returns:
        Gradio Markdown component with use cases
    """
    return gr.Markdown(
        """
        <div class="container-section">
            <div style="text-align: center; margin-bottom: var(--space-3xl);">
                <h2 class="text-display-md mb-lg">
                    Built for Modern Teams
                </h2>
            </div>
            <div class="grid-2 gap-xl">
                <div class="card" style="border-left: 4px solid var(--color-primary-500);">
                    <h3 class="text-heading-md mb-md text-primary">Venture Capital</h3>
                    <p class="text-body-md text-neutral mb-md">
                        Track portfolio company updates across dozens of meetings. Instantly recall what each founder committed to and when.
                    </p>
                    <span class="badge badge-primary">Portfolio Management</span>
                    <span class="badge badge-primary">Founder Updates</span>
                </div>
                <div class="card" style="border-left: 4px solid var(--color-accent-500);">
                    <h3 class="text-heading-md mb-md text-accent">Consulting Firms</h3>
                    <p class="text-body-md text-neutral mb-md">
                        Keep client context fresh. Know exactly what was discussed, decided, and promised before every call.
                    </p>
                    <span class="badge badge-success">Client Relations</span>
                    <span class="badge badge-success">Project Tracking</span>
                </div>
                <div class="card" style="border-left: 4px solid var(--color-warning);">
                    <h3 class="text-heading-md mb-md" style="color: var(--color-warning);">Product Teams</h3>
                    <p class="text-body-md text-neutral mb-md">
                        Never lose track of feature requests, user feedback, or design decisions across sprint planning meetings.
                    </p>
                    <span class="badge badge-warning">Sprint Planning</span>
                    <span class="badge badge-warning">Feature Tracking</span>
                </div>
                <div class="card" style="border-left: 4px solid var(--color-info);">
                    <h3 class="text-heading-md mb-md text-info">Sales Teams</h3>
                    <p class="text-body-md text-neutral mb-md">
                        Maintain perfect context across long sales cycles. Review every promise and requirement before closing.
                    </p>
                    <span class="badge badge-info">Deal Management</span>
                    <span class="badge badge-info">Client Context</span>
                </div>
            </div>
        </div>
        """,
        elem_classes=["use-cases"]
    )


def create_cta_section() -> gr.Markdown:
    """
    Create the final call-to-action section.

    Returns:
        Gradio Markdown component with CTA
    """
    return gr.Markdown(
        """
        <div class="container-section" style="text-align: center;">
            <div class="card" style="padding: var(--space-3xl); background: var(--color-primary-50);">
                <h2 class="text-display-md mb-lg">
                    Ready to remember everything?
                </h2>
                <p class="text-body-lg text-neutral mb-2xl" style="max-width: 600px; margin-left: auto; margin-right: auto;">
                    Start analyzing your meeting recordings and building your corporate memory today.
                </p>
                <div class="flex-center gap-md">
                    <div class="btn-primary" style="cursor: default;">
                        Use the sidebar to get started →
                    </div>
                </div>
            </div>
        </div>
        """,
        elem_classes=["cta-section"]
    )