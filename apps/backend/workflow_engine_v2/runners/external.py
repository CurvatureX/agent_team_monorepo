"""External action runners (Slack, GitHub, etc.) with dedicated implementations."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import ExecutionStatus, TriggerInfo
from shared.models.node_enums import ExternalActionSubtype
from shared.models.workflow_new import Node

from ..core.context import NodeExecutionContext
from ..services.http_client import HTTPClient
from .base import NodeRunner
from .external_actions.github_external_action import GitHubExternalAction
from .external_actions.google_calendar_external_action import GoogleCalendarExternalAction
from .external_actions.notion_external_action import NotionExternalAction

# Import dedicated external action handlers
from .external_actions.slack_external_action import SlackExternalAction


class ExternalActionRunner(NodeRunner):
    def __init__(self):
        # Initialize dedicated handlers
        self.slack_handler = SlackExternalAction()
        self.github_handler = GitHubExternalAction()
        self.google_handler = GoogleCalendarExternalAction()
        self.notion_handler = NotionExternalAction()

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        try:
            esub = ExternalActionSubtype(str(node.subtype))
        except Exception:
            esub = None

        # Create execution context
        # Extract user_id from trigger information
        user_id = getattr(trigger, "user_id", None) if trigger else None

        # Add debug logging
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"🔍 EXTERNAL ACTION DEBUG: trigger={trigger}")
        logger.info(f"🔍 EXTERNAL ACTION DEBUG: user_id={user_id}")

        metadata = {"user_id": user_id} if user_id else {}

        context = NodeExecutionContext(
            node=node,
            input_data=inputs.get("main", {}) if isinstance(inputs.get("main"), dict) else {},
            trigger=trigger,
            metadata=metadata,
        )

        # Get action_type from configurations - required for external actions
        action_type = node.configurations.get("action_type")

        # Route to dedicated handlers for OAuth-based integrations
        if esub == ExternalActionSubtype.SLACK:
            if not action_type:
                return {"error": {"message": "Missing required parameter: action_type"}}
            return self._run_async_handler(
                self.slack_handler.handle_operation(context, action_type)
            )

        elif esub == ExternalActionSubtype.GITHUB:
            if not action_type:
                return {"error": {"message": "Missing required parameter: action_type"}}
            return self._run_async_handler(
                self.github_handler.handle_operation(context, action_type)
            )

        elif esub == ExternalActionSubtype.GOOGLE_CALENDAR:
            if not action_type:
                return {"error": {"message": "Missing required parameter: action_type"}}
            return self._run_async_handler(
                self.google_handler.handle_operation(context, action_type)
            )

        elif esub == ExternalActionSubtype.NOTION:
            if not action_type:
                return {"error": {"message": "Missing required parameter: action_type"}}
            return self._run_async_handler(
                self.notion_handler.handle_operation(context, action_type)
            )

        # Fallback to original implementations for backward compatibility
        return self._run_legacy_action(node, inputs, trigger, esub)

    def _run_async_handler(self, coro) -> Dict[str, Any]:
        """Run async handler and convert result to dict format."""
        try:
            # Run the async handler
            result = asyncio.run(coro)

            if result.status == ExecutionStatus.SUCCESS:
                return result.output_data
            else:
                return {
                    "error": {
                        "message": result.error_message,
                        "details": result.error_details,
                        "status": result.status.value,
                    }
                }
        except Exception as e:
            return {"error": {"message": f"External action failed: {str(e)}"}}

    def _run_legacy_action(
        self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo, esub
    ) -> Dict[str, Any]:
        """Run legacy external action implementations for backward compatibility."""
        cfg = node.configurations or {}
        payload = inputs.get("main", {}) if isinstance(inputs.get("main"), dict) else {}

        # Email external action - send via webhook or API
        if esub == ExternalActionSubtype.EMAIL:
            url = cfg.get("url") or (cfg.get("webhook_url"))
            if not url:
                return {"error": {"message": "Missing URL/webhook_url for EMAIL external action"}}
            try:
                from ..core.template import render_template

                engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
                tctx = {
                    "input": payload,
                    "config": cfg,
                    "nodes_id": getattr(engine_ctx, "node_outputs", {}) if engine_ctx else {},
                    "nodes_name": getattr(engine_ctx, "node_outputs_by_name", {})
                    if engine_ctx
                    else {},
                }
                subject = payload.get("subject") or cfg.get("subject")
                text = payload.get("text") or cfg.get("text")
                html = payload.get("html") or cfg.get("html")
                if isinstance(subject, str) and "{{" in subject:
                    subject = render_template(subject, tctx)
                if isinstance(text, str) and "{{" in text:
                    text = render_template(text, tctx)
                if isinstance(html, str) and "{{" in html:
                    html = render_template(html, tctx)
                body = {
                    "to": payload.get("to") or cfg.get("to"),
                    "subject": subject,
                    "text": text,
                    "html": html,
                }
                client = HTTPClient()
                try:
                    resp = client.request("POST", url, json_body=body, headers=cfg.get("headers"))
                    return {
                        "main": {
                            "status_code": resp.status_code,
                            "json": resp.json,
                            "success": 200 <= resp.status_code < 300,
                        }
                    }
                except Exception as e:
                    return {"error": {"message": str(e)}}
                finally:
                    client.close()
            except ImportError:
                return {"error": {"message": "Template rendering not available"}}

        # Default: generic API call described in config
        method = str(cfg.get("method", "GET"))
        url = cfg.get("url")
        if url:
            client = HTTPClient()
            try:
                resp = client.request(
                    method,
                    url,
                    headers=cfg.get("headers"),
                    params=cfg.get("query"),
                    json_body=payload or cfg.get("body"),
                )
                return {
                    "main": {
                        "status_code": resp.status_code,
                        "json": resp.json,
                        "success": 200 <= resp.status_code < 300,
                    }
                }
            except Exception as e:
                return {"error": {"message": str(e)}}
            finally:
                client.close()

        return {
            "error": {
                "message": f"Unsupported EXTERNAL_ACTION subtype or missing configuration: {esub}"
            }
        }


__all__ = ["ExternalActionRunner"]
