"""
Prompt template loader using Jinja2
"""

from pathlib import Path
from typing import Optional, Any
import json

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    raise ImportError("jinja2 is required for prompt templating. Install it with: pip install jinja2")


class PromptLoader:
    """Load and render Jinja2 prompt templates"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            # Default to the shared prompts directory
            current_dir = Path(__file__).parent
            prompts_dir = str(current_dir)
        
        self.prompts_dir = Path(prompts_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['tojson'] = self._to_json_filter
    
    def _to_json_filter(self, value, ensure_ascii=True, **kwargs):
        """Custom JSON filter for Jinja2"""
        return json.dumps(value, ensure_ascii=ensure_ascii, **kwargs)
    
    def load_template(self, template_name: str):
        """Load a Jinja2 template"""
        return self.env.get_template(template_name)
    
    def render_prompt(self, template_name: str, **context) -> str:
        """Render a prompt template with the given context"""
        template = self.load_template(template_name)
        return template.render(**context)
    
    def get_system_and_user_prompts(self, base_name: str, **context) -> tuple[str, str]:
        """
        Get both system and user prompts for a given base name.
        Expects templates named {base_name}.j2 and {base_name}_user.j2
        """
        system_prompt = self.render_prompt(f"{base_name}.j2", **context)
        user_prompt = self.render_prompt(f"{base_name}_user.j2", **context)
        return system_prompt, user_prompt