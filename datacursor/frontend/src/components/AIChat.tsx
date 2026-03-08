/**
 * AIChat Component - Context-aware AI sidebar.
 */

import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Bot, Info, Code2, Database, Zap, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { RuntimeContext, AIResponseResult } from '../hooks/useWebSocket';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

interface AIChatProps {
    context: RuntimeContext | null;
    onSendMessage: (message: string) => void;
    isConnected: boolean;
    activeProvider?: string;
    onApplyCode?: (code: string) => void;
    onAIResponse: (callback: (result: AIResponseResult) => void) => () => void;
}

const PROVIDER_COLORS: Record<string, string> = {
    openai: '#10a37f',
    anthropic: '#cc785c',
    google: '#4285f4',
    ollama: '#ffffff',
    groq: '#f55036',
    openrouter: '#7f5af0',
};

const PROVIDER_NAMES: Record<string, string> = {
    openai: 'GPT-4',
    anthropic: 'Claude',
    google: 'Gemini',
    ollama: 'Ollama',
    groq: 'Groq',
    openrouter: 'OpenRouter',
};

export function AIChat({
    context,
    onSendMessage,
    isConnected,
    activeProvider = 'google',
    onApplyCode,
    onAIResponse,
}: AIChatProps) {
    const [input, setInput] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: "I'm your AI data science assistant with access to your notebook's runtime context. Press ⌘K in any cell for code generation, or ask me questions here.",
            timestamp: new Date(),
        },
    ]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isGenerating]);

    // Handle AI Responses
    useEffect(() => {
        if (!onAIResponse) return;
        return onAIResponse((result) => {
            setIsGenerating(false);
            if (result.error) {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `**Error:** ${result.error}`,
                    timestamp: new Date()
                }]);
            } else if (result.code) {
                // If we receive code, display it
                // We wrap it in python block for now as default
                const content = "Here is the code:\n\n```python\n" + result.code + "\n```";
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: content,
                    timestamp: new Date()
                }]);
            }
        });
    }, [onAIResponse]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage: Message = {
            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        onSendMessage(input);
        setInput('');
        setIsGenerating(true);

        // Optimistic loading state or similar could be added here
    };

    // Custom Code Block Renderer with "Apply" button
    const CodeBlock = ({ node, inline, className, children, ...props }: any) => {
        const match = /language-(\w+)/.exec(className || '');
        const code = String(children).replace(/\n$/, '');
        const [copied, setCopied] = useState(false);
        const [applied, setApplied] = useState(false);

        const handleCopy = () => {
            navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        };

        const handleApply = () => {
            console.log('[AIChat] Apply button clicked', { code });
            if (onApplyCode) {
                onApplyCode(code);
                setApplied(true);
                setTimeout(() => setApplied(false), 2000);
            }
        };

        return !inline && match ? (
            <div className="rounded border border-[var(--dc-border)] overflow-hidden my-2 bg-[#1e1e1e]">
                <div className="flex items-center justify-between px-2 py-1.5 bg-[#2d2d2d] border-b border-[#404040]">
                    <span className="text-[10px] text-gray-400 font-mono">{match[1]}</span>
                    <div className="flex gap-2">
                        <button
                            onClick={handleCopy}
                            className="flex items-center gap-1 text-[10px] text-gray-400 hover:text-white transition-colors"
                            title="Copy to clipboard"
                        >
                            {copied ? <Check size={12} /> : <Copy size={12} />}
                            {copied ? 'Copied' : 'Copy'}
                        </button>
                        {onApplyCode && (
                            <button
                                onClick={handleApply}
                                className={`flex items-center gap-1 text-[10px] font-medium transition-colors ${applied ? 'text-[var(--dc-success)]' : 'text-[var(--dc-accent)] hover:text-white'}`}
                                title="Apply to active cell"
                            >
                                {applied ? <Check size={12} /> : <Zap size={12} />}
                                {applied ? 'Applied' : 'Apply'}
                            </button>
                        )}
                    </div>
                </div>
                <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{ margin: 0, padding: '12px', background: 'transparent', fontSize: '12px' }}
                    {...props}
                >
                    {code}
                </SyntaxHighlighter>
            </div>
        ) : (
            <code className={className} {...props}>
                {children}
            </code>
        );
    };

    return (
        <div className="ai-sidebar w-80 flex flex-col h-full bg-[var(--dc-bg-secondary)] border-l border-[var(--dc-border)]">
            {/* Header */}
            <div className="p-4 border-b border-[var(--dc-border)] bg-[var(--dc-bg-secondary)]">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <Sparkles className="text-[var(--dc-accent)]" size={20} />
                        <h2 className="font-semibold text-[var(--dc-text-primary)]">AI Assistant</h2>
                    </div>
                </div>

                {/* Provider Badge */}
                <div className="flex items-center justify-between">
                    <div className={`text-xs flex items-center gap-1 ${isConnected ? 'text-[var(--dc-success)]' : 'text-[var(--dc-error)]'} `}>
                        <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[var(--dc-success)]' : 'bg-[var(--dc-error)]'} `} />
                        {isConnected ? 'Connected' : 'Disconnected'}
                    </div>

                    <div
                        className="flex items-center gap-1 px-2 py-1 rounded text-xs"
                        style={{
                            backgroundColor: `${PROVIDER_COLORS[activeProvider] || '#58a6ff'}20`,
                            color: PROVIDER_COLORS[activeProvider] || '#58a6ff'
                        }}
                    >
                        <Bot size={12} />
                        {PROVIDER_NAMES[activeProvider] || activeProvider}
                    </div>
                </div>
            </div>

            {/* Context Panel */}
            <div className="p-3 border-b border-[var(--dc-border)] bg-[var(--dc-bg-tertiary)]">
                <div className="flex items-center gap-2 mb-2">
                    <Info size={14} className="text-[var(--dc-text-secondary)]" />
                    <span className="text-[10px] font-bold text-[var(--dc-text-secondary)] tracking-wider">RUNTIME CONTEXT</span>
                </div>

                {context ? (
                    <div className="space-y-2">
                        {/* Variables */}
                        <div>
                            <div className="flex items-center gap-1 mb-1">
                                <Code2 size={12} className="text-[var(--dc-accent)]" />
                                <span className="text-[10px] text-[var(--dc-text-secondary)]">Variables</span>
                            </div>
                            <div className="flex flex-wrap gap-1">
                                {context.variables.length > 0 ? (
                                    context.variables.slice(0, 8).map((v) => (
                                        <span key={v.name} className="context-badge">
                                            {v.name}
                                            <span className="opacity-60">({v.type})</span>
                                        </span>
                                    ))
                                ) : (
                                    <span className="text-[10px] text-[var(--dc-text-secondary)] italic">No variables</span>
                                )}
                                {context.variables.length > 8 && (
                                    <span className="context-badge opacity-60">
                                        +{context.variables.length - 8} more
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* DataFrames */}
                        {context.dataframes.length > 0 && (
                            <div>
                                <div className="flex items-center gap-1 mb-1">
                                    <Database size={12} className="text-[var(--dc-success)]" />
                                    <span className="text-[10px] text-[var(--dc-text-secondary)]">DataFrames</span>
                                </div>
                                <div className="space-y-1">
                                    {context.dataframes.map((df) => (
                                        <div key={df.name} className="text-[10px] p-1.5 rounded bg-[var(--dc-bg-secondary)] border border-[var(--dc-border)]">
                                            <div className="font-medium text-[var(--dc-text-primary)]">{df.name}</div>
                                            <div className="text-[var(--dc-text-secondary)]" title={`${df.shape} • ${df.columns?.join(', ')}`}>
                                                {df.shape} • {df.columns?.length || 0} cols
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Last Output Indicator (New) */}
                        {context.last_output && (
                            <div className="flex items-center gap-1 mt-2 text-[10px] text-[var(--dc-success)]">
                                <Check size={10} />
                                <span>Context updated with last execution</span>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="text-xs text-[var(--dc-text-secondary)] italic">
                        Run code to see context
                    </div>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`ai-message ${msg.role}`}
                    >
                        <ReactMarkdown
                            components={{
                                code: CodeBlock
                            }}
                        >
                            {msg.content}
                        </ReactMarkdown>
                        <span className="text-[10px] opacity-40 mt-1 block text-right">
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    </div>
                ))}
                {isGenerating && (
                    <div className="ai-message assistant">
                        <div className="flex items-center gap-2 text-[var(--dc-text-secondary)]">
                            <Sparkles size={16} className="animate-pulse" />
                            <span className="text-xs">Generating response...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-4 border-t border-[var(--dc-border)] bg-[var(--dc-bg-secondary)]">
                <div className="flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask AI..."
                        className="flex-1 bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] rounded-lg px-3 py-2 text-sm text-[var(--dc-text-primary)] placeholder:text-[var(--dc-text-secondary)] focus:outline-none focus:border-[var(--dc-accent)] transition-colors"
                    />
                    <button
                        type="submit"
                        className="btn btn-primary p-2 h-full aspect-square flex items-center justify-center"
                        disabled={!input.trim()}
                    >
                        <Send size={16} />
                    </button>
                </div>
                <div className="text-[10px] text-[var(--dc-text-secondary)] mt-2 text-center opacity-70">
                    Use <span className="kbd text-[9px] px-1 py-0.5">⌘K</span> in cells for inline edits
                </div>
            </form>
        </div>
    );
}
