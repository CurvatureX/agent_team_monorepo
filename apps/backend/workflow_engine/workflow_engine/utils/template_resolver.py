"""
Template Variable Resolver for Workflow Engine.

Supports resolving template variables like {{payload.number}}, ${env.VAR}, etc.
This allows workflows to use dynamic values that are resolved at runtime.
"""

import re
import logging
from typing import Any, Dict, Union, List

logger = logging.getLogger(__name__)


class TemplateResolver:
    """Resolve template variables in workflow parameters."""
    
    # Pattern to match template variables: {{var}}, ${var}, <%var%>
    TEMPLATE_PATTERNS = [
        (r'\{\{([^}]+)\}\}', '{{', '}}'),  # {{variable}}
        (r'\$\{([^}]+)\}', '${', '}'),      # ${variable}
        (r'<%([^%]+)%>', '<%', '%>'),       # <%variable%>
    ]
    
    @classmethod
    def is_template_string(cls, value: Any) -> bool:
        """Check if a value contains template variables."""
        if not isinstance(value, str):
            return False
        
        for pattern, _, _ in cls.TEMPLATE_PATTERNS:
            if re.search(pattern, value):
                return True
        return False
    
    @classmethod
    def resolve_value(cls, value: Any, context: Dict[str, Any]) -> Any:
        """
        Resolve a single value that might contain template variables.
        
        Args:
            value: The value to resolve (might be string, dict, list, etc.)
            context: Context containing values for variable resolution
            
        Returns:
            Resolved value with templates replaced
        """
        if isinstance(value, str):
            return cls._resolve_string(value, context)
        elif isinstance(value, dict):
            return cls._resolve_dict(value, context)
        elif isinstance(value, list):
            return cls._resolve_list(value, context)
        else:
            return value
    
    @classmethod
    def _resolve_string(cls, template: str, context: Dict[str, Any]) -> Union[str, Any]:
        """
        Resolve template variables in a string.
        
        If the entire string is a single template variable, return the actual value.
        Otherwise, perform string substitution.
        """
        # Check if entire string is a single template variable
        for pattern, prefix, suffix in cls.TEMPLATE_PATTERNS:
            match = re.fullmatch(pattern.replace(r'([^', r'([^').replace(r']+)', r']+)'), template)
            if match:
                # Entire string is a template, return the actual value
                var_path = match.group(1).strip()
                resolved = cls._get_nested_value(context, var_path)
                if resolved is not None:
                    logger.debug(f"Resolved complete template '{template}' to value: {resolved}")
                    return resolved
                else:
                    logger.warning(f"Could not resolve template variable: {template}")
                    return None  # Return None for unresolved variables instead of template string
        
        # Partial template substitution
        result = template
        for pattern, prefix, suffix in cls.TEMPLATE_PATTERNS:
            def replacer(match):
                var_path = match.group(1).strip()
                value = cls._get_nested_value(context, var_path)
                if value is not None:
                    return str(value)
                else:
                    logger.warning(f"Could not resolve template variable: {prefix}{var_path}{suffix}")
                    return match.group(0)  # Keep original if not resolved
            
            result = re.sub(pattern, replacer, result)
        
        return result
    
    @classmethod
    def _resolve_dict(cls, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve template variables in a dictionary."""
        resolved = {}
        for key, value in data.items():
            resolved[key] = cls.resolve_value(value, context)
        return resolved
    
    @classmethod
    def _resolve_list(cls, data: List[Any], context: Dict[str, Any]) -> List[Any]:
        """Recursively resolve template variables in a list."""
        return [cls.resolve_value(item, context) for item in data]
    
    @classmethod
    def _get_nested_value(cls, context: Dict[str, Any], path: str) -> Any:
        """
        Get a value from nested dictionary using dot notation.
        
        Examples:
            payload.number -> context['payload']['number']
            env.API_KEY -> context['env']['API_KEY']
            data.items[0].id -> context['data']['items'][0]['id']
        """
        # Handle array indices
        parts = []
        current = ""
        in_bracket = False
        
        for char in path:
            if char == '[':
                if current:
                    parts.append(current)
                    current = ""
                in_bracket = True
            elif char == ']':
                if in_bracket and current:
                    parts.append(int(current))
                    current = ""
                in_bracket = False
            elif char == '.' and not in_bracket:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        # Navigate through the context
        value = context
        for part in parts:
            if value is None:
                return None
            
            if isinstance(part, int):
                # Array index
                if isinstance(value, (list, tuple)) and 0 <= part < len(value):
                    value = value[part]
                else:
                    return None
            else:
                # Dictionary key
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    # Try attribute access for objects
                    value = getattr(value, part, None)
        
        return value
    
    @classmethod
    def resolve_parameters(cls, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all template variables in node parameters.
        
        Args:
            parameters: Node parameters that might contain templates
            context: Execution context with available variables
            
        Returns:
            Parameters with all templates resolved
        """
        resolved = cls._resolve_dict(parameters, context)
        
        # Log resolution summary
        template_count = cls._count_templates(parameters)
        if template_count > 0:
            logger.info(f"Resolved {template_count} template variables in parameters")
        
        return resolved
    
    @classmethod
    def _count_templates(cls, value: Any) -> int:
        """Count the number of template variables in a value."""
        count = 0
        
        if isinstance(value, str):
            for pattern, _, _ in cls.TEMPLATE_PATTERNS:
                count += len(re.findall(pattern, value))
        elif isinstance(value, dict):
            for v in value.values():
                count += cls._count_templates(v)
        elif isinstance(value, list):
            for item in value:
                count += cls._count_templates(item)
        
        return count
    
    @classmethod
    def build_execution_context(
        cls,
        workflow_data: Dict[str, Any],
        trigger_data: Dict[str, Any],
        execution_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build the context for template resolution.
        
        Args:
            workflow_data: Static workflow data
            trigger_data: Dynamic trigger/input data
            execution_metadata: Execution metadata (workflow_id, execution_id, etc.)
            
        Returns:
            Complete context for template resolution
        """
        import os
        
        context = {
            # Trigger data (e.g., webhook payload)
            "payload": trigger_data.get("payload", {}),
            "trigger": trigger_data,
            
            # Workflow static data
            "workflow": workflow_data,
            "static": workflow_data.get("static_data", {}),
            
            # Execution metadata
            "execution": execution_metadata,
            
            # Environment variables (filtered for security)
            "env": cls._get_safe_env_vars(),
            
            # Convenience shortcuts
            "data": trigger_data,  # Alias for trigger data
        }
        
        return context
    
    @classmethod
    def _get_safe_env_vars(cls) -> Dict[str, str]:
        """Get environment variables that are safe to expose."""
        import os
        
        # Only expose non-sensitive environment variables
        safe_prefixes = ['WORKFLOW_', 'APP_', 'NODE_']
        safe_vars = {}
        
        for key, value in os.environ.items():
            # Only include variables with safe prefixes
            if any(key.startswith(prefix) for prefix in safe_prefixes):
                safe_vars[key] = value
        
        return safe_vars