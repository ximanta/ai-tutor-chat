import os
import json
import logging
from pathlib import Path
from typing import Dict, AsyncGenerator, Optional, List, Any
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError, Field

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
# Basic logging setup if not configured elsewhere
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class ChatServiceError(Exception):
    """Custom exception for chat service errors"""
    pass

# --- Prompt Loading ---
def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt file {filename}: {e}")
        raise ChatServiceError(f"Failed to load prompt file {filename}") from e

# --- Pydantic Models ---

class StreamedChatResponse(BaseModel):
    text_chunk: Optional[str] = None
    follow_up_prompts: Optional[List[str]] = None
    is_final: bool = False

class LLMStructuredOutput(BaseModel):
    main_response: str = Field(
        description="This field should ideally be an empty string when generating follow-up questions, "
                    "as the main response has already been streamed. It's included for schema consistency."
    )
    follow_up_questions: Optional[List[str]] = Field(
        default=None,
        description="A list of 2-3 **very concise** (3-5 words max, like clickable chips) and engaging follow-up questions. "
                    "These should *only* be generated if the main_response contains substantial information, "
                    "explanations, or concepts that genuinely invite further learning. "
                    "**Omit entirely (provide null or an empty list)** for simple acknowledgements, greetings, short factual answers, "
                    "or if the user's query was very simple (e.g., 'What's your name?', 'Thanks'). "
                    "The goal is to provide useful next steps, not to force conversation."
    )

# --- Chat Service Class ---

class CodeAssistChatService:
    def __init__(self):
        logger.info("CodeAssistChatService: Initializing...")
        
        # Load prompts
        try:
            self.system_prompt_template = load_prompt("system_prompt.md")
            self.follow_up_prompt_template = load_prompt("follow_up_prompt.md")
            logger.info("Prompt templates loaded successfully")
        except Exception as e:
            logger.critical("Failed to load prompt templates", exc_info=True)
            raise

        required_env_vars = {
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION"),
            "AZURE_OPENAI_DEPLOYMENT_NAME": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY")
        }

        missing_vars = [k for k, v in required_env_vars.items() if not v or v.isspace()]
        if missing_vars:
            error_msg = f"Missing or empty required environment variables: {', '.join(missing_vars)}"
            logger.critical(error_msg)
            raise ChatServiceError(error_msg)

        logger.debug("Environment variables validated successfully")
        
        try:
            self.main_llm = AzureChatOpenAI(
                openai_api_version=required_env_vars["AZURE_OPENAI_API_VERSION"],
                azure_deployment=required_env_vars["AZURE_OPENAI_DEPLOYMENT_NAME"],
                azure_endpoint=required_env_vars["AZURE_OPENAI_ENDPOINT"],
                api_key=required_env_vars["AZURE_OPENAI_API_KEY"],
                temperature=0.7,
                streaming=True, 
            )
            logger.info("AzureChatOpenAI initialized successfully")
            
            # Configure non-streaming LLM for structured output
            self.structured_llm = AzureChatOpenAI(
                openai_api_version=required_env_vars["AZURE_OPENAI_API_VERSION"],
                azure_deployment=required_env_vars["AZURE_OPENAI_DEPLOYMENT_NAME"],
                azure_endpoint=required_env_vars["AZURE_OPENAI_ENDPOINT"],
                api_key=required_env_vars["AZURE_OPENAI_API_KEY"],
                temperature=0.7,
                streaming=False,  # Not streaming for structured output
            ).with_structured_output(LLMStructuredOutput)
            logger.info("Structured LLM configured successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize AzureOpenAI: {str(e)}"
            logger.critical(error_msg, exc_info=True)
            raise ChatServiceError(error_msg) from e
            
        logger.info("CodeAssistChatService: Initialization complete")

    async def get_chat_response(self, message: str, conversationId: str, context: Dict) -> AsyncGenerator[str, None]:
        user_id = context.get('userId')
        tutor_name = context.get('tutorName')
        conversation_id=conversationId
        logger.info(f"get_chat_response: Method entered for user '{user_id}'. Message: '{message}' . Conversation ID: '{conversation_id:}'")

        try:
            if not user_id:
                raise ValueError("User ID must be provided in context.")
            if not tutor_name:
                raise ValueError("Tutor name must be provided in context.")

            logger.debug(f"Context received in service: User ID={user_id}, Tutor Name={tutor_name}")
            
            # Format the system prompt with tutor name
            system_prompt = self.system_prompt_template.format(tutor_name=tutor_name)
            human_message_content = message
            
            if "@" in user_id and ("my email" in message.lower() or "what's my email" in message.lower() or "my user id" in message.lower()):
                human_message_content += f"\n\n(Note: The user's registered email/ID is: {user_id})"
                logger.info(f"Injected userId '{user_id}' into prompt as user asked for email/ID.")

            # First, stream the main response
            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{user_input}")
            ])
            
            chain = chat_prompt | self.main_llm
            logger.info("Starting streaming chat completion...")

            accumulated_text = ""
            async for chunk in chain.astream({"user_input": human_message_content}):
                if hasattr(chunk, 'content') and chunk.content:
                    chunk_text = chunk.content
                    accumulated_text += chunk_text
                    response_data = StreamedChatResponse(
                        text_chunk=chunk_text,
                        is_final=False
                    ).model_dump_json()
                    yield f"data: {response_data}\n\n"
                    # logger.debug(f"Streamed chunk: {len(chunk_text)} chars")

            # After streaming is complete, get follow-up questions
            logger.info("Main response complete, generating follow-up questions...")
            try:
                structured_prompt = self.follow_up_prompt_template.format(
                    tutor_name=tutor_name,
                    user_original_query=message,
                    ai_main_response=accumulated_text
                )
                structured_response = await self.structured_llm.ainvoke(structured_prompt)
                
                # Send the final chunk with follow-up prompts
                final_response = StreamedChatResponse(
                    text_chunk=None,
                    follow_up_prompts=structured_response.follow_up_questions,
                    is_final=True
                )
                yield f"data: {final_response.model_dump_json()}\n\n"
                logger.info("Final response chunk sent with follow-up prompts")

            except Exception as e:
                logger.error(f"Error generating follow-up questions: {str(e)}")
                final_response = StreamedChatResponse(is_final=True)
                yield f"data: {final_response.model_dump_json()}\n\n"

        except Exception as e:
            logger.error(f"Error in chat response: {str(e)}", exc_info=True)
            error_response = StreamedChatResponse(
                text_chunk=f"I apologize, but I encountered an error: {str(e)}",
                is_final=True
            ).model_dump_json()
            yield f"data: {error_response}\n\n"