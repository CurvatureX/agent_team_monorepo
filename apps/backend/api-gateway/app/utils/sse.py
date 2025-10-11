"""
Server-Sent Events (SSE) utilities for MVP
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

from fastapi.responses import StreamingResponse


def create_sse_response(generator: AsyncGenerator[Dict[str, Any], None]) -> StreamingResponse:
    """Create SSE response from async generator"""

    async def event_stream():
        async for data in generator:
            # Handle the case where data is already a formatted SSE string
            if isinstance(data, str):
                # If it's already formatted, yield it directly
                yield data
            else:
                # If it's a dict, format it properly
                yield format_sse_event(data)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for immediate SSE delivery
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


def format_sse_event(data: Dict[str, Any]) -> str:
    """Format data as SSE event"""
    return f"data: {json.dumps(data)}\n\n"


def create_sse_event(event_type, data: Dict[str, Any], session_id: str, is_final: bool = False):
    """Create typed SSE event"""
    # Import here to avoid circular imports
    from app.models import ChatSSEEvent, SSEEventType

    return ChatSSEEvent(
        type=event_type,
        data=data,
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        is_final=is_final,
    )


async def create_mock_chat_stream(
    session_id: str, message: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    MVP mock chat stream generator - Industry standard incremental streaming

    Returns only delta (new content) in each event, following OpenAI/Claude/Gemini pattern
    Frontend should append deltas to build full content

    Now also supports workflow generation events based on message content

    TODO: Replace with actual gRPC call to AI service
    """
    # Simulate AI thinking time
    await asyncio.sleep(0.5)

    # Check if this is a workflow generation request
    is_workflow_request = any(
        keyword in message.lower()
        for keyword in ["workflow", "automation", "create", "generate", "build"]
    )

    if is_workflow_request:
        # Simulate workflow generation in chat
        async for event in _yield_workflow_generation_in_chat(session_id):
            yield event
    else:
        # Regular chat response
        ai_response = f"This is a mock AI response to your message: '{message}'. In the real implementation, this would be a streaming response from the AI service."

        words = ai_response.split()

        for i, word in enumerate(words):
            # Calculate delta (new content)
            if i == 0:
                delta = word
            else:
                delta = " " + word

            yield {
                "type": "message",
                "delta": delta,  # Only new content (industry standard)
                "session_id": session_id,
                "chunk_index": i,
                "is_complete": i == len(words) - 1,
            }

            # Simulate streaming delay
            await asyncio.sleep(0.1)


async def _yield_workflow_generation_in_chat(
    session_id: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Internal function to yield workflow generation events within chat stream
    """
    import uuid

    workflow_id = str(uuid.uuid4())

    # Phase 1: AI analysis and clarification
    analysis_response = (
        "I understand you want to create a workflow. Let me analyze your requirements..."
    )
    words = analysis_response.split()

    for i, word in enumerate(words):
        delta = word if i == 0 else " " + word
        yield {
            "type": "message",
            "delta": delta,
            "session_id": session_id,
            "chunk_index": i,
            "is_complete": i == len(words) - 1,
        }
        await asyncio.sleep(0.1)

    await asyncio.sleep(1.0)

    # Phase 2: Workflow generation progress events
    workflow_stages = [
        {"type": "workflow_generation_started", "message": "Starting workflow generation..."},
        {"type": "workflow_draft", "message": "Generating workflow draft..."},
        {"type": "workflow_debugging", "message": "Debugging and optimizing workflow..."},
        {"type": "workflow_complete", "message": "Workflow generation completed!"},
    ]

    for stage in workflow_stages:
        yield {
            "type": stage["type"],
            "workflow_id": workflow_id,
            "data": {"message": stage["message"], "session_id": session_id},
            "timestamp": str(asyncio.get_event_loop().time()),
        }
        await asyncio.sleep(1.5)

    # Phase 3: Final completion message
    completion_response = f"Your workflow has been successfully created! Workflow ID: {workflow_id}"
    words = completion_response.split()

    for i, word in enumerate(words):
        delta = word if i == 0 else " " + word
        yield {
            "type": "message",
            "delta": delta,
            "session_id": session_id,
            "chunk_index": i,
            "is_complete": i == len(words) - 1,
            "workflow_id": workflow_id,  # Include workflow_id in final message
        }
        await asyncio.sleep(0.1)
