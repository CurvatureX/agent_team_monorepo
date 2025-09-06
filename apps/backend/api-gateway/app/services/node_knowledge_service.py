"""
Node Knowledge Service for MCP API.

Provides access to workflow node specifications including types, detailed specs,
and search functionality for LLM clients through MCP tools.
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Import from shared module - Docker has shared/ in /app/shared/
from shared.node_specs.base import NodeSpec
from shared.node_specs.registry import node_spec_registry


class NodeKnowledgeService:
    """Service for accessing workflow node specifications and knowledge."""

    def __init__(self):
        """Initialize the service with node registry."""
        self.registry = node_spec_registry
        if self.registry is None:
            print("Warning: Node registry not available")

    def get_node_types(self, type_filter: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get all node types and subtypes, optionally filtered by type.

        Args:
            type_filter: Optional filter by node type (e.g., "ACTION_NODE")

        Returns:
            Dictionary mapping node types to lists of subtypes
        """
        if self.registry is None:
            return {}

        try:
            all_types = self.registry.get_node_types()

            if type_filter:
                return {k: v for k, v in all_types.items() if k == type_filter}

            return all_types
        except Exception as e:
            print(f"Error getting node types: {e}")
            return {}

    def get_node_details(
        self,
        nodes: List[Dict[str, str]],
        include_examples: bool = True,
        include_schemas: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get detailed specifications for requested nodes.

        Args:
            nodes: List of node identifiers with 'node_type' and 'subtype'
            include_examples: Whether to include usage examples
            include_schemas: Whether to include input/output schemas

        Returns:
            List of node specifications with details
        """
        if self.registry is None:
            return []

        results = []
        registry_errors = 0

        for node_req in nodes:
            try:
                node_type = node_req["node_type"]
                subtype = node_req["subtype"]
                spec = self.registry.get_spec(node_type, subtype)

                if spec:
                    result = self._serialize_node_spec(spec, include_examples, include_schemas)
                    results.append(result)
                else:
                    # 智能纠错：如果节点类型包含 _NODE 后缀，提示正确格式
                    # 但只对已知的有效节点类型进行纠错
                    valid_types = [
                        "TRIGGER",
                        "EXTERNAL_ACTION",
                        "AI_AGENT",
                        "ACTION",
                        "FLOW",
                        "MEMORY",
                        "TOOL",
                        "HUMAN_IN_THE_LOOP",
                    ]

                    if node_type.endswith("_NODE"):
                        correct_type = node_type.replace("_NODE", "")

                        # 只有当纠正后的类型是有效类型时，才提供纠错建议
                        if correct_type in valid_types:
                            # 尝试用正确的类型获取规格
                            correct_spec = self.registry.get_spec(correct_type, subtype)
                            if correct_spec:
                                # 返回正确的规格，并附带纠错信息
                                result = self._serialize_node_spec(
                                    correct_spec, include_examples, include_schemas
                                )
                                result[
                                    "warning"
                                ] = f"Auto-corrected: '{node_type}' → '{correct_type}'. Please use correct format without '_NODE' suffix."
                                result["node_type"] = correct_type  # 使用正确的类型
                                results.append(result)
                            else:
                                results.append(
                                    {
                                        "node_type": node_type,
                                        "subtype": subtype,
                                        "error": f"Incorrect format: '{node_type}' should be '{correct_type}'",
                                        "suggestion": {
                                            "correct_format": {
                                                "node_type": correct_type,
                                                "subtype": subtype,
                                            },
                                            "available_types": valid_types,
                                            "hint": "Remove '_NODE' suffix. Use get_node_types() to see all valid types.",
                                        },
                                    }
                                )
                        else:
                            # 如果纠正后的类型不是有效类型，返回标准的"未找到"错误
                            results.append(
                                {
                                    "node_type": node_type,
                                    "subtype": subtype,
                                    "error": "Node specification not found",
                                    "available_types": valid_types,
                                    "hint": "Check both node_type and subtype. Use get_node_types() for valid combinations.",
                                }
                            )
                    else:
                        # 提供更有用的错误信息
                        results.append(
                            {
                                "node_type": node_type,
                                "subtype": subtype,
                                "error": "Node specification not found",
                                "available_types": valid_types,
                                "hint": "Check both node_type and subtype. Use get_node_types() for valid combinations.",
                            }
                        )
            except Exception as e:
                registry_errors += 1
                results.append(
                    {
                        "node_type": node_req.get("node_type", "unknown"),
                        "subtype": node_req.get("subtype", "unknown"),
                        "error": f"Error retrieving spec: {str(e)}",
                    }
                )

        # If all nodes failed due to registry exceptions and we detect registry-level failure,
        # return empty list. This indicates the registry itself is failing, not individual nodes.
        # We detect registry failure by checking if the error suggests connection/infrastructure issues.
        if registry_errors == len(nodes) and registry_errors > 0:
            # Check if errors suggest registry-level failures (connection, infrastructure)
            registry_level_error_keywords = ["connection", "registry", "retrieval failed"]
            first_error = results[0].get("error", "").lower() if results else ""
            if any(keyword in first_error for keyword in registry_level_error_keywords):
                return []

        return results

    def search_nodes(
        self,
        query: str,
        max_results: int = 10,
        include_details: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search nodes by description and capabilities.

        Args:
            query: Search query describing desired functionality
            max_results: Maximum number of results to return
            include_details: Whether to include full specifications

        Returns:
            List of matching nodes with relevance scores
        """
        if self.registry is None:
            return []

        # Return empty results for empty queries
        if not query or query.strip() == "":
            return []

        try:
            all_specs = self.registry.list_all_specs()
            query_lower = query.lower()

            # Simple text search in description and parameter names
            matches = []
            for spec in all_specs:
                score = 0

                # Search in description
                if query_lower in spec.description.lower():
                    score += 10

                # Search in parameter names and descriptions
                for param in spec.parameters:
                    if query_lower in param.name.lower():
                        score += 5
                    if query_lower in param.description.lower():
                        score += 3

                # Search in port names and descriptions
                for port in spec.input_ports + spec.output_ports:
                    if query_lower in port.name.lower():
                        score += 3
                    if query_lower in port.description.lower():
                        score += 2

                if score > 0:
                    matches.append((spec, score))

            # Sort by relevance score and limit results
            matches.sort(key=lambda x: x[1], reverse=True)
            matches = matches[:max_results]

            # Format results
            results = []
            for spec, score in matches:
                if include_details:
                    result = self._serialize_node_spec(spec, True, True)
                    result["relevance_score"] = score
                else:
                    result = {
                        "node_type": spec.node_type,
                        "subtype": spec.subtype,
                        "description": spec.description,
                        "relevance_score": score,
                    }
                results.append(result)

            return results
        except Exception as e:
            print(f"Error searching nodes: {e}")
            return []

    def _serialize_node_spec(
        self, spec: NodeSpec, include_examples: bool, include_schemas: bool
    ) -> Dict[str, Any]:
        """
        Convert NodeSpec to serializable dictionary.

        Args:
            spec: Node specification to serialize
            include_examples: Whether to include examples
            include_schemas: Whether to include schemas

        Returns:
            Serialized node specification
        """
        try:
            result = {
                "node_type": spec.node_type,
                "subtype": spec.subtype,
                "version": spec.version,
                "description": spec.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type.value if hasattr(p.type, "value") else str(p.type),
                        "required": p.required,
                        "default_value": p.default_value,
                        "description": p.description,
                        "enum_values": p.enum_values,
                        "validation_pattern": p.validation_pattern,
                    }
                    for p in spec.parameters
                ],
                "input_ports": [
                    {
                        "name": port.name,
                        "type": port.type,
                        "required": port.required,
                        "description": port.description,
                        "max_connections": port.max_connections,
                        "data_format": {
                            "mime_type": port.data_format.mime_type,
                            "schema": port.data_format.schema,
                            "examples": port.data_format.examples,
                        }
                        if port.data_format and include_schemas
                        else None,
                        "validation_schema": port.validation_schema if include_schemas else None,
                    }
                    for port in spec.input_ports
                ],
                "output_ports": [
                    {
                        "name": port.name,
                        "type": port.type,
                        "description": port.description,
                        "max_connections": port.max_connections,
                        "data_format": {
                            "mime_type": port.data_format.mime_type,
                            "schema": port.data_format.schema,
                            "examples": port.data_format.examples,
                        }
                        if port.data_format and include_schemas
                        else None,
                        "validation_schema": port.validation_schema if include_schemas else None,
                    }
                    for port in spec.output_ports
                ],
            }

            if include_examples and spec.examples:
                result["examples"] = spec.examples

            return result
        except Exception as e:
            return {
                "node_type": getattr(spec, "node_type", "unknown"),
                "subtype": getattr(spec, "subtype", "unknown"),
                "error": f"Error serializing spec: {str(e)}",
            }
