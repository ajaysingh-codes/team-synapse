"""
Ingestion pipeline for Team Synapse.
Orchestrates the end-to-end process of ingesting and analyzing meetings.
"""
import os
from typing import Dict, Any, Generator, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from services.gcs_service import gcs_service
from services.gemini_service import gemini_service
from utils import setup_logger
from config import config


logger = setup_logger(__name__, config.app.log_level)


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    success: bool
    meeting_id: str
    analysis: Optional[Dict[str, Any]]
    error: Optional[str]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class IngestionPipeline:
    """Pipeline for ingesting and analyzing meeting recordings."""
    
    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.gcs = gcs_service
        self.gemini = gemini_service
        logger.info("Ingestion pipeline initialized")
    
    def process_audio_file(
        self, 
        local_file_path: str
    ) -> Generator[Tuple[str, Optional[Dict[str, Any]]], None, None]:
        """
        Process an audio file through the complete ingestion pipeline.
        
        This is a generator that yields status updates for real-time UI feedback.
        
        Args:
            local_file_path: Path to the local audio file
        
        Yields:
            Tuple of (status_message, analysis_dict)
            - During processing: (message, None)
            - On completion: (final_message, analysis)
            - On error: (error_message, None)
        """
        gcs_uri = None
        meeting_id = None
        
        try:
            # Validate file
            if not os.path.exists(local_file_path):
                yield "Error: File not found", None
                return
            
            filename = os.path.basename(local_file_path)
            file_size_mb = os.path.getsize(local_file_path) / (1024 * 1024)
            
            if file_size_mb > config.app.max_file_size_mb:
                yield f"Error: File size ({file_size_mb:.1f}MB) exceeds limit ({config.app.max_file_size_mb}MB)", None
                return
            
            # Generate meeting ID
            meeting_id = self._generate_meeting_id(filename)
            
            # Step 1: Upload to GCS
            logger.info(f"Processing meeting: {meeting_id}")
            yield f"📤 Uploading '{filename}' to Google Cloud Storage...", None
            
            gcs_uri = self.gcs.upload_file(local_file_path, folder="meetings")
            
            yield f"✅ Upload complete\n\n🧠 Analyzing with Gemini (this may take 30-60 seconds)...", None
            
            # Step 2: Analyze with Gemini
            mime_type = self._get_mime_type(local_file_path)
            analysis = self.gemini.analyze_audio(gcs_uri, mime_type)
            
            # Enrich analysis with metadata
            analysis["meetingId"] = meeting_id
            analysis["originalFilename"] = filename
            analysis["processingTimestamp"] = datetime.utcnow().isoformat()
            analysis["gcsUri"] = gcs_uri
            
            logger.info(f"Analysis complete for meeting: {meeting_id}")
            
            # Step 3: Success
            yield self._format_success_message(analysis), analysis
            
        except Exception as e:
            error_msg = f"❌ Error processing audio: {str(e)}"
            logger.error(f"Pipeline error for {meeting_id}: {e}", exc_info=True)
            yield error_msg, None
            
        finally:
            # Cleanup: Delete from GCS after processing
            if gcs_uri:
                logger.info(f"Cleaning up GCS file: {gcs_uri}")
                self.gcs.delete_file(gcs_uri)
            
            # Cleanup: Delete local temp file
            if local_file_path and self._is_temp_file(local_file_path):
                try:
                    os.remove(local_file_path)
                    logger.debug(f"Cleaned up local temp file: {local_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")
    
    def _generate_meeting_id(self, filename: str) -> str:
        """Generate a unique meeting ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = os.path.splitext(filename)[0].replace(" ", "_")[:30]
        return f"mtg_{timestamp}_{safe_filename}"
    
    def _get_mime_type(self, filepath: str) -> str:
        """Determine MIME type from file extension."""
        ext = os.path.splitext(filepath)[1].lower()
        
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
        }
        
        return mime_types.get(ext, "audio/mpeg")
    
    def _is_temp_file(self, filepath: str) -> bool:
        """Check if file is a temporary file."""
        return any(marker in filepath.lower() for marker in ["temp", "tmp", "gradio"])
    
    def _format_success_message(self, analysis: Dict[str, Any]) -> str:
        """Format a success message with key stats."""
        stats = []
        
        if "actionItems" in analysis:
            stats.append(f"{len(analysis['actionItems'])} action items")
        
        if "keyDecisions" in analysis:
            stats.append(f"{len(analysis['keyDecisions'])} decisions")
        
        if "mentionedPeople" in analysis:
            stats.append(f"{len(analysis['mentionedPeople'])} people mentioned")
        
        stats_str = ", ".join(stats) if stats else "No items extracted"
        
        return f"✅ Analysis complete!\n\n📊 Extracted: {stats_str}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics (placeholder for future implementation)."""
        return {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0
        }


# Global pipeline instance
ingestion_pipeline = IngestionPipeline()