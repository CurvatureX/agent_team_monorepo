"""
GRAPH_MEMORY Memory Node Specification

Graph memory for storing and querying graph-structured relationships
for complex contextual understanding and knowledge representation.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class GraphMemorySpec(BaseNodeSpec):
    """Graph memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.GRAPH_MEMORY,
            name="Graph_Memory",
            description="Store and query graph-structured relationships for complex contextual understanding",
            # Configuration parameters (simplified)
            configurations={
                "graph_database": {
                    "type": "string",
                    "default": "neo4j",
                    "description": "图数据库后端",
                    "required": False,
                    "options": ["neo4j", "arangodb", "tigergraph", "amazon_neptune"],
                },
                "node_types": {
                    "type": "array",
                    "default": ["concept", "entity", "event", "topic"],
                    "description": "节点类型",
                    "required": False,
                },
                "relationship_types": {
                    "type": "array",
                    "default": ["related_to", "part_of", "depends_on", "similar_to"],
                    "description": "关系类型",
                    "required": False,
                },
                "traversal_depth": {
                    "type": "integer",
                    "default": 2,
                    "description": "遍历最大深度",
                    "required": False,
                },
                "relationship_strength_threshold": {
                    "type": "float",
                    "default": 0.3,
                    "description": "关系写入阈值（0.0-1.0）",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Runtime parameters (schema-style)
            input_params={
                "operation": {
                    "type": "string",
                    "default": "query",
                    "description": "图操作",
                    "required": False,
                    "options": ["add", "add_and_query", "query"],
                },
                "nodes": {
                    "type": "array",
                    "default": [],
                    "description": "要添加或查询的节点列表",
                    "required": False,
                },
                "relationships": {
                    "type": "array",
                    "default": [],
                    "description": "关系列表（source/target/type/weight/properties）",
                    "required": False,
                },
                "query": {
                    "type": "object",
                    "default": {},
                    "description": "查询条件（子图、路径、邻居等）",
                    "required": False,
                },
                "start_node": {
                    "type": "string",
                    "default": "",
                    "description": "遍历或路径查询的起始节点",
                    "required": False,
                },
                "filters": {
                    "type": "object",
                    "default": {},
                    "description": "过滤条件（关系类型、权重阈值、深度等）",
                    "required": False,
                },
            },
            output_params={
                "paths": {
                    "type": "array",
                    "default": [],
                    "description": "匹配到的路径集合",
                    "required": False,
                },
                "connected_nodes": {
                    "type": "array",
                    "default": [],
                    "description": "相连节点与连接信息",
                    "required": False,
                },
                "relationship_summary": {
                    "type": "string",
                    "default": "",
                    "description": "关系摘要",
                    "required": False,
                },
                "graph_metrics": {
                    "type": "object",
                    "default": {},
                    "description": "图指标（节点/关系计数、密度等）",
                    "required": False,
                },
            },
            # Port definitions - Memory nodes don't use traditional ports            # Metadata
            tags=["memory", "graph", "relationships", "network", "traversal", "analysis"],
            # Examples
            examples=[
                {
                    "name": "Concept Relationship Graph",
                    "description": "Build and query relationships between concepts and topics for knowledge navigation",
                    "configurations": {
                        "graph_database": "neo4j",
                        "relationship_types": ["related_to", "part_of", "prerequisite", "leads_to"],
                        "traversal_depth": 3,
                        "node_types": ["concept", "skill", "topic", "resource"],
                        "weight_relationships": True,
                        "graph_analysis": True,
                        "auto_relationship_inference": True,
                    },
                    "input_example": {
                        "nodes": [
                            {
                                "id": "machine_learning",
                                "type": "concept",
                                "properties": {
                                    "name": "Machine Learning",
                                    "domain": "artificial_intelligence",
                                    "complexity": "intermediate",
                                    "popularity": 0.95,
                                },
                            },
                            {
                                "id": "neural_networks",
                                "type": "concept",
                                "properties": {
                                    "name": "Neural Networks",
                                    "domain": "deep_learning",
                                    "complexity": "advanced",
                                    "popularity": 0.88,
                                },
                            },
                            {
                                "id": "python_programming",
                                "type": "skill",
                                "properties": {
                                    "name": "Python Programming",
                                    "domain": "programming",
                                    "complexity": "beginner",
                                    "popularity": 0.92,
                                },
                            },
                        ],
                        "relationships": [
                            {
                                "source": "neural_networks",
                                "target": "machine_learning",
                                "type": "part_of",
                                "weight": 0.9,
                                "properties": {"strength": "strong", "bidirectional": False},
                            },
                            {
                                "source": "python_programming",
                                "target": "machine_learning",
                                "type": "prerequisite",
                                "weight": 0.8,
                                "properties": {"importance": "high", "learning_order": 1},
                            },
                        ],
                        "operation": "add_and_query",
                        "start_node": "machine_learning",
                    },
                    "expected_outputs": {
                        "paths": [
                            {
                                "path_id": "path_ml_prerequisites",
                                "nodes": [
                                    "python_programming",
                                    "machine_learning",
                                    "neural_networks",
                                ],
                                "relationships": ["prerequisite", "part_of"],
                                "path_length": 2,
                                "total_weight": 1.7,
                                "path_type": "learning_progression",
                            }
                        ],
                        "connected_nodes": [
                            {
                                "node_id": "neural_networks",
                                "distance": 1,
                                "relationship_type": "part_of",
                                "connection_strength": 0.9,
                                "properties": {"name": "Neural Networks", "complexity": "advanced"},
                            },
                            {
                                "node_id": "python_programming",
                                "distance": 1,
                                "relationship_type": "prerequisite",
                                "connection_strength": 0.8,
                                "properties": {
                                    "name": "Python Programming",
                                    "complexity": "beginner",
                                },
                            },
                        ],
                        "relationship_summary": "Machine Learning concept connected to Python Programming (prerequisite) and Neural Networks (specialization). Forms clear learning pathway from programming fundamentals to advanced AI techniques.",
                        "graph_metrics": {
                            "node_count": 3,
                            "relationship_count": 2,
                            "average_clustering_coefficient": 0.67,
                            "graph_density": 0.33,
                            "diameter": 2,
                        },
                        "centrality_scores": {
                            "machine_learning": {
                                "betweenness": 0.5,
                                "closeness": 0.67,
                                "degree": 2,
                                "importance": "hub",
                            },
                            "neural_networks": {
                                "betweenness": 0.0,
                                "closeness": 0.4,
                                "degree": 1,
                                "importance": "leaf",
                            },
                            "python_programming": {
                                "betweenness": 0.0,
                                "closeness": 0.4,
                                "degree": 1,
                                "importance": "prerequisite",
                            },
                        },
                    },
                },
                {
                    "name": "Business Process Network",
                    "description": "Map business process dependencies and workflow relationships",
                    "configurations": {
                        "graph_database": "neo4j",
                        "relationship_types": [
                            "depends_on",
                            "triggers",
                            "blocks",
                            "enables",
                            "provides_input_to",
                        ],
                        "traversal_depth": 4,
                        "node_types": ["process", "system", "role", "document", "decision"],
                        "temporal_relationships": True,
                        "graph_analysis": True,
                        "relationship_strength_threshold": 0.4,
                    },
                    "input_example": {
                        "query": {
                            "start_node": "employee_onboarding",
                            "relationship_types": ["depends_on", "triggers"],
                            "depth": 3,
                            "filters": {"node_types": ["process", "system"], "active": True},
                        },
                        "operation": "traversal_query",
                    },
                    "expected_outputs": {
                        "paths": [
                            {
                                "path_id": "onboarding_dependency_chain",
                                "nodes": [
                                    "employee_onboarding",
                                    "hr_system",
                                    "it_provisioning",
                                    "access_management",
                                ],
                                "relationships": ["depends_on", "triggers", "depends_on"],
                                "path_length": 3,
                                "critical_path": True,
                                "estimated_duration": "5 business days",
                            }
                        ],
                        "connected_nodes": [
                            {
                                "node_id": "hr_system",
                                "distance": 1,
                                "relationship_type": "depends_on",
                                "connection_strength": 0.95,
                                "node_type": "system",
                                "criticality": "high",
                                "properties": {
                                    "availability": 0.99,
                                    "response_time": "< 2 seconds",
                                },
                            },
                            {
                                "node_id": "it_provisioning",
                                "distance": 2,
                                "relationship_type": "triggers",
                                "connection_strength": 0.87,
                                "node_type": "process",
                                "criticality": "medium",
                                "properties": {"automation_level": 0.75, "sla": "2 business days"},
                            },
                        ],
                        "relationship_summary": "Employee onboarding process forms critical dependency chain through HR system to IT provisioning and access management. Identifies potential bottlenecks and automation opportunities.",
                        "graph_metrics": {
                            "critical_path_length": 5,
                            "bottleneck_nodes": ["hr_system", "access_management"],
                            "automation_coverage": 0.68,
                            "process_efficiency_score": 0.72,
                        },
                        "subgraphs": [
                            {
                                "subgraph_id": "onboarding_cluster",
                                "nodes": ["employee_onboarding", "hr_system", "it_provisioning"],
                                "cluster_type": "process_dependency",
                                "cohesion_score": 0.84,
                            }
                        ],
                    },
                },
                {
                    "name": "Knowledge Discovery Network",
                    "description": "Explore knowledge relationships for research and discovery",
                    "configurations": {
                        "graph_database": "arangodb",
                        "relationship_types": [
                            "cites",
                            "builds_on",
                            "contradicts",
                            "supports",
                            "extends",
                        ],
                        "traversal_depth": 4,
                        "node_types": ["paper", "author", "concept", "methodology", "dataset"],
                        "weight_relationships": True,
                        "auto_relationship_inference": True,
                        "graph_pruning": True,
                    },
                    "input_example": {
                        "query": {
                            "start_node": "transformer_architecture",
                            "relationship_types": ["builds_on", "extends"],
                            "depth": 3,
                            "filters": {
                                "publication_year": {"gte": 2020},
                                "citation_count": {"gte": 100},
                            },
                        },
                        "operation": "research_exploration",
                    },
                    "expected_outputs": {
                        "paths": [
                            {
                                "path_id": "transformer_evolution",
                                "nodes": [
                                    "transformer_architecture",
                                    "bert_model",
                                    "gpt_architecture",
                                    "large_language_models",
                                ],
                                "relationships": ["extends", "builds_on", "enables"],
                                "path_length": 3,
                                "research_trajectory": "attention_to_language_models",
                                "innovation_score": 0.94,
                            }
                        ],
                        "connected_nodes": [
                            {
                                "node_id": "bert_model",
                                "distance": 1,
                                "relationship_type": "extends",
                                "connection_strength": 0.92,
                                "node_type": "methodology",
                                "impact_score": 0.89,
                                "properties": {
                                    "citation_count": 15420,
                                    "publication_year": 2018,
                                    "breakthrough_level": "high",
                                },
                            },
                            {
                                "node_id": "gpt_architecture",
                                "distance": 2,
                                "relationship_type": "builds_on",
                                "connection_strength": 0.88,
                                "node_type": "methodology",
                                "impact_score": 0.95,
                                "properties": {
                                    "citation_count": 8750,
                                    "publication_year": 2020,
                                    "breakthrough_level": "revolutionary",
                                },
                            },
                        ],
                        "relationship_summary": "Transformer architecture serves as foundational innovation leading to BERT's bidirectional encoding and GPT's generative capabilities, ultimately enabling large language models. Clear evolution pathway in NLP research.",
                        "community_clusters": [
                            {
                                "cluster_id": "attention_mechanisms",
                                "nodes": [
                                    "transformer_architecture",
                                    "self_attention",
                                    "multi_head_attention",
                                ],
                                "cluster_strength": 0.91,
                                "research_theme": "attention_based_models",
                            },
                            {
                                "cluster_id": "language_modeling",
                                "nodes": [
                                    "bert_model",
                                    "gpt_architecture",
                                    "large_language_models",
                                ],
                                "cluster_strength": 0.87,
                                "research_theme": "pre_trained_language_models",
                            },
                        ],
                        "graph_metrics": {
                            "research_impact_centrality": {
                                "transformer_architecture": 0.96,
                                "bert_model": 0.84,
                                "gpt_architecture": 0.91,
                            },
                            "innovation_flow_strength": 0.89,
                            "cross_pollination_score": 0.76,
                        },
                    },
                },
            ],
        )


# Export the specification instance
GRAPH_MEMORY_SPEC = GraphMemorySpec()
