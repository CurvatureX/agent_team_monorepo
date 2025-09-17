"""
Entity Memory Implementation.

This implements entity extraction and tracking using PostgreSQL:
- Extract entities from conversation text
- Track entity relationships and importance
- Maintain entity attributes and evolution over time
- Support for various entity types (person, organization, location, etc.)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import openai
from supabase import Client, create_client

# Fallback for shared models when not available
try:
    from shared.models.node_enums import MemorySubtype, OpenAIModel
except ImportError:
    # Fallback enum values for standalone use
    class OpenAIModel:
        GPT_5_NANO = "gpt-5-nano"

    class MemorySubtype:
        ENTITY_MEMORY = "entity_memory"


from .base import MemoryBase

logger = logging.getLogger(__name__)


class EntityMemory(MemoryBase):
    """
    Entity Memory with PostgreSQL backend for entity tracking.

    Features:
    - Automated entity extraction from text
    - Entity relationship tracking
    - Importance scoring and evolution
    - Multiple entity types support
    - Attribute management and updates
    - Mention frequency tracking
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize entity memory.

        Args:
            config: Configuration dict with keys:
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - openai_api_key: OpenAI API key for extraction
                - entity_types: List of entity types to track
                - extraction_model: Model for entity extraction (default: 'gpt-5-nano')
                - relationship_tracking: Enable relationship tracking (default: True)
                - importance_scoring: Enable importance scoring (default: True)
                - min_confidence: Minimum confidence for entity storage (default: 0.7)
        """
        super().__init__(config)

        # Configuration
        self.entity_types = config.get(
            "entity_types", ["person", "organization", "location", "product", "concept"]
        )
        self.extraction_model = config.get("extraction_model", OpenAIModel.GPT_5_NANO)
        self.relationship_tracking = config.get("relationship_tracking", True)
        self.importance_scoring = config.get("importance_scoring", True)
        self.min_confidence = config.get("min_confidence", 0.7)

        # Clients
        self.supabase_client: Optional[Client] = None
        self.openai_client: Optional[openai.OpenAI] = None

    async def _setup(self) -> None:
        """Setup Supabase and OpenAI clients."""
        try:
            # Setup Supabase
            supabase_url = self.config["supabase_url"]
            supabase_key = self.config["supabase_key"]
            self.supabase_client = create_client(supabase_url, supabase_key)

            # Setup OpenAI
            openai_api_key = self.config["openai_api_key"]
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

            logger.info("EntityMemory initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup EntityMemory: {str(e)}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and store entities from content.

        Args:
            data: Data dict with keys:
                - content: Text content to extract entities from
                - context: Additional context (optional)
                - user_id: User identifier (optional)
                - existing_entities: Known entities to update (optional)
                - session_id: Session identifier for context (optional)

        Returns:
            Dict with extracted entities
        """
        await self.initialize()

        try:
            content = data["content"]
            context = data.get("context", {})
            user_id = data.get("user_id")
            existing_entities = data.get("existing_entities", [])
            session_id = context.get("session_id")

            # Extract entities from content
            extracted_entities = await self._extract_entities(content, context)

            stored_entities = []
            updated_entities = []
            relationships = []

            for entity_data in extracted_entities:
                if entity_data["confidence"] < self.min_confidence:
                    continue

                # Store or update entity
                entity_result = await self._store_entity(entity_data, user_id, session_id)

                if entity_result["created"]:
                    stored_entities.append(entity_result["entity"])
                else:
                    updated_entities.append(entity_result["entity"])

                # Extract relationships if enabled
                if self.relationship_tracking:
                    entity_relationships = await self._extract_relationships(
                        entity_result["entity"], extracted_entities, content
                    )
                    relationships.extend(entity_relationships)

            # Store relationships
            if relationships:
                await self._store_relationships(relationships)

            logger.info(f"Processed {len(extracted_entities)} entities from content")

            return {
                "entities_processed": len(extracted_entities),
                "entities_stored": len(stored_entities),
                "entities_updated": len(updated_entities),
                "relationships_created": len(relationships),
                "new_entities": stored_entities,
                "updated_entities": updated_entities,
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to store entities: {str(e)}")
            raise

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve entities by various criteria.

        Args:
            query: Query dict with keys:
                - entity_name: Specific entity name (optional)
                - entity_type: Filter by entity type (optional)
                - user_id: Filter by user (optional)
                - min_importance: Minimum importance score (optional)
                - limit: Maximum results (optional, default: 50)
                - include_relationships: Include relationships (optional, default: False)

        Returns:
            Dict with matching entities
        """
        await self.initialize()

        try:
            entity_name = query.get("entity_name")
            entity_type = query.get("entity_type")
            user_id = query.get("user_id")
            min_importance = query.get("min_importance", 0.0)
            limit = query.get("limit", 50)
            include_relationships = query.get("include_relationships", False)

            # Build query
            supabase_query = self.supabase_client.table("entities").select("*")

            if entity_name:
                supabase_query = supabase_query.eq("name", entity_name)
            if entity_type:
                supabase_query = supabase_query.eq("type", entity_type)
            if user_id:
                supabase_query = supabase_query.eq("user_id", user_id)
            if min_importance > 0:
                supabase_query = supabase_query.gte("importance_score", min_importance)

            # Order and limit
            result = supabase_query.order("importance_score", desc=True).limit(limit).execute()
            entities = result.data if result.data else []

            # Include relationships if requested
            if include_relationships and entities:
                entity_ids = [e["id"] for e in entities]
                relationships = await self._get_relationships(entity_ids)

                # Add relationships to entities
                for entity in entities:
                    entity["relationships"] = relationships.get(entity["id"], [])

            return {
                "entities": entities,
                "total_count": len(entities),
                "query_filters": {
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "min_importance": min_importance,
                },
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to retrieve entities: {str(e)}")
            raise

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get entity context for LLM consumption.

        Args:
            query: Query dict with keys:
                - content: Content to find relevant entities for (optional)
                - entity_names: Specific entities to include (optional)
                - user_id: User context (optional)
                - max_entities: Maximum entities to include (optional, default: 20)
                - include_relationships: Include relationships (optional, default: True)

        Returns:
            Dict with formatted entity context for LLM
        """
        await self.initialize()

        try:
            content = query.get("content")
            entity_names = query.get("entity_names", [])
            user_id = query.get("user_id")
            max_entities = query.get("max_entities", 20)
            include_relationships = query.get("include_relationships", True)

            relevant_entities = []

            if content:
                # Find entities mentioned in content
                mentioned_entities = await self._find_mentioned_entities(content, user_id)
                relevant_entities.extend(mentioned_entities)

            if entity_names:
                # Get specific entities by name
                for name in entity_names:
                    entity_result = await self.retrieve(
                        {
                            "entity_name": name,
                            "user_id": user_id,
                            "include_relationships": include_relationships,
                        }
                    )
                    relevant_entities.extend(entity_result.get("entities", []))

            # If no specific criteria, get most important entities
            if not relevant_entities:
                entity_result = await self.retrieve(
                    {
                        "user_id": user_id,
                        "min_importance": 0.6,
                        "limit": max_entities,
                        "include_relationships": include_relationships,
                    }
                )
                relevant_entities = entity_result.get("entities", [])

            # Remove duplicates and limit results
            seen_ids = set()
            unique_entities = []
            for entity in relevant_entities:
                if entity["id"] not in seen_ids:
                    unique_entities.append(entity)
                    seen_ids.add(entity["id"])
                if len(unique_entities) >= max_entities:
                    break

            # Format for LLM context
            entities_summary = []
            relationships_summary = []

            for entity in unique_entities:
                entity_info = {
                    "name": entity["name"],
                    "type": entity["type"],
                    "description": entity.get("description", ""),
                    "attributes": entity.get("attributes", {}),
                    "importance": entity.get("importance_score", 0.0),
                    "mentions": entity.get("mention_count", 0),
                    "last_seen": entity.get("last_seen"),
                }
                entities_summary.append(entity_info)

                # Add relationships
                if include_relationships and entity.get("relationships"):
                    for rel in entity["relationships"]:
                        relationships_summary.append(
                            {
                                "source": entity["name"],
                                "relationship": rel["relationship_type"],
                                "target": rel.get("target_entity_name", "Unknown"),
                                "confidence": rel.get("confidence", 1.0),
                            }
                        )

            # Create entity summary text
            entity_summary = self._create_entity_summary(entities_summary, relationships_summary)

            return {
                "entities": entities_summary,
                "relationships": relationships_summary,
                "entity_summary": entity_summary,
                "total_entities": len(entities_summary),
                "context_generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get entity context: {str(e)}")
            raise

    async def _extract_entities(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract entities from content using OpenAI."""
        try:
            prompt = self._create_extraction_prompt(content, context)

            # Call OpenAI
            response = await self._call_openai_async(prompt)

            # Parse response
            entities = self._parse_extraction_response(response)

            return entities

        except Exception as e:
            logger.error(f"Failed to extract entities: {str(e)}")
            return []

    def _create_extraction_prompt(self, content: str, context: Dict[str, Any]) -> str:
        """Create prompt for entity extraction."""
        entity_types_str = ", ".join(self.entity_types)

        prompt = f"""
Extract entities from the following text. Focus on these types: {entity_types_str}

For each entity, provide:
1. Name (the entity as mentioned in text)
2. Type (one of: {entity_types_str})
3. Description (brief description of the entity)
4. Attributes (key properties as JSON)
5. Aliases (alternative names/variations)
6. Confidence (0.0-1.0 confidence in extraction)

Text to analyze:
{content}

Context: {json.dumps(context, indent=2)}

Respond with a JSON array of entities:
[
    {{
        "name": "Entity Name",
        "type": "person|organization|location|product|concept",
        "description": "Brief description",
        "attributes": {{"key": "value"}},
        "aliases": ["alias1", "alias2"],
        "confidence": 0.95
    }}
]
"""
        return prompt

    async def _call_openai_async(self, prompt: str) -> str:
        """Call OpenAI API asynchronously."""

        def _call_openai_sync():
            response = self.openai_client.chat.completions.create(
                model=self.extraction_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert entity extraction system. Extract entities accurately and provide confidence scores.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call_openai_sync)

    def _parse_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse OpenAI response to extract entities."""
        try:
            # Try to find JSON in response
            if "[" in response and "]" in response:
                json_start = response.find("[")
                json_end = response.rfind("]") + 1
                json_str = response[json_start:json_end]
                entities = json.loads(json_str)

                # Validate and clean entities
                valid_entities = []
                for entity in entities:
                    if self._validate_entity(entity):
                        valid_entities.append(entity)

                return valid_entities
            else:
                logger.warning("No JSON array found in extraction response")
                return []

        except Exception as e:
            logger.error(f"Failed to parse extraction response: {str(e)}")
            return []

    def _validate_entity(self, entity: Dict[str, Any]) -> bool:
        """Validate extracted entity data."""
        required_fields = ["name", "type", "confidence"]

        for field in required_fields:
            if field not in entity:
                return False

        if entity["type"] not in self.entity_types:
            return False

        if not 0.0 <= entity["confidence"] <= 1.0:
            return False

        return True

    async def _store_entity(
        self, entity_data: Dict[str, Any], user_id: Optional[str], session_id: Optional[str]
    ) -> Dict[str, Any]:
        """Store or update an entity."""
        try:
            name = entity_data["name"]
            entity_type = entity_data["type"]

            # Check if entity already exists
            existing_result = (
                self.supabase_client.table("entities")
                .select("*")
                .eq("name", name)
                .eq("type", entity_type)
                .eq("user_id", user_id)
                .execute()
            )

            if existing_result.data:
                # Update existing entity
                existing_entity = existing_result.data[0]

                # Merge attributes
                existing_attributes = existing_entity.get("attributes", {})
                new_attributes = entity_data.get("attributes", {})
                merged_attributes = {**existing_attributes, **new_attributes}

                # Merge aliases
                existing_aliases = existing_entity.get("aliases", [])
                new_aliases = entity_data.get("aliases", [])
                merged_aliases = list(set(existing_aliases + new_aliases))

                # Calculate new importance score
                new_importance = self._calculate_importance_score(
                    existing_entity, entity_data, is_update=True
                )

                update_data = {
                    "description": entity_data.get(
                        "description", existing_entity.get("description", "")
                    ),
                    "attributes": merged_attributes,
                    "aliases": merged_aliases,
                    "importance_score": new_importance,
                    "mention_count": existing_entity.get("mention_count", 0) + 1,
                    "last_seen": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }

                result = (
                    self.supabase_client.table("entities")
                    .update(update_data)
                    .eq("id", existing_entity["id"])
                    .execute()
                )

                updated_entity = {**existing_entity, **update_data}

                return {"created": False, "entity": updated_entity}

            else:
                # Create new entity
                importance_score = self._calculate_importance_score(
                    None, entity_data, is_update=False
                )

                new_entity_data = {
                    "name": name,
                    "type": entity_type,
                    "description": entity_data.get("description", ""),
                    "attributes": entity_data.get("attributes", {}),
                    "aliases": entity_data.get("aliases", []),
                    "importance_score": importance_score,
                    "mention_count": 1,
                    "user_id": user_id,
                    "first_seen": datetime.utcnow().isoformat(),
                    "last_seen": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }

                result = self.supabase_client.table("entities").insert(new_entity_data).execute()

                if result.data:
                    created_entity = result.data[0]
                    return {"created": True, "entity": created_entity}
                else:
                    raise Exception("Failed to create entity")

        except Exception as e:
            logger.error(f"Failed to store entity: {str(e)}")
            raise

    def _calculate_importance_score(
        self,
        existing_entity: Optional[Dict[str, Any]],
        new_entity_data: Dict[str, Any],
        is_update: bool,
    ) -> float:
        """Calculate importance score for an entity."""
        if not self.importance_scoring:
            return 0.5

        base_score = new_entity_data.get("confidence", 0.5)

        # Boost for certain entity types
        entity_type = new_entity_data["type"]
        type_boost = {
            "person": 0.1,
            "organization": 0.05,
            "location": 0.02,
            "product": 0.05,
            "concept": 0.03,
        }.get(entity_type, 0.0)

        base_score += type_boost

        # Boost for updates (repeated mentions)
        if is_update and existing_entity:
            mention_boost = min(0.2, existing_entity.get("mention_count", 0) * 0.02)
            base_score += mention_boost

        # Boost for rich attributes
        attributes = new_entity_data.get("attributes", {})
        if len(attributes) > 2:
            base_score += 0.05

        return min(1.0, base_score)

    async def _extract_relationships(
        self, entity: Dict[str, Any], all_entities: List[Dict[str, Any]], content: str
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities."""
        if not self.relationship_tracking:
            return []

        relationships = []

        # Simple relationship detection based on common patterns
        entity_name = entity["name"]

        for other_entity in all_entities:
            if other_entity["name"] == entity_name:
                continue

            other_name = other_entity["name"]

            # Look for relationship patterns in content
            relationship_type = self._detect_relationship(entity_name, other_name, content)

            if relationship_type:
                relationships.append(
                    {
                        "source_entity_id": entity["id"],
                        "target_entity_name": other_name,
                        "relationship_type": relationship_type,
                        "confidence": 0.8,
                        "source": "content_extraction",
                    }
                )

        return relationships

    def _detect_relationship(self, entity1: str, entity2: str, content: str) -> Optional[str]:
        """Detect relationship type between two entities."""
        content_lower = content.lower()
        entity1_lower = entity1.lower()
        entity2_lower = entity2.lower()

        # Work relationship patterns
        work_patterns = [
            f"{entity1_lower} works at {entity2_lower}",
            f"{entity1_lower} is employed by {entity2_lower}",
            f"{entity1_lower} works for {entity2_lower}",
        ]

        for pattern in work_patterns:
            if pattern in content_lower:
                return "works_at"

        # Location relationship patterns
        location_patterns = [
            f"{entity1_lower} is in {entity2_lower}",
            f"{entity1_lower} is located in {entity2_lower}",
            f"{entity1_lower} lives in {entity2_lower}",
        ]

        for pattern in location_patterns:
            if pattern in content_lower:
                return "located_in"

        # Generic related pattern
        if f"{entity1_lower}" in content_lower and f"{entity2_lower}" in content_lower:
            return "related_to"

        return None

    async def _store_relationships(self, relationships: List[Dict[str, Any]]) -> None:
        """Store entity relationships."""
        if not relationships:
            return

        try:
            for rel in relationships:
                # Add timestamps
                rel["created_at"] = datetime.utcnow().isoformat()
                rel["updated_at"] = datetime.utcnow().isoformat()

            # Insert relationships
            self.supabase_client.table("entity_relationships").insert(relationships).execute()

        except Exception as e:
            logger.warning(f"Failed to store relationships: {str(e)}")

    async def _get_relationships(self, entity_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get relationships for entities."""
        try:
            result = (
                self.supabase_client.table("entity_relationships")
                .select("*")
                .in_("source_entity_id", entity_ids)
                .execute()
            )

            relationships_by_entity = {}
            for rel in result.data or []:
                entity_id = rel["source_entity_id"]
                if entity_id not in relationships_by_entity:
                    relationships_by_entity[entity_id] = []
                relationships_by_entity[entity_id].append(rel)

            return relationships_by_entity

        except Exception as e:
            logger.warning(f"Failed to get relationships: {str(e)}")
            return {}

    async def _find_mentioned_entities(
        self, content: str, user_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Find entities that are mentioned in content."""
        try:
            # Get all entities for user
            all_entities_result = await self.retrieve({"user_id": user_id, "limit": 1000})

            all_entities = all_entities_result.get("entities", [])
            mentioned_entities = []

            content_lower = content.lower()

            for entity in all_entities:
                # Check if entity name or aliases are mentioned
                entity_mentioned = False

                if entity["name"].lower() in content_lower:
                    entity_mentioned = True

                for alias in entity.get("aliases", []):
                    if alias.lower() in content_lower:
                        entity_mentioned = True
                        break

                if entity_mentioned:
                    mentioned_entities.append(entity)

            return mentioned_entities

        except Exception as e:
            logger.warning(f"Failed to find mentioned entities: {str(e)}")
            return []

    def _create_entity_summary(
        self, entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]
    ) -> str:
        """Create a summary of entities for LLM context."""
        if not entities:
            return "No entities found."

        summary_parts = []

        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity["type"]
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Create type-based summaries
        for entity_type, type_entities in entities_by_type.items():
            type_summary = f"{entity_type.title()}s: "
            entity_names = []

            for entity in type_entities:
                name = entity["name"]
                importance = entity.get("importance", 0.0)
                if importance > 0.7:
                    name += " (important)"
                entity_names.append(name)

            type_summary += ", ".join(entity_names)
            summary_parts.append(type_summary)

        # Add relationship summary
        if relationships:
            rel_summary = f"Relationships: {len(relationships)} connections found"
            summary_parts.append(rel_summary)

        return ". ".join(summary_parts) + "."
