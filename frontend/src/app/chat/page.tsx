'use client'; 

import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '@/components/client/ChatMessage';
import { Button } from '@/components/ui/button';
import { ChatSidebar } from '@/components/client/ChatSidebar';
import { chatStream, fetchMessagesForConversation, clearBackendMemory } from '@/lib/chat-api';
import {
    loadConversations,
    saveConversations,
    createNewConversationSummary,
    addOrUpdateConversationInStorage,
    deleteConversationFromStorage,
    ConversationSummary,
} from '@/lib/conversation-manager';

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
    const [conversationsHistory, setConversationsHistory] = useState<ConversationSummary[]>([]);
    const [currentConversationTitle, setCurrentConversationTitle] = useState<string>('');
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

    // On mount: load conversation history and set initial conversation
    useEffect(() => {
        const history = loadConversations();
        setConversationsHistory(history);
        if (history.length > 0 && !currentConversationId) {
            setCurrentConversationId(history[0].id);
            setCurrentConversationTitle(history[0].title);
        } else if (history.length === 0 && !currentConversationId) {
            handleNewChatInternalLogic(false);
        }
    }, []);

    // When currentConversationId changes, load messages and set title
    useEffect(() => {
        const loadMessages = async () => {
            if (currentConversationId) {
                setIsLoading(true);
                setMessages([]);
                const found = conversationsHistory.find(c => c.id === currentConversationId);
                setCurrentConversationTitle(found ? found.title : 'Chat');
                const historicalMsgs = await fetchMessagesForConversation(currentConversationId);
                if (historicalMsgs && Array.isArray(historicalMsgs)) {
                    setMessages(
                        historicalMsgs.map((msg, idx) => ({
                            id: `${currentConversationId}-msg-${idx}`,
                            content: msg.content,
                            isAI: msg.role !== 'user',
                        }))
                    );
                }
                setIsLoading(false);
            } else {
                setMessages([]);
                setCurrentConversationTitle('Select or Start a Chat');
            }
        };
        loadMessages();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentConversationId]);

    // Function to handle clicking on a follow-up prompt
    const handleFollowUpClick = (prompt: string) => {
        // Automatically send the follow-up prompt as a new user message
        handleSubmit({ preventDefault: () => {} } as React.FormEvent, prompt);
    };

    // Select a conversation from sidebar
    const handleSelectConversation = (id: string) => {
        setCurrentConversationId(id);
    };

    // Internal logic for starting a new chat
    const handleNewChatInternalLogic = (shouldClearOldBackendMemory: boolean, oldIdToClear?: string) => {
        if (shouldClearOldBackendMemory && oldIdToClear) {
            clearBackendMemory(oldIdToClear);
        }
        const newConv = createNewConversationSummary();
        const updatedHistory = addOrUpdateConversationInStorage(newConv);
        setConversationsHistory(updatedHistory);
        setCurrentConversationId(newConv.id);
        setCurrentConversationTitle(newConv.title);
        setMessages([]);
        setInput('');
        setCurrentStreamingAIResponse(null);
        setCurrentStreamingFollowUpPrompts(null);
    };

    // Handler for sidebar's New Chat button
    const handleNewChatClick = () => {
        handleNewChatInternalLogic(true, currentConversationId || undefined);
    };

    // Handler for deleting a conversation
    const handleDeleteConversation = (id: string) => {
        const updatedHistory = deleteConversationFromStorage(id);
        setConversationsHistory(updatedHistory);
        if (id === currentConversationId) {
            if (updatedHistory.length > 0) {
                setCurrentConversationId(updatedHistory[0].id);
            } else {
                handleNewChatInternalLogic(false);
            }
        }
    };

    const handleSubmit = async (e: React.FormEvent, predefinedMessage?: string) => {
        e.preventDefault();
        if (!currentConversationId) return;
        const userMessage = predefinedMessage || input.trim();
        if (!userMessage || isLoading) return;
        setInput('');
        setMessages(prev => [...prev, { id: Date.now().toString() + '-user', content: userMessage, isAI: false }]);
        
        // Title update logic
        const currentConvSummary = conversationsHistory.find(c => c.id === currentConversationId);
        if (currentConvSummary && (currentConvSummary.title === 'New Conversation' || messages.filter(m => !m.isAI).length === 1)) {
            const newTitle = userMessage.substring(0, 40) + (userMessage.length > 40 ? '...' : '');
            const updatedConv = { ...currentConvSummary, title: newTitle, lastActivity: Date.now() };
            const updatedHistory = addOrUpdateConversationInStorage(updatedConv);
            setConversationsHistory(updatedHistory);
            setCurrentConversationTitle(newTitle);
        } else if (currentConvSummary) {
            const updatedConv = { ...currentConvSummary, lastActivity: Date.now() };
            const updatedHistory = addOrUpdateConversationInStorage(updatedConv);
            setConversationsHistory(updatedHistory);
        }
        setIsLoading(true);
        let accumulatedContent = '';

        try {
            for await (const chunk of chatStream({
                conversationId: currentConversationId,
                message: userMessage,
                context: {
                    userId: 'xam@gmail.com',
                    tutorName: 'Alice',
                },
            })) {
                if (chunk.text_chunk) {
                    accumulatedContent += chunk.text_chunk;
                    setCurrentStreamingAIResponse(accumulatedContent);
                }

                if (chunk.follow_up_prompts) {
                    setCurrentStreamingFollowUpPrompts(chunk.follow_up_prompts);
                }

                if (chunk.is_final) {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: Date.now().toString() + '-ai-final',
                            content: accumulatedContent,
                            isAI: true,
                            followUpPrompts: chunk.follow_up_prompts,
                        },
                    ]);
                    setCurrentStreamingAIResponse(null);
                    setCurrentStreamingFollowUpPrompts(null);
                    break;
                }
            }
        } catch (error) {
            setMessages(prev => [
                ...prev,
                {
                    id: Date.now().toString() + '-error',
                    content: 'Sorry, there was an error processing your message.',
                    isAI: true,
                },
            ]);
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

    return (
        <div className="flex h-screen">
            <ChatSidebar
                conversations={conversationsHistory}
                activeConversationId={currentConversationId}
                onSelectConversation={handleSelectConversation}
                onNewChat={handleNewChatClick}
                onDeleteConversation={handleDeleteConversation}
            />
            <div className="flex-grow flex flex-col">
                <div className="p-4 border-b">
                    <h1 className="text-xl font-semibold truncate">{currentConversationTitle || 'Chat'}</h1>
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
        </div>
    );
}