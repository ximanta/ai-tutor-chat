# main/codeassist_chat_service.py
import os
import json
import logging
from dotenv import load_dotenv
from typing import Dict, AsyncGenerator, Optional, List, Any
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel

logger = logging.getLogger(__name__)
load_dotenv() # Ensure .env is loaded for environment variables

# Define a Pydantic model for the streamed output chunks
class StreamedChatResponse(BaseModel):
    text_chunk: Optional[str] = None # Contains partial text during streaming
    follow_up_prompts: Optional[List[str]] = None # Contains clickable follow-up questions/prompts in the final chunk
    is_final: bool = False # Explicitly signals the end of the stream for the frontend

class CodeAssistChatService:
    def __init__(self):
        # Initialize the main LLM for generating text responses.
        self.main_llm = AzureChatOpenAI(
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0.7,
            streaming=True,
        )
        
    async def get_chat_response(self, message: str, context: Dict) -> AsyncGenerator[str, None]:
        """
        Generates a chat response from the LLM.
        1. Streams the main text content.
        2. After text is complete, generates clickable follow-up prompts.
        3. Sends a final JSON chunk containing the follow-up prompts and an 'is_final' flag.
        """
        try:
            user_id = context.get('userId')
            tutor_name = context.get('tutorName')
            
            if not user_id:
                raise ValueError("User ID must be provided in context.")
            if not tutor_name:
                raise ValueError("Tutor name must be provided in context.")

            logger.info(f"Starting chat response for user {user_id} with tutor {tutor_name}")
            
            # Construct the system prompt
            system_prompt = f"""You are a helpful and engaging mentor named {tutor_name} who helps students learn. 
            Remember to:
            1. Suggest improvements 
            2. Be encouraging and supportive
            3. Focus on teaching and understanding
                
            IMPORTANT:
            - If question is not related to learning domain, politely decline in a humorous tone.
            - Always refer to yourself as {tutor_name} and NOT as an AI assistant.
            """
            
            # Create the chat prompt for the main response
            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{user_input}")
            ])
            
            response_text_buffer = ""
            logger.info(f"Starting main LLM text streaming for user {user_id}...")
            
            # Stream the main text response
            async for chunk in self.main_llm.astream(
                chat_prompt.format_messages(user_input=message)
            ):
                if hasattr(chunk, 'content') and chunk.content:
                    logger.info(f"Received text chunk: {chunk.content[:50]}...")
                    response_text_buffer += chunk.content
                    response_data = StreamedChatResponse(text_chunk=chunk.content).model_dump_json()
                    yield f"data: {response_data}\n\n"
            
            logger.info("Main LLM text streaming complete.")

            # Generate follow-up prompts
            if response_text_buffer:
                logger.info("Starting generation of follow-up prompts...")
                follow_up_prompt = ChatPromptTemplate.from_messages([
                    ("system", "Generate 2-4 concise follow-up questions based on the previous explanation. Return them as a comma-separated list without any additional text or formatting."),
                    ("human", f"Based on this explanation: {response_text_buffer[:500]}... Generate follow-up questions.")
                ])
                
                try:
                    follow_up_response = await self.main_llm.ainvoke(follow_up_prompt.format_messages())
                    follow_up_content = follow_up_response.content.strip()
                    logger.info(f"Raw follow-up response: {follow_up_content}")
                    
                    # Split and clean the prompts
                    follow_up_prompts = [q.strip() for q in follow_up_content.split(',') if q.strip()][:4]
                    logger.info(f"Processed follow-up prompts: {follow_up_prompts}")
                    
                    # Send the final chunk with follow-ups
                    final_response = StreamedChatResponse(
                        follow_up_prompts=follow_up_prompts,
                        is_final=True
                    )
                    yield f"data: {final_response.model_dump_json()}\n\n"
                    logger.info("Final response chunk sent with follow-up prompts.")
                except Exception as e:
                    logger.error(f"Error generating follow-up prompts: {e}", exc_info=True)
                    # Send final chunk without follow-ups if there's an error
                    final_response = StreamedChatResponse(is_final=True)
                    yield f"data: {final_response.model_dump_json()}\n\n"

        except ValueError as ve:
            logger.error(f"Input validation error in chat service for user {user_id}: {ve}", exc_info=True)
            error_response = StreamedChatResponse(
                text_chunk=f"Input error: {str(ve)}. Please ensure required fields like 'userId' and 'tutorName' are provided.",
                is_final=True
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
        except Exception as e:
            logger.error(f"Unhandled error in chat response for user {user_id}: {str(e)}", exc_info=True)
            error_response = StreamedChatResponse(
                text_chunk=f"I apologize, but I encountered an internal server error. Please try again later.",
                is_final=True
            )
            yield f"data: {error_response.model_dump_json()}\n\n"