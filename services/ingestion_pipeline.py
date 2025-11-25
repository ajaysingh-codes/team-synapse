"""
Ingestion pipeline for Team Synapse.
Orchestrates the end-to-end process of ingesting and analyzing meetings.

Updated in Step 3: Now stores meeting data in Neo4j knowledge graph.
"""
import os
from typing import Dict, Any, Generator, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from services.gcs_service import gcs_service
from services.gemini_service import gemini_service
from services.neo4j_service import neo4j_service
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
    neo4j_stored: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class IngestionPipeline:
    """Pipeline for ingesting and analyzing meeting recordings."""
    
    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.gcs = gcs_service
        self.gemini = gemini_service
        self.neo4j = neo4j_service
        logger.info("Ingestion pipeline initialized (with Neo4j support)")

    def extract_meeting_context_from_text(
        self,
        context_text: str,
    ) -> Dict[str, Any]:
        """
        Extract structured meeting context from an uploaded text file.

        This is used when the user uploads a calendar invite or agenda file.

        Args:
            context_text: Raw text content from the uploaded file

        Returns:
            Dictionary containing structured meeting context
        """
        logger.info("Extracting meeting context from uploaded file text")

        # Heuristic: detect .ics calendar files by typical VCALENDAR markers
        sample = context_text.lstrip().upper()
        is_ics = sample.startswith("BEGIN:VCALENDAR") or "BEGIN:VEVENT" in sample[:500]
        source_type_hint = "ics" if is_ics else "other"

        return self.gemini.extract_meeting_context(context_text, source_type_hint=source_type_hint)
    
    def process_audio_file(
        self, 
        local_file_path: str,
        meeting_context: Optional[Dict[str, Any]] = None,
        analysis_mode: str = "corporate",
    ) -> Generator[Tuple[str, Optional[Dict[str, Any]]], None, None]:
        """
        Process an audio file through the complete ingestion pipeline.
        
        NOW INCLUDES: Neo4j knowledge graph storage (Step 3)
        
        This is a generator that yields status updates for real-time UI feedback.
        
        Args:
            local_file_path: Path to the local audio file
            meeting_context: Optional dict of meeting metadata extracted from
                a calendar invite / agenda (title, date, attendees, etc.)
        
        Yields:
            Tuple of (status_message, analysis_dict)
            - During processing: (message, None)
            - On completion: (final_message, analysis)
            - On error: (error_message, None)
        """
        gcs_uri = None
        meeting_id = None
        neo4j_stored = False
        
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
            
            # Step 2: Analyze with Gemini (include meeting context when available)
            mime_type = self._get_mime_type(local_file_path)
            analysis = self.gemini.analyze_audio(
                gcs_uri,
                mime_type,
                meeting_context=meeting_context,
                analysis_mode=analysis_mode,
            )
            
            # Enrich analysis with metadata
            analysis["meetingId"] = meeting_id
            analysis["tenantId"] = config.app.tenant_id
            analysis["originalFilename"] = filename
            analysis["processingTimestamp"] = datetime.utcnow().isoformat()
            analysis["gcsUri"] = gcs_uri
            
            # If we have structured meeting context, attach it and prefer it
            # for certain high-level fields (title/date) where appropriate.
            if meeting_context:
                logger.info("Merging invite/agenda context into meeting analysis")
                analysis["inviteContext"] = meeting_context

                # Prefer explicit meeting metadata from the invite over inferred values
                ctx_title = meeting_context.get("meetingTitle")
                ctx_date = meeting_context.get("meetingDate")
                ctx_start = meeting_context.get("meetingStartTime")
                ctx_end = meeting_context.get("meetingEndTime")
                ctx_desc = meeting_context.get("description")
                ctx_attendees = meeting_context.get("attendees", [])

                if ctx_title:
                    analysis["meetingTitle"] = ctx_title
                if ctx_date and ctx_date != "unknown":
                    analysis["meetingDate"] = ctx_date

                # Store a normalized block for downstream systems (e.g., Neo4j, MCP tools)
                analysis["inviteMetadata"] = {
                    "meetingTitle": ctx_title or analysis.get("meetingTitle"),
                    "meetingDate": ctx_date or analysis.get("meetingDate"),
                    "meetingStartTime": ctx_start,
                    "meetingEndTime": ctx_end,
                    "description": ctx_desc,
                    "attendees": ctx_attendees,
                }
            
            logger.info(f"Analysis complete for meeting: {meeting_id}")
            
            # Step 3: Store in Neo4j (NEW!)
            if config.app.neo4j_enabled:
                yield f"✅ Analysis complete!\n\n💾 Storing in Neo4j knowledge graph...", analysis
                
                try:
                    neo4j_stored = self.neo4j.store_meeting_data(analysis)
                    
                    if neo4j_stored:
                        logger.info(f"Stored meeting in Neo4j: {meeting_id}")
                        yield f"✅ Stored in Neo4j knowledge graph!\n\n{self._format_success_message(analysis)}", analysis
                    else:
                        logger.warning(f"Neo4j storage failed for meeting: {meeting_id}")
                        yield f"⚠️ Neo4j storage failed (non-critical)\n\n{self._format_success_message(analysis)}", analysis
                        
                except Exception as neo4j_error:
                    logger.error(f"Neo4j storage error: {neo4j_error}", exc_info=True)
                    yield f"⚠️ Neo4j storage error (non-critical): {str(neo4j_error)}\n\n{self._format_success_message(analysis)}", analysis
            else:
                # Neo4j disabled, just return success
                logger.info("Neo4j storage disabled, skipping graph storage")
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
        tenant = (config.app.tenant_id or "demo").strip()
        safe_tenant = (
            tenant.replace("@", "_")
                  .replace(" ", "_")
                  .replace("/", "_")
                  .replace("\\", "_")
        )[:30]
        return f"{safe_tenant}_mtg_{timestamp}_{safe_filename}"
    
    def _get_mime_type(self, filepath: str) -> str:
        """Determine MIME type from file extension."""
        ext = os.path.splitext(filepath)[1].lower()
        
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
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
        """
        Get pipeline statistics including Neo4j graph stats.
        
        Returns:
            Dictionary with processing and knowledge graph statistics
        """
        stats = {
            "pipeline": {
                "total_processed": 0,  # Could track this with a counter
                "success_count": 0,
                "error_count": 0
            }
        }
        
        # Add Neo4j knowledge graph statistics if enabled
        if config.app.neo4j_enabled:
            try:
                graph_stats = self.neo4j.get_knowledge_graph_summary()
                stats["knowledge_graph"] = graph_stats
            except Exception as e:
                logger.warning(f"Could not retrieve knowledge graph stats: {e}")
                stats["knowledge_graph"] = {"error": str(e)}
        
        return stats


# Global pipeline instance
ingestion_pipeline = IngestionPipeline()