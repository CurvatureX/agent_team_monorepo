"""
Public Node Schema API
获取节点手动调用参数schema的公开接口
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/node-schemas/{node_type}/{node_subtype}")
async def get_node_schema(node_type: str, node_subtype: str) -> Dict[str, Any]:
    """
    Get manual invocation parameter schema for any node type and subtype.

    This is a public endpoint that returns the JSON schema and examples
    for manually invoking a node of the specified type and subtype.

    Args:
        node_type: The main node type (e.g., 'TRIGGER', 'ACTION', 'AI_AGENT', etc.)
        node_subtype: The node subtype (e.g., 'SLACK', 'HTTP_REQUEST', 'OPENAI_CHATGPT', etc.)

    Returns:
        Dictionary containing:
        - node_type: The requested node type
        - node_subtype: The requested node subtype
        - schema: JSON schema for the manual invocation parameters
        - examples: Example parameter values
        - description: Human-readable description
        - supported: Boolean indicating if manual invocation is supported
    """
    try:
        logger.info(f"🔍 Getting node schema for {node_type}.{node_subtype}")

        # Get node spec for this node type and subtype
        from shared.node_specs.registry import NodeSpecRegistry

        registry = NodeSpecRegistry()

        # Convert to uppercase to match node specs
        node_type_upper = node_type.upper()
        node_subtype_upper = node_subtype.upper()

        try:
            # Get the node spec
            node_spec = registry.get_spec(node_type_upper, node_subtype_upper)

            if not node_spec:
                raise HTTPException(
                    status_code=404, detail=f"Node type '{node_type}.{node_subtype}' not found"
                )

            # Extract manual invocation parameters from the spec
            manual_invocation = node_spec.manual_invocation
            supported = False

            if (
                not manual_invocation
                or not hasattr(manual_invocation, "supported")
                or not manual_invocation.supported
            ):
                # If no manual invocation support, return unsupported response
                schema = {"type": "object", "properties": {}, "required": []}
                examples = [{}]
                description = f"Manual invocation not supported for {node_type}.{node_subtype}"
            else:
                supported = True
                # Use the parameter schema from the spec
                schema = manual_invocation.parameter_schema or {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }

                # Use the parameter examples from the spec
                examples = []
                if manual_invocation.parameter_examples:
                    for example in manual_invocation.parameter_examples:
                        examples.append(example.get("parameters", {}))

                # If no examples, create a basic one from defaults
                if not examples and manual_invocation.default_parameters:
                    examples = [manual_invocation.default_parameters]
                elif not examples:
                    examples = [{}]

                description = (
                    manual_invocation.description
                    or f"Manual invocation parameters for {node_type}.{node_subtype}"
                )

            logger.info(
                f"✅ Retrieved schema for node type: {node_type}.{node_subtype} (supported: {supported})"
            )

            return {
                "node_type": node_type,
                "node_subtype": node_subtype,
                "supported": supported,
                "schema": schema,
                "examples": examples,
                "description": description,
                "success": True,
            }

        except Exception as spec_error:
            logger.error(f"❌ Error getting node spec for {node_type}.{node_subtype}: {spec_error}")
            raise HTTPException(
                status_code=404, detail=f"Node type '{node_type}.{node_subtype}' not supported"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting node schema for {node_type}.{node_subtype}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/node-types")
async def list_node_types() -> Dict[str, Any]:
    """
    List all available node types and subtypes with manual invocation support status.

    Returns:
        Dictionary containing list of all node types, subtypes, and their manual invocation support
    """
    try:
        logger.info("📋 Listing available node types")

        from shared.node_specs.registry import NodeSpecRegistry

        registry = NodeSpecRegistry()

        try:
            # Get all specs
            all_specs = registry.list_all_specs()
            node_types = {}

            for spec in all_specs:
                node_type = str(spec.node_type).split(".")[-1]  # Extract enum name
                subtype = str(spec.subtype).split(".")[-1]  # Extract enum name

                if node_type not in node_types:
                    node_types[node_type] = {
                        "subtypes": [],
                        "manual_invocation_count": 0,
                        "total_count": 0,
                    }

                has_manual = (
                    hasattr(spec, "manual_invocation")
                    and spec.manual_invocation
                    and hasattr(spec.manual_invocation, "supported")
                    and spec.manual_invocation.supported
                )

                node_types[node_type]["subtypes"].append(
                    {
                        "subtype": subtype,
                        "name": getattr(spec, "display_name", subtype.replace("_", " ").title()),
                        "description": getattr(spec, "description", f"{subtype} node"),
                        "manual_invocation_supported": has_manual,
                    }
                )

                if has_manual:
                    node_types[node_type]["manual_invocation_count"] += 1
                node_types[node_type]["total_count"] += 1

            # Sort subtypes within each node type
            for node_type_info in node_types.values():
                node_type_info["subtypes"].sort(key=lambda x: x["subtype"])

            # Calculate totals
            total_manual = sum(info["manual_invocation_count"] for info in node_types.values())
            total_specs = sum(info["total_count"] for info in node_types.values())

            logger.info(
                f"✅ Found {len(node_types)} node types with {total_manual}/{total_specs} supporting manual invocation"
            )

            return {
                "node_types": dict(sorted(node_types.items())),
                "summary": {
                    "total_node_types": len(node_types),
                    "total_specifications": total_specs,
                    "manual_invocation_supported": total_manual,
                    "manual_invocation_percentage": round((total_manual / total_specs) * 100, 1)
                    if total_specs > 0
                    else 0,
                },
                "success": True,
            }

        except Exception as e:
            logger.error(f"❌ Error listing node types: {e}")
            # Fallback response with known trigger types
            return {
                "node_types": {
                    "TRIGGER": {
                        "subtypes": [
                            {
                                "subtype": "SLACK",
                                "name": "Slack",
                                "description": "Slack integration trigger",
                                "manual_invocation_supported": True,
                            },
                            {
                                "subtype": "WEBHOOK",
                                "name": "Webhook",
                                "description": "HTTP webhook trigger",
                                "manual_invocation_supported": True,
                            },
                            {
                                "subtype": "MANUAL",
                                "name": "Manual",
                                "description": "Manual execution trigger",
                                "manual_invocation_supported": True,
                            },
                            {
                                "subtype": "CRON",
                                "name": "Scheduled",
                                "description": "Cron-based scheduled trigger",
                                "manual_invocation_supported": True,
                            },
                            {
                                "subtype": "EMAIL",
                                "name": "Email",
                                "description": "Email-based trigger",
                                "manual_invocation_supported": True,
                            },
                            {
                                "subtype": "GITHUB",
                                "name": "GitHub",
                                "description": "GitHub webhook trigger",
                                "manual_invocation_supported": True,
                            },
                        ],
                        "manual_invocation_count": 6,
                        "total_count": 6,
                    }
                },
                "summary": {
                    "total_node_types": 1,
                    "total_specifications": 6,
                    "manual_invocation_supported": 6,
                    "manual_invocation_percentage": 100.0,
                },
                "success": True,
            }

    except Exception as e:
        logger.error(f"❌ Error listing node types: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
