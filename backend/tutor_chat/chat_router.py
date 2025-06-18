# tutor_chat/chat_router.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
import logging

# Relative import for service
from .chat_service import CodeAssistChatService

# Get a logger for this module
logger = logging.getLogger(__name__) # __name__ will typically be 'tutor_chat.chat_router'

router = APIRouter(prefix="/aitutor", tags=["Code Assist Chat"]) 

# Instantiate the service once when the router is loaded.
# This makes it a singleton for the application's lifetime, which is generally
# good for resources like LLM clients.
chat_service = CodeAssistChatService()
logger.info("CodeAssistChatService instance created for router.")

# --- Pydantic Models for request body validation ---
# IMPORTANT: These models define what your FastAPI endpoint expects.
# They must match what your frontend sends.

class ChatContext(BaseModel):
    userId: str    # Matches frontend payload
    tutorName: str # Matches frontend payload
    # Removed userEmail as it's not in the provided frontend payload.
    # If userEmail is ever needed, it should be added here as Optional[str]
    # and passed from the frontend.

class ChatRequest(BaseModel):
    conversationId: str # Matches frontend payload
    message: str
    context: ChatContext


@router.post("/chat")
async def chat(chat_request: ChatRequest):
    """
    Chat endpoint for Code Assist.
    It streams the AI's textual response and then sends a final chunk
    containing extracted followup prompts
    """
    try:
        logger.info("=== Chat Request Received ===")
        logger.info(f"User ID: {chat_request.context.userId}")
        logger.info(f"Tutor Name: {chat_request.context.tutorName}")
        logger.info(f"COnversation ID: {chat_request.conversationId}") 

        # Log first 100 characters of the message to avoid logging very long inputs
        logger.info(f"Message: {chat_request.message[:100]}{'...' if len(chat_request.message) > 100 else ''}") 
        
        # Get the response generator from the service
        # Don't await the async generator, pass it directly to StreamingResponse
        response_generator = chat_service.get_chat_response(
            message=chat_request.message,
            conversationId=chat_request.conversationId,
            # .model_dump() converts the Pydantic ChatContext object to a plain dictionary
            context=chat_request.context.model_dump() 
        )
        
        # Return a streaming response with SSE media type
        return StreamingResponse(
            response_generator,
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'text/event-stream',
                'Access-Control-Allow-Origin': '*', # Adjust for production
            }
        )

    except ValueError as ve:
        logger.error(f"Validation error in chat endpoint: {ve}", exc_info=True)
        # HTTP 400 Bad Request is appropriate for client-side input validation errors
        raise HTTPException(status_code=400, detail=f"Bad Request: {str(ve)}")
    except Exception as e:
        logger.critical(f"Unhandled error in chat endpoint: {e}", exc_info=True)
        # For unhandled server errors, return HTTP 500
        raise HTTPException(status_code=500, detail=str(e))