// Centralized localStorage management for chat conversation history
export const CONVERSATIONS_HISTORY_KEY = 'chatConversationsHistory_v1';
export const MAX_HISTORY_ITEMS = 15;

export interface ConversationSummary {
    id: string; // UUID
    title: string;
    lastActivity: number; // Timestamp
}

function safeParse(json: string): any {
    try {
        return JSON.parse(json);
    } catch {
        return null;
    }
}

export function loadConversations(): ConversationSummary[] {
    if (typeof window === 'undefined') return [];
    const raw = localStorage.getItem(CONVERSATIONS_HISTORY_KEY);
    if (!raw) return [];
    const parsed = safeParse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
        .filter((c: any) => c && c.id && c.title && c.lastActivity)
        .sort((a: ConversationSummary, b: ConversationSummary) => b.lastActivity - a.lastActivity);
}

export function saveConversations(conversations: ConversationSummary[]): void {
    if (typeof window === 'undefined') return;
    const sorted = [...conversations].sort((a, b) => b.lastActivity - a.lastActivity).slice(0, MAX_HISTORY_ITEMS);
    localStorage.setItem(CONVERSATIONS_HISTORY_KEY, JSON.stringify(sorted));
}

export function createNewConversationSummary(): ConversationSummary {
    const newId = (typeof crypto !== 'undefined' && crypto.randomUUID)
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now();
    return {
        id: newId,
        title: 'New Conversation',
        lastActivity: Date.now(),
    };
}

export function addOrUpdateConversationInStorage(conversation: ConversationSummary): ConversationSummary[] {
    const conversations = loadConversations();
    const idx = conversations.findIndex(c => c.id === conversation.id);
    if (idx !== -1) {
        conversations[idx] = { ...conversations[idx], ...conversation };
    } else {
        conversations.unshift(conversation);
    }
    saveConversations(conversations);
    return loadConversations();
}

export function deleteConversationFromStorage(id: string): ConversationSummary[] {
    const conversations = loadConversations().filter(c => c.id !== id);
    saveConversations(conversations);
    return loadConversations();
}
