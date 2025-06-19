'use client';

import { ConversationSummary } from '@/lib/conversation-manager';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react'; // For delete icon, or use any icon you prefer

interface ChatSidebarProps {
    conversations: ConversationSummary[];
    activeConversationId: string | null;
    onSelectConversation: (id: string) => void;
    onNewChat: () => void;
    onDeleteConversation: (id: string) => void;
}

export function ChatSidebar({
    conversations,
    activeConversationId,
    onSelectConversation,
    onNewChat,
    onDeleteConversation,
}: ChatSidebarProps) {
    return (
        <aside className="w-64 min-w-[200px] max-w-xs border-r h-full flex flex-col bg-background">
            <div className="p-4 border-b">
                <Button onClick={onNewChat} className="w-full mb-4">New Chat</Button>
                <h2 className="text-lg font-semibold mb-2">History</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
                {conversations.length === 0 ? (
                    <div className="text-muted-foreground text-sm px-2 py-4">No chat history.</div>
                ) : (
                    <ul className="space-y-1">
                        {conversations.map((conv) => (
                            <li key={conv.id} className="relative group">
                                <Button
                                    variant={activeConversationId === conv.id ? 'secondary' : 'ghost'}
                                    onClick={() => onSelectConversation(conv.id)}
                                    className="w-full justify-between pr-10 truncate"
                                >
                                    <span className="truncate">{conv.title}</span>
                                </Button>
                                <button
                                    className="absolute right-2 top-1/2 -translate-y-1/2 opacity-60 hover:opacity-100 text-destructive p-1 rounded group-hover:opacity-100 focus:outline-none"
                                    title="Delete conversation"
                                    onClick={e => {
                                        e.stopPropagation();
                                        if (window.confirm('Delete this conversation?')) {
                                            onDeleteConversation(conv.id);
                                        }
                                    }}
                                >
                                    <X size={16} />
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </aside>
    );
}
