"""
Enhanced Tracking ID Generation
生成和管理跟踪ID，支持OpenTelemetry和fallback模式
"""

import uuid
from opentelemetry import trace
from typing import Optional


def generate_tracking_id() -> str:
    """
    Generate a tracking ID, preferring OpenTelemetry trace ID if available,
    otherwise generating a UUID-based tracking ID.
    
    Returns:
        A hex string tracking ID (32 characters)
    """
    # Try to get OpenTelemetry trace ID first
    span = trace.get_current_span()
    
    if span and span.is_recording():
        # Use OpenTelemetry trace ID
        span_context = span.get_span_context()
        if span_context and span_context.trace_id:
            return format(span_context.trace_id, '032x')
    
    # Fallback: Generate UUID-based tracking ID
    # Use UUID4 and convert to hex format similar to trace ID
    return uuid.uuid4().hex


def get_or_create_tracking_id(request_state: Optional[object] = None) -> str:
    """
    Get existing tracking ID from request state or create a new one.
    
    Args:
        request_state: The request.state object from FastAPI
        
    Returns:
        A tracking ID string
    """
    # Check if tracking_id already exists in request state
    if request_state and hasattr(request_state, 'tracking_id'):
        tracking_id = getattr(request_state, 'tracking_id')
        if tracking_id and tracking_id != 'no-trace':
            return tracking_id
    
    # Generate new tracking ID
    return generate_tracking_id()


def format_tracking_id(tracking_id: Optional[str]) -> str:
    """
    Format tracking ID for display, handling None and invalid values.
    
    Args:
        tracking_id: The tracking ID to format
        
    Returns:
        Formatted tracking ID or 'no-trace' if invalid
    """
    if not tracking_id or tracking_id == 'unknown':
        return 'no-trace'
    
    # Ensure it's a valid hex string
    if len(tracking_id) == 32:
        try:
            int(tracking_id, 16)
            return tracking_id
        except ValueError:
            pass
    
    return 'no-trace'