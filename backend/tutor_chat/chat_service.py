import os
import json
import logging
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

            self.structured_llm = AzureChatOpenAI(
                openai_api_version=required_env_vars["AZURE_OPENAI_API_VERSION"],
                azure_deployment=required_env_vars["AZURE_OPENAI_DEPLOYMENT_NAME"],
                azure_endpoint=required_env_vars["AZURE_OPENAI_ENDPOINT"],
                api_key=required_env_vars["AZURE_OPENAI_API_KEY"],
                temperature=0.3, # Slightly lower temperature for more deterministic structured output
                streaming=False,
            ).with_structured_output(LLMStructuredOutput)
            logger.info("Structured LLM configured successfully")

        except Exception as e:
            error_msg = f"Failed to initialize AzureOpenAI: {str(e)}"
            logger.critical(error_msg, exc_info=True)
            raise ChatServiceError(error_msg) from e

        logger.info("CodeAssistChatService: Initialization complete")

    async def get_chat_response(self, message: str, context: Dict) -> AsyncGenerator[str, None]:
        user_id = context.get('userId')
        tutor_name = context.get('tutorName')

        logger.info(f"get_chat_response: Method entered for user '{user_id}'. Message: '{message}'")

        try:
            if not user_id:
                raise ValueError("User ID must be provided in context.")
            if not tutor_name:
                raise ValueError("Tutor name must be provided in context.")

            logger.debug(f"Context received in service: User ID={user_id}, Tutor Name={tutor_name}")

            system_prompt = f"""You are a helpful and engaging mentor named {tutor_name} who helps students learn.
            Remember to:
            1. Suggest improvements
            2. Be encouraging and supportive
            3. Focus on teaching and understanding

            IMPORTANT:
            - If question is not related to learning domain, politely decline in a humorous tone.
            - Always refer to yourself as {tutor_name} and NOT as an AI assistant."""

            human_message_content = message

            if "@" in user_id and ("my email" in message.lower() or "what's my email" in message.lower() or "my user id" in message.lower()):
                human_message_content += f"\n\n(Note: The user's registered email/ID is: {user_id})"
                logger.info(f"Injected userId '{user_id}' into prompt as user asked for email/ID.")

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
                    logger.debug(f"Streamed chunk: {len(chunk_text)} chars")

            logger.info("Main response complete, generating follow-up questions...")
            try:
                # Note the change from {{ to {{{{ and }} to }}}} in the JSON examples
                structured_prompt_template = ChatPromptTemplate.from_messages([
                    ("system",
                     f"""You are an AI assistant that generates follow-up questions based on a user's query and the main AI's response.
                     Your goal is to provide 2-3 **very concise** (3-5 words max, like clickable chips) follow-up questions.

                     **GUIDING PRINCIPLE FOR GENERATING FOLLOW-UPS:**
                     - **DO** generate follow-up questions if the `ai_main_response` provides a **detailed explanation, introduces concepts, discusses mechanisms, or offers substantial information** in response to the `user_original_query`. This is especially true if the query asks for an explanation (e.g., "Explain X", "What is Y?", "How does Z work?").
                     - The purpose of follow-ups is to encourage deeper learning and exploration of the topic just discussed.

                     **WHEN *NOT* TO GENERATE FOLLOW-UPS (provide null or empty list for `follow_up_questions`):**
                     1.  If the `user_original_query` was a simple social interaction (e.g., "Hi", "Thanks", "How are you?").
                     2.  If the `user_original_query` asks for a very simple, self-contained piece of information that is answered tersely and doesn't naturally open up broader discussion (e.g., "What's your name?", "What time is it right now?").
                     3.  If the `ai_main_response` is a polite refusal to answer an off-topic question.
                     4.  If the `ai_main_response` is a very short acknowledgement or a simple confirmation without new educational content.

                     **IMPORTANT:** A query like "What are arrays?" or "What are Java Streams?" when answered with a proper explanation IS a candidate for follow-up questions. Do not confuse this with a simple factual lookup.

                     Follow-up questions must be directly related to the `ai_main_response` and the `user_original_query`.
                     Ensure questions are unique and encourage further exploration of the topic.
                     The `main_response` field in your output should always be an empty string.

                     Example 1 (NO follow-ups - Simple Query/Greeting):
                     User Query: What's your name?
                     Main AI Response: My name is {tutor_name}.
                     Your Output: {{{{ "main_response": "", "follow_up_questions": null }}}}

                     Example 2 (NO follow-ups - Simple Social Interaction):
                     User Query: Thanks!
                     Main AI Response: You're welcome! Let me know if you have other questions.
                     Your Output: {{{{ "main_response": "", "follow_up_questions": null }}}}

                     Example 3 (YES follow-ups - Concept Explanation):
                     User Query: Can you explain Python decorators?
                     Main AI Response: Sure! Python decorators are a powerful way to modify or enhance functions or methods... [detailed explanation of what they are, how they work, syntax]
                     Your Output: {{{{ "main_response": "", "follow_up_questions": ["How do they work?", "Common use cases?", "Decorator syntax?"] }}}}

                     Example 4 (YES follow-ups - "What is X?" type question leading to substantial explanation):
                     User Query: What are streams in Java?
                     Main AI Response: Java Streams, introduced in Java 8, are a sequence of elements supporting sequential and parallel aggregate operations. They allow you to process collections of objects in a functional style... [explains key characteristics like pipelining, laziness, immutability, common operations like map, filter, reduce].
                     Your Output: {{{{ "main_response": "", "follow_up_questions": ["Stream vs Collection?", "Parallel streams?", "Terminal operations?"] }}}}
                     """),
                    ("human",
                     """User Original Query:
                     {user_original_query}

                     Main AI Response to User:
                     {ai_main_response}

                     Please generate your response according to the LLMStructuredOutput schema.""")
                ])

                # Prepare the input for the structured LLM
                structured_input = {
                    "user_original_query": message, # Original user message
                    "ai_main_response": accumulated_text
                }

                # Construct the chain for structured output
                structured_chain = structured_prompt_template | self.structured_llm
                structured_response: LLMStructuredOutput = await structured_chain.ainvoke(structured_input)

                follow_ups = structured_response.follow_up_questions
                if follow_ups and not all(isinstance(q, str) and q.strip() for q in follow_ups):
                    logger.warning(f"LLM returned invalid follow-ups: {follow_ups}. Discarding.")
                    follow_ups = None
                elif follow_ups and any(len(q.split()) > 7 for q in follow_ups): # Heuristic for too long
                    logger.warning(f"LLM returned follow-ups that are too long: {follow_ups}. Discarding some or all if not useful.")
                    # Potentially filter here, or just let them pass if they are still somewhat useful

                final_response_data = StreamedChatResponse(
                    text_chunk=None,
                    follow_up_prompts=follow_ups if follow_ups else None, # Ensure None if empty list
                    is_final=True
                )
                yield f"data: {final_response_data.model_dump_json()}\n\n"
                logger.info(f"Final response chunk sent. Follow-ups: {follow_ups}")

            except ValidationError as ve:
                logger.error(f"Pydantic validation error generating follow-up questions: {ve}", exc_info=True)
                final_response_data = StreamedChatResponse(is_final=True) # Send final without follow-ups
                yield f"data: {final_response_data.model_dump_json()}\n\n"
            except Exception as e:
                logger.error(f"Error generating follow-up questions: {str(e)}", exc_info=True)
                final_response_data = StreamedChatResponse(is_final=True) # Send final without follow-ups
                yield f"data: {final_response_data.model_dump_json()}\n\n"

        except ValueError as ve: # Catch specific ValueErrors like missing user_id/tutor_name
            logger.error(f"Configuration error in chat response: {str(ve)}", exc_info=True)
            error_response = StreamedChatResponse(
                text_chunk=f"I apologize, but there's a configuration issue: {str(ve)}",
                is_final=True
            ).model_dump_json()
            yield f"data: {error_response}\n\n"
        except Exception as e:
            logger.error(f"Error in chat response: {str(e)}", exc_info=True)
            error_response_data = StreamedChatResponse(
                text_chunk=f"I apologize, but I encountered an error. Please try again later.",
                is_final=True
            ).model_dump_json()
            yield f"data: {error_response_data}\n\n"