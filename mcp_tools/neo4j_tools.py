"""
Neo4j Knowledge Graph MCP Tools.
Tools for querying the Team Synapse knowledge graph.
"""
from typing import Optional
from datetime import datetime, timedelta
from services.neo4j_service import neo4j_service
from utils import setup_logger
from config import config

logger = setup_logger(__name__)


def get_graph_stats() -> str:
    """
    Get high-level statistics about the knowledge graph.
    Shows the scale and richness of captured meeting intelligence.

    Returns:
        Formatted markdown string with graph statistics
    """
    stats = neo4j_service.get_knowledge_graph_summary()
    if not stats:
        return "Could not retrieve graph statistics."

    return (
        f"## Knowledge Graph Statistics\n\n"
        f"- **Meetings:** {stats.get('meetings', 0)}\n"
        f"- **People:** {stats.get('people', 0)}\n"
        f"- **Clients:** {stats.get('clients', 0)}\n"
        f"- **Projects:** {stats.get('projects', 0)}\n"
        f"- **Action Items:** {stats.get('actionItems', 0)}\n"
        f"- **Decisions:** {stats.get('decisions', 0)}"
    )


def get_action_items(person_name: str) -> str:
    """
    Get action items assigned to a specific person.
    Shows accountability tracking and task status.

    Args:
        person_name: Name of the person to query action items for

    Returns:
        Formatted markdown string with action items
    """
    results = neo4j_service.get_action_items_by_person(person_name)

    if not results:
        return f"No action items found for '{person_name}'."

    formatted = [f"## Action Items for {person_name}\n"]

    blocked_count = 0
    pending_count = 0

    for item in results:
        status = item.get('status', 'pending')
        status_emoji = {
            "pending": "[ ]",
            "in_progress": "[~]",
            "blocked": "[!]",
            "completed": "[x]"
        }.get(status, "[ ]")

        if status == "blocked":
            blocked_count += 1
        elif status == "pending":
            pending_count += 1

        priority = item.get('priority', 'unspecified')
        priority_marker = {"high": "HIGH", "medium": "MED", "low": "LOW"}.get(priority, "")

        formatted.append(f"{status_emoji} **{item['task']}** {priority_marker}")
        formatted.append(f"   Due: {item.get('dueDate', 'none')} | From: {item.get('meetingTitle', 'Unknown')}")

        if item.get('blockers'):
            formatted.append(f"   Blocked by: {', '.join(item['blockers'])}")

        formatted.append("")

    formatted.append(f"\n**Summary:** {len(results)} total items")
    if blocked_count > 0:
        formatted.append(f"**{blocked_count} BLOCKED items need attention**")
    if pending_count > 0:
        formatted.append(f"{pending_count} pending items")

    return "\n".join(formatted)


def search_meetings(keyword: str, limit: int = 5) -> str:
    """
    Search meetings by keyword to find past discussions and decisions.

    Args:
        keyword: Search term to look for in meeting content
        limit: Maximum number of results (default 5)

    Returns:
        Formatted markdown string with matching meetings
    """
    results = neo4j_service.search_meetings(keyword, limit=limit)

    if not results:
        return f"No meetings found containing '{keyword}'."

    formatted = [f"## Meetings about '{keyword}'\n"]

    for m in results:
        urgency = m.get('urgencyLevel', 'normal')
        urgency_badge = " [URGENT]" if urgency in ['urgent', 'high'] else ""

        formatted.append(f"**{m['title']}** ({m['meetingDate']}){urgency_badge}")

        summary = m.get('summary', '')
        if summary:
            formatted.append(f"   {summary[:200]}...")

        if m.get('requiresFollowUp'):
            formatted.append(f"   *Requires follow-up*")

        formatted.append("")

    return "\n".join(formatted)


