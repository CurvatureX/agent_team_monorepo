"""
KNOWLEDGE_BASE Memory Node Specification

Knowledge base memory for storing and querying structured knowledge facts
and rules for factual context enhancement and reasoning support.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class KnowledgeBaseMemorySpec(BaseNodeSpec):
    """Knowledge base memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.KNOWLEDGE_BASE,
            name="Knowledge_Base_Memory",
            description="Store and query structured knowledge facts and rules for factual context",
            # Configuration parameters (simplified)
            configurations={
                "storage_backend": {
                    "type": "string",
                    "default": "neo4j",
                    "description": "知识存储后端",
                    "required": False,
                    "options": ["neo4j", "postgresql", "arangodb", "rdf_triple_store"],
                },
                "confidence_threshold": {
                    "type": "float",
                    "default": 0.8,
                    "description": "事实入库的最小置信度（0.0-1.0）",
                    "required": False,
                },
                "fact_validation": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否在写入前进行事实校验",
                    "required": False,
                },
                "knowledge_domains": {
                    "type": "array",
                    "default": ["general", "technical", "business"],
                    "description": "事实所属域（用于组织与检索）",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Runtime parameters (schema-style)
            input_params={
                "operation": {
                    "type": "string",
                    "default": "query",
                    "description": "知识库操作",
                    "required": False,
                    "options": ["store", "query", "update", "delete"],
                },
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "原始文本内容（可从中抽取结构化事实）",
                    "required": False,
                    "multiline": True,
                },
                "facts": {
                    "type": "array",
                    "default": [],
                    "description": "已结构化的事实（subject/predicate/object 等）",
                    "required": False,
                },
                "query": {
                    "type": "string",
                    "default": "",
                    "description": "检索查询字符串",
                    "required": False,
                },
                "domain": {
                    "type": "string",
                    "default": "",
                    "description": "限定域（可选）",
                    "required": False,
                },
                "validation_required": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否需要事实校验",
                    "required": False,
                },
            },
            output_params={
                "facts": {
                    "type": "array",
                    "default": [],
                    "description": "事实列表（查询或写入后返回）",
                    "required": False,
                },
                "knowledge_summary": {
                    "type": "string",
                    "default": "",
                    "description": "知识摘要或说明",
                    "required": False,
                },
                "related_concepts": {
                    "type": "array",
                    "default": [],
                    "description": "相关概念或实体（可选）",
                    "required": False,
                },
            },
            # Port definitions - Memory nodes don't use traditional ports
            input_ports=[],
            output_ports=[],
            # Metadata
            tags=["memory", "knowledge-base", "facts", "reasoning", "inference", "validation"],
            # Examples
            examples=[
                {
                    "name": "Domain Knowledge Base",
                    "description": "Maintain structured knowledge about a specific domain with fact validation",
                    "configurations": {
                        "storage_backend": "neo4j",
                        "fact_extraction_model": OpenAIModel.GPT_5.value,
                        "confidence_threshold": 0.9,
                        "fact_validation": True,
                        "rule_inference": True,
                        "knowledge_domains": ["machine_learning", "data_science", "statistics"],
                        "reasoning_depth": 3,
                        "fact_linking": True,
                    },
                    "input_example": {
                        "content": "Neural networks with multiple hidden layers are called deep neural networks. Deep learning typically requires large amounts of training data. Gradient descent is the most common optimization algorithm used in training neural networks.",
                        "domain": "machine_learning",
                        "fact_type": "technical_definition",
                        "operation": "extract_and_store",
                        "validation_required": True,
                    },
                    "expected_outputs": {
                        "facts": [
                            {
                                "id": "fact_deep_networks",
                                "subject": "neural networks",
                                "predicate": "classified_as",
                                "object": "deep neural networks",
                                "condition": "when having multiple hidden layers",
                                "confidence": 0.96,
                                "domain": "machine_learning",
                                "fact_type": "definition",
                                "sources": ["extracted_content"],
                                "validation_status": "validated",
                            },
                            {
                                "id": "fact_deep_learning_data",
                                "subject": "deep learning",
                                "predicate": "requires",
                                "object": "large training datasets",
                                "confidence": 0.92,
                                "domain": "machine_learning",
                                "fact_type": "requirement",
                                "sources": ["extracted_content"],
                                "validation_status": "validated",
                            },
                            {
                                "id": "fact_gradient_descent",
                                "subject": "gradient descent",
                                "predicate": "is_most_common",
                                "object": "optimization algorithm",
                                "context": "neural network training",
                                "confidence": 0.94,
                                "domain": "machine_learning",
                                "fact_type": "prevalence",
                                "sources": ["extracted_content"],
                                "validation_status": "validated",
                            },
                        ],
                        "rules": [
                            {
                                "rule_id": "rule_deep_learning_inference",
                                "premise": [
                                    "neural networks with multiple layers",
                                    "uses large datasets",
                                ],
                                "conclusion": "likely implementing deep learning",
                                "confidence": 0.88,
                                "domain": "machine_learning",
                                "rule_type": "inference",
                            }
                        ],
                        "inferences": [
                            {
                                "inference_id": "inf_training_complexity",
                                "conclusion": "Deep neural networks require complex training processes",
                                "reasoning_chain": [
                                    "Deep networks have multiple layers",
                                    "Multiple layers require more parameters",
                                    "More parameters need more optimization",
                                    "Therefore complex training processes",
                                ],
                                "confidence": 0.85,
                                "inference_depth": 3,
                            }
                        ],
                        "knowledge_summary": "Machine learning knowledge base updated with 3 facts about neural networks, deep learning, and optimization. Established relationships between network architecture, data requirements, and training algorithms.",
                        "confidence_scores": {
                            "fact_extraction": 0.94,
                            "domain_classification": 0.98,
                            "validation_accuracy": 0.91,
                            "inference_reliability": 0.85,
                        },
                        "related_concepts": [
                            {
                                "concept": "backpropagation",
                                "relation": "training_method",
                                "strength": 0.87,
                            },
                            {
                                "concept": "overfitting",
                                "relation": "training_concern",
                                "strength": 0.82,
                            },
                            {
                                "concept": "regularization",
                                "relation": "optimization_technique",
                                "strength": 0.79,
                            },
                        ],
                    },
                },
                {
                    "name": "Business Process Knowledge",
                    "description": "Store and query business process facts and rules for decision support",
                    "configurations": {
                        "storage_backend": "postgresql",
                        "fact_validation": True,
                        "rule_inference": True,
                        "knowledge_domains": ["business_process", "compliance", "operations"],
                        "fact_update_strategy": "versioned",
                        "temporal_facts": True,
                        "reasoning_depth": 2,
                    },
                    "input_example": {
                        "query": "What are the requirements for expense approval above $5000?",
                        "domain": "business_process",
                        "operation": "query",
                        "context": {
                            "department": "engineering",
                            "employee_level": "senior",
                            "expense_category": "software_licenses",
                        },
                    },
                    "expected_outputs": {
                        "facts": [
                            {
                                "id": "fact_expense_approval_5k",
                                "subject": "expenses above $5000",
                                "predicate": "requires",
                                "object": "manager approval",
                                "confidence": 0.98,
                                "domain": "business_process",
                                "fact_type": "policy_requirement",
                                "valid_from": "2024-01-01",
                                "sources": ["company_policy_manual"],
                            },
                            {
                                "id": "fact_software_license_additional",
                                "subject": "software license expenses above $5000",
                                "predicate": "also_requires",
                                "object": "IT security review",
                                "confidence": 0.95,
                                "domain": "compliance",
                                "fact_type": "additional_requirement",
                                "valid_from": "2024-06-01",
                                "sources": ["security_policy_v2"],
                            },
                        ],
                        "rules": [
                            {
                                "rule_id": "rule_expense_escalation",
                                "premise": ["expense > $5000", "category = software"],
                                "conclusion": "requires both manager and IT security approval",
                                "confidence": 0.93,
                                "domain": "business_process",
                            }
                        ],
                        "inferences": [
                            {
                                "inference_id": "inf_approval_timeline",
                                "conclusion": "Software license expense of $6000 will need 3-5 business days for full approval",
                                "reasoning_chain": [
                                    "Amount requires manager approval (1-2 days)",
                                    "Software category requires IT security review (2-3 days)",
                                    "Reviews can run in parallel",
                                    "Total timeline: 3-5 business days",
                                ],
                                "confidence": 0.87,
                            }
                        ],
                        "knowledge_summary": "Expense approval requirements for amounts above $5000 include manager approval, with additional IT security review required for software licenses. Estimated approval timeline is 3-5 business days.",
                        "reasoning_chain": [
                            "Query: expense approval requirements > $5000",
                            "Retrieved: manager approval policy",
                            "Context: software licenses",
                            "Additional rule: IT security review",
                            "Combined requirements identified",
                        ],
                    },
                },
                {
                    "name": "Technical Standards Knowledge",
                    "description": "Maintain technical standards and best practices with inference capabilities",
                    "configurations": {
                        "storage_backend": "neo4j",
                        "confidence_threshold": 0.85,
                        "rule_inference": True,
                        "knowledge_domains": ["software_engineering", "architecture", "security"],
                        "fact_linking": True,
                        "reasoning_depth": 4,
                        "temporal_facts": True,
                    },
                    "input_example": {
                        "content": "API endpoints should use HTTPS for all external communications. RESTful APIs should follow semantic versioning. Authentication tokens should expire within 24 hours for security. Rate limiting should be implemented to prevent abuse.",
                        "domain": "software_engineering",
                        "fact_type": "best_practice",
                        "operation": "extract_and_store",
                        "validation_required": True,
                    },
                    "expected_outputs": {
                        "facts": [
                            {
                                "id": "fact_api_https",
                                "subject": "API endpoints",
                                "predicate": "should_use",
                                "object": "HTTPS",
                                "condition": "for external communications",
                                "confidence": 0.97,
                                "domain": "security",
                                "fact_type": "security_requirement",
                                "priority": "high",
                            },
                            {
                                "id": "fact_api_versioning",
                                "subject": "RESTful APIs",
                                "predicate": "should_follow",
                                "object": "semantic versioning",
                                "confidence": 0.94,
                                "domain": "software_engineering",
                                "fact_type": "best_practice",
                                "priority": "medium",
                            },
                            {
                                "id": "fact_token_expiry",
                                "subject": "authentication tokens",
                                "predicate": "should_expire_within",
                                "object": "24 hours",
                                "confidence": 0.96,
                                "domain": "security",
                                "fact_type": "security_requirement",
                                "priority": "high",
                            },
                            {
                                "id": "fact_rate_limiting",
                                "subject": "APIs",
                                "predicate": "should_implement",
                                "object": "rate limiting",
                                "purpose": "prevent abuse",
                                "confidence": 0.93,
                                "domain": "security",
                                "fact_type": "protection_measure",
                                "priority": "medium",
                            },
                        ],
                        "rules": [
                            {
                                "rule_id": "rule_secure_api_design",
                                "premise": ["API is external-facing", "handles sensitive data"],
                                "conclusion": "must implement HTTPS, token expiry, and rate limiting",
                                "confidence": 0.95,
                                "domain": "security",
                                "rule_type": "security_pattern",
                            }
                        ],
                        "inferences": [
                            {
                                "inference_id": "inf_api_security_checklist",
                                "conclusion": "Comprehensive API security requires layered protections",
                                "reasoning_chain": [
                                    "HTTPS protects data in transit",
                                    "Token expiry limits exposure window",
                                    "Rate limiting prevents abuse",
                                    "Semantic versioning enables secure updates",
                                    "Combined approach provides defense in depth",
                                ],
                                "confidence": 0.91,
                                "domain": "security",
                                "inference_depth": 4,
                            }
                        ],
                        "related_concepts": [
                            {
                                "concept": "OAuth2",
                                "relation": "authentication_method",
                                "strength": 0.88,
                            },
                            {
                                "concept": "API_gateway",
                                "relation": "implementation_pattern",
                                "strength": 0.85,
                            },
                            {
                                "concept": "TLS_certificates",
                                "relation": "security_component",
                                "strength": 0.82,
                            },
                            {
                                "concept": "request_throttling",
                                "relation": "rate_limiting_technique",
                                "strength": 0.79,
                            },
                        ],
                    },
                },
            ],
        )


# Export the specification instance
KNOWLEDGE_BASE_MEMORY_SPEC = KnowledgeBaseMemorySpec()
