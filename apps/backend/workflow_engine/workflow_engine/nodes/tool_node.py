"""
Tool Node Executor.

Handles tool integrations including MCP tools, calendar, email, HTTP tools, etc.
"""

import json
import time
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus
from ..core.audit import get_audit_logger, AuditEventType, AuditSeverity


class ToolNodeExecutor(BaseNodeExecutor):
    """Executor for TOOL_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported tool subtypes."""
        return [
            "MCP",
            "CALENDAR",
            "EMAIL",
            "HTTP",
            "GITHUB"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate tool node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Tool subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "MCP":
            errors.extend(self._validate_required_parameters(node, ["tool_name", "tool_action"]))
        
        elif subtype == "CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["calendar_provider", "action"]))
            provider = node.parameters.get("calendar_provider")
            if provider not in ["google", "outlook", "apple", "generic"]:
                errors.append(f"Unsupported calendar provider: {provider}")
        
        elif subtype == "EMAIL":
            errors.extend(self._validate_required_parameters(node, ["email_provider", "action"]))
            provider = node.parameters.get("email_provider")
            if provider not in ["gmail", "outlook", "smtp", "generic"]:
                errors.append(f"Unsupported email provider: {provider}")
        
        elif subtype == "HTTP":
            errors.extend(self._validate_required_parameters(node, ["url", "method"]))
            method = node.parameters.get("method", "GET")
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute tool node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing tool node with subtype: {subtype}")
            
            if subtype == "MCP":
                return self._execute_mcp_tool(context, logs, start_time)
            elif subtype == "CALENDAR":
                return self._execute_calendar_tool(context, logs, start_time)
            elif subtype == "EMAIL":
                return self._execute_email_tool(context, logs, start_time)
            elif subtype == "HTTP":
                return self._execute_http_tool(context, logs, start_time)
            elif subtype == "GITHUB":
                return self._execute_github_tool(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported tool subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing tool: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_mcp_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute MCP (Model Context Protocol) tool."""
        tool_name = context.get_parameter("tool_name")
        tool_action = context.get_parameter("tool_action")
        tool_parameters = context.get_parameter("tool_parameters", {})
        
        logs.append(f"Executing MCP tool: {tool_name} with action: {tool_action}")
        
        # Simulate MCP tool execution
        mcp_result = self._simulate_mcp_tool_call(tool_name, tool_action, tool_parameters, context.input_data)
        
        output_data = {
            "tool_type": "mcp",
            "tool_name": tool_name,
            "tool_action": tool_action,
            "tool_parameters": tool_parameters,
            "input_data": context.input_data,
            "mcp_result": mcp_result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_calendar_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute calendar tool."""
        calendar_provider = context.get_parameter("calendar_provider")
        action = context.get_parameter("action")
        user_id = context.get_parameter("user_id", "unknown")
        
        logs.append(f"Executing {calendar_provider} calendar tool with action: {action}")
        
        # Get audit logger
        audit_logger = get_audit_logger()
        execution_time = 0
        success = True
        error_message = None
        
        try:
            # Execute calendar action
            if action == "create_event":
                result = self._create_calendar_event(context, calendar_provider)
            elif action == "list_events":
                result = self._list_calendar_events(context, calendar_provider)
            elif action == "update_event":
                result = self._update_calendar_event(context, calendar_provider)
            elif action == "delete_event":
                result = self._delete_calendar_event(context, calendar_provider)
            else:
                success = False
                error_message = f"Unknown calendar action: {action}"
                result = {"error": error_message}
                
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
        except Exception as e:
            success = False
            error_message = str(e)
            execution_time = (time.time() - start_time) * 1000
            result = {"error": error_message}
        
        # Log tool execution for audit
        asyncio.create_task(audit_logger.log_tool_execution(
            tool_type="calendar",
            provider=calendar_provider,
            user_id=user_id,
            execution_time=execution_time / 1000,  # Convert back to seconds for audit
            success=success,
            error_message=error_message,
            details={
                "action": action,
                "input_data_keys": list(context.input_data.keys()) if context.input_data else [],
                "result_keys": list(result.keys()) if isinstance(result, dict) else None
            }
        ))
        
        output_data = {
            "tool_type": "calendar",
            "calendar_provider": calendar_provider,
            "action": action,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_email_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute email tool (implemented as Slack messaging)."""
        provider = context.get_parameter("provider", "slack")
        action = context.get_parameter("action", "send_message")
        
        logs.append(f"Executing {provider} email tool with action: {action}")
        
        try:
            # Import required modules locally to avoid circular imports
            import asyncio
            from workflow_engine.clients.slack_client import SlackClient
            from workflow_engine.services.credential_service import CredentialService
            
            # Execute Slack action (treating as email-like functionality)
            if action == "send_email" or action == "send_message":
                result = asyncio.run(self._send_slack_message_sync(context))
            else:
                result = {"error": f"Unknown email action: {action}. Supported: send_email/send_message"}
            
            output_data = {
                "tool_type": "email",
                "provider": provider,
                "action": action,
                "result": result,
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            logs.append(f"Email tool execution failed: {str(e)}")
            return self._create_error_result(
                f"Email tool execution failed: {str(e)}",
                error_details={"exception": str(e), "provider": provider, "action": action},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_http_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute HTTP tool with real HTTP requests."""
        url = context.get_parameter("url")
        method = context.get_parameter("method", "GET")
        headers = context.get_parameter("headers", {})
        auth_config = context.get_parameter("auth", {})
        
        logs.append(f"Executing HTTP {method} request to {url}")
        
        try:
            # Import HTTPClient locally to avoid circular imports
            from workflow_engine.clients.http_client import HTTPClient
            
            # Create HTTP client
            http_client = HTTPClient()
            
            # Prepare request data
            request_data = context.input_data
            json_data = context.get_parameter("json", None)
            
            # Make HTTP request
            http_result = http_client.request(
                method=method,
                url=url,
                auth_config=auth_config if auth_config else None,
                headers=headers if headers else None,
                data=request_data if request_data else None,
                json_data=json_data if json_data else None
            )
            
            logs.append(f"HTTP request completed with status {http_result.get('status_code')}")
            
            output_data = {
                "tool_type": "http",
                "url": url,
                "method": method,
                "headers": headers,
                "auth_config": auth_config,
                "request_data": request_data,
                "json_data": json_data,
                "http_result": http_result,
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            logs.append(f"HTTP request failed: {str(e)}")
            return self._create_error_result(
                f"HTTP request failed: {str(e)}",
                error_details={"exception": str(e), "url": url, "method": method},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _simulate_mcp_tool_call(self, tool_name: str, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate MCP tool call."""
        # Simulate different MCP tools
        if tool_name == "file_system":
            return self._simulate_file_system_tool(action, parameters, input_data)
        elif tool_name == "database":
            return self._simulate_database_tool(action, parameters, input_data)
        elif tool_name == "web_scraper":
            return self._simulate_web_scraper_tool(action, parameters, input_data)
        elif tool_name == "ai_assistant":
            return self._simulate_ai_assistant_tool(action, parameters, input_data)
        else:
            return {
                "tool_name": tool_name,
                "action": action,
                "parameters": parameters,
                "success": True,
                "result": f"MCP tool {tool_name} executed successfully",
                "data": input_data
            }
    
    def _simulate_file_system_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate file system MCP tool."""
        if action == "read_file":
            return {
                "action": "read_file",
                "file_path": parameters.get("file_path", ""),
                "content": "Simulated file content",
                "size": 1024,
                "success": True
            }
        elif action == "write_file":
            return {
                "action": "write_file",
                "file_path": parameters.get("file_path", ""),
                "content": input_data.get("content", ""),
                "bytes_written": len(input_data.get("content", "")),
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown file system action"}
    
    def _simulate_database_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate database MCP tool."""
        if action == "query":
            return {
                "action": "query",
                "query": parameters.get("query", ""),
                "results": [
                    {"id": 1, "name": "Item 1", "value": 100},
                    {"id": 2, "name": "Item 2", "value": 200}
                ],
                "row_count": 2,
                "success": True
            }
        elif action == "insert":
            return {
                "action": "insert",
                "table": parameters.get("table", ""),
                "data": input_data,
                "inserted_id": 123,
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown database action"}
    
    def _simulate_web_scraper_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate web scraper MCP tool."""
        if action == "scrape_url":
            return {
                "action": "scrape_url",
                "url": parameters.get("url", ""),
                "scraped_data": {
                    "title": "Sample Page Title",
                    "content": "Sample page content",
                    "links": ["https://example.com/link1", "https://example.com/link2"]
                },
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown web scraper action"}
    
    def _simulate_ai_assistant_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate AI assistant MCP tool."""
        if action == "generate_text":
            return {
                "action": "generate_text",
                "prompt": parameters.get("prompt", ""),
                "generated_text": "This is simulated AI-generated text based on the prompt.",
                "model": parameters.get("model", "gpt-4"),
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown AI assistant action"}
    
    def _create_calendar_event(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Create calendar event."""
        title = context.input_data.get("title", "New Event")
        start_time = context.input_data.get("start_time", datetime.now().isoformat())
        duration = context.input_data.get("duration", 60)  # minutes
        
        return {
            "action": "create_event",
            "provider": provider,
            "event": {
                "id": f"event_{int(time.time())}",
                "title": title,
                "start_time": start_time,
                "duration": duration,
                "created_at": datetime.now().isoformat()
            },
            "success": True
        }
    
    def _list_calendar_events(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """List calendar events."""
        start_date = context.input_data.get("start_date", datetime.now().isoformat())
        end_date = context.input_data.get("end_date", datetime.now().isoformat())
        
        return {
            "action": "list_events",
            "provider": provider,
            "date_range": {"start": start_date, "end": end_date},
            "events": [
                {
                    "id": "event_1",
                    "title": "Meeting 1",
                    "start_time": "2024-01-15T10:00:00Z",
                    "duration": 60
                },
                {
                    "id": "event_2",
                    "title": "Meeting 2", 
                    "start_time": "2024-01-15T14:00:00Z",
                    "duration": 30
                }
            ],
            "success": True
        }
    
    def _update_calendar_event(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Update calendar event."""
        event_id = context.input_data.get("event_id", "")
        updates = context.input_data.get("updates", {})
        
        return {
            "action": "update_event",
            "provider": provider,
            "event_id": event_id,
            "updates": updates,
            "updated_at": datetime.now().isoformat(),
            "success": True
        }
    
    def _delete_calendar_event(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Delete calendar event."""
        event_id = context.input_data.get("event_id", "")
        
        return {
            "action": "delete_event",
            "provider": provider,
            "event_id": event_id,
            "deleted_at": datetime.now().isoformat(),
            "success": True
        }
    
    def _send_email(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Send email."""
        recipient = context.input_data.get("recipient", "")
        subject = context.input_data.get("subject", "")
        body = context.input_data.get("body", "")
        
        return {
            "action": "send_email",
            "provider": provider,
            "email": {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "message_id": f"msg_{int(time.time())}",
                "sent_at": datetime.now().isoformat()
            },
            "success": True
        }
    
    def _read_emails(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Read emails."""
        limit = context.input_data.get("limit", 10)
        
        return {
            "action": "read_emails",
            "provider": provider,
            "emails": [
                {
                    "id": "email_1",
                    "subject": "Test Email 1",
                    "sender": "sender1@example.com",
                    "received_at": "2024-01-15T10:00:00Z"
                },
                {
                    "id": "email_2",
                    "subject": "Test Email 2",
                    "sender": "sender2@example.com",
                    "received_at": "2024-01-15T11:00:00Z"
                }
            ],
            "count": 2,
            "limit": limit,
            "success": True
        }
    
    def _search_emails(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Search emails."""
        query = context.input_data.get("query", "")
        
        return {
            "action": "search_emails",
            "provider": provider,
            "query": query,
            "results": [
                {
                    "id": "email_search_1",
                    "subject": "Search Result 1",
                    "sender": "search1@example.com",
                    "snippet": "This email matches your search query",
                    "received_at": "2024-01-15T09:00:00Z"
                }
            ],
            "count": 1,
            "success": True
        }
    
    def _delete_email(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Delete email."""
        email_id = context.input_data.get("email_id", "")
        
        return {
            "action": "delete_email",
            "provider": provider,
            "email_id": email_id,
            "deleted_at": datetime.now().isoformat(),
            "success": True
        }
    
    async def _send_slack_message_sync(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Send Slack message (async helper method)."""
        from workflow_engine.clients.slack_client import SlackClient
        from workflow_engine.services.credential_service import CredentialService
        
        # Get credentials for Slack
        credential_service = CredentialService()
        user_id = context.get_parameter("user_id", "default_user")
        credentials = await credential_service.get_credential(user_id, "slack")
        
        if not credentials:
            raise Exception("Slack credentials not found")
        
        # Create Slack client
        slack_client = SlackClient(credentials)
        
        # Get message parameters
        channel = context.get_parameter("channel", context.input_data.get("recipient", "#general"))
        message = context.input_data.get("message", context.input_data.get("body", ""))
        subject = context.input_data.get("subject", "")
        
        # Format message (add subject if provided)
        if subject:
            formatted_message = f"**{subject}**\n{message}"
        else:
            formatted_message = message
        
        # Send Slack message
        result = await slack_client.send_message(channel, formatted_message)
        
        # Format response to match email-like structure
        return {
            "action": "send_message",
            "channel": channel,
            "message": formatted_message,
            "slack_response": result,
            "sent_at": datetime.now().isoformat(),
            "success": result.get("ok", False)
        }
    
    def _execute_github_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute GitHub tool with real GitHub API calls."""
        import asyncio
        
        action = context.get_parameter("action")
        repository = context.get_parameter("repository")
        user_id = context.get_parameter("user_id", "unknown")
        
        logs.append(f"Executing GitHub {action} on repository {repository}")
        
        # Get audit logger
        audit_logger = get_audit_logger()
        execution_time = 0
        success = True
        error_message = None
        
        try:
            # Execute GitHub action asynchronously
            result = asyncio.run(self._execute_github_action_sync(context, action, repository))
            execution_time = (time.time() - start_time) * 1000
            
            output_data = {
                "tool_type": "github",
                "repository": repository,
                "action": action,
                "result": result,
                "executed_at": datetime.now().isoformat()
            }
            
            # Log tool execution for audit
            asyncio.create_task(audit_logger.log_tool_execution(
                tool_type="github",
                provider="github",
                user_id=user_id,
                execution_time=execution_time / 1000,
                success=success,
                error_message=error_message,
                details={
                    "action": action,
                    "repository": repository,
                    "input_data_keys": list(context.input_data.keys()) if context.input_data else [],
                    "result_keys": list(result.keys()) if isinstance(result, dict) else None
                }
            ))
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            success = False
            error_message = str(e)
            execution_time = (time.time() - start_time) * 1000
            
            logs.append(f"GitHub tool execution failed: {error_message}")
            
            # Log tool execution failure for audit
            asyncio.create_task(audit_logger.log_tool_execution(
                tool_type="github",
                provider="github",
                user_id=user_id,
                execution_time=execution_time / 1000,
                success=success,
                error_message=error_message,
                details={
                    "action": action,
                    "repository": repository,
                    "exception_type": type(e).__name__
                }
            ))
            
            return self._create_error_result(
                f"GitHub tool execution failed: {error_message}",
                error_details={"exception": error_message, "repository": repository, "action": action},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    async def _execute_github_action_sync(self, context: NodeExecutionContext, action: str, repository: str) -> Dict[str, Any]:
        """Execute GitHub action (async helper method)."""
        from workflow_engine.clients.github_client import GitHubClient
        from workflow_engine.services.credential_service import CredentialService
        
        # Get credentials for GitHub
        credential_service = CredentialService()
        user_id = context.get_parameter("user_id", "default_user")
        credentials = await credential_service.get_credential(user_id, "github")
        
        if not credentials:
            raise Exception("GitHub credentials not found")
        
        # Create GitHub client
        github_client = GitHubClient(credentials)
        
        # Execute GitHub action based on action type
        if action == "create_issue":
            title = context.input_data.get("title", "New Issue")
            body = context.input_data.get("body", "")
            labels = context.input_data.get("labels", [])
            assignees = context.input_data.get("assignees", [])
            
            result = await github_client.create_issue(
                repo=repository,
                title=title,
                body=body,
                labels=labels,
                assignees=assignees
            )
            
        elif action == "create_pull_request":
            title = context.input_data.get("title", "New Pull Request")
            head = context.input_data.get("head", context.input_data.get("branch", "feature/new-feature"))
            base = context.input_data.get("base", "main")
            body = context.input_data.get("body", "")
            draft = context.input_data.get("draft", False)
            
            result = await github_client.create_pull_request(
                repo=repository,
                title=title,
                head=head,
                base=base,
                body=body,
                draft=draft
            )
            
        elif action == "get_repository_info":
            result = await github_client.get_repository_info(repository)
            
        elif action == "create_file":
            path = context.input_data.get("path", context.input_data.get("file_path"))
            content = context.input_data.get("content", "")
            message = context.input_data.get("message", context.input_data.get("commit_message", "Create file"))
            branch = context.input_data.get("branch", "main")
            
            if not path:
                raise Exception("File path is required for create_file action")
            
            result = await github_client.create_file(
                repo=repository,
                path=path,
                content=content,
                message=message,
                branch=branch
            )
            
        elif action == "update_file":
            path = context.input_data.get("path", context.input_data.get("file_path"))
            content = context.input_data.get("content", "")
            message = context.input_data.get("message", context.input_data.get("commit_message", "Update file"))
            sha = context.input_data.get("sha")
            branch = context.input_data.get("branch", "main")
            
            if not path:
                raise Exception("File path is required for update_file action")
            if not sha:
                raise Exception("File SHA is required for update_file action")
            
            result = await github_client.update_file(
                repo=repository,
                path=path,
                content=content,
                message=message,
                sha=sha,
                branch=branch
            )
            
        elif action == "get_file_content":
            path = context.input_data.get("path", context.input_data.get("file_path"))
            branch = context.input_data.get("branch", "main")
            
            if not path:
                raise Exception("File path is required for get_file_content action")
            
            result = await github_client.get_file_content(
                repo=repository,
                path=path,
                branch=branch
            )
            
        elif action == "search_repositories":
            query = context.input_data.get("query", "")
            limit = context.input_data.get("limit", 10)
            sort = context.input_data.get("sort", "updated")
            
            if not query:
                raise Exception("Search query is required for search_repositories action")
            
            result = await github_client.search_repositories(
                query=query,
                limit=limit,
                sort=sort
            )
            
        elif action == "list_issues":
            state = context.input_data.get("state", "open")
            limit = context.input_data.get("limit", 30)
            
            result = await github_client.list_repository_issues(
                repo=repository,
                state=state,
                limit=limit
            )
            
        else:
            raise Exception(f"Unknown GitHub action: {action}")
        
        # Close the client
        await github_client.close()
        
        return {
            "action": action,
            "repository": repository,
            "github_response": result,
            "success": True
        }
    
