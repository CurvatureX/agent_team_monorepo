"""
EPISODIC_MEMORY Memory Node Specification

Episodic memory for storing and retrieving timestamped events and experiences
for temporal context understanding and behavioral pattern recognition.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class EpisodicMemorySpec(BaseNodeSpec):
    """Episodic memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.EPISODIC_MEMORY,
            name="Episodic_Memory",
            description="Store and retrieve timestamped events and experiences for temporal context",
            # Configuration parameters
            configurations={
                "storage_backend": {
                    "type": "string",
                    "default": "timescaledb",
                    "description": "Storage backend optimized for time-series data",
                    "required": False,
                    "options": ["timescaledb", "postgresql", "elasticsearch", "influxdb"],
                },
                "importance_threshold": {
                    "type": "float",
                    "default": 0.5,
                    "description": "Minimum importance score for event storage (0.0-1.0)",
                    "required": False,
                },
                "retention_period": {
                    "type": "string",
                    "default": "30 days",
                    "description": "How long to retain episodic memories",
                    "required": False,
                },
                "event_embedding": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to generate embeddings for semantic event search",
                    "required": False,
                },
                "temporal_context_window": {
                    "type": "string",
                    "default": "7 days",
                    "description": "Time window for retrieving relevant episodic context",
                    "required": False,
                },
                "event_categorization": {
                    "type": "boolean",
                    "default": True,
                    "description": "Automatically categorize events by type",
                    "required": False,
                },
                "pattern_detection": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable temporal pattern detection in events",
                    "required": False,
                },
                "outcome_tracking": {
                    "type": "boolean",
                    "default": True,
                    "description": "Track outcomes and consequences of events",
                    "required": False,
                },
                "context_linking": {
                    "type": "boolean",
                    "default": True,
                    "description": "Link related events and build context chains",
                    "required": False,
                },
                "compression_strategy": {
                    "type": "string",
                    "default": "importance_based",
                    "description": "How to compress old episodic memories",
                    "required": False,
                    "options": ["importance_based", "time_based", "frequency_based", "none"],
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={
                "actor": "",
                "action": "",
                "object": {},
                "context": {},
                "outcome": {},
                "importance": 0.5,
                "timestamp": "",
                "event_type": "",
                "query_params": {},
            },
            default_output_params={
                "episodes": [],
                "temporal_patterns": {},
                "context_summary": "",
                "related_events": [],
                "behavioral_insights": {},
                "timeline": [],
                "pattern_analysis": {},
            },
            # Port definitions - Memory nodes don't use traditional ports
            input_ports=[],
            output_ports=[],
            # Metadata
            tags=["memory", "episodic", "temporal", "events", "experiences", "patterns"],
            # Examples
            examples=[
                {
                    "name": "User Behavior Tracking",
                    "description": "Track user actions and decisions over time for behavioral analysis",
                    "configurations": {
                        "storage_backend": "timescaledb",
                        "importance_threshold": 0.6,
                        "temporal_context_window": "14 days",
                        "event_categorization": True,
                        "pattern_detection": True,
                        "outcome_tracking": True,
                        "retention_period": "90 days",
                    },
                    "input_example": {
                        "actor": "user_12345",
                        "action": "completed_task",
                        "object": {
                            "task_id": "TASK-789",
                            "task_type": "code_review",
                            "complexity": "high",
                            "estimated_duration": "2 hours",
                        },
                        "context": {
                            "session_id": "session_456",
                            "project": "web_platform",
                            "team": "frontend_team",
                            "time_of_day": "afternoon",
                            "previous_tasks_today": 3,
                        },
                        "outcome": {
                            "success": True,
                            "actual_duration": "1.5 hours",
                            "quality_score": 0.92,
                            "issues_found": 2,
                            "feedback_positive": True,
                        },
                        "importance": 0.8,
                        "timestamp": "2025-01-20T14:30:00Z",
                        "event_type": "task_completion",
                    },
                    "expected_outputs": {
                        "episodes": [
                            {
                                "episode_id": "ep_789_completion",
                                "actor": "user_12345",
                                "action": "completed_task",
                                "timestamp": "2025-01-20T14:30:00Z",
                                "importance": 0.8,
                                "category": "productivity",
                                "context_summary": "High-complexity code review completed efficiently in afternoon session",
                                "outcome_success": True,
                                "related_episode_ids": ["ep_789_start", "ep_previous_reviews"],
                            }
                        ],
                        "temporal_patterns": {
                            "productivity_patterns": {
                                "peak_performance_time": "afternoon",
                                "task_completion_rate": 0.87,
                                "average_efficiency": 1.33,
                            },
                            "behavioral_trends": {
                                "task_estimation_accuracy": "improving",
                                "quality_consistency": "high",
                                "learning_velocity": "positive",
                            },
                        },
                        "context_summary": "User demonstrates consistent high-quality task completion with improving time estimation accuracy. Shows peak productivity in afternoon sessions with strong code review skills.",
                        "related_events": [
                            {
                                "episode_id": "ep_789_start",
                                "action": "started_task",
                                "timestamp": "2025-01-20T13:00:00Z",
                                "relation_type": "sequence_start",
                            },
                            {
                                "episode_id": "ep_previous_review",
                                "action": "completed_task",
                                "timestamp": "2025-01-19T15:15:00Z",
                                "relation_type": "similar_task",
                            },
                        ],
                        "behavioral_insights": {
                            "efficiency_trend": "increasing",
                            "quality_maintenance": "consistent",
                            "optimal_task_timing": "13:00-16:00",
                            "strength_areas": ["code_review", "time_management"],
                        },
                    },
                },
                {
                    "name": "Decision Making Analysis",
                    "description": "Track decision-making events and their outcomes for learning insights",
                    "configurations": {
                        "storage_backend": "postgresql",
                        "importance_threshold": 0.7,
                        "temporal_context_window": "21 days",
                        "pattern_detection": True,
                        "outcome_tracking": True,
                        "context_linking": True,
                        "compression_strategy": "importance_based",
                    },
                    "input_example": {
                        "actor": "product_manager_alice",
                        "action": "made_decision",
                        "object": {
                            "decision_type": "feature_prioritization",
                            "options_considered": [
                                "user_analytics",
                                "performance_optimization",
                                "new_integrations",
                            ],
                            "chosen_option": "performance_optimization",
                            "reasoning": "Performance issues affecting 23% of users based on recent metrics",
                            "stakeholders_involved": [
                                "engineering_team",
                                "ux_team",
                                "customer_success",
                            ],
                        },
                        "context": {
                            "meeting_type": "sprint_planning",
                            "quarter": "Q1_2025",
                            "current_sprint": "sprint_4",
                            "pressure_level": "medium",
                            "available_resources": "full_team",
                            "previous_decisions": ["delayed_analytics", "prioritized_ux"],
                        },
                        "outcome": {
                            "implementation_success": None,
                            "team_buy_in": 0.85,
                            "estimated_impact": "high",
                            "resource_allocation": "appropriate",
                        },
                        "importance": 0.9,
                        "timestamp": "2025-01-20T11:00:00Z",
                        "event_type": "strategic_decision",
                    },
                    "expected_outputs": {
                        "episodes": [
                            {
                                "episode_id": "decision_perf_opt_q1",
                                "actor": "product_manager_alice",
                                "action": "made_decision",
                                "decision_impact_level": "high",
                                "stakeholder_alignment": 0.85,
                                "context_complexity": "medium",
                                "follow_up_required": True,
                            }
                        ],
                        "temporal_patterns": {
                            "decision_patterns": {
                                "data_driven_decisions": 0.78,
                                "stakeholder_consultation_rate": 0.92,
                                "decision_confidence_trend": "increasing",
                            },
                            "outcome_patterns": {
                                "implementation_success_rate": 0.81,
                                "team_satisfaction_average": 0.83,
                                "impact_realization_rate": 0.75,
                            },
                        },
                        "behavioral_insights": {
                            "decision_making_style": "collaborative_data_driven",
                            "strength": "stakeholder_alignment",
                            "improvement_area": "follow_up_tracking",
                            "pattern": "prioritizes_user_impact",
                        },
                        "timeline": [
                            {
                                "timestamp": "2025-01-20T11:00:00Z",
                                "event": "Decision made: Performance optimization priority",
                                "impact_level": "high",
                            },
                            {
                                "timestamp": "2025-01-15T14:30:00Z",
                                "event": "Previous decision: Delayed analytics features",
                                "relation": "context_influence",
                            },
                        ],
                    },
                },
                {
                    "name": "Learning Experience Tracking",
                    "description": "Track learning events and knowledge acquisition patterns",
                    "configurations": {
                        "storage_backend": "elasticsearch",
                        "importance_threshold": 0.4,
                        "temporal_context_window": "30 days",
                        "event_categorization": True,
                        "pattern_detection": True,
                        "context_linking": True,
                        "retention_period": "1 year",
                    },
                    "input_example": {
                        "actor": "developer_bob",
                        "action": "learned_concept",
                        "object": {
                            "concept": "kubernetes_networking",
                            "learning_source": "official_documentation",
                            "difficulty_level": "intermediate",
                            "time_spent": "3 hours",
                            "practice_exercises": 5,
                            "concepts_mastered": [
                                "pods_communication",
                                "services",
                                "ingress_controllers",
                            ],
                        },
                        "context": {
                            "learning_goal": "infrastructure_modernization",
                            "project_context": "microservices_migration",
                            "mentor_available": True,
                            "learning_session_type": "self_directed",
                            "prior_knowledge": "docker_basics",
                        },
                        "outcome": {
                            "comprehension_level": 0.75,
                            "confidence_score": 0.68,
                            "immediate_application": True,
                            "follow_up_needed": True,
                            "knowledge_gaps_identified": ["network_policies", "service_mesh"],
                        },
                        "importance": 0.7,
                        "timestamp": "2025-01-20T16:00:00Z",
                        "event_type": "skill_development",
                    },
                    "expected_outputs": {
                        "episodes": [
                            {
                                "episode_id": "learn_k8s_networking",
                                "actor": "developer_bob",
                                "action": "learned_concept",
                                "knowledge_domain": "infrastructure",
                                "mastery_progression": 0.75,
                                "application_readiness": True,
                                "learning_efficiency": "good",
                            }
                        ],
                        "temporal_patterns": {
                            "learning_patterns": {
                                "preferred_learning_time": "afternoon",
                                "optimal_session_duration": "3-4 hours",
                                "retention_rate": 0.82,
                                "application_success_rate": 0.78,
                            },
                            "knowledge_acquisition": {
                                "infrastructure_skills": "advancing",
                                "learning_velocity": "consistent",
                                "complexity_tolerance": "increasing",
                            },
                        },
                        "context_summary": "Developer Bob demonstrates consistent learning progress in infrastructure domain with good retention and practical application. Shows preference for self-directed learning with documentation sources.",
                        "behavioral_insights": {
                            "learning_style": "documentation_focused",
                            "strength": "practical_application",
                            "growth_pattern": "incremental_building",
                            "next_recommendations": ["network_policies", "service_mesh_concepts"],
                        },
                        "pattern_analysis": {
                            "skill_building_trajectory": "infrastructure_specialization",
                            "learning_consistency": "high",
                            "knowledge_transfer": "effective",
                        },
                    },
                },
            ],
        )


# Export the specification instance
EPISODIC_MEMORY_SPEC = EpisodicMemorySpec()
