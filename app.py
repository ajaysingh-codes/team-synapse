"""
Team Synapse - Main Application
Phase 1-3: Audio Ingestion & Analysis Pipeline

A professional Gradio interface for the Team Synapse corporate memory system.
"""
import gradio as gr
from typing import Optional, Dict, Any, Union

from services import ingestion_pipeline
from ui import (
    seafoam,
    create_header,
    format_analysis_summary
)
from config import config
from utils import setup_logger


# Setup logging
logger = setup_logger(__name__, config.app.log_level)


# ============================================================================
# EVENT HANDLERS
# ============================================================================

def handle_audio_upload(audio_file: Optional[str]) -> tuple:
    """
    Handle uploaded audio file processing.
    
    Args:
        audio_file: Path to uploaded audio file
    
    Returns:
        Tuple of (status_log, analysis_json, summary_text)
    """
    if audio_file is None:
        return "⚠️ Please upload an audio file first.", None, ""
    
    logger.info(f"Processing uploaded file: {audio_file}")
    
    # Process through ingestion pipeline
    final_status = ""
    final_analysis = None
    
    for status, analysis in ingestion_pipeline.process_audio_file(audio_file):
        final_status = status
        if analysis:
            final_analysis = analysis
    
    # Create summary text
    summary = format_analysis_summary(final_analysis) if final_analysis else ""
    
    return final_status, final_analysis, summary


def handle_audio_recording(audio_file: Optional[Any]) -> tuple:
    """
    Handle live audio recording processing.
    
    Args:
        audio_file: Audio file path or tuple from Gradio Audio component
    
    Returns:
        Tuple of (status_log, analysis_json, summary_text)
    """
    import os
    
    if audio_file is None:
        return "⚠️ Please record some audio first.", None, ""
    
    # Handle different return types from Gradio Audio component
    audio_path = None
    if isinstance(audio_file, tuple):
        # Gradio can return tuple: (sample_rate, audio_data) or (file_path,)
        # With type="filepath", it should be the file path
        audio_path = audio_file[1] if len(audio_file) > 1 and isinstance(audio_file[1], str) else audio_file[0]
    elif isinstance(audio_file, str):
        audio_path = audio_file
    else:
        return "⚠️ Invalid audio format. Please try recording again.", None, ""
    
    if not audio_path:
        return "⚠️ Audio file path not found. Please record again.", None, ""
    
    # Verify file exists
    if not os.path.exists(audio_path):
        return f"⚠️ Audio file not found at: {audio_path}. Please record again.", None, ""
    
    logger.info(f"Processing recorded audio: {audio_path}")
    
    # Process through ingestion pipeline
    final_status = ""
    final_analysis = None
    
    try:
        for status, analysis in ingestion_pipeline.process_audio_file(audio_path):
            final_status = status
            if analysis:
                final_analysis = analysis
        
        # Create summary text
        summary = format_analysis_summary(final_analysis) if final_analysis else ""
        
        return final_status, final_analysis, summary
    except Exception as e:
        logger.error(f"Error processing recorded audio: {e}", exc_info=True)
        return f"❌ Error processing audio: {str(e)}", None, ""


# ============================================================================
# UI CONSTRUCTION
# ============================================================================

def create_app() -> gr.Blocks:
    """
    Create the main Gradio application.
    
    Returns:
        Configured Gradio Blocks app
    """
    
    with gr.Blocks(
        theme=seafoam,
        title="Team Synapse - Corporate Memory AI",
        analytics_enabled=False
    ) as app:
        
        # ====================================================================
        # HEADER SECTION
        # ====================================================================
        create_header()
        
        # ====================================================================
        # MAIN INTERFACE
        # ====================================================================
        gr.Markdown("## 🎙️ Upload or Record Meeting Audio")
        
        with gr.Tabs() as tabs:
            
            # ================================================================
            # TAB 1: FILE UPLOAD
            # ================================================================
            with gr.TabItem("📁 Upload File", id=0):
                
                with gr.Row():
                    with gr.Column(scale=1):
                        upload_input = gr.File(
                            label="Upload Meeting Recording",
                            file_types=["audio"],
                            type="filepath"
                        )
                        
                        upload_button = gr.Button(
                            "🚀 Analyze Recording",
                            variant="primary",
                            size="lg"
                        )
                        
                        gr.Markdown(
                            """
                            <small>Supported: MP3, WAV, M4A, OGG • Max size: 100 MB</small>
                            """
                        )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        upload_status = gr.Textbox(
                            label="📊 Processing Status",
                            lines=6,
                            max_lines=10,
                            interactive=False,
                            placeholder="Status updates will appear here..."
                        )
                        
                        upload_summary = gr.Markdown(
                            label="📋 Analysis Summary",
                            value=""
                        )
                    
                    with gr.Column(scale=1):
                        upload_json = gr.JSON(
                            label="🔍 Full Analysis (JSON)",
                            container=True
                        )
            
            # ================================================================
            # TAB 2: LIVE RECORDING
            # ================================================================
            with gr.TabItem("🎤 Record Live", id=1):
                
                with gr.Row():
                    with gr.Column(scale=1):
                        record_input = gr.Audio(
                            sources=["microphone"],
                            type="filepath",
                            label="Record Your Meeting",
                            show_download_button=True,
                            show_share_button=False
                        )
                        
                        record_button = gr.Button(
                            "🚀 Analyze Recording",
                            variant="primary",
                            size="lg"
                        )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        record_status = gr.Textbox(
                            label="📊 Processing Status",
                            lines=6,
                            max_lines=10,
                            interactive=False,
                            placeholder="Status updates will appear here..."
                        )
                        
                        record_summary = gr.Markdown(
                            label="📋 Analysis Summary",
                            value=""
                        )
                    
                    with gr.Column(scale=1):
                        record_json = gr.JSON(
                            label="🔍 Full Analysis (JSON)",
                            container=True
                        )
        
        # ====================================================================
        # EVENT BINDINGS
        # ====================================================================
        
        # Upload tab
        upload_button.click(
            fn=handle_audio_upload,
            inputs=[upload_input],
            outputs=[upload_status, upload_json, upload_summary],
            api_name="upload_audio"
        )
        
        # Record tab
        record_button.click(
            fn=handle_audio_recording,
            inputs=[record_input],
            outputs=[record_status, record_json, record_summary],
            api_name="record_audio"
        )
    
    return app


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the application."""
    
    # Validate configuration
    logger.info("Starting Team Synapse application...")
    
    if not config.validate():
        logger.error("Configuration validation failed. Please check your settings.")
        logger.error("Make sure to set VERTEX_PROJECT_ID and GCS_BUCKET_NAME")
        return
    
    logger.info("Configuration validated successfully")
    logger.info(f"Project ID: {config.google_cloud.project_id}")
    logger.info(f"GCS Bucket: {config.google_cloud.gcs_bucket_name}")
    logger.info(f"Gemini Model: {config.gemini.model_name}")
    
    # Create and launch app
    app = create_app()
    
    logger.info("Launching Gradio interface...")
    
    app.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,
        share=True,  # Set to True for public link
        show_error=True,
        debug=True
    )

if __name__ == "__main__":
    main()