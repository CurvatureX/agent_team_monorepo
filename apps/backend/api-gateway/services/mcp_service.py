"""
MCP service for tool discovery and invocation with comprehensive error handling
"""

import time
from typing import Any, Dict, List

import jsonschema
import structlog
from jsonschema import ValidationError

from clients.elasticsearch_client import ElasticsearchClient
from clients.node_knowledge_client import NodeKnowledgeClient
from core.mcp_exceptions import (
    MCPDatabaseError,
    MCPNetworkError,
    MCPParameterError,
    MCPServiceError,
    MCPTimeoutError,
    MCPToolNotFoundError,
    MCPValidationError,
    classify_error,
)
from models.mcp_models import TOOL_REGISTRY, MCPInvokeResponse, MCPToolSchema, MCPToolsResponse

logger = structlog.get_logger()


class MCPService:
    """Service for managing MCP tools and invocations"""

    def __init__(self):
        try:
            self.tool_registry = TOOL_REGISTRY
            self.node_knowledge_client = NodeKnowledgeClient()
            self.elasticsearch_client = ElasticsearchClient()

            logger.info(
                "MCP service initialized successfully",
                available_tools=list(self.tool_registry.keys()),
                tool_count=len(self.tool_registry),
            )
        except Exception as e:
            logger.error(
                "Failed to initialize MCP service", error=str(e), error_type=type(e).__name__
            )
            raise MCPServiceError(
                message=f"MCP service initialization failed: {str(e)}",
                user_message="Service temporarily unavailable",
            )

    def get_available_tools(self) -> MCPToolsResponse:
        """
        Get list of available tools with comprehensive error handling

        Returns:
            MCPToolsResponse with all available tools

        Raises:
            MCPServiceError: If tool registry is corrupted or unavailable
        """
        start_time = time.time()

        try:
            logger.info("Retrieving available tools from registry")

            if not self.tool_registry:
                raise MCPServiceError(
                    message="Tool registry is empty or not initialized",
                    user_message="No tools available at this time",
                )

            tools = []
            failed_tools = []

            for tool_name, tool_config in self.tool_registry.items():
                try:
                    # Validate tool configuration
                    if not all(key in tool_config for key in ["name", "description", "parameters"]):
                        failed_tools.append(tool_name)
                        logger.warning(
                            "Invalid tool configuration",
                            tool_name=tool_name,
                            missing_keys=[
                                key
                                for key in ["name", "description", "parameters"]
                                if key not in tool_config
                            ],
                        )
                        continue

                    tools.append(
                        MCPToolSchema(
                            name=tool_config["name"],
                            description=tool_config["description"],
                            parameters=tool_config["parameters"],
                        )
                    )
                except Exception as e:
                    failed_tools.append(tool_name)
                    logger.error(
                        "Failed to process tool configuration",
                        tool_name=tool_name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

            processing_time = time.time() - start_time

            if not tools:
                raise MCPServiceError(
                    message="No valid tools available in registry",
                    user_message="No tools available at this time",
                )

            logger.info(
                "Available tools retrieved successfully",
                tool_count=len(tools),
                failed_tools=failed_tools,
                processing_time_ms=round(processing_time * 1000, 2),
            )

            return MCPToolsResponse(tools=tools)

        except MCPServiceError:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Unexpected error retrieving tools",
                error=str(e),
                error_type=type(e).__name__,
                processing_time_ms=round(processing_time * 1000, 2),
            )
            raise MCPServiceError(
                message=f"Failed to retrieve tools: {str(e)}",
                user_message="Unable to retrieve available tools",
            )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """
        Invoke a specific tool with parameters and comprehensive error handling

        Args:
            tool_name: Name of the tool to invoke
            params: Parameters for the tool

        Returns:
            MCPInvokeResponse with tool execution result

        Raises:
            MCPToolNotFoundError: If tool doesn't exist
            MCPValidationError: If parameters are invalid
            MCPServiceError: If tool execution fails
        """
        start_time = time.time()

        logger.info(
            "Starting tool invocation",
            tool_name=tool_name,
            params=params,
            param_count=len(params) if params else 0,
        )

        try:
            # Check if tool exists
            if tool_name not in self.tool_registry:
                logger.error(
                    "Tool not found in registry",
                    tool_name=tool_name,
                    available_tools=list(self.tool_registry.keys()),
                )
                raise MCPToolNotFoundError(tool_name)

            # Validate parameters
            try:
                self.validate_tool_params(tool_name, params)
                logger.debug("Parameter validation successful", tool_name=tool_name)
            except MCPValidationError as e:
                logger.error(
                    "Parameter validation failed",
                    tool_name=tool_name,
                    error=e.message,
                    validation_details=e.details,
                )
                raise

            # Route to appropriate tool handler with error handling
            try:
                if tool_name == "node_knowledge_retriever":
                    result = await self._handle_node_knowledge_retriever(params)
                elif tool_name == "elasticsearch":
                    result = await self._handle_elasticsearch(params)
                else:
                    logger.error(
                        "Tool handler not implemented",
                        tool_name=tool_name,
                        available_handlers=["node_knowledge_retriever", "elasticsearch"],
                    )
                    raise MCPServiceError(
                        message=f"Tool handler not implemented for '{tool_name}'",
                        user_message=f"Tool '{tool_name}' is not currently available",
                    )

                processing_time = time.time() - start_time

                logger.info(
                    "Tool invocation completed successfully",
                    tool_name=tool_name,
                    processing_time_ms=round(processing_time * 1000, 2),
                    result_size=len(str(result)) if result else 0,
                )

                return MCPInvokeResponse(success=True, result=result)

            except (
                MCPParameterError,
                MCPServiceError,
                MCPDatabaseError,
                MCPNetworkError,
                MCPTimeoutError,
            ):
                # Re-raise known MCP errors
                raise
            except Exception as e:
                # Classify and wrap unknown errors
                processing_time = time.time() - start_time
                classified_error = classify_error(e)

                logger.error(
                    "Tool execution failed with unexpected error",
                    tool_name=tool_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    processing_time_ms=round(processing_time * 1000, 2),
                    classified_as=classified_error.error_type.value,
                )

                # Re-raise as classified error
                raise classified_error

        except (
            MCPToolNotFoundError,
            MCPValidationError,
            MCPParameterError,
            MCPServiceError,
            MCPDatabaseError,
            MCPNetworkError,
            MCPTimeoutError,
        ):
            # Re-raise known MCP errors
            raise
        except Exception as e:
            # Handle any remaining unexpected errors
            processing_time = time.time() - start_time
            logger.error(
                "Unexpected error during tool invocation",
                tool_name=tool_name,
                error=str(e),
                error_type=type(e).__name__,
                processing_time_ms=round(processing_time * 1000, 2),
            )
            raise MCPServiceError(
                message=f"Unexpected error during tool invocation: {str(e)}",
                user_message="An unexpected error occurred while processing your request",
            )

    def validate_tool_params(self, tool_name: str, params: Dict[str, Any]) -> None:
        """
        Validate tool parameters against schema

        Args:
            tool_name: Name of the tool
            params: Parameters to validate

        Raises:
            MCPValidationError: If validation fails
        """
        if tool_name not in self.tool_registry:
            raise MCPToolNotFoundError(tool_name)

        tool_schema = self.tool_registry[tool_name]["parameters"]

        try:
            jsonschema.validate(params, tool_schema)
            logger.debug("Parameter validation successful", tool_name=tool_name)

        except ValidationError as e:
            error_msg = f"Parameter validation failed: {e.message}"
            logger.error("Parameter validation error", tool_name=tool_name, error=error_msg)
            raise MCPValidationError(
                message=error_msg,
                user_message=f"Invalid parameters: {e.message}",
                details={"validation_error": str(e)},
            )

    async def _handle_node_knowledge_retriever(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle node knowledge retriever tool invocation with comprehensive error handling

        Args:
            params: Tool parameters

        Returns:
            Tool execution result

        Raises:
            MCPParameterError: If parameters are invalid
            MCPDatabaseError: If database operation fails
            MCPServiceError: If retrieval fails
        """
        start_time = time.time()
        node_names = params.get("node_names", [])
        include_metadata = params.get("include_metadata", False)

        # Enhanced parameter validation
        if not node_names:
            logger.error("Empty node_names parameter provided")
            raise MCPParameterError(
                message="node_names parameter is required and cannot be empty",
                user_message="node_names is required",
                details={"provided_params": params},
            )

        if not isinstance(node_names, list):
            logger.error("Invalid node_names type", node_names_type=type(node_names).__name__)
            raise MCPParameterError(
                message="node_names must be a list",
                user_message="Invalid node_names format",
                details={"expected_type": "list", "actual_type": type(node_names).__name__},
            )

        # Validate individual node names
        invalid_nodes = [
            name for name in node_names if not isinstance(name, str) or not name.strip()
        ]
        if invalid_nodes:
            logger.error("Invalid node names found", invalid_nodes=invalid_nodes)
            raise MCPParameterError(
                message="All node names must be non-empty strings",
                user_message="Invalid node names provided",
                details={"invalid_nodes": invalid_nodes},
            )

        logger.info(
            "Executing node knowledge retrieval",
            node_names=node_names,
            node_count=len(node_names),
            include_metadata=include_metadata,
        )

        try:
            response = await self.node_knowledge_client.retrieve_node_knowledge(
                node_names=node_names, include_metadata=include_metadata
            )

            processing_time = time.time() - start_time

            # Convert response to dict format with enhanced logging
            result = {
                "success": response.success,
                "results": [
                    {
                        "node_name": result.node_name,
                        "knowledge": result.knowledge,
                        "metadata": result.metadata if include_metadata else {},
                        "similarity_score": result.similarity_score,
                    }
                    for result in response.results
                ],
                "total_nodes": response.total_nodes,
                "processing_time_ms": response.processing_time_ms,
            }

            logger.info(
                "Node knowledge retrieval completed successfully",
                requested_nodes=len(node_names),
                returned_results=len(result["results"]),
                total_processing_time_ms=round(processing_time * 1000, 2),
                client_processing_time_ms=response.processing_time_ms,
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)

            logger.error(
                "Node knowledge retrieval failed",
                node_names=node_names,
                error=error_message,
                error_type=type(e).__name__,
                processing_time_ms=round(processing_time * 1000, 2),
            )

            # Classify the error for better handling
            if "database" in error_message.lower() or "supabase" in error_message.lower():
                raise MCPDatabaseError(
                    message=f"Database error during node knowledge retrieval: {error_message}",
                    user_message="Database temporarily unavailable",
                    details={"node_names": node_names, "original_error": error_message},
                )
            elif "network" in error_message.lower() or "connection" in error_message.lower():
                raise MCPNetworkError(
                    message=f"Network error during node knowledge retrieval: {error_message}",
                    user_message="Network connection issue",
                    details={"node_names": node_names, "original_error": error_message},
                )
            elif "timeout" in error_message.lower():
                raise MCPTimeoutError(
                    message=f"Timeout during node knowledge retrieval: {error_message}",
                    user_message="Request timed out",
                    details={"node_names": node_names, "original_error": error_message},
                )
            else:
                raise MCPServiceError(
                    message=f"Node knowledge retrieval failed: {error_message}",
                    user_message="Failed to retrieve node knowledge",
                    details={"node_names": node_names, "original_error": error_message},
                )

    async def _handle_elasticsearch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Elasticsearch tool invocation (placeholder)

        Args:
            params: Tool parameters

        Returns:
            Tool execution result
        """
        index = params.get("index")
        query = params.get("query")

        logger.info("Elasticsearch tool invoked", index=index, query=query)

        # Placeholder implementation
        return {
            "message": "Elasticsearch tool not yet implemented",
            "index": index,
            "query": query,
            "results": [],
            "total_hits": 0,
        }

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        Get information about a specific tool

        Args:
            tool_name: Name of the tool

        Returns:
            Tool information
        """
        if tool_name not in self.tool_registry:
            raise MCPToolNotFoundError(tool_name)

        return self.tool_registry[tool_name]

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the MCP service

        Returns:
            Health status information
        """
        try:
            # Check node knowledge client health
            node_health = self.node_knowledge_client.health_check()

            return {
                "healthy": True,
                "available_tools": list(self.tool_registry.keys()),
                "tool_count": len(self.tool_registry),
                "node_knowledge_client": node_health,
            }

        except Exception as e:
            logger.error("MCP service health check failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
                "available_tools": list(self.tool_registry.keys()),
                "tool_count": len(self.tool_registry),
            }
