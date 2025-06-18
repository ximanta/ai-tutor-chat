from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

# Relative import for service and shared modules
from .chat_service import CodeAssistChatService

from starlette.requests import Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aitutor", tags=["Code Assist Chat"]) 
chat_service = CodeAssistChatService()

# Pydantic Models for request body validation
class TestCase(BaseModel):
    input: List[Any]
    output: Any

class SubmissionResults(BaseModel):
    completed: bool
    passed: bool
    results: List[Any]

class ChatContext(BaseModel):
    userId: str
    tutorName: str  
   

class ChatRequest(BaseModel):
    message: str
    context: ChatContext

@router.post("/chat")

async def chat(request: Request, chat_request: ChatRequest):
    """
    Chat endpoint for Code Assist.
    It streams the AI's textual response and then sends a final chunk
    containing extracted followup prompts
    """
    try:
        logger.info("=== Chat Request Received ===")
        logger.info(f"User ID: {chat_request.context.userId}")
        # Log first 100 characters of the message to avoid logging very long inputs
        logger.info(f"Message: {chat_request.message[:100]}{'...' if len(chat_request.message) > 100 else ''}") 
        
        # Get the response generator from the service
        response_generator = chat_service.get_chat_response(
            message=chat_request.message,
            context=chat_request.context.model_dump() # .model_dump() is recommended in Pydantic v2
        )
          # Return a streaming response with SSE media type
        return StreamingResponse(
            response_generator,
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'text/event-stream',
                'Access-Control-Allow-Origin': '*',
            }
        )

    except ValueError as ve:
        logger.error(f"Validation error in chat endpoint: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unhandled error in chat endpoint: {e}", exc_info=True)
        # Return HTTP 500 with a generic error detail for client, log full detail on server
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
