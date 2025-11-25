"""
Miro Visualization MCP Tools.
Tools for creating visual mind maps and knowledge graphs in Miro.
"""
import os
import math
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from dotenv import load_dotenv
from utils import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# Miro API configuration
MIRO_API_TOKEN = os.getenv("MIRO_API_TOKEN")
MIRO_BOARD_ID = os.getenv("MIRO_BOARD_ID")
MIRO_BASE_URL = "https://api.miro.com/v2"


def _get_headers() -> Dict[str, str]:
    """Get Miro API headers."""
    return {
        "Authorization": f"Bearer {MIRO_API_TOKEN}",
        "Content-Type": "application/json"
    }


def _is_configured() -> bool:
    """Check if Miro is properly configured."""
    return bool(MIRO_API_TOKEN and MIRO_BOARD_ID)


def _create_sticky_note(
    content: str,
    x: float,
    y: float,
    color: str = "yellow"
) -> Optional[Dict[str, Any]]:
    """Create a sticky note on the Miro board."""
    if not _is_configured():
        return None

    # Map color names to Miro color codes
    color_map = {
        "yellow": "yellow",
        "blue": "blue",
        "green": "green",
        "red": "red",
        "purple": "violet",
        "orange": "orange",
        "cyan": "cyan",
        "gray": "gray"
    }

    try:
        data = {
            "data": {
                "content": content,
                "shape": "square"
            },
            "style": {
                "fillColor": color_map.get(color, "yellow")
            },
            "position": {
                "x": x,
                "y": y
            }
        }

        response = requests.post(
            f"{MIRO_BASE_URL}/boards/{MIRO_BOARD_ID}/sticky_notes",
            headers=_get_headers(),
            json=data
        )

        if response.status_code == 201:
            return response.json()
        else:
            logger.error(f"Failed to create sticky note: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error creating sticky note: {e}")
        return None


def _create_shape(
    text: str,
    x: float,
    y: float,
    width: int = 200,
    height: int = 100,
    color: str = "blue"
) -> Optional[Dict[str, Any]]:
    """Create a shape on the Miro board."""
    if not _is_configured():
        return None

    color_map = {
        "yellow": "#fef445",
        "blue": "#2d9bf0",
        "green": "#8fd14f",
        "red": "#f24726",
        "purple": "#da0063",
        "orange": "#fac710",
        "cyan": "#12cdd4",
        "gray": "#808080"
    }

    try:
        data = {
            "data": {
                "content": f"<p>{text}</p>",
                "shape": "round_rectangle"
            },
            "style": {
                "fillColor": color_map.get(color, "#2d9bf0"),
                "borderColor": "#1a1a1a",
                "borderWidth": "2"
            },
            "position": {
                "x": x,
                "y": y
            },
            "geometry": {
                "width": width,
                "height": height
            }
        }

        response = requests.post(
            f"{MIRO_BASE_URL}/boards/{MIRO_BOARD_ID}/shapes",
            headers=_get_headers(),
            json=data
        )

        if response.status_code == 201:
            return response.json()
        else:
            logger.error(f"Failed to create shape: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error creating shape: {e}")
        return None


def _create_connector(
    start_item_id: str,
    end_item_id: str
) -> Optional[Dict[str, Any]]:
    """Create a connector between two items on the Miro board."""
    if not _is_configured():
        return None

    try:
        data = {
            "startItem": {
                "id": start_item_id
            },
            "endItem": {
                "id": end_item_id
            },
            "style": {
                "strokeColor": "#1a1a1a",
                "strokeWidth": "2"
            }
        }

        response = requests.post(
            f"{MIRO_BASE_URL}/boards/{MIRO_BOARD_ID}/connectors",
            headers=_get_headers(),
            json=data
        )

        if response.status_code == 201:
            return response.json()
        else:
            logger.error(f"Failed to create connector: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error creating connector: {e}")
        return None


def get_miro_board_url() -> str:
    """
    Get the URL to the configured Miro board.

    Returns:
        The Miro board URL or an error message if not configured
    """
    if not _is_configured():
        return "Miro is not configured. Set MIRO_API_TOKEN and MIRO_BOARD_ID environment variables."

    return f"https://miro.com/app/board/{MIRO_BOARD_ID}/"


