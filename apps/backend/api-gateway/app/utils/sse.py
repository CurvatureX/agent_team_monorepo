"""
Server-Sent Events (SSE) utilities for MVP
"""

import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from fastapi.responses import StreamingResponse


def create_sse_response(generator: AsyncGenerator[Dict[str, Any], None]) -> StreamingResponse:
    """Create SSE response from async generator"""
    
    async def event_stream():
        async for data in generator:
            yield format_sse_event(data)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )


def format_sse_event(data: Dict[str, Any]) -> str:
    """Format data as SSE event"""
    return f"data: {json.dumps(data)}\n\n"


async def create_mock_chat_stream(session_id: str, message: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    MVP mock chat stream generator - Industry standard incremental streaming
    
    Returns only delta (new content) in each event, following OpenAI/Claude/Gemini pattern
    Frontend should append deltas to build full content
    
    TODO: Replace with actual gRPC call to AI service
    """
    # Simulate AI thinking time
    await asyncio.sleep(0.5)
    
    # Mock AI response in chunks
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
            "delta": delta,             # Only new content (industry standard)
            "session_id": session_id,
            "chunk_index": i,
            "is_complete": i == len(words) - 1
        }
        
        # Simulate streaming delay
        await asyncio.sleep(0.1)


async def create_mock_workflow_stream(session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    MVP mock workflow stream generator
    TODO: Replace with actual gRPC call to workflow service
    """
    import uuid
    
    workflow_id = str(uuid.uuid4())
    
    # Simulate workflow generation stages
    stages = [
        {"type": "waiting", "message": "Waiting for workflow generation to start"},
        {"type": "start", "message": "Starting workflow generation", "workflow_id": workflow_id},
        {"type": "draft", "message": "Generating workflow draft", "workflow_id": workflow_id},
        {"type": "debugging", "message": "Debugging and optimizing workflow", "workflow_id": workflow_id},
        {"type": "complete", "message": "Workflow generation completed", "workflow_id": workflow_id}
    ]
    
    for stage in stages:
        yield {
            "type": stage["type"],
            "workflow_id": stage.get("workflow_id"),
            "data": {
                "message": stage["message"],
                "session_id": session_id
            },
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        # Simulate processing time
        await asyncio.sleep(1.0)