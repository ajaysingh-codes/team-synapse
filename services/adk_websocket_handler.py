"""
ADK WebSocket Handler for Team Synapse.
Bridges browser audio streaming with ADK's run_live() bidirectional streaming.
"""
import asyncio
import base64
import os
from typing import Optional, AsyncIterator, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from google.adk.streaming import LiveRequestQueue
from google.adk.agents.run_config import RunConfig

from services.adk_agent_service import get_runner
from utils import setup_logger
from config import config

logger = setup_logger(__name__, config.app.log_level)


@dataclass
class LiveSession:
    """Tracks state for a live meeting session."""
    session_id: str
    user_id: str = "live_user"
    start_time: datetime = field(default_factory=datetime.now)
    transcript_buffer: list = field(default_factory=list)
    entities_mentioned: Dict[str, set] = field(default_factory=dict)

    def add_transcript(self, text: str):
        """Add text to transcript buffer."""
        self.transcript_buffer.append(text)
        if len(self.transcript_buffer) > 500:  # Keep last 500 entries
            self.transcript_buffer = self.transcript_buffer[-500:]

    def get_full_transcript(self) -> str:
        """Get complete transcript."""
        return " ".join(self.transcript_buffer)


class AdkStreamHandler:
    """
    Handles bidirectional audio streaming with ADK agent.

    This class manages the lifecycle of a live meeting session,
    including audio I/O, entity tracking, and meeting storage.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the stream handler.

        Args:
            api_key: Optional Gemini API key
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.runner = None
        self.session: Optional[LiveSession] = None
        self.live_request_queue: Optional[LiveRequestQueue] = None
        self.is_running = False

    async def start_session(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Start a live meeting session with ADK streaming.

        Args:
            session_id: Unique session identifier

        Yields:
            Dict with event type and data
        """
        if self.is_running:
            raise RuntimeError("Session already running")

        try:
            self.is_running = True
            self.session = LiveSession(session_id=session_id)
            self.live_request_queue = LiveRequestQueue()

            # Get runner instance
            self.runner = get_runner(api_key=self.api_key)

            logger.info(f"Starting ADK live session: {session_id}")

            # Configure for audio responses
            run_config = RunConfig(
                response_modalities=["AUDIO"],  # Audio output
                input_modalities=["AUDIO"],     # Audio input
            )

            # Start ADK live session
            live_events = self.runner.run_live(
                user_id=self.session.user_id,
                session_id=session_id,
                live_request_queue=self.live_request_queue,
                config=run_config
            )

            # Stream events back
            async for event in live_events:
                event_data = await self._process_event(event)
                if event_data:
                    yield event_data

        except Exception as e:
            logger.error(f"Error in live session: {e}", exc_info=True)
            yield {
                "type": "error",
                "message": str(e)
            }
        finally:
            self.is_running = False
            logger.info(f"Ended live session: {session_id}")

    async def _process_event(self, event) -> Optional[Dict[str, Any]]:
        """
        Process an event from ADK.

        Args:
            event: ADK event object

        Returns:
            Dict with processed event data or None
        """
        try:
            # Audio response
            if hasattr(event, 'data') and event.data:
                return {
                    "type": "audio",
                    "data": event.data  # Base64 PCM audio
                }

            # Text response (for transcript/logging)
            if hasattr(event, 'text') and event.text:
                text = event.text.strip()
                if text:
                    self.session.add_transcript(f"[Agent]: {text}")
                    logger.info(f"Agent: {text[:100]}...")
                    return {
                        "type": "text",
                        "text": text,
                        "role": "assistant"
                    }

            # Server content (may contain function calls)
            if hasattr(event, 'server_content') and event.server_content:
                return await self._process_server_content(event.server_content)

            # Tool calls
            if hasattr(event, 'tool_call') and event.tool_call:
                tool_name = event.tool_call.name
                logger.info(f"Tool called: {tool_name}")
                return {
                    "type": "tool_call",
                    "tool": tool_name
                }

            return None

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return None

    async def _process_server_content(self, content) -> Optional[Dict[str, Any]]:
        """Process server content from ADK."""
        try:
            # Extract text from model turn
            if hasattr(content, 'model_turn') and content.model_turn:
                model_turn = content.model_turn
                if hasattr(model_turn, 'parts') and model_turn.parts:
                    for part in model_turn.parts:
                        if hasattr(part, 'text') and part.text:
                            text = part.text.strip()
                            if text:
                                self.session.add_transcript(f"[Agent]: {text}")
                                return {
                                    "type": "text",
                                    "text": text,
                                    "role": "assistant"
                                }
            return None
        except Exception as e:
            logger.error(f"Error processing server content: {e}")
            return None

    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to the agent.

        Args:
            audio_data: Raw PCM audio bytes
        """
        if not self.live_request_queue:
            raise RuntimeError("Session not started")

        try:
            # Convert to ADK format (Base64 PCM)
            audio_message = {
                "mime_type": "audio/pcm",
                "data": base64.b64encode(audio_data).decode("UTF-8")
            }

            await self.live_request_queue.put(audio_message)

        except Exception as e:
            logger.error(f"Error sending audio: {e}")

    async def send_text(self, text: str):
        """
        Send text input to the agent.

        Args:
            text: User text input
        """
        if not self.live_request_queue:
            raise RuntimeError("Session not started")

        try:
            self.session.add_transcript(f"[User]: {text}")

            text_message = {
                "text": text
            }

            await self.live_request_queue.put(text_message)

        except Exception as e:
            logger.error(f"Error sending text: {e}")

    async def end_session(self):
        """End the current session gracefully."""
        if self.live_request_queue:
            # Signal end of input
            await self.live_request_queue.close()

        self.is_running = False
        logger.info("Session ended")

    def get_transcript(self) -> str:
        """Get the full meeting transcript."""
        if self.session:
            return self.session.get_full_transcript()
        return ""


# Helper function for simple audio streaming
async def stream_audio_to_agent(
    audio_iterator: AsyncIterator[bytes],
    session_id: str,
    api_key: Optional[str] = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream audio to ADK agent and yield responses.

    Args:
        audio_iterator: Async iterator yielding audio chunks
        session_id: Unique session ID
        api_key: Optional Gemini API key

    Yields:
        Dict with event type and data
    """
    handler = AdkStreamHandler(api_key=api_key)

    # Start session
    session_task = asyncio.create_task(
        _collect_events(handler.start_session(session_id))
    )

    # Send audio
    try:
        async for audio_chunk in audio_iterator:
            await handler.send_audio(audio_chunk)

            # Yield any pending events
            while not session_task.done():
                try:
                    event = await asyncio.wait_for(
                        session_task.__anext__(),
                        timeout=0.01
                    )
                    yield event
                except asyncio.TimeoutError:
                    break
                except StopAsyncIteration:
                    break
    finally:
        await handler.end_session()

        # Yield remaining events
        try:
            async for event in session_task:
                yield event
        except StopAsyncIteration:
            pass


async def _collect_events(event_stream):
    """Helper to collect events from stream."""
    async for event in event_stream:
        yield event
