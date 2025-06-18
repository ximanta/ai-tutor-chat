# main.py

import logging
from dotenv import load_dotenv
# --- CRITICAL: load_dotenv() MUST be called BEFORE any imports that rely on env vars ---
load_dotenv()

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from tutor_chat import chat_router as codeassist

# --- Logging Configuration for the entire application ---
# This must be run ONCE at application startup.
logging.basicConfig(
    level=logging.DEBUG,  # Set to INFO for production, DEBUG for development
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Outputs logs to the console (stderr by default)
    ],
    force=True  # Force reconfiguration of the root logger
)
logger = logging.getLogger(__name__) # Logger for main.py itself
logger.info("Application logging configured.")

app = FastAPI(
    title="AI Tutor Chat API",
    description="API for an AI-powered  chat.",
    version="1.0.0",
    # Enable debug mode for better error messages
    debug=True
)

# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    # In development, allow all origins. For production, restrict this!
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for Pydantic validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles validation errors for incoming requests, providing a clear error message.
    """
    logger.error(f"Validation error for request {request.url}: {exc.errors()}", exc_info=True)
    return PlainTextResponse(f"Validation Error: {exc.errors()}", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

# Global exception handler for all unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handles any unhandled exceptions and logs them properly
    """
    logger.critical(
        f"Unhandled exception occurred",
        exc_info=True,
        extra={
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers),
            "exception_type": type(exc).__name__
        }
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An internal server error occurred: {str(exc)}"}
    )

# Include the chat router
app.include_router(codeassist.router)
logger.info("Chat router included.")

@app.get("/")
async def root():
    """
    Root endpoint for the API, providing a welcome message.
    """
    return {"message": "Welcome to AI Tutor."}