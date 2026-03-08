/**
 * Cell Component - Individual notebook cell with Monaco Editor and output area.
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import type { OnMount } from '@monaco-editor/react';
import { Play, Square, Sparkles, Trash2, GripVertical } from 'lucide-react';
import { DiffView, type DiffLine } from './DiffView';

export interface CellOutput {
    type: string;
    text?: string;
    data?: Record<string, unknown>;
    name?: string;
    ename?: string;
    evalue?: string;
    traceback?: string[];
}

interface CellProps {
    id: string;
    initialCode?: string;
    isActive: boolean;
    isRunning: boolean;
    outputs: CellOutput[];
    executionCount: number | null;
    onExecute: (id: string, code: string) => void;
    onAIRequest: (id: string, prompt: string, code: string) => void;
    onDelete: (id: string) => void;
    onFocus: (id: string) => void;
    onCodeChange: (id: string, code: string) => void;
    aiSuggestion?: {
        code: string;
        diff: DiffLine[];
    } | null;
    onAcceptAI?: (id: string, code: string) => void;
    onRejectAI?: (id: string) => void;
}

export function Cell({
    id,
    initialCode = '',
    isActive,
    isRunning,
    outputs,
    executionCount,
    onExecute,
    onAIRequest,
    onDelete,
    onFocus,
    onCodeChange,
    aiSuggestion,
    onAcceptAI,
    onRejectAI,
}: CellProps) {
    const [code, setCode] = useState(initialCode);
    const [showAIPrompt, setShowAIPrompt] = useState(false);
    const [aiPrompt, setAIPrompt] = useState('');
    const editorRef = useRef<unknown>(null);
    const promptInputRef = useRef<HTMLInputElement>(null);

    // Sync local state with prop when external updates occur (e.g. Apply from Chat)
    useEffect(() => {
        setCode(initialCode);
    }, [initialCode]);

    const handleEditorMount: OnMount = (editor) => {
        editorRef.current = editor;

        // Add Cmd+Enter to execute
        editor.addCommand(
            // Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux)
            2048 | 3, // monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter
            () => {
                onExecute(id, code);
            }
        );

        // Add Shift+Enter to execute and move to next cell
        editor.addCommand(
            1024 | 3, // monaco.KeyMod.Shift | monaco.KeyCode.Enter
            () => {
                onExecute(id, code);
            }
        );

        // Add Cmd+K for AI request
        editor.addCommand(
            2048 | 41, // monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyK
            () => {
                setShowAIPrompt(true);
                setTimeout(() => promptInputRef.current?.focus(), 100);
            }
        );

        // Update active cell on editor focus
        editor.onDidFocusEditorText(() => {
            onFocus(id);
        });
    };

    const handleCodeChange = useCallback((value: string | undefined) => {
        const newCode = value || '';
        setCode(newCode);
        onCodeChange(id, newCode);
    }, [id, onCodeChange]);

    const handleAISubmit = useCallback((e: React.FormEvent) => {
        e.preventDefault();
        if (aiPrompt.trim()) {
            onAIRequest(id, aiPrompt, code);
            setAIPrompt('');
            setShowAIPrompt(false);
        }
    }, [id, aiPrompt, code, onAIRequest]);

    const handleAcceptAI = useCallback(() => {
        if (aiSuggestion) {
            setCode(aiSuggestion.code);
            onAcceptAI?.(id, aiSuggestion.code);
        }
    }, [id, aiSuggestion, onAcceptAI]);

    const handleRejectAI = useCallback(() => {
        onRejectAI?.(id);
    }, [id, onRejectAI]);

    useEffect(() => {
        if (showAIPrompt) {
            promptInputRef.current?.focus();
        }
    }, [showAIPrompt]);

    // Format output for display
    const renderOutput = (output: CellOutput, index: number) => {
        if (output.type === 'stream') {
            return (
                <div key={index} className="cell-output">
                    {output.text}
                </div>
            );
        }

        if (output.type === 'execute_result') {
            return (
                <div key={index} className="cell-output">
                    {output.text || JSON.stringify(output.data)}
                </div>
            );
        }

        if (output.type === 'error') {
            return (
                <div key={index} className="cell-output error">
                    <div className="font-bold">{output.ename}: {output.evalue}</div>
                    {output.traceback?.map((line, i) => (
                        <div key={i} dangerouslySetInnerHTML={{
                            __html: line.replace(/\x1b\[[0-9;]*m/g, '')
                        }} />
                    ))}
                </div>
            );
        }

        if (output.type === 'display_data' && output.data) {
            // Handle images
            if (output.data['image/png']) {
                return (
                    <div key={index} className="cell-output">
                        <img
                            src={`data:image/png;base64,${output.data['image/png']}`}
                            alt="Output"
                            className="max-w-full"
                        />
                    </div>
                );
            }
            // Handle HTML
            if (output.data['text/html']) {
                return (
                    <div
                        key={index}
                        className="cell-output"
                        dangerouslySetInnerHTML={{ __html: output.data['text/html'] as string }}
                    />
                );
            }
        }

        return null;
    };

    return (
        <div
            className={`cell ${isActive ? 'active' : ''} ${isRunning ? 'running' : ''}`}
            onClick={() => onFocus(id)}
        >
            {/* Cell Header */}
            <div className="cell-header">
                <div className="flex items-center gap-3">
                    <GripVertical size={16} className="text-[var(--dc-text-secondary)] cursor-grab" />
                    <span className="text-xs text-[var(--dc-text-secondary)] font-mono">
                        [{executionCount ?? ' '}]
                    </span>
                    {isRunning && (
                        <span className="text-xs text-[var(--dc-warning)] flex items-center gap-1 animate-pulse">
                            <div className="spinner" />
                            Running...
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-2">
                    <span className="kbd">⌘K</span>
                    <span className="text-xs text-[var(--dc-text-secondary)]">AI</span>

                    <button
                        onClick={() => onExecute(id, code)}
                        className="btn btn-ghost"
                        disabled={isRunning}
                        title="Run cell (⌘Enter)"
                    >
                        {isRunning ? <Square size={14} /> : <Play size={14} />}
                    </button>

                    <button
                        onClick={() => {
                            setShowAIPrompt(true);
                            setTimeout(() => promptInputRef.current?.focus(), 100);
                        }}
                        className="btn btn-ghost"
                        title="AI Assist (⌘K)"
                    >
                        <Sparkles size={14} />
                    </button>

                    <button
                        onClick={() => onDelete(id)}
                        className="btn btn-ghost text-[var(--dc-error)]"
                        title="Delete cell"
                    >
                        <Trash2 size={14} />
                    </button>
                </div>
            </div>

            {/* AI Prompt Input */}
            {showAIPrompt && (
                <form onSubmit={handleAISubmit} className="p-3 border-b border-[var(--dc-border)] bg-[rgba(88,166,255,0.05)]">
                    <div className="flex items-center gap-2">
                        <Sparkles size={16} className="text-[var(--dc-accent)]" />
                        <input
                            ref={promptInputRef}
                            type="text"
                            value={aiPrompt}
                            onChange={(e) => setAIPrompt(e.target.value)}
                            placeholder="What would you like to do? (e.g., 'plot a histogram of the age column')"
                            className="flex-1 bg-transparent border-none outline-none text-sm text-[var(--dc-text-primary)] placeholder:text-[var(--dc-text-secondary)]"
                            onKeyDown={(e) => {
                                if (e.key === 'Escape') {
                                    setShowAIPrompt(false);
                                    setAIPrompt('');
                                }
                            }}
                        />
                        <button type="submit" className="btn btn-primary">
                            Generate
                        </button>
                    </div>
                </form>
            )}

            {/* AI Suggestion Diff View */}
            {aiSuggestion && (
                <div className="p-3 border-b border-[var(--dc-border)]">
                    <DiffView
                        diff={aiSuggestion.diff}
                        onAccept={handleAcceptAI}
                        onReject={handleRejectAI}
                    />
                </div>
            )}

            {/* Monaco Editor */}
            <Editor
                height={Math.max(100, code.split('\n').length * 20 + 20)}
                language="python"
                theme="vs-dark"
                value={code}
                onChange={handleCodeChange}
                onMount={handleEditorMount}
                options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    lineNumbersMinChars: 3,
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    automaticLayout: true,
                    padding: { top: 8, bottom: 8 },
                    renderLineHighlight: 'none',
                    overviewRulerBorder: false,
                    hideCursorInOverviewRuler: true,
                    scrollbar: {
                        vertical: 'hidden',
                        horizontal: 'hidden',
                    },
                }}
            />

            {/* Cell Output */}
            {outputs.length > 0 && (
                <div className="border-t border-[var(--dc-border)]">
                    {outputs.map(renderOutput)}
                </div>
            )}
        </div>
    );
}
