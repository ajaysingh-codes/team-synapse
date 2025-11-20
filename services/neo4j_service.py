"""
Neo4j service for Team Synapse.
Handles knowledge graph storage and querying.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from neo4j import GraphDatabase, Session
from neo4j.exceptions import Neo4jError

from config import config
from utils import setup_logger

logger = setup_logger(__name__, config.app.log_level)

class Neo4jService:
    """Service for Neo4j graph database operations."""
    
    def __init__(self):
        """Initialize Neo4j driver and verify connection."""
        try:
            self.driver = GraphDatabase.driver(
                config.neo4j.uri,
                auth=(config.neo4j.username, config.neo4j.password)
            )
            self.database = config.neo4j.database
            
            # Verify connectivity on initialization
            self.driver.verify_connectivity()
            logger.info(f"Neo4j service initialized: {config.neo4j.uri}")
            
            # Create indexes for better performance
            self._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j service: {e}")
            raise
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def _create_indexes(self):
        """Create indexes on key properties for query performance."""
        indexes = [
            "CREATE INDEX meeting_id IF NOT EXISTS FOR (m:Meeting) ON (m.meetingId)",
            "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
            "CREATE INDEX person_email IF NOT EXISTS FOR (p:Person) ON (p.email)",
            "CREATE INDEX client_name IF NOT EXISTS FOR (c:Client) ON (c.name)",
            "CREATE INDEX project_name IF NOT EXISTS FOR (p:Project) ON (p.name)",
        ]
        
        try:
            with self.driver.session(database=self.database) as session:
                for index_query in indexes:
                    session.run(index_query)
            logger.info("Neo4j indexes created/verified")
        except Exception as e:
            logger.warning(f"Could not create indexes (non-critical): {e}")
    
    def store_meeting_data(self, analysis: Dict[str, Any]) -> bool:
        """
        Store complete meeting analysis in Neo4j knowledge graph.
        
        This is the main entry point called by the ingestion pipeline.
        
        Args:
            analysis: Complete analysis dictionary from Gemini
        
        Returns:
            True if storage successful, False otherwise
        """
        try:
            meeting_id = analysis.get("meetingId")
            if not meeting_id:
                logger.error("Analysis missing meetingId, cannot store")
                return False
            
            logger.info(f"Storing meeting data in Neo4j: {meeting_id}")
            
            with self.driver.session(database=self.database) as session:
                # Use a write transaction for ACID guarantees
                session.execute_write(self._store_meeting_transaction, analysis)
            
            logger.info(f"Successfully stored meeting in Neo4j: {meeting_id}")
            return True
            
        except Neo4jError as e:
            logger.error(f"Neo4j error storing meeting data: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing meeting data: {e}")
            return False
    
    def _store_meeting_transaction(self, tx, analysis: Dict[str, Any]):
        """
        Transaction function to store all meeting data atomically.
        
        This ensures that either all data is stored or none is (ACID).
        """
        meeting_id = analysis["meetingId"]
        
        # 1. Create Meeting node (includes core metadata and transcript)
        self._create_meeting_node(tx, analysis)
        
        # 2. Create and link Action Items (and only then create People who own work)
        action_items = analysis.get("actionItems", [])
        invite_meta = analysis.get("inviteMetadata")
        invite_attendees = invite_meta.get("attendees") if invite_meta else None
        if action_items:
            self._create_action_items(tx, meeting_id, action_items, invite_attendees)
        
        # 3. Create and link Key Decisions
        decisions = analysis.get("keyDecisions", [])
        if decisions:
            self._create_decisions(tx, meeting_id, decisions)
        
        # 4. (Intentionally do NOT create generic Person nodes for every mention or invitee)
        # We only create/link Person nodes where they actually own work (action items),
        # which keeps the graph focused on relevant team/client/project relationships.
        
        # 5. Create and link Clients
        clients = analysis.get("mentionedClients", [])
        if clients:
            self._create_clients(tx, meeting_id, clients)
        
        # 6. Create and link Projects
        projects = analysis.get("mentionedProjects", [])
        if projects:
            self._create_projects(tx, meeting_id, projects)
        
        logger.debug(f"Transaction complete for meeting: {meeting_id}")
    
    def _create_meeting_node(self, tx, analysis: Dict[str, Any]):
        """Create the central Meeting node."""
        query = """
        CREATE (m:Meeting {
            meetingId: $meetingId,
            title: $title,
            summary: $summary,
            meetingDate: $meetingDate,
            sentiment: $sentiment,
            processingTimestamp: $processingTimestamp,
            originalFilename: $originalFilename,
            transcript: $transcript
        })
        RETURN m.meetingId AS meetingId
        """
        
        params = {
            "meetingId": analysis["meetingId"],
            "title": analysis.get("meetingTitle", "Untitled Meeting"),
            "summary": analysis.get("summary", ""),
            "meetingDate": analysis.get("meetingDate", "unknown"),
            "sentiment": analysis.get("sentiment", "neutral"),
            "processingTimestamp": analysis.get("processingTimestamp", datetime.utcnow().isoformat()),
            "originalFilename": analysis.get("originalFilename", ""),
            "transcript": analysis.get("transcript", "")[:10000]  # Limit transcript size
        }
        
        result = tx.run(query, params)
        record = result.single()
        logger.debug(f"Created Meeting node: {record['meetingId']}")
    
    def _create_action_items(
        self,
        tx,
        meeting_id: str,
        action_items: List[Dict[str, Any]],
        invite_attendees: Optional[List[Dict[str, Any]]] = None,
    ):
        """Create ActionItem nodes and link them to Meeting and People."""
        for idx, item in enumerate(action_items):
            # Create ActionItem node
            query_item = """
            MATCH (m:Meeting {meetingId: $meetingId})
            CREATE (a:ActionItem {
                actionId: $actionId,
                task: $task,
                assignee: $assignee,
                dueDate: $dueDate,
                priority: $priority,
                status: $status
            })
            CREATE (m)-[:HAS_ACTION_ITEM]->(a)
            RETURN a.actionId AS actionId
            """
            
            action_id = f"{meeting_id}_action_{idx}"
            assignee = item.get("assignee", "unassigned")
            
            params = {
                "meetingId": meeting_id,
                "actionId": action_id,
                "task": item.get("task", ""),
                "assignee": assignee,
                "dueDate": item.get("dueDate", "none"),
                "priority": item.get("priority", "unspecified"),
                "status": "pending"
            }
            
            tx.run(query_item, params)
            
            # If assignee is specified, link to Person node
            if assignee and assignee != "unassigned":
                # Try to match assignee to an invite attendee to get a stable email key
                email = None
                canonical_name = assignee
                if invite_attendees:
                    assignee_lower = assignee.lower()
                    for attendee in invite_attendees:
                        if not isinstance(attendee, dict):
                            continue
                        att_name = (attendee.get("name") or "").strip()
                        att_email = (attendee.get("email") or "").strip()
                        if not att_name and not att_email:
                            continue

                        # Simple fuzzy match: first-name or full-name containment
                        if att_name and (
                            assignee_lower == att_name.lower()
                            or assignee_lower in att_name.lower()
                            or att_name.lower() in assignee_lower
                        ):
                            email = att_email or None
                            canonical_name = att_name
                            break

                if email:
                    query_person = """
                    MERGE (p:Person {email: $email})
                    ON CREATE SET p.name = $name
                    ON MATCH SET p.name = coalesce(p.name, $name)
                    WITH p
                    MATCH (a:ActionItem {actionId: $actionId})
                    MERGE (p)-[:ASSIGNED_TO]->(a)
                    """
                    params_person = {
                        "email": email,
                        "name": canonical_name,
                        "actionId": action_id,
                    }
                else:
                    # Fallback: merge by name only
                    query_person = """
                    MERGE (p:Person {name: $name})
                    WITH p
                    MATCH (a:ActionItem {actionId: $actionId})
                    MERGE (p)-[:ASSIGNED_TO]->(a)
                    """
                    params_person = {
                        "name": canonical_name,
                        "actionId": action_id,
                    }

                tx.run(query_person, params_person)
        
        logger.debug(f"Created {len(action_items)} action items for {meeting_id}")
    
    def _create_decisions(self, tx, meeting_id: str, decisions: List[str]):
        """Create Decision nodes and link them to Meeting."""
        for idx, decision_text in enumerate(decisions):
            query = """
            MATCH (m:Meeting {meetingId: $meetingId})
            CREATE (d:Decision {
                decisionId: $decisionId,
                description: $description
            })
            CREATE (m)-[:HAS_DECISION]->(d)
            """
            
            params = {
                "meetingId": meeting_id,
                "decisionId": f"{meeting_id}_decision_{idx}",
                "description": decision_text
            }
            
            tx.run(query, params)
        
        logger.debug(f"Created {len(decisions)} decisions for {meeting_id}")
    
    def _create_clients(self, tx, meeting_id: str, clients: List[str]):
        """Create Client nodes and link them to Meeting."""
        for client_name in clients:
            if not client_name:
                continue
            
            query = """
            MATCH (m:Meeting {meetingId: $meetingId})
            MERGE (c:Client {name: $name})
            MERGE (m)-[:DISCUSSED_CLIENT]->(c)
            """
            
            tx.run(query, {"meetingId": meeting_id, "name": client_name})
        
        logger.debug(f"Created/linked {len(clients)} clients for {meeting_id}")
    
    def _create_projects(self, tx, meeting_id: str, projects: List[str]):
        """Create Project nodes and link them to Meeting."""
        for project_name in projects:
            if not project_name:
                continue
            
            query = """
            MATCH (m:Meeting {meetingId: $meetingId})
            MERGE (p:Project {name: $name})
            MERGE (m)-[:RELATES_TO_PROJECT]->(p)
            """
            
            tx.run(query, {"meetingId": meeting_id, "name": project_name})
        
        logger.debug(f"Created/linked {len(projects)} projects for {meeting_id}")
    
    # ========================================================================
    # QUERY METHODS (for Phase 3: MCP Tools)
    # ========================================================================
    
    def get_action_items_by_person(self, person_name: str) -> List[Dict[str, Any]]:
        """
        Get all action items assigned to a specific person.
        
        This will become an MCP tool in Phase 3.
        
        Args:
            person_name: Name of the person
        
        Returns:
            List of action items with meeting context
        """
        query = """
        MATCH (p:Person {name: $name})-[:ASSIGNED_TO]->(a:ActionItem)
        MATCH (m:Meeting)-[:HAS_ACTION_ITEM]->(a)
        RETURN 
            a.task AS task,
            a.dueDate AS dueDate,
            a.priority AS priority,
            a.status AS status,
            m.meetingId AS meetingId,
            m.title AS meetingTitle,
            m.meetingDate AS meetingDate
        ORDER BY a.priority DESC, a.dueDate
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, {"name": person_name})
                items = [dict(record) for record in result]
                logger.info(f"Found {len(items)} action items for {person_name}")
                return items
        except Exception as e:
            logger.error(f"Error querying action items: {e}")
            return []
    
    def get_meetings_by_project(self, project_name: str) -> List[Dict[str, Any]]:
        """
        Get all meetings related to a specific project.
        
        Args:
            project_name: Name of the project
        
        Returns:
            List of meetings with summaries
        """
        query = """
        MATCH (m:Meeting)-[:RELATES_TO_PROJECT]->(p:Project {name: $name})
        RETURN 
            m.meetingId AS meetingId,
            m.title AS title,
            m.summary AS summary,
            m.meetingDate AS meetingDate,
            m.sentiment AS sentiment
        ORDER BY m.processingTimestamp DESC
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, {"name": project_name})
                meetings = [dict(record) for record in result]
                logger.info(f"Found {len(meetings)} meetings for project {project_name}")
                return meetings
        except Exception as e:
            logger.error(f"Error querying meetings by project: {e}")
            return []
    
    def get_client_relationships(self, client_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get client relationships and their meeting history.
        
        Args:
            client_name: Specific client name, or None for all clients
        
        Returns:
            List of client relationships with meeting counts
        """
        if client_name:
            query = """
            MATCH (c:Client {name: $name})<-[:DISCUSSED_CLIENT]-(m:Meeting)
            RETURN 
                c.name AS clientName,
                count(m) AS meetingCount,
                collect(m.title)[0..5] AS recentMeetings
            """
            params = {"name": client_name}
        else:
            query = """
            MATCH (c:Client)<-[:DISCUSSED_CLIENT]-(m:Meeting)
            RETURN 
                c.name AS clientName,
                count(m) AS meetingCount,
                collect(m.title)[0..5] AS recentMeetings
            ORDER BY meetingCount DESC
            """
            params = {}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, params)
                relationships = [dict(record) for record in result]
                logger.info(f"Found {len(relationships)} client relationships")
                return relationships
        except Exception as e:
            logger.error(f"Error querying client relationships: {e}")
            return []
    
    def get_knowledge_graph_summary(self) -> Dict[str, Any]:
        """
        Get high-level statistics about the knowledge graph.
        
        Returns:
            Dictionary with node counts and relationship counts
        """
        query = """
        MATCH (m:Meeting) WITH count(m) AS meetings
        MATCH (p:Person) WITH meetings, count(p) AS people
        MATCH (c:Client) WITH meetings, people, count(c) AS clients
        MATCH (pr:Project) WITH meetings, people, clients, count(pr) AS projects
        MATCH (a:ActionItem) WITH meetings, people, clients, projects, count(a) AS actionItems
        MATCH (d:Decision) WITH meetings, people, clients, projects, actionItems, count(d) AS decisions
        RETURN 
            meetings,
            people,
            clients,
            projects,
            actionItems,
            decisions
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query)
                record = result.single()
                
                if record:
                    summary = dict(record)
                    logger.info(f"Knowledge graph summary: {summary}")
                    return summary
                else:
                    return {
                        "meetings": 0,
                        "people": 0,
                        "clients": 0,
                        "projects": 0,
                        "actionItems": 0,
                        "decisions": 0
                    }
        except Exception as e:
            logger.error(f"Error getting knowledge graph summary: {e}")
            return {}
    
    def search_meetings(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search meetings by title, summary, or transcript content.
        
        Args:
            search_term: Text to search for
            limit: Maximum number of results
        
        Returns:
            List of matching meetings
        """
        query = """
        MATCH (m:Meeting)
        WHERE m.title CONTAINS $term 
           OR m.summary CONTAINS $term
           OR m.transcript CONTAINS $term
        RETURN 
            m.meetingId AS meetingId,
            m.title AS title,
            m.summary AS summary,
            m.meetingDate AS meetingDate,
            m.sentiment AS sentiment
        ORDER BY m.processingTimestamp DESC
        LIMIT $limit
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, {"term": search_term, "limit": limit})
                meetings = [dict(record) for record in result]
                logger.info(f"Found {len(meetings)} meetings matching '{search_term}'")
                return meetings
        except Exception as e:
            logger.error(f"Error searching meetings: {e}")
            return []


# Global service instance
neo4j_service = Neo4jService()