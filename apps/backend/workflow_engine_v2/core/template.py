"""Template rendering utilities for v2 engine.

Supports simple {{ path.to.value }} substitution against a context dict.
Integrates with dot-path get_path() from core.expr.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict

from workflow_engine_v2.core.expr import get_path

TEMPLATE_RE = re.compile(r"\{\{\s*([^}]+)\s*\}\}")


def _eval_expression(expr: str, ctx: Dict[str, Any]) -> Any:
    expr = expr.strip()
    # $json and $json.path -> current main input
    if expr == "$json":
        return ctx.get("input")
    if expr.startswith("$json."):
        base = ctx.get("input")
        return get_path(base, expr[len("$json.") :])
    # $input.port or $input.port.path -> full inputs dict by port
    if expr.startswith("$input"):
        match = re.match(r"\$input(?:\.([a-zA-Z0-9_]+))?(?:\.(.+))?", expr)
        if match:
            port = match.group(1) or "main"
            tail = match.group(2)
            inputs = ctx.get("inputs") or {}
            base = inputs.get(port)
            if tail:
                return get_path(base, tail)
            return base
        return None
    # $config.path -> node configuration
    if expr.startswith("$config"):
        match = re.match(r"\$config(?:\.(.+))?", expr)
        if match:
            tail = match.group(1)
            base = ctx.get("config") or {}
            if tail:
                return get_path(base, tail)
            return base
        return None
    # $trigger.path -> trigger details
    if expr.startswith("$trigger"):
        match = re.match(r"\$trigger(?:\.(.+))?", expr)
        if match:
            tail = match.group(1)
            base = ctx.get("trigger") or {}
            if tail and isinstance(base, dict):
                return get_path(base, tail)
            return base
        return None
    # Support $node["id"].port.path
    if expr.startswith("$node["):
        match = re.match(r"\$node\[\"([^\"]+)\"\](?:\.([a-zA-Z0-9_]+))?(?:\.(.+))?", expr)
        if match:
            node_id = match.group(1)
            port = match.group(2) or "main"
            tail = match.group(3)
            nodes_by_id = ctx.get("nodes_id") or ctx.get("nodes") or {}
            nodes_by_name = ctx.get("nodes_name") or {}
            node_out = nodes_by_id.get(node_id) or nodes_by_name.get(node_id) or {}
            base = node_out.get(port)
            if tail:
                return get_path(base, tail)
            return base
        return None
    # Fallback to dot-path on the full ctx
    return get_path(ctx, expr)


def _strip_parens(string_value: str) -> str:
    string_value = string_value.strip()
    while string_value.startswith("(") and string_value.endswith(")"):
        string_value = string_value[1:-1].strip()
    return string_value


def _parse_literal(token: str, ctx: Dict[str, Any]) -> Any:
    trimmed_token = token.strip()
    # function call: name(arg1, arg2, ...)
    match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)$", trimmed_token)
    if match:
        function_name = match.group(1)
        args_string = match.group(2)
        args = _split_args(args_string)
        args_eval = [_parse_literal(argument, ctx) for argument in args]
        return _call_func(function_name, args_eval)
    # quoted string
    if (trimmed_token.startswith('"') and trimmed_token.endswith('"')) or (
        trimmed_token.startswith("'") and trimmed_token.endswith("'")
    ):
        return trimmed_token[1:-1]
    # booleans/null
    if trimmed_token.lower() == "true":
        return True
    if trimmed_token.lower() == "false":
        return False
    if trimmed_token.lower() in ("null", "none"):
        return None
    # number
    try:
        if "." in trimmed_token:
            return float(trimmed_token)
        return int(trimmed_token)
    except Exception:
        pass
    # expression/path
    return _eval_expression(trimmed_token, ctx)


def eval_boolean(expr: str, ctx: Dict[str, Any]) -> bool:
    """Evaluate a boolean expression with simple ||, &&, and comparison ops.

    Supported ops: ==, ===, !=, !==, >=, <=, >, < with minimal precedence
    and grouping by parentheses. This is a pragmatic parser for workflow
    conditions, not a full language.
    """
    stripped_expr = _strip_parens(expr)
    # Or split
    parts = stripped_expr.split("||")
    if len(parts) > 1:
        return any(eval_boolean(part, ctx) for part in parts)
    # And split
    parts = stripped_expr.split("&&")
    if len(parts) > 1:
        return all(eval_boolean(part, ctx) for part in parts)
    # Comparison
    match = re.match(r"^(.*?)(===|==|!==|!=|>=|<=|>|<)(.*)$", stripped_expr)
    if match:
        left = _parse_literal(match.group(1), ctx)
        operator = match.group(2)
        right = _parse_literal(match.group(3), ctx)
        if operator in ("==", "==="):
            return left == right
        if operator in ("!=", "!=="):
            return left != right
        if operator == ">=":
            return left is not None and right is not None and left >= right
        if operator == "<=":
            return left is not None and right is not None and left <= right
        if operator == ">":
            return left is not None and right is not None and left > right
        if operator == "<":
            return left is not None and right is not None and left < right
    # Fallback: treat non-empty evaluation as truthy
    value = _parse_literal(stripped_expr, ctx)
    return bool(value)


def _split_args(args_string: str) -> list[str]:
    args = []
    current_arg = []
    depth = 0
    quote = None
    index = 0
    while index < len(args_string):
        char = args_string[index]
        if quote:
            current_arg.append(char)
            if char == quote:
                quote = None
        else:
            if char in ('"', "'"):
                quote = char
                current_arg.append(char)
            elif char == "(":
                depth += 1
                current_arg.append(char)
            elif char == ")":
                depth = max(0, depth - 1)
                current_arg.append(char)
            elif char == "," and depth == 0:
                args.append("".join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)
        index += 1
    if current_arg:
        args.append("".join(current_arg).strip())
    return [arg for arg in args if arg != ""]


def _call_func(name: str, args: list) -> Any:
    function_name = name.lower()
    try:
        if function_name == "not" and len(args) == 1:
            return not bool(args[0])
        if function_name == "and" and len(args) >= 2:
            return all(bool(a) for a in args)
        if function_name == "or" and len(args) >= 2:
            return any(bool(a) for a in args)
        if function_name == "now" and len(args) == 0:
            return int(time.time() * 1000)
        if function_name == "len" and len(args) == 1:
            return 0 if args[0] is None else (len(args[0]) if hasattr(args[0], "__len__") else 0)
        if function_name == "contains" and len(args) == 2:
            try:
                return (args[1] in args[0]) if args[0] is not None else False
            except Exception:
                return False
        if (
            function_name == "startswith"
            and len(args) == 2
            and isinstance(args[0], str)
            and isinstance(args[1], str)
        ):
            return args[0].startswith(args[1])
        if (
            function_name == "endswith"
            and len(args) == 2
            and isinstance(args[0], str)
            and isinstance(args[1], str)
        ):
            return args[0].endswith(args[1])
        if function_name == "lower" and len(args) == 1 and isinstance(args[0], str):
            return args[0].lower()
        if function_name == "upper" and len(args) == 1 and isinstance(args[0], str):
            return args[0].upper()
        if function_name == "tonumber" and len(args) == 1:
            try:
                return float(args[0]) if ("." in str(args[0])) else int(args[0])
            except Exception:
                return 0
        if function_name == "if" and len(args) >= 2:
            cond = bool(args[0])
            return args[1] if cond else (args[2] if len(args) > 2 else None)
        if function_name == "clamp" and len(args) == 3:
            try:
                v = float(args[0])
                lo = float(args[1])
                hi = float(args[2])
                return max(lo, min(hi, v))
            except Exception:
                return args[0]
        if function_name == "add" and len(args) == 2:
            try:
                return (args[0] or 0) + (args[1] or 0)
            except Exception:
                return None
        if function_name == "sub" and len(args) == 2:
            try:
                return (args[0] or 0) - (args[1] or 0)
            except Exception:
                return None
        if function_name == "mul" and len(args) == 2:
            try:
                return (args[0] or 0) * (args[1] or 0)
            except Exception:
                return None
        if function_name == "div" and len(args) == 2:
            try:
                return (args[0] or 0) / (args[1] or 1)
            except Exception:
                return None
        if function_name == "mod" and len(args) == 2:
            try:
                return (args[0] or 0) % (args[1] or 1)
            except Exception:
                return None
        if function_name == "regex" and len(args) >= 2:
            try:
                pattern = str(args[1])
                flags = re.IGNORECASE if (len(args) > 2 and bool(args[2])) else 0
                return re.search(pattern, str(args[0] or ""), flags) is not None
            except Exception:
                return False
        if function_name == "coalesce" and len(args) >= 1:
            for a in args:
                if a not in (None, ""):
                    return a
            return None
    except Exception:
        return None
    return None


def render_template(text: str, ctx: Dict[str, Any]) -> str:
    def repl(m):
        raw = m.group(1).strip()
        val = _eval_expression(raw, ctx)
        if val is None:
            return ""
        return str(val)

    return TEMPLATE_RE.sub(repl, text)


def render_structure(data: Any, ctx: Dict[str, Any]) -> Any:
    if isinstance(data, str):
        return render_template(data, ctx) if "{{" in data else data
    if isinstance(data, dict):
        return {k: render_structure(v, ctx) for k, v in data.items()}
    if isinstance(data, list):
        return [render_structure(v, ctx) for v in data]
    return data


__all__ = ["render_template", "render_structure"]
