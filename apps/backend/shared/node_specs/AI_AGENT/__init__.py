# AI_AGENT node specifications
from .OPENAI_CHATGPT import OPENAI_CHATGPT_SPEC

try:
    from .ANTHROPIC_CLAUDE import ANTHROPIC_CLAUDE_SPEC  # type: ignore
except Exception:  # pragma: no cover - optional spec may have JSON-like examples
    ANTHROPIC_CLAUDE_SPEC = None  # type: ignore
try:
    from .GOOGLE_GEMINI import GOOGLE_GEMINI_SPEC  # type: ignore
except Exception:  # pragma: no cover - optional spec may have JSON-like examples
    GOOGLE_GEMINI_SPEC = None  # type: ignore

__all__ = [
    "OPENAI_CHATGPT_SPEC",
    "ANTHROPIC_CLAUDE_SPEC",
    "GOOGLE_GEMINI_SPEC",
]
