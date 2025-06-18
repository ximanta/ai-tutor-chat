# main.py
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import PlainTextResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from tutor_chat import chat_router as codeassist


# Load environment variables from .env file
load_dotenv()

# Configure logging
# Set up basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



app = FastAPI(
    title="Code Assist API",
    description="API for an AI-powered code assistance chat.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow local Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


# Global exception handler for Pydantic validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles validation errors for incoming requests, providing a clear error message.
    """
    logger.error(f"Validation error for request {request.url}: {exc.errors()}", exc_info=True)
    return PlainTextResponse(f"Validation Error: {exc.errors()}", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

# Include your router
app.include_router(codeassist.router)

@app.get("/")
async def root():
    """
    Root endpoint for the API, providing a welcome message.
    """
    return {"message": "Welcome to Code Assist API! Use /docs for API documentation or /codeassist/chat for chat functionality."}


