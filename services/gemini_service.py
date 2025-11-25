"""
Gemini AI service for Team Synapse.
Handles audio analysis and structured data extraction.
"""
import json
from typing import Dict, Any, Optional, List
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Part,
    GenerationConfig,
    Tool,
    FunctionDeclaration,
    Content,
)

from config import config
from utils import setup_logger


logger = setup_logger(__name__, config.app.log_level)


class GeminiService:
    """Service for Gemini AI operations."""
    
    # Corporate-focused extraction (academic and creative modes removed)
    CORPORATE_CONFIG = {
        "role": "expert corporate meeting analyst",
        "action_label": "Action Items",
        "decision_label": "Key Decisions",
        "project_label": "Projects",
        "people_label": "Stakeholders",
        "instruction": "Focus on accountability, deadlines, business outcomes, strategic alignment, risks, and blockers.",
    }

    def _get_analysis_prompt(self, mode: str = "corporate") -> str:
        """Build corporate-focused analysis prompt."""
        persona = self.CORPORATE_CONFIG

        return f"""
You are an {persona['role']} for a knowledge management system called Team Synapse.

Your task is to:
1. Transcribe the audio file completely and accurately.
2. Extract structured information to build a knowledge graph.

Analyze the recording and return a JSON object using the following schema.
You must reinterpret the semantics of each field according to your role, but keep
the JSON keys and overall structure exactly the same:

- "transcript": Verbatim transcript of the recording.
- "meetingTitle": A short, descriptive title.
- "summary": A concise summary of the discussion.
- "meetingDate": ISO date (YYYY-MM-DD) if mentioned, otherwise "unknown".
- "actionItems": List of **{persona['action_label']}** with accountability and deadlines.
    - "task": Clear description of what needs to be done.
    - "assignee": Full name of person responsible.
    - "assigneeRole": Job title/role if mentioned (e.g., "PM", "Engineering Lead").
    - "dueDate": Deadline if mentioned, otherwise "none".
    - "priority": "high", "medium", "low", or "unspecified".
    - "status": "pending", "in_progress", "blocked", or "completed" (infer from context).
    - "blockers": List of blockers or dependencies mentioned (e.g., ["Security audit pending"]).
    - "estimatedEffort": Time estimate if mentioned (e.g., "2 days", "4 hours") or "unknown".
- "keyDecisions": List of **{persona['decision_label']}** made during the meeting.
- "mentionedProjects": List of **{persona['project_label']}** discussed.
- "mentionedPeople": List of **{persona['people_label']}** mentioned by full name.
- "mentionedClients": Client or company names mentioned.
- "sentiment": Overall sentiment of the discussion (positive/neutral/negative/mixed).
- "topics": Main topics discussed (3-5 key topics).
- "meetingType": Type of meeting - one of: "strategy", "planning", "standup", "review", "client_call", "all_hands", "retrospective", "other".
- "duration": Estimated duration in minutes (number) or null if unknown.
- "metadata": Optional object with:
    - "urgencyLevel": "urgent", "high", "normal", or "low" (based on tone and content).
    - "requiresFollowUp": true or false.
    - "tags": List of relevant tags for categorization.

CRITICAL INSTRUCTIONS:
- {persona['instruction']}
- Return ONLY valid JSON, with no markdown formatting or code fences.
- Do NOT include ```json or ``` markers.
- Ensure all string values are properly escaped.
- If information is not available, use sensible defaults as described above.
"""

    # Prompt for extracting meeting context from a wide range of "context documents"
    CONTEXT_PROMPT = """
You are an expert assistant that extracts LIGHTWEIGHT meeting or session metadata from
raw "context documents" for a system called Team Synapse.

These documents may include calendar invites, meeting agendas, course syllabuses,
assignment sheets, or similar planning/description documents.

Your job is to read the provided text and return a SINGLE JSON object with the
following structure:

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
        analysis_mode: str = "corporate",  # Only corporate mode supported
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
            logger.info(f"Starting Gemini analysis ({analysis_mode}) for: {gcs_uri}")
            
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

            # Generate content with the audio, optional context, and persona-aware prompt
            prompt_text = self._get_analysis_prompt(analysis_mode)
            parts.append(prompt_text)

            # Use JSON-focused generation config to improve structured extraction
            json_config = GenerationConfig(
                temperature=config.gemini.temperature,
                max_output_tokens=config.gemini.max_output_tokens,
                response_mime_type="application/json",
            )

            response = self.model.generate_content(
                parts,
                generation_config=json_config,
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

            # Use JSON-focused generation config to improve structured extraction
            json_config = GenerationConfig(
                temperature=config.gemini.temperature,
                max_output_tokens=config.gemini.max_output_tokens,
                response_mime_type="application/json",
            )

            response = self.model.generate_content(
                [prompt],
                generation_config=json_config,
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
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from text using Gemini.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Dictionary with entity types and lists of entities
        """
        try:
            prompt = f"""
            Extract entities from this text:
            
            {text}
            
            Return ONLY a plain JSON object (no code blocks, no markdown):
            {{
                "people": ["name1", "name2"],
                "projects": ["project1"],
                "clients": ["company1"],
                "technologies": ["tech1"]
            }}
            
            Rules:
            - Return ONLY the JSON object, nothing else
            - No markdown code blocks (no ```json)
            - Only extract actual proper nouns, not generic terms
            - Empty arrays if no entities found
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.1,
                    top_p=0.95,
                    max_output_tokens=1024,
                )
            )
            
            # Parse JSON response - strip code blocks if present
            response_text = response.text.strip()
            
            # Remove markdown code blocks if Gemini added them
            if response_text.startswith("```"):
                # Find the actual JSON content between code fences
                lines = response_text.split('\n')
                # Skip first line (```json or ```) and last line (```)
                response_text = '\n'.join(lines[1:-1]).strip()
            
            result = json.loads(response_text)
            
            # Ensure all keys exist
            entities = {
                "people": result.get("people", []),
                "projects": result.get("projects", []),
                "clients": result.get("clients", []),
                "technologies": result.get("technologies", [])
            }
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {"people": [], "projects": [], "clients": [], "technologies": []}
    
    def extract_commitments(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Extract commitments and promises from conversation transcript.
        
        Args:
            transcript: Conversation transcript
            
        Returns:
            List of commitment dictionaries
        """
        try:
            prompt = f"""
            Analyze this conversation for commitments and promises:
            
            {transcript}
            
            Extract any commitments made, including:
            - Who made the commitment (assignee)
            - What was promised (task)
            - When it's due (deadline) - if mentioned
            - What it depends on (dependencies) - if mentioned
            
            Return as JSON array of objects with keys:
            assignee, task, deadline, dependencies
            
            Only include clear commitments, not vague statements.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.2,
                    top_p=0.95,
                    max_output_tokens=2048,
                )
            )
            
            # Parse JSON response - strip code blocks if present
            response_text = response.text.strip()
            if response_text.startswith("```"):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]).strip()
            
            commitments = json.loads(response_text)
            
            # Ensure it's a list
            if not isinstance(commitments, list):
                commitments = [commitments] if commitments else []
            
            # Validate structure
            for commit in commitments:
                commit.setdefault("assignee", "Unassigned")
                commit.setdefault("task", "")
                commit.setdefault("deadline", "Not specified")
                commit.setdefault("dependencies", [])
            
            return commitments
            
        except Exception as e:
            logger.error(f"Error extracting commitments: {e}")
            return []
    
    def extract_live_entities(self, transcript_chunk: str) -> Dict[str, Any]:
        """
        Extract entities from a live transcript chunk.
        Lightweight extraction for real-time processing.
        
        Args:
            transcript_chunk: Recent transcript text
            
        Returns:
            Dictionary with extracted entities
        """
        try:
            # Use simpler extraction for real-time
            entities = self.extract_entities(transcript_chunk)
            
            # Format for live agent
            return {
                "currentTopic": self._extract_topic(transcript_chunk),
                "people": entities.get("people", []),
                "projects": entities.get("projects", []),
                "clients": entities.get("clients", []),
                "decisions": [],  # Would need more context
                "questions": self._extract_questions(transcript_chunk),
                "actionItems": [],  # Would need commitment detection
                "keyTerms": entities.get("technologies", [])
            }
            
        except Exception as e:
            logger.error(f"Error in live entity extraction: {e}")
            return {
                "currentTopic": "",
                "people": [],
                "projects": [],
                "clients": [],
                "decisions": [],
                "questions": [],
                "actionItems": [],
                "keyTerms": []
            }
    
    def _extract_topic(self, text: str) -> str:
        """Extract the main topic from text."""
        try:
            prompt = f"What is the main topic of this text in 5 words or less: {text[:200]}"
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return ""
    
    def _extract_questions(self, text: str) -> List[str]:
        """Extract questions from text."""
        import re
        questions = re.findall(r'[^.!?]*\?', text)
        return [q.strip() for q in questions if len(q.strip()) > 10]


# Global service instance
gemini_service = GeminiService()
