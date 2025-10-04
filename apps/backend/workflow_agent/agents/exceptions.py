"""Custom exceptions for workflow agent nodes."""


class WorkflowGenerationError(RuntimeError):
    """Raised when the agent fails to produce a workflow JSON."""

    def __init__(self, message: str, *, recoverable: bool = False) -> None:
        super().__init__(message)
        self.recoverable = recoverable
