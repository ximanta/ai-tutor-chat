import { ChatRequest, StreamResponse } from '@/types/chat';

export async function* chatStream(request: ChatRequest): AsyncGenerator<StreamResponse, void, unknown> {
    console.log('Sending request to backend:', request);
    
    try {
        const response = await fetch('http://localhost:8000/aitutor/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
            },
            body: JSON.stringify(request),
        });

        console.log('Received response:', response.status, response.statusText);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('No reader available');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('Stream complete');
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                console.log('Received chunk:', chunk);
                
                buffer += chunk;
                const lines = buffer.split('\n');
                
                // Process all complete lines
                buffer = lines.pop() || ''; // Keep the last incomplete line in buffer
                
                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (trimmedLine.startsWith('data: ')) {
                        try {
                            const jsonStr = trimmedLine.slice(6);
                            const data = JSON.parse(jsonStr) as StreamResponse;
                            console.log('Parsed SSE data:', data);
                            yield data;
                        } catch (e) {
                            console.error('Error parsing SSE data:', trimmedLine, e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    } catch (error) {
        console.error('Error in chatStream:', error);
        throw error;
    }
}

export async function fetchMessagesForConversation(conversationId: string): Promise<Array<{role: string, content: string}> | null> {
    try {
        const response = await fetch(`http://localhost:8000/aitutor/api/conversations/memory/${conversationId}`);
        if (!response.ok) return null;
        return await response.json();
    } catch (e) {
        console.error('Failed to fetch conversation memory', e);
        return null;
    }
}

export async function clearBackendMemory(conversationId: string): Promise<void> {
    try {
        await fetch(`http://localhost:8000/aitutor/chat/memory/${conversationId}`, { method: 'DELETE' });
    } catch (e) {
        console.error('Failed to clear backend memory', e);
    }
}
