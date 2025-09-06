"""
Graph Memory Implementation with PostgreSQL relationship modeling.

This implementation stores entities and relationships in PostgreSQL tables
optimized for graph traversal and path finding operations.
Provides relationship-based context for LLM memory enhancement.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import openai
    from supabase import Client, create_client
except ImportError as e:
    logging.warning(f"Optional dependencies not available: {e}")
    create_client = None
    openai = None

from shared.models.node_enums import OpenAIModel

from .base import MemoryBase

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a node in the graph."""

    id: str
    label: str
    type: str
    properties: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class GraphRelationship:
    """Represents a relationship between graph nodes."""

    id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    properties: Dict[str, Any]
    weight: float
    created_at: datetime


@dataclass
class GraphPath:
    """Represents a path through the graph."""

    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    total_weight: float
    path_length: int


class GraphMemory(MemoryBase):
    """
    Graph Memory implementation with PostgreSQL backend.

    Stores entities as nodes and relationships as edges, enabling:
    - Complex relationship modeling
    - Path finding between entities
    - Subgraph extraction
    - Relationship weight analysis
    - Temporal relationship tracking
    """

    def __init__(
        self,
        user_id: str,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        max_path_depth: int = 5,
        relationship_threshold: float = 0.1,
    ):
        super().__init__(user_id)
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SECRET_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.max_path_depth = max_path_depth
        self.relationship_threshold = relationship_threshold
        self.supabase: Optional[Client] = None

    async def _setup(self) -> None:
        """Initialize Supabase client and ensure graph tables exist."""
        try:
            if not create_client:
                raise ImportError("supabase-py not available")

            if not self.supabase_url or not self.supabase_key:
                raise ValueError("Supabase URL and key are required")

            self.supabase = create_client(self.supabase_url, self.supabase_key)

            await self._ensure_graph_tables()
            logger.info("GraphMemory initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize GraphMemory: {e}")
            raise

    async def _ensure_graph_tables(self) -> None:
        """Ensure graph_nodes and graph_relationships tables exist."""
        try:
            # Test table access - tables should exist from migrations
            result = self.supabase.table("graph_nodes").select("id").limit(1).execute()
            result = self.supabase.table("graph_relationships").select("id").limit(1).execute()
            logger.info("Graph tables verified")
        except Exception as e:
            logger.error(f"Graph tables not available: {e}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store graph data (nodes and relationships).

        Expected data format:
        {
            "nodes": [{"label": "Person", "type": "entity", "properties": {...}}],
            "relationships": [{"source": "node1", "target": "node2", "type": "knows", "weight": 0.8}],
            "extract_entities": True,  # Optional: extract entities from text
            "text": "John works at Google and knows Mary."  # For entity extraction
        }
        """
        if not self.supabase:
            await self._setup()

        try:
            stored_nodes = []
            stored_relationships = []

            # Extract entities from text if requested
            if data.get("extract_entities") and data.get("text"):
                extracted = await self._extract_entities_and_relationships(data["text"])
                data.setdefault("nodes", []).extend(extracted.get("nodes", []))
                data.setdefault("relationships", []).extend(extracted.get("relationships", []))

            # Store nodes
            if "nodes" in data:
                for node_data in data["nodes"]:
                    stored_node = await self._store_node(node_data)
                    if stored_node:
                        stored_nodes.append(stored_node)

            # Store relationships
            if "relationships" in data:
                for rel_data in data["relationships"]:
                    stored_rel = await self._store_relationship(rel_data)
                    if stored_rel:
                        stored_relationships.append(stored_rel)

            return {
                "stored": True,
                "nodes_stored": len(stored_nodes),
                "relationships_stored": len(stored_relationships),
                "node_ids": [n.id for n in stored_nodes],
                "relationship_ids": [r.id for r in stored_relationships],
            }

        except Exception as e:
            logger.error(f"Error storing graph data: {e}")
            return {"stored": False, "error": str(e)}

    async def _store_node(self, node_data: Dict[str, Any]) -> Optional[GraphNode]:
        """Store a single node in the graph."""
        try:
            node_id = str(uuid.uuid4())
            now = datetime.utcnow()

            # Check if similar node exists
            existing = await self._find_similar_node(
                node_data.get("label", ""), node_data.get("type", "")
            )

            if existing:
                # Update existing node
                updated_properties = {**existing.properties, **node_data.get("properties", {})}

                result = (
                    self.supabase.table("graph_nodes")
                    .update({"properties": updated_properties, "updated_at": now.isoformat()})
                    .eq("id", existing.id)
                    .execute()
                )

                if result.data:
                    return GraphNode(
                        id=existing.id,
                        label=existing.label,
                        type=existing.type,
                        properties=updated_properties,
                        created_at=existing.created_at,
                        updated_at=now,
                    )
            else:
                # Create new node
                result = (
                    self.supabase.table("graph_nodes")
                    .insert(
                        {
                            "id": node_id,
                            "user_id": self.user_id,
                            "label": node_data.get("label", ""),
                            "type": node_data.get("type", "entity"),
                            "properties": node_data.get("properties", {}),
                            "created_at": now.isoformat(),
                            "updated_at": now.isoformat(),
                        }
                    )
                    .execute()
                )

                if result.data:
                    return GraphNode(
                        id=node_id,
                        label=node_data.get("label", ""),
                        type=node_data.get("type", "entity"),
                        properties=node_data.get("properties", {}),
                        created_at=now,
                        updated_at=now,
                    )

        except Exception as e:
            logger.error(f"Error storing node: {e}")
            return None

    async def _store_relationship(self, rel_data: Dict[str, Any]) -> Optional[GraphRelationship]:
        """Store a single relationship in the graph."""
        try:
            rel_id = str(uuid.uuid4())
            now = datetime.utcnow()

            # Find source and target nodes
            source_node = await self._find_node_by_label(rel_data.get("source", ""))
            target_node = await self._find_node_by_label(rel_data.get("target", ""))

            if not source_node or not target_node:
                logger.warning(f"Could not find nodes for relationship: {rel_data}")
                return None

            # Check if relationship already exists
            existing_rel = (
                self.supabase.table("graph_relationships")
                .select("*")
                .eq("source_node_id", source_node.id)
                .eq("target_node_id", target_node.id)
                .eq("relationship_type", rel_data.get("type", ""))
                .execute()
            )

            weight = rel_data.get("weight", 1.0)

            if existing_rel.data:
                # Update existing relationship weight (average)
                existing = existing_rel.data[0]
                new_weight = (existing["weight"] + weight) / 2

                result = (
                    self.supabase.table("graph_relationships")
                    .update(
                        {
                            "weight": new_weight,
                            "properties": {
                                **existing["properties"],
                                **rel_data.get("properties", {}),
                            },
                            "updated_at": now.isoformat(),
                        }
                    )
                    .eq("id", existing["id"])
                    .execute()
                )

                if result.data:
                    return GraphRelationship(
                        id=existing["id"],
                        source_node_id=source_node.id,
                        target_node_id=target_node.id,
                        relationship_type=rel_data.get("type", ""),
                        properties={**existing["properties"], **rel_data.get("properties", {})},
                        weight=new_weight,
                        created_at=datetime.fromisoformat(
                            existing["created_at"].replace("Z", "+00:00")
                        ),
                    )
            else:
                # Create new relationship
                result = (
                    self.supabase.table("graph_relationships")
                    .insert(
                        {
                            "id": rel_id,
                            "user_id": self.user_id,
                            "source_node_id": source_node.id,
                            "target_node_id": target_node.id,
                            "relationship_type": rel_data.get("type", ""),
                            "properties": rel_data.get("properties", {}),
                            "weight": weight,
                            "created_at": now.isoformat(),
                        }
                    )
                    .execute()
                )

                if result.data:
                    return GraphRelationship(
                        id=rel_id,
                        source_node_id=source_node.id,
                        target_node_id=target_node.id,
                        relationship_type=rel_data.get("type", ""),
                        properties=rel_data.get("properties", {}),
                        weight=weight,
                        created_at=now,
                    )

        except Exception as e:
            logger.error(f"Error storing relationship: {e}")
            return None

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve graph data based on query.

        Query types:
        - "find_paths": Find paths between entities
        - "get_subgraph": Get subgraph around entities
        - "traverse": Traverse relationships from starting point
        - "search_nodes": Search for nodes by properties
        """
        if not self.supabase:
            await self._setup()

        try:
            query_type = query.get("type", "search_nodes")

            if query_type == "find_paths":
                return await self._find_paths(query)
            elif query_type == "get_subgraph":
                return await self._get_subgraph(query)
            elif query_type == "traverse":
                return await self._traverse_relationships(query)
            elif query_type == "search_nodes":
                return await self._search_nodes(query)
            else:
                return {"paths": [], "error": f"Unknown query type: {query_type}"}

        except Exception as e:
            logger.error(f"Error retrieving graph data: {e}")
            return {"paths": [], "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get relationship-based context for LLM enhancement."""
        if not self.supabase:
            await self._setup()

        try:
            entities = query.get("entities", [])
            max_relationships = query.get("max_relationships", 20)

            if not entities:
                # Find recent nodes if no specific entities
                recent_nodes = await self._get_recent_nodes(limit=5)
                entities = [node.label for node in recent_nodes]

            context = {
                "relationships": [],
                "entities": [],
                "paths": [],
                "relationship_summary": "",
                "context_type": "graph_relationships",
            }

            # Get relationships for each entity
            for entity in entities:
                node = await self._find_node_by_label(entity)
                if node:
                    relationships = await self._get_node_relationships(
                        node.id, limit=max_relationships // len(entities)
                    )
                    context["relationships"].extend(relationships)
                    context["entities"].append(
                        {"label": node.label, "type": node.type, "properties": node.properties}
                    )

            # Find paths between entities if multiple
            if len(entities) > 1:
                paths = await self._find_paths(
                    {
                        "source": entities[0],
                        "target": entities[1] if len(entities) > 1 else entities[0],
                        "max_depth": 3,
                    }
                )
                context["paths"] = paths.get("paths", [])

            # Generate relationship summary
            context["relationship_summary"] = self._generate_relationship_summary(context)

            return context

        except Exception as e:
            logger.error(f"Error getting graph context: {e}")
            return {
                "relationships": [],
                "entities": [],
                "paths": [],
                "relationship_summary": f"Error retrieving context: {str(e)}",
                "context_type": "graph_relationships",
            }

    async def _extract_entities_and_relationships(self, text: str) -> Dict[str, Any]:
        """Extract entities and relationships from text using OpenAI."""
        if not openai or not self.openai_api_key:
            return {"nodes": [], "relationships": []}

        try:
            client = openai.AsyncOpenAI(api_key=self.openai_api_key)

            extraction_prompt = f"""
            Extract entities and relationships from the following text. Return JSON with:
            {{
                "nodes": [
                    {{"label": "entity_name", "type": "person|organization|concept|location", "properties": {{"description": "brief description"}}}}
                ],
                "relationships": [
                    {{"source": "entity1", "target": "entity2", "type": "relationship_type", "weight": 0.8}}
                ]
            }}

            Text: {text}
            """

            response = await client.chat.completions.create(
                model=OpenAIModel.GPT_5_NANO.value,
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {"nodes": [], "relationships": []}

    async def _find_similar_node(self, label: str, node_type: str) -> Optional[GraphNode]:
        """Find similar existing node."""
        try:
            result = (
                self.supabase.table("graph_nodes")
                .select("*")
                .eq("user_id", self.user_id)
                .eq("label", label)
                .eq("type", node_type)
                .limit(1)
                .execute()
            )

            if result.data:
                data = result.data[0]
                return GraphNode(
                    id=data["id"],
                    label=data["label"],
                    type=data["type"],
                    properties=data["properties"],
                    created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
                )
            return None

        except Exception as e:
            logger.error(f"Error finding similar node: {e}")
            return None

    async def _find_node_by_label(self, label: str) -> Optional[GraphNode]:
        """Find node by exact label match."""
        try:
            result = (
                self.supabase.table("graph_nodes")
                .select("*")
                .eq("user_id", self.user_id)
                .eq("label", label)
                .limit(1)
                .execute()
            )

            if result.data:
                data = result.data[0]
                return GraphNode(
                    id=data["id"],
                    label=data["label"],
                    type=data["type"],
                    properties=data["properties"],
                    created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
                )
            return None

        except Exception as e:
            logger.error(f"Error finding node by label: {e}")
            return None

    async def _find_paths(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Find paths between two entities using BFS."""
        try:
            source_label = query.get("source")
            target_label = query.get("target")
            max_depth = query.get("max_depth", self.max_path_depth)

            source_node = await self._find_node_by_label(source_label)
            target_node = await self._find_node_by_label(target_label)

            if not source_node or not target_node:
                return {"paths": [], "message": "Source or target node not found"}

            paths = await self._bfs_paths(source_node.id, target_node.id, max_depth)

            return {
                "paths": [self._format_path(path) for path in paths],
                "source": source_label,
                "target": target_label,
                "total_paths": len(paths),
            }

        except Exception as e:
            logger.error(f"Error finding paths: {e}")
            return {"paths": [], "error": str(e)}

    async def _bfs_paths(self, source_id: str, target_id: str, max_depth: int) -> List[List[str]]:
        """Breadth-first search for paths between nodes."""
        queue = [(source_id, [source_id])]
        paths = []
        visited_paths = set()

        while queue and len(paths) < 10:  # Limit to 10 paths
            current_id, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            if current_id == target_id and len(path) > 1:
                path_key = tuple(path)
                if path_key not in visited_paths:
                    paths.append(path)
                    visited_paths.add(path_key)
                continue

            # Get connected nodes
            relationships = await self._get_node_relationships(current_id, limit=20)

            for rel in relationships:
                next_id = (
                    rel["target_node_id"]
                    if rel["source_node_id"] == current_id
                    else rel["source_node_id"]
                )

                if next_id not in path:  # Avoid cycles
                    queue.append((next_id, path + [next_id]))

        return paths

    async def _get_node_relationships(self, node_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all relationships for a node."""
        try:
            # Get outgoing relationships
            outgoing = (
                self.supabase.table("graph_relationships")
                .select(
                    "*, source_node:graph_nodes!source_node_id(label, type), target_node:graph_nodes!target_node_id(label, type)"
                )
                .eq("source_node_id", node_id)
                .limit(limit // 2)
                .execute()
            )

            # Get incoming relationships
            incoming = (
                self.supabase.table("graph_relationships")
                .select(
                    "*, source_node:graph_nodes!source_node_id(label, type), target_node:graph_nodes!target_node_id(label, type)"
                )
                .eq("target_node_id", node_id)
                .limit(limit // 2)
                .execute()
            )

            return (outgoing.data or []) + (incoming.data or [])

        except Exception as e:
            logger.error(f"Error getting node relationships: {e}")
            return []

    async def _get_recent_nodes(self, limit: int = 10) -> List[GraphNode]:
        """Get recently created/updated nodes."""
        try:
            result = (
                self.supabase.table("graph_nodes")
                .select("*")
                .eq("user_id", self.user_id)
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )

            nodes = []
            for data in result.data or []:
                nodes.append(
                    GraphNode(
                        id=data["id"],
                        label=data["label"],
                        type=data["type"],
                        properties=data["properties"],
                        created_at=datetime.fromisoformat(
                            data["created_at"].replace("Z", "+00:00")
                        ),
                        updated_at=datetime.fromisoformat(
                            data["updated_at"].replace("Z", "+00:00")
                        ),
                    )
                )

            return nodes

        except Exception as e:
            logger.error(f"Error getting recent nodes: {e}")
            return []

    def _format_path(self, node_ids: List[str]) -> Dict[str, Any]:
        """Format path for output."""
        return {
            "node_ids": node_ids,
            "length": len(node_ids) - 1,
            "formatted": " → ".join([f"node_{i}" for i in range(len(node_ids))]),
        }

    def _generate_relationship_summary(self, context: Dict[str, Any]) -> str:
        """Generate natural language summary of relationships."""
        relationships = context.get("relationships", [])
        entities = context.get("entities", [])

        if not relationships:
            return "No relationships found."

        summary_parts = []

        # Entity summary
        if entities:
            entity_types = {}
            for entity in entities:
                entity_type = entity.get("type", "entity")
                entity_types.setdefault(entity_type, []).append(entity["label"])

            type_summaries = []
            for ent_type, labels in entity_types.items():
                if len(labels) == 1:
                    type_summaries.append(f"{labels[0]} ({ent_type})")
                else:
                    type_summaries.append(f"{len(labels)} {ent_type}s: {', '.join(labels[:3])}")

            summary_parts.append(f"Entities: {'; '.join(type_summaries)}")

        # Relationship summary
        rel_types = {}
        for rel in relationships[:10]:  # Limit for summary
            rel_type = rel.get("relationship_type", "related")
            rel_types.setdefault(rel_type, 0)
            rel_types[rel_type] += 1

        if rel_types:
            rel_summaries = [f"{count} {rel_type}" for rel_type, count in rel_types.items()]
            summary_parts.append(f"Relationships: {', '.join(rel_summaries)}")

        return ". ".join(summary_parts) if summary_parts else "Graph context available."

    async def _get_subgraph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get subgraph around specified entities."""
        # Placeholder for subgraph extraction
        return {"subgraph": [], "message": "Subgraph extraction not yet implemented"}

    async def _traverse_relationships(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Traverse relationships from starting point."""
        # Placeholder for relationship traversal
        return {"traversal": [], "message": "Relationship traversal not yet implemented"}

    async def _search_nodes(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Search for nodes by properties."""
        try:
            search_term = query.get("search", "")
            node_type = query.get("node_type")
            limit = query.get("limit", 10)

            query_builder = (
                self.supabase.table("graph_nodes").select("*").eq("user_id", self.user_id)
            )

            if node_type:
                query_builder = query_builder.eq("type", node_type)

            if search_term:
                # Simple label search - could be enhanced with full-text search
                query_builder = query_builder.ilike("label", f"%{search_term}%")

            result = query_builder.limit(limit).execute()

            nodes = []
            for data in result.data or []:
                nodes.append(
                    {
                        "id": data["id"],
                        "label": data["label"],
                        "type": data["type"],
                        "properties": data["properties"],
                        "created_at": data["created_at"],
                    }
                )

            return {"nodes": nodes, "total": len(nodes)}

        except Exception as e:
            logger.error(f"Error searching nodes: {e}")
            return {"nodes": [], "error": str(e)}
