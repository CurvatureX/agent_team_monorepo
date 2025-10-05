"""
Jinja2-based Prompt Engine for loading and rendering prompts.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def tojsonpretty(value):
    """Custom Jinja2 filter to format JSON with pretty printing"""
    return json.dumps(value, indent=2, ensure_ascii=False)


class PromptEngine:
    """A Jinja2-based prompt loading and rendering engine."""

    def __init__(self, template_folder: str = "shared/prompts"):
        # In Docker, use absolute path; in development, resolve monorepo layout
        if Path("/shared/prompts").exists():
            self.template_path = Path("/shared/prompts")
        else:
            # Prefer apps/backend/shared/prompts; fallback to apps/shared/prompts
            backend_base = Path(__file__).parents[2]  # apps/backend
            candidate1 = backend_base / template_folder  # apps/backend/shared/prompts
            candidate2 = Path(__file__).parents[3] / template_folder  # apps/shared/prompts

            if candidate1.exists():
                self.template_path = candidate1
            elif candidate2.exists():
                self.template_path = candidate2
            else:
                raise FileNotFoundError(
                    f"Template folder not found. Tried: {candidate1} and {candidate2}"
                )

        self.env = Environment(
            loader=FileSystemLoader(self.template_path),
            trim_blocks=True,
            lstrip_blocks=True,
            enable_async=True,
        )

        # Register custom filters
        self.env.filters["tojsonpretty"] = tojsonpretty

        logger.info(
            "Jinja2 prompt engine initialized", extra={"template_path": str(self.template_path)}
        )

    async def render_prompt(self, template_name: str, **context: Any) -> str:
        """
        Renders a single prompt template.

        Args:
            template_name: The name of the template file (e.g., 'analyze_requirement.j2').
            **context: The context variables to pass to the template.

        Returns:
            The rendered prompt as a string.
        """
        try:
            template = await asyncio.to_thread(self.env.get_template, f"{template_name}.j2")
            return await template.render_async(context)
        except Exception as e:
            logger.error(
                "Failed to render prompt template",
                extra={"template_name": template_name, "error": str(e)},
            )
            return f"Error rendering template {template_name}: {e}"

    async def get_system_and_user_prompts(
        self, template_name: str, **context: Any
    ) -> Tuple[str, str]:
        """
        Renders separate system and user prompts from a single template file.
        The template should contain 'system' and 'user' blocks.

        Args:
            template_name: The name of the template file (e.g., 'analyze_requirement.j2').
            **context: The context variables to pass to the template.

        Returns:
            A tuple containing the rendered system and user prompts.
        """
        try:
            template = await asyncio.to_thread(self.env.get_template, f"{template_name}.j2")

            system_prompt = await template.render_async(context, prompt_section="system")
            user_prompt = await template.render_async(context, prompt_section="user")

            return system_prompt.strip(), user_prompt.strip()

        except Exception as e:
            logger.error(
                "Failed to render system and user prompts",
                extra={"template_name": template_name, "error": str(e)},
            )
            return (
                f"Error rendering system prompt for {template_name}",
                f"Error rendering user prompt for {template_name}",
            )


# Singleton instance of the prompt engine
prompt_engine = PromptEngine()


def get_prompt_engine() -> PromptEngine:
    """Returns the singleton instance of the PromptEngine."""
    return prompt_engine