def create_meeting_mindmap(
    meeting_title: str,
    meeting_date: str,
    action_items: str = "",
    decisions: str = "",
    people: str = "",
    clients: str = "",
    projects: str = ""
) -> str:
    """
    Create a visual mind map for a meeting in Miro.
    Creates a central meeting node with branches for entities.

    Args:
        meeting_title: Title of the meeting
        meeting_date: Date of the meeting (YYYY-MM-DD)
        action_items: Comma-separated list of action items
        decisions: Comma-separated list of decisions
        people: Comma-separated list of people mentioned
        clients: Comma-separated list of clients mentioned
        projects: Comma-separated list of projects mentioned

    Returns:
        Success message with board URL or error message
    """
    if not _is_configured():
        return "Miro is not configured. Set MIRO_API_TOKEN and MIRO_BOARD_ID environment variables to enable visual mind maps."

    try:
        # Parse comma-separated inputs
        action_list = [a.strip() for a in action_items.split(",") if a.strip()] if action_items else []
        decision_list = [d.strip() for d in decisions.split(",") if d.strip()] if decisions else []
        people_list = [p.strip() for p in people.split(",") if p.strip()] if people else []
        client_list = [c.strip() for c in clients.split(",") if c.strip()] if clients else []
        project_list = [p.strip() for p in projects.split(",") if p.strip()] if projects else []

        # Center position for the mind map
        center_x, center_y = 0, 0
        radius = 400

        # Create central meeting node
        meeting_node = _create_shape(
            text=f"<strong>{meeting_title}</strong><br/>{meeting_date}",
            x=center_x,
            y=center_y,
            width=250,
            height=120,
            color="blue"
        )

        if not meeting_node:
            return "Failed to create meeting node in Miro. Check your API credentials."

        created_nodes = {"meeting": meeting_node["id"]}
        node_count = 1

        # Define entity branches
        entity_types = [
            ("Action Items", action_list, "red", "checkbox"),
            ("Decisions", decision_list, "green", "star"),
            ("People", people_list, "yellow", "person"),
            ("Clients", client_list, "purple", "building"),
            ("Projects", project_list, "cyan", "folder"),
        ]

        # Filter to only entities with data
        entity_types = [(name, items, color, icon) for name, items, color, icon in entity_types if items]

        if not entity_types:
            board_url = get_miro_board_url()
            return f"Created meeting node in Miro (no entities to add).\n\nView board: {board_url}"

        # Create branches for each entity type
        for idx, (entity_name, items, color, icon) in enumerate(entity_types):
            # Calculate position on circle
            angle = (2 * math.pi * idx) / len(entity_types) - math.pi / 2
            branch_x = center_x + radius * math.cos(angle)
            branch_y = center_y + radius * math.sin(angle)

            # Create category node
            category_node = _create_shape(
                text=f"<strong>{entity_name}</strong><br/>({len(items)} items)",
                x=branch_x,
                y=branch_y,
                width=180,
                height=80,
                color=color
            )

            if category_node:
                node_count += 1
                created_nodes[entity_name] = category_node["id"]

                # Connect to central node
                _create_connector(meeting_node["id"], category_node["id"])

                # Create child nodes for each item (max 5 per category)
                child_radius = 150
                for i, item in enumerate(items[:5]):
                    child_angle = angle + (i - len(items[:5]) / 2) * 0.3
                    child_x = branch_x + child_radius * math.cos(child_angle)
                    child_y = branch_y + child_radius * math.sin(child_angle)

                    # Truncate long items
                    display_text = item[:50] + "..." if len(item) > 50 else item

                    child_node = _create_sticky_note(
                        content=display_text,
                        x=child_x,
                        y=child_y,
                        color=color
                    )

                    if child_node:
                        node_count += 1
                        _create_connector(category_node["id"], child_node["id"])

        board_url = get_miro_board_url()
        logger.info(f"Created Miro mind map with {node_count} nodes for: {meeting_title}")

        return (
            f"Successfully created mind map in Miro!\n\n"
            f"**Meeting:** {meeting_title}\n"
            f"**Nodes created:** {node_count}\n"
            f"**Categories:** {', '.join(name for name, _, _, _ in entity_types)}\n\n"
            f"**View board:** {board_url}"
        )

    except Exception as e:
        logger.error(f"Error creating Miro mind map: {e}")
        return f"Error creating mind map: {str(e)}"
