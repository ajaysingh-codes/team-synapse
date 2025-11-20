"""
Gemini AI service for Team Synapse.
Handles audio analysis and structured data extraction.
"""
import json
from typing import Dict, Any, Optional, List, Union
import vertexai
from vertexai.generative_models import (
    GenerativeModel, 
    Part, 
    GenerationConfig,
    Tool,
    FunctionDeclaration,
    Content,
    HarmCategory,
    HarmBlockThreshold
)

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

    # Prompt for extracting meeting context from a calendar invite / agenda
    CONTEXT_PROMPT = """
You are an expert assistant that extracts LIGHTWEIGHT meeting metadata from raw calendar invites,
email invites, and agenda documents for a system called Team Synapse.

Your job is to read the provided text (which may be a calendar invite, .ics file, pasted email,
or written agenda) and return a SINGLE JSON object with the following structure:

{
  "sourceType": "ics" or "other",
  "meetingTitle": "Short descriptive title of the meeting",
  "meetingDate": "ISO date if present (YYYY-MM-DD) or 'unknown'",
  "meetingStartTime": "ISO time if present (HH:MM, 24h) or 'unknown'",
  "meetingEndTime": "ISO time if present (HH:MM, 24h) or 'unknown'",
  "description": "If sourceType is 'other': 1-3 sentence human summary of the invite/agenda (no raw URLs; replace any line breaks with spaces). If sourceType is 'ics': empty string ''.",
  "previousMeetingSummary": "If sourceType is 'other' and prior meeting context is clearly described, a 1-2 sentence summary of what was discussed previously. Otherwise, empty string ''.",
  "attendees": [
    {
      "name": "Full name of attendee if present",
      "email": "Email address if present, otherwise ''"
    }
  ]
}

CRITICAL INSTRUCTIONS:
- You MUST return ONLY valid JSON (no markdown, no comments, no extra text).
- Do NOT wrap the JSON in ```json or ``` markers.
- If a field is not present in the text, use the default values described above.
- If the text clearly looks like an .ics file (e.g., starts with BEGIN:VCALENDAR / VEVENT / DTSTART), set "sourceType" to "ics" and only populate meetingTitle, meetingDate, meetingStartTime, meetingEndTime, and attendees. In that case, set description and previousMeetingSummary to "".
- For non-.ics sources (emails, docs, plaintext agendas), set "sourceType" to "other" and also populate description and previousMeetingSummary when you can infer them.
- In description and previousMeetingSummary, do NOT include full URLs or Zoom/SIP dial-in strings; summarize them in plain language instead.
- Do NOT include raw line breaks inside any string values; replace them with spaces.
- Do NOT invent projects or extra structure beyond this schema.
- Extract all attendees that appear or are clearly implied.
"""

    # System instruction for the chatbot
    CHAT_SYSTEM_INSTRUCTION = """
You are the Team Synapse Meeting Copilot.
You help users explore their meeting knowledge graph.
You have access to tools to search meetings, find action items, and look up project/client history.
Use these tools whenever the user asks a question that requires looking up data.
Always answer in a helpful, professional, and concise manner.
"""
    
    def __init__(self):
        """Initialize Vertex AI and Gemini model."""
        try:
            vertexai.init(
                project=config.google_cloud.project_id,
                location=config.google_cloud.location
            )
            
            self.model = GenerativeModel(
                config.gemini.model_name,
                system_instruction=self.CHAT_SYSTEM_INSTRUCTION
            )
            
            self.generation_config = GenerationConfig(
                temperature=config.gemini.temperature,
                max_output_tokens=config.gemini.max_output_tokens,
            )
            
            logger.info(f"Gemini Service initialized with model: {config.gemini.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            raise
    
    def analyze_audio(
        self,
        gcs_uri: str,
        mime_type: str = "audio/mpeg",
        meeting_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze audio file with Gemini.
        
        This is the "WINNER STEP" - Gemini handles both transcription
        and intelligent analysis in a single API call.
        
        Args:
            gcs_uri: GCS URI of the audio file (gs://bucket/path)
            mime_type: MIME type of the audio file
            meeting_context: Optional dict with meeting metadata (title, attendees, etc.)
        
        Returns:
            Dictionary containing structured meeting analysis
        
        Raises:
            Exception: If analysis fails
        """
        try:
            logger.info(f"Starting Gemini analysis for: {gcs_uri}")
            
            # Create audio part from GCS URI
            audio_part = Part.from_uri(gcs_uri, mime_type=mime_type)

            # Build optional context text so Gemini can align entities
            parts = [audio_part]
            if meeting_context:
                context_lines = []
                title = meeting_context.get("meetingTitle")
                date = meeting_context.get("meetingDate")
                start = meeting_context.get("meetingStartTime")
                end = meeting_context.get("meetingEndTime")
                attendees = meeting_context.get("attendees", []) or []

                if title:
                    context_lines.append(f"Canonical meeting title: {title}")
                if date or start or end:
                    context_lines.append(
                        f"Canonical meeting time: {date or 'unknown date'} {start or ''}-{end or ''}".strip()
                    )

                if attendees:
                    context_lines.append("Canonical participants (name and optional email):")
                    for a in attendees:
                        name = (a.get("name") or "").strip()
                        email = (a.get("email") or "").strip()
                        if name or email:
                            if email:
                                context_lines.append(f"- {name} <{email}>".strip())
                            else:
                                context_lines.append(f"- {name}")

                context_text = (
                    "You are also given canonical meeting metadata. "
                    "When extracting people and assigning action items, "
                    "map participant mentions to these canonical participants when possible.\n\n"
                    + "\n".join(context_lines)
                )
                parts.append(context_text)

            # Generate content with the audio, optional context, and prompt
            parts.append(self.ANALYSIS_PROMPT)

            response = self.model.generate_content(
                parts,
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

    def extract_meeting_context(self, source_text: str, source_type_hint: str = "auto") -> Dict[str, Any]:
        """
        Extract structured meeting context (attendees, projects, agenda) from text.

        This is used for processing uploaded calendar invites and agendas prior
        to audio ingestion, to reduce friction for the user.

        Args:
            source_text: Raw text content from the uploaded file
            source_type_hint: Optional hint, "ics" or "other" or "auto"

        Returns:
            Dictionary containing structured meeting context

        Raises:
            Exception: If extraction fails or JSON is invalid
        """
        try:
            logger.info("Starting Gemini meeting context extraction")

            # Combine the instruction prompt with the raw source text
            prompt = (
                self.CONTEXT_PROMPT
                + f"\n\nSource type hint: {source_type_hint}\n"
                + "\n---\n\nHere is the calendar invite / agenda text:\n\n"
                + source_text
            )

            response = self.model.generate_content(
                [prompt],
                generation_config=self.generation_config,
            )

            response_text = response.text.strip()
            response_text = self._clean_json_response(response_text)

            logger.debug(f"Raw meeting context response: {response_text[:200]}...")

            context = json.loads(response_text)
            logger.info("Gemini meeting context extraction completed successfully")
            return context

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse meeting context JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response from Gemini (context): {e}")
        except Exception as e:
            logger.error(f"Error during meeting context extraction: {e}")
            raise
            
    def chat(self, history: List[Content], mcp_tools: Optional[List[Any]] = None) -> Any:
        """
        Generate a chat response, potentially using tools.
        
        Args:
            history: List of Vertex AI Content objects representing the conversation history.
            mcp_tools: List of MCP tool definitions to be converted for Gemini.
            
        Returns:
            Vertex AI GenerationResponse
        """
        try:
            tools = []
            if mcp_tools:
                gemini_tools = self._convert_mcp_tools_to_gemini(mcp_tools)
                if gemini_tools:
                    tools = [Tool(function_declarations=gemini_tools)]
            
            response = self.model.generate_content(
                history,
                tools=tools,
                generation_config=self.generation_config
            )
            return response
            
        except Exception as e:
            logger.error(f"Error during chat generation: {e}")
            raise

    def _convert_mcp_tools_to_gemini(self, mcp_tools: List[Any]) -> List[FunctionDeclaration]:
        """
        Convert MCP tool definitions to Gemini FunctionDeclarations.
        """
        declarations = []
        for tool in mcp_tools:
            # MCP tool structure: name, description, inputSchema
            # Gemini structure: name, description, parameters
            
            # Ensure inputSchema is a dict
            parameters = tool.inputSchema if isinstance(tool.inputSchema, dict) else tool.inputSchema.model_dump()
            
            # Fix for Gemini: 'type' is required in parameters
            if "type" not in parameters:
                parameters["type"] = "object"
                
            declarations.append(
                FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=parameters
                )
            )
        return declarations
    
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