def find_blockers() -> str:
    """
    Find all blocked action items across the organization.
    Critical for identifying bottlenecks and escalation needs.

    Returns:
        Formatted markdown string with blocked items
    """
    query = """
    MATCH (a:ActionItem {tenantId: $tenantId})
    WHERE a.status = 'blocked' OR size(a.blockers) > 0
    OPTIONAL MATCH (m:Meeting {tenantId: $tenantId})-[:HAS_ACTION_ITEM]->(a)
    OPTIONAL MATCH (p:Person {tenantId: $tenantId})-[:ASSIGNED_TO]->(a)
    RETURN a.task AS task,
           a.assignee AS assignee,
           a.blockers AS blockers,
           a.priority AS priority,
           m.title AS meetingTitle
    ORDER BY
        CASE a.priority
            WHEN 'high' THEN 1
            WHEN 'medium' THEN 2
            ELSE 3
        END
    LIMIT 10
    """

    try:
        with neo4j_service.driver.session(database=neo4j_service.database) as session:
            result = session.run(query, tenantId=config.app.tenant_id)
            blocked_items = [dict(record) for record in result]
    except Exception as e:
        return f"Error finding blockers: {e}"

    if not blocked_items:
        return "No blocked items found. All action items are progressing."

    formatted = [f"## BLOCKED Items Requiring Attention\n"]
    formatted.append(f"**Found {len(blocked_items)} blocked items**\n")

    high_priority_count = sum(1 for item in blocked_items if item.get('priority') == 'high')
    if high_priority_count > 0:
        formatted.append(f"**{high_priority_count} HIGH PRIORITY items are blocked!**\n")

    for item in blocked_items:
        priority = item.get('priority', 'unspecified')
        priority_marker = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(priority, "")

        formatted.append(f"{priority_marker} **{item['task']}**")
        formatted.append(f"   Assignee: {item.get('assignee', 'Unassigned')}")

        if item.get('blockers'):
            formatted.append(f"   Blockers: {', '.join(item['blockers'])}")

        if item.get('meetingTitle'):
            formatted.append(f"   From: {item['meetingTitle']}")

        formatted.append("")

    return "\n".join(formatted)


def get_historical_context(topic: str, time_range_days: int = 30) -> str:
    """
    Retrieve historical context about a topic from past meetings.
    Helps prevent repeated discussions and forgotten decisions.

    Args:
        topic: Topic or keyword to search
        time_range_days: Number of days to look back (default 30)

    Returns:
        Formatted markdown string with historical context
    """
    try:
        cutoff_date = (datetime.now() - timedelta(days=time_range_days)).isoformat()

        query = """
        MATCH (m:Meeting {tenantId: $tenantId})
        WHERE m.transcript CONTAINS $topic AND m.meetingDate >= $cutoff
        OPTIONAL MATCH (m)-[:HAS_DECISION]->(d:Decision {tenantId: $tenantId})
        OPTIONAL MATCH (m)-[:HAS_ACTION_ITEM]->(a:ActionItem {tenantId: $tenantId})
        RETURN m.title AS meetingTitle,
               m.meetingDate AS date,
               m.summary AS summary,
               COLLECT(DISTINCT d.decision) AS decisions,
               COLLECT(DISTINCT a.task) AS actionItems
        ORDER BY m.meetingDate DESC
        LIMIT 5
        """

        with neo4j_service.driver.session(database=neo4j_service.database) as session:
            result = session.run(query, topic=topic, cutoff=cutoff_date, tenantId=config.app.tenant_id)
            meetings = [dict(record) for record in result]

        if not meetings:
            return f"No historical context found for '{topic}' in the last {time_range_days} days"

        formatted = [f"## Historical Context: '{topic}'\n"]

        for meeting in meetings:
            formatted.append(f"**{meeting['meetingTitle']}** ({meeting['date']})")

            if summary := meeting.get('summary'):
                formatted.append(f"   Summary: {summary[:150]}...")

            if decisions := meeting.get('decisions'):
                decisions = [d for d in decisions if d]
                if decisions:
                    formatted.append("   Key Decisions:")
                    for decision in decisions[:3]:
                        formatted.append(f"   - {decision}")

            if actions := meeting.get('actionItems'):
                actions = [a for a in actions if a]
                if actions:
                    formatted.append(f"   Related Actions: {len(actions)} items")

            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        logger.error(f"Error retrieving historical context: {e}")
        return f"Error: {str(e)}"


