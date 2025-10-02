"""
ENTITY_MEMORY Memory Node Specification

Entity memory for extracting, storing and tracking entities mentioned in
conversations for enhanced contextual understanding.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class EntityMemorySpec(BaseNodeSpec):
    """Entity memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.ENTITY_MEMORY,
            name="Entity_Memory",
            description="Extract, store and track entities mentioned in conversations for context enhancement",
            # Configuration parameters (simplified)
            configurations={
                "entity_types": {
                    "type": "array",
                    "default": ["person", "organization", "location", "product", "concept"],
                    "description": "需要抽取和跟踪的实体类型",
                    "required": False,
                },
                "confidence_threshold": {
                    "type": "float",
                    "default": 0.7,
                    "description": "实体抽取的最小置信度阈值（0.0-1.0）",
                    "required": False,
                },
                "relationship_tracking": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否跟踪实体之间的关系",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Runtime parameters (schema-style)
            input_params={
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "原始文本内容（来自AI节点上下文或用户输入）",
                    "required": False,
                    "multiline": True,
                },
                "existing_entities": {
                    "type": "array",
                    "default": [],
                    "description": "已有实体（用于增量更新或去重）",
                    "required": False,
                },
                "session_metadata": {
                    "type": "object",
                    "default": {},
                    "description": "会话相关元数据（工单、项目、标签等）",
                    "required": False,
                },
            },
            output_params={
                "entities": {
                    "type": "array",
                    "default": [],
                    "description": "抽取得到的实体列表（含名称、类型、置信度、属性等）",
                    "required": False,
                },
                "relationships": {
                    "type": "array",
                    "default": [],
                    "description": "实体之间的关系（可选）",
                    "required": False,
                },
                "entity_summary": {
                    "type": "string",
                    "default": "",
                    "description": "实体和关系的简要总结",
                    "required": False,
                },
            },
            # Port definitions - Memory nodes don't use traditional ports
            input_ports=[],
            output_ports=[],
            # Metadata
            tags=["memory", "entities", "nlp", "extraction", "relationships", "context"],
            # Examples
            examples=[
                {
                    "name": "Customer Entity Tracking",
                    "description": "Track customer entities and relationships in support conversations",
                    "configurations": {
                        "entity_types": ["person", "company", "product", "issue", "location"],
                        "extraction_model": OpenAIModel.GPT_5_NANO.value,
                        "relationship_tracking": True,
                        "importance_scoring": True,
                        "confidence_threshold": 0.8,
                        "temporal_tracking": True,
                        "storage_backend": "postgresql",
                    },
                    "input_example": {
                        "content": "John Smith from Acme Corp called about issues with the DataSync Pro software deployment at their Seattle office. He mentioned that Sarah Johnson, their IT director, has been coordinating with our technical team.",
                        "context": {
                            "session_id": "support_session_123",
                            "conversation_type": "customer_support",
                            "timestamp": "2025-01-20T14:30:00Z",
                        },
                        "session_metadata": {
                            "ticket_id": "SUPP-789",
                            "priority": "high",
                            "category": "technical_support",
                        },
                    },
                    "expected_outputs": {
                        "entities": [
                            {
                                "name": "John Smith",
                                "type": "person",
                                "confidence": 0.95,
                                "attributes": {"role": "customer_contact", "company": "Acme Corp"},
                                "first_mentioned": "2025-01-20T14:30:00Z",
                                "mention_count": 1,
                                "importance_score": 0.9,
                            },
                            {
                                "name": "Acme Corp",
                                "type": "organization",
                                "confidence": 0.98,
                                "attributes": {"industry": "unknown", "relationship": "customer"},
                                "first_mentioned": "2025-01-20T14:30:00Z",
                                "mention_count": 1,
                                "importance_score": 0.85,
                            },
                            {
                                "name": "DataSync Pro",
                                "type": "product",
                                "confidence": 0.92,
                                "attributes": {
                                    "category": "software",
                                    "issue_context": "deployment_issue",
                                },
                                "first_mentioned": "2025-01-20T14:30:00Z",
                                "mention_count": 1,
                                "importance_score": 0.88,
                            },
                            {
                                "name": "Seattle",
                                "type": "location",
                                "confidence": 0.96,
                                "attributes": {"type": "city", "context": "office_location"},
                                "first_mentioned": "2025-01-20T14:30:00Z",
                                "mention_count": 1,
                                "importance_score": 0.6,
                            },
                            {
                                "name": "Sarah Johnson",
                                "type": "person",
                                "confidence": 0.94,
                                "attributes": {"role": "IT director", "company": "Acme Corp"},
                                "first_mentioned": "2025-01-20T14:30:00Z",
                                "mention_count": 1,
                                "importance_score": 0.82,
                            },
                        ],
                        "relationships": [
                            {
                                "source": "John Smith",
                                "target": "Acme Corp",
                                "relationship_type": "works_at",
                                "confidence": 0.9,
                                "context": "customer contact from company",
                            },
                            {
                                "source": "Sarah Johnson",
                                "target": "Acme Corp",
                                "relationship_type": "works_at",
                                "confidence": 0.92,
                                "context": "IT director at company",
                            },
                            {
                                "source": "Acme Corp",
                                "target": "DataSync Pro",
                                "relationship_type": "uses",
                                "confidence": 0.88,
                                "context": "company using software product",
                            },
                            {
                                "source": "Acme Corp",
                                "target": "Seattle",
                                "relationship_type": "located_in",
                                "confidence": 0.85,
                                "context": "office location",
                            },
                        ],
                        "entity_summary": "Support conversation involving John Smith (customer) and Sarah Johnson (IT director) from Acme Corp regarding DataSync Pro deployment issues at their Seattle office. Key stakeholders and technical context identified for follow-up.",
                        "confidence_scores": {
                            "overall_extraction": 0.93,
                            "relationship_inference": 0.89,
                            "entity_classification": 0.95,
                        },
                        "temporal_mentions": [
                            {
                                "entity": "John Smith",
                                "timestamp": "2025-01-20T14:30:00Z",
                                "context": "initial_contact",
                                "mention_type": "explicit",
                            },
                            {
                                "entity": "DataSync Pro",
                                "timestamp": "2025-01-20T14:30:00Z",
                                "context": "problem_report",
                                "mention_type": "explicit",
                            },
                        ],
                    },
                },
                {
                    "name": "Project Entity Management",
                    "description": "Track project-related entities and their evolving relationships",
                    "configurations": {
                        "entity_types": [
                            "person",
                            "project",
                            "technology",
                            "milestone",
                            "organization",
                        ],
                        "relationship_tracking": True,
                        "importance_scoring": True,
                        "entity_linking": True,
                        "update_frequency": "real_time",
                        "context_window": 3,
                    },
                    "input_example": {
                        "content": "The new ML platform project is progressing well. Maria Rodriguez, our lead data scientist, completed the model training pipeline using TensorFlow 2.15. We're on track to meet the Q2 milestone for the beta release.",
                        "context": {
                            "conversation_type": "project_update",
                            "meeting_id": "proj_update_456",
                            "timestamp": "2025-01-20T10:15:00Z",
                        },
                        "existing_entities": [
                            {
                                "name": "ML platform",
                                "type": "project",
                                "last_seen": "2025-01-15T09:00:00Z",
                            }
                        ],
                    },
                    "expected_outputs": {
                        "entities": [
                            {
                                "name": "ML platform",
                                "type": "project",
                                "confidence": 0.96,
                                "attributes": {
                                    "status": "in_progress",
                                    "progress": "progressing_well",
                                },
                                "first_mentioned": "2025-01-15T09:00:00Z",
                                "last_mentioned": "2025-01-20T10:15:00Z",
                                "mention_count": 5,
                                "importance_score": 0.95,
                            },
                            {
                                "name": "Maria Rodriguez",
                                "type": "person",
                                "confidence": 0.97,
                                "attributes": {
                                    "role": "lead data scientist",
                                    "expertise": "machine_learning",
                                },
                                "first_mentioned": "2025-01-20T10:15:00Z",
                                "mention_count": 1,
                                "importance_score": 0.88,
                            },
                            {
                                "name": "TensorFlow 2.15",
                                "type": "technology",
                                "confidence": 0.99,
                                "attributes": {
                                    "category": "ml_framework",
                                    "version": "2.15",
                                    "usage": "model_training",
                                },
                                "first_mentioned": "2025-01-20T10:15:00Z",
                                "mention_count": 1,
                                "importance_score": 0.75,
                            },
                            {
                                "name": "Q2 beta release",
                                "type": "milestone",
                                "confidence": 0.91,
                                "attributes": {
                                    "quarter": "Q2",
                                    "type": "beta_release",
                                    "status": "on_track",
                                },
                                "first_mentioned": "2025-01-20T10:15:00Z",
                                "mention_count": 1,
                                "importance_score": 0.82,
                            },
                        ],
                        "relationships": [
                            {
                                "source": "Maria Rodriguez",
                                "target": "ML platform",
                                "relationship_type": "works_on",
                                "confidence": 0.93,
                                "context": "lead data scientist on project",
                            },
                            {
                                "source": "ML platform",
                                "target": "TensorFlow 2.15",
                                "relationship_type": "uses",
                                "confidence": 0.95,
                                "context": "project uses technology for model training",
                            },
                            {
                                "source": "ML platform",
                                "target": "Q2 beta release",
                                "relationship_type": "targets",
                                "confidence": 0.90,
                                "context": "project milestone target",
                            },
                        ],
                        "knowledge_links": {
                            "TensorFlow 2.15": {
                                "external_id": "tensorflow_2_15",
                                "source": "tech_knowledge_base",
                                "additional_info": "Latest TensorFlow version with enhanced GPU support",
                            }
                        },
                    },
                },
            ],
        )


# Export the specification instance
ENTITY_MEMORY_SPEC = EntityMemorySpec()
