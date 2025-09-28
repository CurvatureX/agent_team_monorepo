"""Action node runners (e.g., HTTP_REQUEST, DATA_TRANSFORMATION)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

import re

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.workflow_new import Node

from ..core.expr import get_path
from ..core.template import render_structure
from ..services.http_client import HTTPClient
from .base import NodeRunner


class HttpRequestRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        cfg = node.configurations or {}
        method = str(cfg.get("method", "GET")).upper()
        url = str(cfg.get("url", cfg.get("endpoint", "")))
        headers = cfg.get("headers", {}) or {}
        query_params = cfg.get("query_params", {}) or {}
        body_type = cfg.get("body_type", "json")
        follow_redirects = bool(cfg.get("follow_redirects", True))
        verify_ssl = bool(cfg.get("verify_ssl", True))
        timeout = float(cfg.get("timeout", cfg.get("timeout_seconds", 30)))

        dyn = inputs.get("main", {}) if isinstance(inputs.get("main"), dict) else {}
        dyn_headers = dyn.get("dynamic_headers", {}) or cfg.get("dynamic_headers", {}) or {}
        dyn_params = (
            dyn.get("dynamic_query_params", {}) or cfg.get("dynamic_query_params", {}) or {}
        )
        resolved_headers = {**headers, **dyn_headers}
        resolved_params = {**query_params, **dyn_params}

        # Simple template substitution for URL using {{path}} against dyn
        def render_template(s: str) -> str:
            pattern = re.compile(r"\{\{\s*([^}]+)\s*\}\}")

            def repl(m):
                path = m.group(1).strip()
                from ..core.expr import get_path

                val = get_path(dyn, path) if dyn else None
                return str(val) if val is not None else ""

            return pattern.sub(repl, s)

        if "{{" in url:
            url = render_template(url)

        # Render templated headers/params/body using combined context
        engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
        ctx = {
            "input": dyn,
            "config": cfg,
            "trigger": {"type": trigger.trigger_type, "data": trigger.trigger_data},
            "nodes": getattr(engine_ctx, "node_outputs", {}) if engine_ctx else {},
            "nodes_id": getattr(engine_ctx, "node_outputs", {}) if engine_ctx else {},
            "nodes_name": getattr(engine_ctx, "node_outputs_by_name", {}) if engine_ctx else {},
        }
        resolved_headers = render_structure(resolved_headers, ctx)
        resolved_params = render_structure(resolved_params, ctx)

        if not url:
            return {"error": {"message": "Missing URL"}}

        json_body: Optional[Any] = None
        data_body: Optional[Dict[str, Any]] = None
        if body_type == "json":
            json_body = dyn.get("body") or cfg.get("body")
        elif body_type == "form":
            data_body = dyn.get("body") or cfg.get("body")
        elif body_type == "raw":
            json_body = dyn.get("body") or cfg.get("body")

        client = HTTPClient(
            timeout=timeout, follow_redirects=follow_redirects, verify_ssl=verify_ssl
        )
        try:
            auth = None
            atype = str(cfg.get("auth_type", "none")).lower()
            if atype in ("bearer", "basic"):
                auth = {"type": atype, **(cfg.get("auth_config") or {})}
            retries = int(cfg.get("retry_attempts", 0) or 0)
            backoff = float(cfg.get("backoff_seconds", 0) or 0)
            resp = client.request(
                method=method,
                url=url,
                headers=resolved_headers,
                params=resolved_params,
                json_body=json_body,
                data_body=data_body,
                auth=auth,
                retry_attempts=retries,
                backoff_seconds=backoff,
            )
            return {
                "main": {
                    "status_code": resp.status_code,
                    "headers": resp.headers,
                    "json": resp.json,
                    "text": resp.text,
                    "success": 200 <= resp.status_code < 300,
                    "url": url,
                    "method": method,
                },
                "_details": {
                    "api_endpoint": url,
                    "http_method": method,
                    "response_status": resp.status_code,
                    "response_headers": resp.headers,
                },
            }
        except Exception as e:
            return {"error": {"message": str(e), "url": url, "method": method}}
        finally:
            client.close()


class DataTransformationRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        cfg = node.configurations or {}
        transform_type = cfg.get("transform_type") or cfg.get("transformation_type", "mapping")
        src = inputs.get("main", inputs)
        if transform_type == "mapping":
            mapping = cfg.get("mapping_rules") or cfg.get("field_mappings") or {}
            out = {}
            for target, path in mapping.items():
                if isinstance(path, str):
                    out[target] = get_path(src, path)
                else:
                    out[target] = None
            return {"main": out}
        if transform_type in ("jsonpath", "path"):
            path = cfg.get("transform_script") or cfg.get("jsonpath") or cfg.get("path")
            if isinstance(path, str):
                return {"main": get_path(src, path)}
            return {"main": src}
        if transform_type == "template_map":
            # template_map: {key: "Hello {{ input.user }}"}
            tmpl_map = cfg.get("template_map", {}) or {}
            ctx = {"input": src, "config": cfg}
            return {"main": render_structure(tmpl_map, ctx)}
        # Default pass-through
        return {"main": src}


__all__ = ["HttpRequestRunner", "DataTransformationRunner"]
