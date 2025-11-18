"""
Reusable UI components for Team Synapse.
"""
import gradio as gr
from typing import Dict, Any, Optional


def create_header() -> gr.Markdown:
    """
    Create the application header.
    
    Returns:
        Gradio Markdown component with header content
    """
    return gr.Markdown(
        """
        <div style="text-align: center; padding: 2rem 0;">
            <h1 class="header-title">🧠 Team Synapse</h1>
            <p class="header-subtitle">
                Transform meeting recordings into actionable intelligence
            </p>
        </div>
        """,
        elem_classes=["header"]
    )


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