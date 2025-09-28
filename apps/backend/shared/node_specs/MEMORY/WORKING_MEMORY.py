"""
WORKING_MEMORY Memory Node Specification

Working memory for temporary storage during active reasoning and
multi-step problem solving with fast access patterns.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class WorkingMemorySpec(BaseNodeSpec):
    """Working memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.WORKING_MEMORY,
            name="Working_Memory",
            description="Temporary memory for active reasoning and multi-step problem solving",
            # Configuration parameters
            configurations={
                "storage_backend": {
                    "type": "string",
                    "default": "redis",
                    "description": "Fast storage backend for working memory",
                    "required": False,
                    "options": ["redis", "memory", "memcached"],
                },
                "ttl_seconds": {
                    "type": "integer",
                    "default": 3600,
                    "description": "Time-to-live for working memory items in seconds",
                    "required": False,
                },
                "capacity_limit": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of items in working memory",
                    "required": False,
                },
                "eviction_policy": {
                    "type": "string",
                    "default": "lru",
                    "description": "Eviction policy when capacity limit is reached",
                    "required": False,
                    "options": ["lru", "fifo", "importance", "temporal", "access_frequency"],
                },
                "namespace": {
                    "type": "string",
                    "default": "default",
                    "description": "Namespace for isolating working memory contexts",
                    "required": False,
                },
                "persistence_level": {
                    "type": "string",
                    "default": "session",
                    "description": "How long items persist beyond active use",
                    "required": False,
                    "options": ["temporary", "session", "task", "persistent"],
                },
                "reasoning_context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Maintain reasoning chain context",
                    "required": False,
                },
                "auto_organization": {
                    "type": "boolean",
                    "default": True,
                    "description": "Automatically organize items by relevance",
                    "required": False,
                },
                "compression": {
                    "type": "boolean",
                    "default": False,
                    "description": "Compress stored items to save memory",
                    "required": False,
                },
                "access_optimization": {
                    "type": "string",
                    "default": "recency",
                    "description": "Optimize access patterns",
                    "required": False,
                    "options": ["recency", "importance", "frequency", "semantic"],
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={
                "operation": "store",
                "key": "",
                "value": {},
                "importance": 0.5,
                "context": {},
                "ttl_override": None,
                "tags": [],
            },
            default_output_params={
                "current_state": {},
                "recent_items": [],
                "reasoning_chain": [],
                "operation_result": {},
                "memory_stats": {},
                "context_summary": "",
                "related_items": [],
            },
            # Port definitions - Memory nodes don't use traditional ports
            input_ports=[],
            output_ports=[],
            # Metadata
            tags=["memory", "working", "temporary", "reasoning", "problem-solving", "cache"],
            # Examples
            examples=[
                {
                    "name": "Multi-Step Reasoning",
                    "description": "Maintain intermediate results during complex problem solving",
                    "configurations": {
                        "storage_backend": "redis",
                        "ttl_seconds": 1800,
                        "capacity_limit": 50,
                        "eviction_policy": "importance",
                        "namespace": "reasoning_session",
                        "reasoning_context": True,
                        "auto_organization": True,
                        "access_optimization": "importance",
                    },
                    "input_example": {
                        "operation": "store",
                        "key": "market_analysis_step_1",
                        "value": {
                            "analysis_type": "competitive_landscape",
                            "market_segments": ["enterprise", "smb", "consumer"],
                            "key_competitors": ["CompanyA", "CompanyB", "CompanyC"],
                            "market_size": "$2.3B",
                            "growth_rate": "12%",
                            "findings": [
                                "Enterprise segment dominated by CompanyA",
                                "SMB segment highly fragmented",
                                "Consumer segment emerging opportunity",
                            ],
                        },
                        "importance": 0.9,
                        "context": {
                            "reasoning_step": 1,
                            "total_steps": 5,
                            "problem_type": "strategic_analysis",
                            "decision_context": "market_entry",
                        },
                        "tags": ["market_analysis", "competitive", "strategic"],
                    },
                    "expected_outputs": {
                        "current_state": {
                            "active_reasoning": "market_entry_analysis",
                            "step_progress": "1/5",
                            "key_insights_count": 3,
                            "confidence_level": 0.75,
                        },
                        "recent_items": [
                            {
                                "key": "market_analysis_step_1",
                                "timestamp": "2025-01-20T15:30:00Z",
                                "importance": 0.9,
                                "item_type": "analysis_result",
                                "access_count": 1,
                                "summary": "Competitive landscape analysis identifying market segments and key competitors",
                            }
                        ],
                        "reasoning_chain": [
                            {
                                "step": 1,
                                "operation": "market_analysis",
                                "key_finding": "Enterprise segment dominated by CompanyA",
                                "confidence": 0.85,
                                "timestamp": "2025-01-20T15:30:00Z",
                                "next_step_hint": "analyze_customer_needs",
                            }
                        ],
                        "operation_result": {
                            "success": True,
                            "key": "market_analysis_step_1",
                            "storage_location": "redis:reasoning_session",
                            "ttl_remaining": 1800,
                            "memory_usage": "2.3KB",
                        },
                        "memory_stats": {
                            "total_items": 1,
                            "capacity_used": "2%",
                            "average_importance": 0.9,
                            "active_reasoning_chains": 1,
                            "memory_efficiency": 0.95,
                        },
                        "context_summary": "Strategic market entry analysis in progress. Completed competitive landscape assessment showing enterprise dominance and SMB fragmentation. Ready for next analysis step.",
                    },
                },
                {
                    "name": "Code Analysis Workspace",
                    "description": "Temporary storage for code analysis and debugging information",
                    "configurations": {
                        "storage_backend": "memory",
                        "ttl_seconds": 900,
                        "capacity_limit": 75,
                        "eviction_policy": "access_frequency",
                        "namespace": "code_analysis",
                        "persistence_level": "task",
                        "auto_organization": True,
                        "compression": True,
                    },
                    "input_example": {
                        "operation": "store",
                        "key": "function_analysis_getUserProfile",
                        "value": {
                            "function_name": "getUserProfile",
                            "file_path": "/src/user/profile.js",
                            "complexity_score": 7.2,
                            "dependencies": ["database.js", "auth.js", "validation.js"],
                            "potential_issues": [
                                "Missing null check on line 45",
                                "Inefficient database query in loop",
                                "Hardcoded timeout value",
                            ],
                            "performance_metrics": {
                                "avg_execution_time": "120ms",
                                "memory_usage": "2.3MB",
                                "cpu_usage": "15%",
                            },
                            "test_coverage": 0.78,
                            "refactor_suggestions": [
                                "Extract database query logic",
                                "Add input validation middleware",
                                "Implement caching layer",
                            ],
                        },
                        "importance": 0.8,
                        "context": {
                            "analysis_type": "code_review",
                            "reviewer": "senior_dev_alice",
                            "review_session": "code_review_20250120",
                            "priority": "medium",
                        },
                        "tags": ["code_analysis", "performance", "refactoring"],
                    },
                    "expected_outputs": {
                        "current_state": {
                            "active_analysis": "code_review_session",
                            "functions_analyzed": 1,
                            "issues_found": 3,
                            "refactor_opportunities": 3,
                            "overall_health_score": 0.72,
                        },
                        "recent_items": [
                            {
                                "key": "function_analysis_getUserProfile",
                                "summary": "Function analysis revealing performance and validation issues",
                                "complexity": "medium",
                                "urgency": "medium",
                                "refactor_potential": "high",
                            }
                        ],
                        "reasoning_chain": [
                            {
                                "step": "code_analysis",
                                "finding": "Performance bottleneck in getUserProfile function",
                                "evidence": "Database query in loop, 120ms avg execution time",
                                "recommendation": "Extract query logic and implement caching",
                                "priority": "medium",
                            }
                        ],
                        "memory_stats": {
                            "compressed_size": "1.8KB",
                            "compression_ratio": 0.65,
                            "access_patterns": "sequential",
                            "cache_hit_rate": 0.92,
                        },
                        "related_items": [
                            {
                                "key": "auth_js_analysis",
                                "relation": "dependency",
                                "relevance_score": 0.7,
                            },
                            {
                                "key": "database_patterns",
                                "relation": "common_issue",
                                "relevance_score": 0.8,
                            },
                        ],
                    },
                },
                {
                    "name": "Problem-Solving Context",
                    "description": "Maintain context and intermediate solutions for complex problem solving",
                    "configurations": {
                        "storage_backend": "redis",
                        "ttl_seconds": 2400,
                        "capacity_limit": 120,
                        "eviction_policy": "temporal",
                        "namespace": "problem_solving",
                        "reasoning_context": True,
                        "auto_organization": True,
                        "access_optimization": "semantic",
                        "persistence_level": "session",
                    },
                    "input_example": {
                        "operation": "retrieve_and_update",
                        "key": "optimization_problem_context",
                        "context": {
                            "problem_type": "resource_allocation",
                            "constraints": [
                                "budget_limit",
                                "time_constraints",
                                "skill_availability",
                            ],
                            "current_iteration": 3,
                            "solution_approach": "constraint_satisfaction",
                        },
                        "tags": ["optimization", "resource_planning", "constraints"],
                    },
                    "expected_outputs": {
                        "current_state": {
                            "problem_context": "resource_allocation_optimization",
                            "solution_iterations": 3,
                            "constraint_satisfaction_level": 0.73,
                            "convergence_trend": "improving",
                            "next_optimization_direction": "skill_matching",
                        },
                        "recent_items": [
                            {
                                "key": "optimization_problem_context",
                                "value": {
                                    "current_solution": {
                                        "resource_assignments": [
                                            {
                                                "resource": "dev_team_A",
                                                "task": "feature_development",
                                                "allocation": 0.8,
                                            },
                                            {
                                                "resource": "dev_team_B",
                                                "task": "bug_fixes",
                                                "allocation": 0.6,
                                            },
                                        ],
                                        "constraints_satisfied": [
                                            "budget_limit",
                                            "time_constraints",
                                        ],
                                        "constraints_violated": ["skill_availability"],
                                        "objective_value": 0.73,
                                        "improvement_potential": 0.15,
                                    }
                                },
                                "last_updated": "2025-01-20T16:45:00Z",
                                "access_count": 7,
                                "optimization_iteration": 3,
                            }
                        ],
                        "reasoning_chain": [
                            {
                                "iteration": 1,
                                "approach": "greedy_allocation",
                                "result": "budget_constraint_violated",
                                "lesson": "need_constraint_prioritization",
                            },
                            {
                                "iteration": 2,
                                "approach": "constraint_prioritized",
                                "result": "improved_budget_compliance",
                                "lesson": "skill_matching_remains_issue",
                            },
                            {
                                "iteration": 3,
                                "approach": "skill_aware_allocation",
                                "result": "better_skill_utilization",
                                "lesson": "convergence_toward_optimal",
                                "next_focus": "fine_tuning_allocations",
                            },
                        ],
                        "context_summary": "Resource allocation optimization showing convergent improvement over 3 iterations. Budget and time constraints now satisfied, focusing on skill availability optimization. Solution quality at 73% with 15% improvement potential identified.",
                        "memory_stats": {
                            "reasoning_depth": 3,
                            "context_coherence": 0.88,
                            "solution_evolution_rate": 0.12,
                            "memory_utilization": "efficient",
                        },
                    },
                },
            ],
        )


# Export the specification instance
WORKING_MEMORY_SPEC = WorkingMemorySpec()
