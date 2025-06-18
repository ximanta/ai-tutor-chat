'use client'; 

import { cn } from "@/lib/utils";
import { Button } from '@/components/ui/button'; // Assuming you have a shadcn/ui Button component

interface MessageProps {
    content: string;
    isAI: boolean;
    followUpPrompts?: string[]; // Renamed from keywords
    isStreaming?: boolean; // Added for streaming indication
    onFollowUpClick?: (prompt: string) => void; // New prop for click handler
}

export function ChatMessage({ content, isAI, followUpPrompts, isStreaming = false, onFollowUpClick }: MessageProps) {
    return (
        <div className={cn(
            "flex w-full",
            isAI ? "justify-start" : "justify-end"
        )}>
            <div className={cn(
                "max-w-[80%] rounded-lg px-4 py-2 mb-2",
                isAI ? "bg-secondary text-secondary-foreground" : "bg-primary text-primary-foreground",
                isAI && isStreaming && "animate-pulse" // Simple pulse for streaming AI response
            )}>
                <div className="whitespace-pre-wrap">{content}</div>
                {/* Check for followUpPrompts instead of keywords */}
                {isAI && followUpPrompts && followUpPrompts.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2"> {/* Increased gap for better spacing */}
                        {followUpPrompts.map((prompt, index) => (
                            <Button // Changed from <span> to <Button> for clickability
                                key={index} // Using index as key is generally okay for static lists, but if prompts can reorder or be identical, a unique ID per prompt is better.
                                onClick={() => onFollowUpClick?.(prompt)} // Call the provided handler on click
                                className="inline-block bg-muted text-muted-foreground rounded-full px-3 py-1 text-sm
                                           hover:bg-muted/80 focus-visible:outline-none focus-visible:ring-2 
                                           focus-visible:ring-ring focus-visible:ring-offset-2" // Dark mode compatible
                                variant="outline" // Assuming shadcn/ui button variants
                            >
                                {prompt}
                            </Button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}