def analyze_team_health() -> str:
    """
    Analyze overall team health based on action items and meeting patterns.
    Provides insights on workload, blockers, and team dynamics.

    Returns:
        Formatted markdown string with team health analysis
    """
    try:
        query = """
        MATCH (p:Person {tenantId: $tenantId})-[:ASSIGNED_TO]->(a:ActionItem {tenantId: $tenantId})
        WITH p.name AS person,
             COUNT(a) AS totalTasks,
             SUM(CASE WHEN a.status = 'blocked' THEN 1 ELSE 0 END) AS blockedTasks,
             SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completedTasks,
             SUM(CASE WHEN a.priority = 'high' THEN 1 ELSE 0 END) AS highPriorityTasks
        RETURN person, totalTasks, blockedTasks, completedTasks, highPriorityTasks
        ORDER BY totalTasks DESC
        """

        with neo4j_service.driver.session(database=neo4j_service.database) as session:
            result = session.run(query, tenantId=config.app.tenant_id)
            team_metrics = [dict(record) for record in result]

        if not team_metrics:
            return "No team metrics available yet. Analyze some meetings first."

        total_tasks = sum(m['totalTasks'] for m in team_metrics)
        total_blocked = sum(m['blockedTasks'] for m in team_metrics)
        total_completed = sum(m['completedTasks'] for m in team_metrics)

        completion_rate = (total_completed / total_tasks * 100) if total_tasks > 0 else 0
        blocked_rate = (total_blocked / total_tasks * 100) if total_tasks > 0 else 0

        if blocked_rate > 30:
            health_status = "CRITICAL - High blocker rate"
        elif blocked_rate > 15:
            health_status = "WARNING - Moderate blockers"
        else:
            health_status = "HEALTHY - Low blocker rate"

        formatted = [
            "## Team Health Analysis\n",
            f"**Status:** {health_status}",
            f"**Completion Rate:** {completion_rate:.1f}%",
            f"**Blocked Items:** {total_blocked}/{total_tasks} ({blocked_rate:.1f}%)\n",
            "### Individual Workload"
        ]

        overloaded = []
        for member in team_metrics[:5]:
            workload = "HIGH" if member['totalTasks'] > 10 else "MED" if member['totalTasks'] > 5 else "LOW"
            formatted.append(
                f"[{workload}] **{member['person']}**: "
                f"{member['totalTasks']} tasks "
                f"({member['blockedTasks']} blocked, "
                f"{member['highPriorityTasks']} high priority)"
            )

            if member['totalTasks'] > 10:
                overloaded.append(member['person'])

        if overloaded:
            formatted.append(f"\n**Overloaded:** {', '.join(overloaded)} may need support")

        return "\n".join(formatted)

    except Exception as e:
        logger.error(f"Error analyzing team health: {e}")
        return f"Error: {str(e)}"


def store_meeting_data_tool(
    meeting_title: str,
    meeting_date: str,
    transcript: str,
    people: str = "",
    clients: str = "",
    projects: str = "",
    action_items: str = "",
    key_decisions: str = ""
) -> str:
    """
    Store meeting data to Neo4j knowledge graph.
    Called by ADK agent at the end of a live meeting.

    Args:
        meeting_title: Title of the meeting
        meeting_date: Date (YYYY-MM-DD)
        transcript: Full meeting transcript
        people: Comma-separated list of people mentioned (default: "")
        clients: Comma-separated list of clients mentioned (default: "")
        projects: Comma-separated list of projects mentioned (default: "")
        action_items: JSON string array of action items (default: "")
        key_decisions: JSON string array of decisions (default: "")

    Returns:
        Success message with meeting ID
    """
    try:
        import json
        from datetime import datetime

        meeting_data = {
            "meetingId": f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "meetingTitle": meeting_title,
            "meetingDate": meeting_date,
            "transcript": transcript[:10000],  # Truncate for Neo4j
            "summary": f"Live meeting: {meeting_title}",
            "mentionedPeople": [p.strip() for p in people.split(",") if p.strip()] if people else [],
            "mentionedClients": [c.strip() for c in clients.split(",") if c.strip()] if clients else [],
            "mentionedProjects": [p.strip() for p in projects.split(",") if p.strip()] if projects else [],
            "actionItems": json.loads(action_items) if action_items else [],
            "keyDecisions": json.loads(key_decisions) if key_decisions else [],
            "sentiment": "neutral"
        }

        success = neo4j_service.store_meeting_data(meeting_data)

        if success:
            logger.info(f"Stored live meeting: {meeting_data['meetingId']}")
            return f"Meeting stored successfully: {meeting_data['meetingId']}"
        else:
            logger.warning("Failed to store meeting data to Neo4j")
            return "Failed to store meeting data"

    except Exception as e:
        logger.error(f"Error storing meeting: {e}")
        return f"Error: {str(e)}"
