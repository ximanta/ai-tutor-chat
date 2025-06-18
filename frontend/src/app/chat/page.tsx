'use client'; 

import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '@/components/client/ChatMessage';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { chatStream } from '@/lib/chat-api';

const CONVERSATION_ID_STORAGE_KEY = 'activeConversationId';

// Define the shape of a chat message to be stored in the component's state
// It should now include 'follow_up_prompts' instead of 'keywords'
interface MessageState {
    id: string; // Add an ID for better key management in lists
    content: string;
    isAI: boolean;
    followUpPrompts?: string[]; // Renamed from 'keywords'
    isStreaming?: boolean; // To indicate if a message is currently being streamed
}

export default function ChatPage() {
    const [messages, setMessages] = useState<MessageState[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    
    // This state will temporarily hold the streaming AI response
    // to distinguish it from finalized messages
    const [currentStreamingAIResponse, setCurrentStreamingAIResponse] = useState<string | null>(null);
    const [currentStreamingFollowUpPrompts, setCurrentStreamingFollowUpPrompts] = useState<string[] | null>(null);


    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, currentStreamingAIResponse]); // Scroll when messages or streaming response updates

    // Initialize or restore conversationId
    useEffect(() => {
        const storedConversationId = localStorage.getItem(CONVERSATION_ID_STORAGE_KEY);
        if (storedConversationId) {
            setCurrentConversationId(storedConversationId);
        } else {
            const newId = (typeof crypto !== 'undefined' && crypto.randomUUID)
                ? crypto.randomUUID()
                : Math.random().toString(36).slice(2) + Date.now(); // fallback
            setCurrentConversationId(newId);
            localStorage.setItem(CONVERSATION_ID_STORAGE_KEY, newId);
        }
    }, []);

    // Function to handle clicking on a follow-up prompt
    const handleFollowUpClick = (prompt: string) => {
        // Automatically send the follow-up prompt as a new user message
        handleSubmit({ preventDefault: () => {} } as React.FormEvent, prompt);
    };

    const handleSubmit = async (e: React.FormEvent, predefinedMessage?: string) => {
        e.preventDefault();

        // Ensure conversation ID exists before sending a message
        if (!currentConversationId) {
            console.error("No active conversation ID. Cannot send message.");
            return;
        }

        const userMessage = predefinedMessage || input.trim();
        if (!userMessage || isLoading) return;

        setInput(''); // Clear input for manual entry
        
        // Add user message to state
        setMessages(prev => [...prev, { id: Date.now().toString() + '-user', content: userMessage, isAI: false }]);
        
        setIsLoading(true);
        let accumulatedContent = ''; // Keep track of accumulated content

        try {
            for await (const chunk of chatStream({
                conversationId: currentConversationId, // Pass conversationId
                message: userMessage,
                context: {
                    userId: 'xam@gmail.com', // Use consistent userId
                    tutorName: 'Alice'
                }
            })) {
                if (chunk.text_chunk) {
                    accumulatedContent += chunk.text_chunk;
                    setCurrentStreamingAIResponse(accumulatedContent);
                }

                if (chunk.follow_up_prompts) {
                    setCurrentStreamingFollowUpPrompts(chunk.follow_up_prompts);
                }

                if (chunk.is_final) {
                    // When the stream is final, add the complete message to the messages array
                    setMessages(prev => [
                        ...prev,
                        {
                            id: Date.now().toString() + '-ai-final',
                            content: accumulatedContent, // Use accumulated content instead of state
                            isAI: true,
                            followUpPrompts: chunk.follow_up_prompts
                        }
                    ]);
                    setCurrentStreamingAIResponse(null);
                    setCurrentStreamingFollowUpPrompts(null);
                    break;
                }
            }
        } catch (error) {
            console.error('Error during chat stream:', error);
            setMessages(prev => [...prev, {
                id: Date.now().toString() + '-error',
                content: 'Sorry, there was an error processing your message.',
                isAI: true
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as unknown as React.FormEvent);
        }
    };

    const handleNewChat = () => {
        setMessages([]);
        setCurrentStreamingAIResponse(null);
        setCurrentStreamingFollowUpPrompts(null);
        setInput('');
        const newId = (typeof crypto !== 'undefined' && crypto.randomUUID)
            ? crypto.randomUUID()
            : Math.random().toString(36).slice(2) + Date.now(); // fallback
        setCurrentConversationId(newId);
        localStorage.setItem(CONVERSATION_ID_STORAGE_KEY, newId);
        // Optionally: clear backend memory for old conversationId
    };

    return (
        <div className="flex flex-col h-screen">
            {/* New Chat Button */}
            <div className="p-4 border-b flex items-center gap-4">
                <Button onClick={handleNewChat} className="mb-0">
                    New Chat
                </Button>
                {/* Optionally show conversationId for debugging */}
                {/* <span className="text-xs text-muted-foreground">ID: {currentConversationId}</span> */}
            </div>
            <div className="flex-grow overflow-y-auto p-4">
                {/* Render all finalized messages */}
                {messages.map((message) => (
                    <ChatMessage
                        key={message.id}
                        content={message.content}
                        isAI={message.isAI}
                        followUpPrompts={message.followUpPrompts}
                        onFollowUpClick={handleFollowUpClick}
                    />
                ))}
                
                {/* Render currently streaming message if exists */}
                {currentStreamingAIResponse && (
                    <ChatMessage
                        content={currentStreamingAIResponse}
                        isAI={true}
                        isStreaming={true}
                        followUpPrompts={currentStreamingFollowUpPrompts || undefined}
                        onFollowUpClick={handleFollowUpClick}
                    />
                )}
                
                {/* Invisible div for scrolling */}
                <div ref={messagesEndRef} />
            </div>

            {/* Chat input form */}
            <form onSubmit={handleSubmit} className="p-4 border-t">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your message..."
                        className="flex-grow p-2 border rounded"
                        disabled={isLoading}
                    />
                    <Button type="submit" disabled={isLoading}>
                        Send
                    </Button>
                </div>
            </form>
        </div>
    );
}