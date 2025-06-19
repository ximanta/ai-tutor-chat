export interface ChatContext {
    userId: string;
    tutorName: string;
}

export interface ChatRequest {
    conversationId: string; // Added for conversational memory
    message: string;
    context: ChatContext;
}

export interface StreamResponse {
    text_chunk?: string;
    follow_up_prompts?: string[];
    is_final: boolean;
}

export interface ConversationSummary {
    id: string; // UUID
    title: string;
    lastActivity: number; // Timestamp
}
