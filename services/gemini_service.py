"""
Gemini AI service for Team Synapse.
Handles audio analysis and structured data extraction.
"""
import json
from typing import Dict, Any
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from config import config
from utils import setup_logger


logger = setup_logger(__name__, config.app.log_level)


class GeminiService:
    """Service for Gemini AI operations."""
    
    # Enhanced prompt for structured meeting analysis
    ANALYSIS_PROMPT = """
You are an expert meeting analyst for an enterprise knowledge management system called Team Synapse.

Your task is to:
1. Transcribe the audio file completely and accurately
2. Extract structured information to build a corporate knowledge graph

Analyze the meeting and return a JSON object with the following structure:

{
  "transcript": "Complete verbatim transcript of the meeting",
  "meetingTitle": "A short, descriptive title (5-8 words)",
  "summary": "One paragraph summary highlighting key points",
  "meetingDate": "Inferred date if mentioned, or 'unknown' (ISO format: YYYY-MM-DD)",
  "actionItems": [
    {
      "task": "Specific action item description",
      "assignee": "Person name if mentioned, or 'unassigned'",
      "dueDate": "Due date if mentioned, or 'none' (ISO format: YYYY-MM-DD)",
      "priority": "high/medium/low or 'unspecified'"
    }
  ],
  "keyDecisions": [
    "Each key decision made during the meeting"
  ],
  "sentiment": "overall/positive/neutral/negative/mixed",
  "mentionedPeople": [
    "All person names mentioned (first and last when available)"
  ],
  "mentionedClients": [
    "All client or company names mentioned"
  ],
  "mentionedProjects": [
    "All project names or codenames mentioned"
  ],
  "topics": [
    "Main topics discussed (3-5 key topics)"
  ]
}

CRITICAL INSTRUCTIONS:
- Return ONLY valid JSON, no markdown formatting, no code blocks
- Do not include ```json or ``` markers
- Ensure all string values are properly escaped
- If information is not available, use the defaults specified above
- Be comprehensive in the transcript
- Extract ALL names, clients, and projects mentioned
"""
    
    def __init__(self):
        """Initialize Vertex AI and Gemini model."""
        try:
            vertexai.init(
                project=config.google_cloud.project_id,
                location=config.google_cloud.location
            )
            
            self.model = GenerativeModel(config.gemini.model_name)
            
            self.generation_config = GenerationConfig(
                temperature=config.gemini.temperature,
                max_output_tokens=config.gemini.max_output_tokens,
            )
            
            logger.info(f"Gemini Service initialized with model: {config.gemini.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            raise
    
    def analyze_audio(self, gcs_uri: str, mime_type: str = "audio/mpeg") -> Dict[str, Any]:
        """
        Analyze audio file with Gemini.
        
        This is the "WINNER STEP" - Gemini handles both transcription
        and intelligent analysis in a single API call.
        
        Args:
            gcs_uri: GCS URI of the audio file (gs://bucket/path)
            mime_type: MIME type of the audio file
        
        Returns:
            Dictionary containing structured meeting analysis
        
        Raises:
            Exception: If analysis fails
        """
        try:
            logger.info(f"Starting Gemini analysis for: {gcs_uri}")
            
            # Create audio part from GCS URI
            audio_part = Part.from_uri(gcs_uri, mime_type=mime_type)
            
            # Generate content with the audio and prompt
            response = self.model.generate_content(
                [audio_part, self.ANALYSIS_PROMPT],
                generation_config=self.generation_config
            )
            
            # Extract and parse response
            response_text = response.text.strip()
            
            # Clean up any markdown formatting that might slip through
            response_text = self._clean_json_response(response_text)
            
            logger.debug(f"Raw Gemini response: {response_text[:200]}...")
            
            # Parse JSON
            analysis = json.loads(response_text)
            
            # Validate required fields
            self._validate_analysis(analysis)
            
            logger.info("Gemini analysis completed successfully")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            logger.error(f"Error during Gemini analysis: {e}")
            raise
    
    def _clean_json_response(self, text: str) -> str:
        """
        Clean markdown formatting from JSON response.
        
        Args:
            text: Raw response text
        
        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        text = text.replace("```json", "").replace("```", "")
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _validate_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Validate that analysis contains required fields.
        
        Args:
            analysis: Parsed analysis dictionary
        
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "transcript",
            "meetingTitle",
            "summary",
            "actionItems",
            "keyDecisions",
            "sentiment",
            "mentionedPeople"
        ]
        
        missing_fields = [field for field in required_fields if field not in analysis]
        
        if missing_fields:
            raise ValueError(f"Analysis missing required fields: {missing_fields}")
        
        logger.debug("Analysis validation passed")


# Global service instance
gemini_service = GeminiService()