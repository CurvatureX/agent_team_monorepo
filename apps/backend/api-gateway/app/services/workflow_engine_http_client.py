"""
HTTP Client for Workflow Engine Service
Replaces the gRPC client with HTTP/FastAPI calls
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import get_settings
from app.utils.logger import log_error, log_info

settings = get_settings()


class WorkflowEngineHTTPClient:
    """
    HTTP client for the Workflow Engine FastAPI service
    Replaces the gRPC WorkflowService interface with HTTP calls
    """

    def __init__(self):
        # Always use Workflow Engine V2 (V1 is deprecated and removed)
        self.base_url = settings.workflow_engine_http_url  # Port 8002 runs Workflow Engine V2
        self._api_prefix = "/v2"  # V2 API prefix
        # Separate timeouts for different operations
        self.connect_timeout = httpx.Timeout(5.0, connect=5.0)
        self.execute_timeout = httpx.Timeout(
            300.0, connect=5.0
        )  # 5 minutes for long-running workflows
        self.query_timeout = httpx.Timeout(60.0, connect=5.0)  # Longer timeout for queries
        self.logs_timeout = httpx.Timeout(90.0, connect=5.0)  # Extra long timeout for logs queries
        self.connected = False
        # Connection pool for better performance
        self._client = None
        self._limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.connect_timeout,
                limits=self._limits,
                http2=True,  # Enable HTTP/2 for multiplexing
            )
        return self._client

    async def connect(self):
        """Test connection to workflow engine service"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            self.connected = True
            log_info(f"✅ Connected to Workflow Engine at {self.base_url}")
        except Exception as e:
            log_error(f"❌ Failed to connect to Workflow Engine at {self.base_url}: {e}")
            self.connected = False
            raise

    async def close(self):
        """Close HTTP connection and client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self.connected = False
        log_info("Closed Workflow Engine HTTP connection")

    async def list_all_node_templates(
        self,
        category_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        include_system_templates: bool = True,
    ) -> List[Dict[str, Any]]:
        """List all available node templates via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            # Prepare query parameters
            params = {"include_system_templates": include_system_templates}
            if category_filter:
                params["category_filter"] = category_filter
            if type_filter:
                params["type_filter"] = type_filter

            log_info(
                f"📨 HTTP request to {self.base_url}{self._api_prefix}/workflows/node-templates"
            )

            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}{self._api_prefix}/workflows/node-templates", params=params
            )
            response.raise_for_status()

            data = response.json()
            # The workflow engine returns the array directly
            templates = data if isinstance(data, list) else data.get("node_templates", [])
            log_info(f"✅ Retrieved {len(templates)} node templates")
            return templates

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error listing node templates: {e.response.status_code}")
            return []
        except Exception as e:
            log_error(f"❌ Error listing node templates: {e}")
            return []

    async def create_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        nodes: List[Dict[str, Any]] = None,
        connections: Dict[str, Any] = None,
        settings: Optional[Dict[str, Any]] = None,
        static_data: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        user_id: str = "anonymous",
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        icon_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            # Convert settings to dict if it's an object
            settings_dict = settings or {}
            if hasattr(settings, "model_dump"):
                settings_dict = settings.model_dump()
            elif hasattr(settings, "dict"):
                settings_dict = settings.dict()
            elif hasattr(settings, "__dict__"):
                settings_dict = settings.__dict__

            log_info(f"📨 HTTP request to create workflow: {name}")

            headers = {}
            if trace_id:
                headers["X-Trace-ID"] = trace_id

            # Convert to v2 creation payload (using spec-driven server-side instance creation)
            v2_nodes: List[Dict[str, Any]] = []
            for nd in nodes or []:
                converted_node = {
                    "id": nd.get("id") or nd.get("name"),
                    "name": nd.get("name"),
                    "description": nd.get("description", ""),  # Required field
                    "type": nd.get("type"),
                    "subtype": nd.get("subtype"),
                    "position": nd.get("position"),
                    # map parameters -> configurations for v2
                    # Support both 'configurations' (new format) and 'parameters' (legacy format)
                    "configurations": nd.get("configurations") or nd.get("parameters", {}),
                    # Support both formats for input/output params and ports
                    "input_params": nd.get("input_params", {}),
                    "output_params": nd.get("output_params", {}),
                    "input_ports": nd.get("input_ports", []),
                    "output_ports": nd.get("output_ports", []),
                    # attach list if present in UI payload
                    "attached_nodes": nd.get("attached_nodes"),
                }
                v2_nodes.append(converted_node)

            def _convert_connections(conn_input: Any) -> List[Dict[str, str]]:
                """Convert connections to v2 format - handles both list and dict formats"""
                result: List[Dict[str, str]] = []

                # If connections is already a list (new format), pass through with validation
                if isinstance(conn_input, list):
                    for conn in conn_input:
                        if isinstance(conn, dict) and "from_node" in conn and "to_node" in conn:
                            result.append(
                                {
                                    "id": conn.get("id", f"{conn['from_node']}->{conn['to_node']}"),
                                    "from_node": conn["from_node"],
                                    "to_node": conn["to_node"],
                                    "from_port": conn.get("from_port", "main"),
                                    "to_port": conn.get("to_port", "main"),
                                    "conversion_function": conn.get("conversion_function"),
                                }
                            )
                    return result

                # Legacy dict format (n8n-style)
                if not isinstance(conn_input, dict):
                    return result
                for src, node_conns in conn_input.items():
                    ctypes = (
                        (node_conns or {}).get("connection_types", {})
                        if isinstance(node_conns, dict)
                        else {}
                    )
                    for from_port, arr in ctypes.items():
                        conns = (arr or {}).get("connections", []) if isinstance(arr, dict) else []
                        for idx, c in enumerate(conns):
                            if not isinstance(c, dict):
                                continue
                            tgt = c.get("node")
                            to_port = c.get("type", "main")
                            if not tgt:
                                continue
                            result.append(
                                {
                                    "id": f"{src}:{from_port}->{tgt}:{to_port}:{idx}",
                                    "from_node": src,
                                    "to_node": tgt,
                                    "from_port": from_port,
                                    "to_port": to_port,
                                }
                            )
                return result

            v2_payload = {
                "workflow_id": str(uuid.uuid4()),  # Always generate a fresh UUID
                "name": name,
                "created_by": user_id,
                "created_time_ms": int(time.time() * 1000),
                "nodes": v2_nodes,
                "connections": _convert_connections(connections or []),
                "triggers": [
                    n.get("id") or n.get("name") for n in v2_nodes if (n.get("type") == "TRIGGER")
                ],
            }

            # Preserve optional metadata fields for the workflow engine to stitch in later
            if description:
                v2_payload["description"] = description
            if tags:
                v2_payload["tags"] = tags
            if static_data:
                v2_payload["static_data"] = static_data
            if session_id:
                v2_payload["session_id"] = session_id
            if icon_url:
                v2_payload["icon_url"] = icon_url
            if settings_dict:
                v2_payload["settings"] = settings_dict

            # Use dedicated client with query_timeout for create operations
            # Complex workflows with many nodes need longer processing time
            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.post(
                    f"{self.base_url}{self._api_prefix}/workflows", json=v2_payload, headers=headers
                )
                response.raise_for_status()

            data = response.json()
            log_info(f"✅ Created workflow: {data.get('workflow', {}).get('id', 'unknown')}")
            return data

        except httpx.HTTPStatusError as e:
            error_details = ""
            try:
                error_details = e.response.text
            except:
                pass
            log_error(f"❌ HTTP error creating workflow: {e.response.status_code}")
            log_error(f"🐛 DEBUG: Error response: {error_details}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error creating workflow: {e}")
            return {"success": False, "error": str(e)}

    async def get_workflow(self, workflow_id: str, access_token: str) -> Dict[str, Any]:
        """Get workflow by ID via HTTP using JWT token for RLS"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to get workflow: {workflow_id}")

            # Use individual client with proper timeout
            headers = {"Authorization": f"Bearer {access_token}"}
            path = f"{self._api_prefix}/workflows/{workflow_id}"

            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.get(f"{self.base_url}{path}", headers=headers)
                response.raise_for_status()
                data = response.json()

                # Debug: Check the type of data returned
                log_info(
                    f"🐛 DEBUG HTTP Client: data type = {type(data)}, is_dict = {isinstance(data, dict)}"
                )
                if isinstance(data, str):
                    log_info(
                        f"🐛 DEBUG HTTP Client: data is a string, length = {len(data)}, first 100 chars = {data[:100]}"
                    )
                elif isinstance(data, dict):
                    log_info(f"🐛 DEBUG HTTP Client: data keys = {list(data.keys())}")

                log_info(f"✅ Retrieved workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting workflow: {e.response.status_code}")
            try:
                error_details = e.response.text
                log_error(f"🐛 DEBUG: Response body: {error_details}")
            except:
                pass
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error getting workflow: {e}")
            log_error(f"🐛 DEBUG: Exception type: {type(e).__name__}")
            log_error(f"🐛 DEBUG: Exception args: {e.args}")
            return {"success": False, "error": str(e)}

    async def execute_workflow(
        self,
        workflow_id: str,
        user_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        start_from_node: Optional[str] = None,
        skip_trigger_validation: bool = False,
        access_token: Optional[str] = None,
        async_execution: bool = True,  # Default to async to prevent timeouts
    ) -> Dict[str, Any]:
        """Execute workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            headers = {}
            if trace_id:
                headers["X-Trace-ID"] = trace_id
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            # Use appropriate timeout for async vs sync execution
            # Async execution should return immediately with execution_id, so use short timeout
            timeout = httpx.Timeout(10.0, connect=5.0) if async_execution else self.execute_timeout

            log_info(
                f"📨 HTTP request to execute workflow: {workflow_id} (async: {async_execution})"
            )

            # Use pooled client for better connection handling
            client = await self._get_client()

            # Time the HTTP request to debug performance
            import time

            start_time = time.time()

            v2_payload: Dict[str, Any] = {
                "trigger_type": "manual",
                "trigger_data": input_data or {},
                "async_execution": async_execution,
            }
            if trace_id:
                v2_payload["trace_id"] = trace_id
            if start_from_node:
                v2_payload["start_from_node"] = start_from_node
                v2_payload["skip_trigger_validation"] = skip_trigger_validation
            if user_id:
                v2_payload["user_id"] = user_id

            response = await client.post(
                f"{self.base_url}{self._api_prefix}/workflows/{workflow_id}/execute",
                json=v2_payload,
                headers=headers,
                timeout=timeout,
            )

            end_time = time.time()
            response_time = end_time - start_time

            response.raise_for_status()

            data = response.json()
            log_info(
                f"✅ Executed workflow: {workflow_id} (execution_id: {data.get('execution_id', 'N/A')}) - HTTP response time: {response_time:.2f}s"
            )
            return data

        except httpx.HTTPStatusError as e:
            error_details = f"HTTP {e.response.status_code}"
            try:
                response_text = e.response.text
                if response_text:
                    error_details += f" - Response: {response_text[:500]}"  # Limit response text
            except Exception as text_error:
                error_details += (
                    f" - Failed to read response: {type(text_error).__name__}: {str(text_error)}"
                )
                # Add full traceback for response text reading issues
                import traceback

                log_error(f"🐛 Response text read error traceback: {traceback.format_exc()}")
            log_error(f"❌ HTTP error executing workflow: {error_details}")
            return {"success": False, "error": error_details}
        except httpx.TimeoutException as e:
            error_details = f"Timeout error: {type(e).__name__} - {str(e)}"
            log_error(f"❌ Timeout executing workflow: {error_details}")
            return {"success": False, "error": error_details}
        except Exception as e:
            error_details = f"{type(e).__name__}: {str(e)}"
            log_error(f"❌ Error executing workflow: {error_details}")
            # Add more detailed logging for debugging
            import traceback

            log_error(f"🐛 Full exception traceback: {traceback.format_exc()}")
            return {"success": False, "error": error_details}

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            # Use DEBUG level for frequent polling operations
            import logging

            logging.getLogger(__name__).debug(
                f"📨 HTTP request to get execution status: {execution_id}"
            )

            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.get(
                    f"{self.base_url}{self._api_prefix}/executions/{execution_id}"
                )
                response.raise_for_status()

                data = response.json()
                logging.getLogger(__name__).debug(f"✅ Retrieved execution status: {execution_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting execution status: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error getting execution status: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """Cancel execution via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to cancel execution: {execution_id}")

            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.post(f"{self.base_url}/v2/executions/{execution_id}/cancel")
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Cancelled execution: {execution_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error cancelling execution: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error cancelling execution: {e}")
            return {"success": False, "error": str(e)}

    async def get_execution_history(
        self, workflow_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution history for a workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to get execution history: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.get(
                    f"{self.base_url}{self._api_prefix}/workflows/{workflow_id}/executions",
                    params={"limit": limit},
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Retrieved execution history: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting execution history: {e.response.status_code}")
            return []
        except Exception as e:
            log_error(f"❌ Error getting execution history: {e}")
            return []

    async def update_workflow(
        self,
        workflow_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        connections: Optional[Dict[str, Any]] = None,
        triggers: Optional[List[str]] = None,
        settings: Optional[Dict[str, Any]] = None,
        static_data: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            # Build update data - only include non-None values
            update_data = {"user_id": user_id, "workflow_id": workflow_id}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if nodes is not None:
                update_data["nodes"] = nodes
            if connections is not None:
                update_data["connections"] = connections
            if triggers is not None:
                update_data["triggers"] = triggers
            if settings is not None:
                update_data["settings"] = settings
            if static_data is not None:
                update_data["static_data"] = static_data
            if tags is not None:
                update_data["tags"] = tags
            if active is not None:
                update_data["active"] = active

            log_info(f"📨 HTTP request to update workflow: {workflow_id}")
            log_info(f"📦 Update data: {update_data}")

            # Debug log the exact request
            import json

            log_info(f"🐛 DEBUG: Update request JSON: {json.dumps(update_data, indent=2)}")
            log_info(f"🐛 DEBUG: URL: {self.base_url}{self._api_prefix}/workflows/{workflow_id}")

            # Use dedicated client with query_timeout for update operations
            # Complex workflows with many nodes need longer processing time
            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.put(
                    f"{self.base_url}{self._api_prefix}/workflows/{workflow_id}", json=update_data
                )

            # Log response details before checking status
            log_info(f"🐛 DEBUG: Response status: {response.status_code}")
            if response.status_code != 200:
                log_error(f"🐛 DEBUG: Response body: {response.text}")

            response.raise_for_status()

            data = response.json()
            log_info(f"✅ Updated workflow: {workflow_id}")
            return data

        except httpx.HTTPStatusError as e:
            error_details = ""
            try:
                error_details = e.response.text
                error_json = e.response.json()
                log_error(f"🐛 DEBUG: Error JSON: {json.dumps(error_json, indent=2)}")
            except:
                pass
            log_error(f"❌ HTTP error updating workflow: {e.response.status_code}")
            log_error(f"🐛 DEBUG: Error response: {error_details}")
            return {"success": False, "error": f"HTTP {e.response.status_code}: {error_details}"}
        except Exception as e:
            log_error(f"❌ Error updating workflow: {e}")
            log_error(f"🐛 DEBUG: Exception type: {type(e).__name__}")
            return {"success": False, "error": str(e)}

    async def delete_workflow(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """Delete workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to delete workflow: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.delete(
                    f"{self.base_url}{self._api_prefix}/workflows/{workflow_id}",
                    params={"user_id": user_id},
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Deleted workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error deleting workflow: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error deleting workflow: {e}")
            return {"success": False, "error": str(e)}

    async def list_workflows(
        self,
        access_token: str,
        active_only: bool = False,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List workflows via HTTP using JWT token for RLS"""
        if not self.connected:
            await self.connect()

        try:
            # Build query parameters (no user_id needed - RLS handles filtering)
            params = {
                "active_only": active_only,
                "limit": limit,
                "offset": offset,
            }
            if tags:
                params["tags"] = ",".join(tags)

            # Set up headers with JWT token for RLS
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            log_info(f"📨 HTTP request to list workflows using RLS")

            async with httpx.AsyncClient(timeout=self.query_timeout) as client:
                response = await client.get(
                    f"{self.base_url}{self._api_prefix}/workflows", params=params, headers=headers
                )
                response.raise_for_status()
                data = response.json()
                log_info(f"✅ Listed workflows using RLS")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error listing workflows: {e.response.status_code}")
            try:
                error_details = e.response.text
                log_error(f"🐛 DEBUG: Response body: {error_details}")
            except:
                pass
            return {"workflows": [], "total_count": 0, "has_more": False}
        except Exception as e:
            log_error(f"❌ Error listing workflows: {e}")
            log_error(f"🐛 DEBUG: Exception type: {type(e).__name__}")
            log_error(f"🐛 DEBUG: Exception args: {e.args}")
            return {"workflows": [], "total_count": 0, "has_more": False}

    async def get_execution_logs(
        self, execution_id: str, access_token: str = None, params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Get execution logs from database with user access control"""
        try:
            # Use DEBUG level for frequent polling operations
            import logging

            logging.getLogger(__name__).debug(f"📋 Getting execution logs for: {execution_id}")

            client = await self._get_client()
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            # Build query parameters
            query_params = {}
            if params:
                for key, value in params.items():
                    if value is not None:
                        query_params[key] = value

            response = await client.get(
                f"{self.base_url}{self._api_prefix}/workflows/executions/{execution_id}/logs",
                headers=headers,
                params=query_params,
                timeout=self.logs_timeout,  # Use dedicated logs timeout (90s)
            )
            response.raise_for_status()
            result = response.json()

            logging.getLogger(__name__).debug(f"✅ Retrieved execution logs for {execution_id}")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log_info(f"📭 No logs found for execution {execution_id}")
                return {"execution_id": execution_id, "logs": [], "total_count": 0}
            else:
                log_error(
                    f"HTTP error getting execution logs {execution_id}: {e.response.status_code} - {e.response.text}"
                )
                return {"execution_id": execution_id, "logs": [], "total_count": 0}
        except Exception as e:
            error_details = f"{type(e).__name__}: {str(e)}"
            log_error(f"Error getting execution logs {execution_id}: {error_details}")
            # Add traceback for debugging
            import traceback

            log_error(f"🐛 Full exception traceback: {traceback.format_exc()}")
            return {"execution_id": execution_id, "logs": [], "total_count": 0}

    async def stream_execution_logs(self, execution_id: str, access_token: str = None):
        """Stream real-time execution logs"""
        import json

        try:
            log_info(f"📡 Starting log stream for execution: {execution_id}")

            client = await self._get_client()
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            # Connect to the streaming endpoint
            async with client.stream(
                "GET",
                f"{self.base_url}{self._api_prefix}/executions/{execution_id}/logs/stream",
                headers=headers,
                timeout=httpx.Timeout(connect=5.0, read=None),  # No read timeout for streaming
            ) as response:
                response.raise_for_status()

                async for chunk in response.aiter_text():
                    if chunk.strip():
                        try:
                            # Parse SSE event
                            if chunk.startswith("data: "):
                                data_part = chunk[6:].strip()
                                if data_part and data_part != "[DONE]":
                                    log_data = json.loads(data_part)
                                    yield log_data
                        except json.JSONDecodeError:
                            # Skip malformed JSON
                            continue

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log_info(f"📭 Execution {execution_id} not found for streaming")
                return
            else:
                log_error(
                    f"HTTP error streaming execution logs {execution_id}: {e.response.status_code}"
                )
                raise
        except Exception as e:
            log_error(f"Error streaming execution logs {execution_id}: {e}")
            raise


# Global HTTP client instance
workflow_engine_client = WorkflowEngineHTTPClient()


async def get_workflow_engine_client() -> WorkflowEngineHTTPClient:
    """Get workflow engine HTTP client instance"""
    return workflow_engine_client
