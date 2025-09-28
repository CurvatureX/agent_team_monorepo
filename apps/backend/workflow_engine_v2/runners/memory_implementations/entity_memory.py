"""
Entity Memory implementation for workflow_engine_v2.

Tracks and stores information about entities (people, places, things) mentioned in conversations.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from .base import MemoryBase


class EntityMemory(MemoryBase):
    """Entity memory implementation for tracking entities."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.entities = {}  # entity_name -> entity_data

    async def _setup(self) -> None:
        """Setup entity memory."""
        self.logger.info("Entity Memory initialized")

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store entity information."""
        try:
            entity_name = data.get("entity_name", "").strip()
            entity_info = data.get("entity_info", "")
            entity_type = data.get("entity_type", "general")

            if not entity_name:
                return {"success": False, "error": "Missing 'entity_name'"}

            # Update or create entity
            if entity_name not in self.entities:
                self.entities[entity_name] = {
                    "name": entity_name,
                    "type": entity_type,
                    "information": [],
                    "first_mentioned": datetime.utcnow().isoformat(),
                    "last_updated": datetime.utcnow().isoformat(),
                }

            # Add new information
            self.entities[entity_name]["information"].append(
                {
                    "content": entity_info,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": data.get("source", "conversation"),
                }
            )
            self.entities[entity_name]["last_updated"] = datetime.utcnow().isoformat()

            return {
                "success": True,
                "entity": entity_name,
                "info_count": len(self.entities[entity_name]["information"]),
            }

        except Exception as e:
            self.logger.error(f"Error storing entity: {e}")
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve entity information."""
        try:
            entity_name = query.get("entity_name")

            if entity_name:
                entity_data = self.entities.get(entity_name)
                if entity_data:
                    return {"success": True, "entity": entity_data}
                else:
                    return {"success": False, "error": f"Entity '{entity_name}' not found"}
            else:
                return {"success": True, "entities": list(self.entities.values())}

        except Exception as e:
            self.logger.error(f"Error retrieving entity: {e}")
            return {"success": False, "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Get formatted entity context for LLM."""
        try:
            entity_name = query.get("entity_name")
            limit = query.get("limit", 10)

            context_lines = []

            if entity_name:
                # Get specific entity
                entity_data = self.entities.get(entity_name)
                if entity_data:
                    context_lines.append(f"Entity: {entity_data['name']} ({entity_data['type']})")
                    for info in entity_data["information"][-5:]:  # Recent 5 pieces of info
                        context_lines.append(f"- {info['content']}")
            else:
                # Get all entities
                context_lines.append("Known Entities:")
                for entity_name, entity_data in list(self.entities.items())[:limit]:
                    info_count = len(entity_data["information"])
                    context_lines.append(
                        f"- {entity_name} ({entity_data['type']}, {info_count} facts)"
                    )

            context = (
                "\n".join(context_lines) if context_lines else "No entity information available."
            )

            return {"success": True, "context": context, "entity_count": len(self.entities)}

        except Exception as e:
            self.logger.error(f"Error getting entity context: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["EntityMemory"]
