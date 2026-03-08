/**
 * Notebook Component - Main container managing notebook cells.
 */

import { useCallback } from 'react';
import { Plus, Save, FolderOpen, Zap } from 'lucide-react';
import { Cell } from './Cell';
import type { CellData } from '../hooks/useNotebook';

interface NotebookProps {
    cells: CellData[];
    activeCellId: string;
    isConnected: boolean;
    onRunCell: (id: string, code: string) => void;
    onAddCell: (afterId?: string) => void;
    onDeleteCell: (id: string) => void;
    onUpdateCellCode: (id: string, code: string) => void;
    onFocusCell: (id: string) => void;
    onAcceptAI: (id: string, code: string) => void;
    onRejectAI: (id: string) => void;
    requestAI: (id: string, prompt: string, code: string) => void;
}

export function Notebook({
    cells,
    activeCellId,
    isConnected,
    onRunCell,
    onAddCell,
    onDeleteCell,
    onUpdateCellCode,
    onFocusCell,
    onAcceptAI,
    onRejectAI,
    requestAI,
}: NotebookProps) {

    const handleExecute = useCallback((id: string, code: string) => {
        onRunCell(id, code);
    }, [onRunCell]);

    const handleCodeChange = useCallback((id: string, code: string) => {
        onUpdateCellCode(id, code);
    }, [onUpdateCellCode]);

    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-3 border-b border-[var(--dc-border)] bg-[var(--dc-bg-secondary)]">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Zap className="text-[var(--dc-accent)]" size={24} />
                        <h1 className="text-lg font-bold text-[var(--dc-text-primary)]">DataCursor</h1>
                    </div>
                    <span className="text-xs text-[var(--dc-text-secondary)]">Untitled.ipynb</span>
                </div>

                <div className="flex items-center gap-2">
                    <button className="btn btn-ghost" title="Open">
                        <FolderOpen size={16} />
                    </button>
                    <button className="btn btn-ghost" title="Save">
                        <Save size={16} />
                    </button>
                    <button
                        onClick={() => onAddCell()}
                        className="btn btn-primary"
                        title="Add cell"
                    >
                        <Plus size={16} />
                        Add Cell
                    </button>
                </div>
            </div>

            {/* Connection Status */}
            {!isConnected && (
                <div className="px-4 py-2 bg-[var(--dc-error)] text-white text-sm text-center">
                    ⚠️ Disconnected from kernel. Trying to reconnect...
                </div>
            )}

            {/* Cells Container */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-4xl mx-auto">
                    {cells.map((cell) => (
                        <Cell
                            key={cell.id}
                            id={cell.id}
                            initialCode={cell.code}
                            isActive={cell.id === activeCellId}
                            isRunning={cell.isRunning}
                            outputs={cell.outputs}
                            executionCount={cell.executionCount}
                            onExecute={handleExecute}
                            onAIRequest={requestAI}
                            onDelete={onDeleteCell}
                            onFocus={onFocusCell}
                            onCodeChange={handleCodeChange}
                            aiSuggestion={cell.aiSuggestion}
                            onAcceptAI={onAcceptAI}
                            onRejectAI={onRejectAI}
                        />
                    ))}

                    {/* Add Cell Button */}
                    <button
                        onClick={() => onAddCell()}
                        className="w-full py-3 border-2 border-dashed border-[var(--dc-border)] rounded-lg text-[var(--dc-text-secondary)] hover:border-[var(--dc-accent)] hover:text-[var(--dc-accent)] transition-colors flex items-center justify-center gap-2"
                    >
                        <Plus size={18} />
                        Add Cell
                    </button>
                </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2 border-t border-[var(--dc-border)] bg-[var(--dc-bg-secondary)] text-xs text-[var(--dc-text-secondary)]">
                <div className="flex items-center gap-4">
                    <span>{cells.length} cells</span>
                    <span>Python 3</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="kbd">⇧↵</span> Run
                    <span className="kbd">⌘K</span> AI
                </div>
            </div>
        </div>
    );
}
