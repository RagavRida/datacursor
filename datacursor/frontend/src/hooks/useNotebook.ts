import { useState, useCallback } from 'react';
import type { CellOutput } from '../components/Cell';
import type { DiffLine } from '../components/DiffView';
import type { ExecutionResult, AIResponseResult } from './useWebSocket';

export interface CellData {
    id: string;
    code: string;
    outputs: CellOutput[];
    executionCount: number | null;
    isRunning: boolean;
    aiSuggestion?: {
        code: string;
        diff: DiffLine[];
    } | null;
}

let idCounter = 0;
const generateId = () => `cell-${++idCounter}`;

export function useNotebook(
    execute: (id: string, code: string) => void,
    getContext: () => void
) {
    const [cells, setCells] = useState<CellData[]>([
        {
            id: generateId(),
            code: '# Welcome to DataCursor!\n# Press Shift+Enter to run, Cmd+K for AI assistance\n\nimport pandas as pd\nimport numpy as np',
            outputs: [],
            executionCount: null,
            isRunning: false,
        },
    ]);
    const [activeCellId, setActiveCellId] = useState<string>(cells[0].id);
    const [executionCounter, setExecutionCounter] = useState(0);

    const addCell = useCallback((afterId?: string) => {
        const newCell: CellData = {
            id: generateId(),
            code: '',
            outputs: [],
            executionCount: null,
            isRunning: false,
        };

        setCells((prev) => {
            if (afterId) {
                const index = prev.findIndex((c) => c.id === afterId);
                if (index !== -1) {
                    const newCells = [...prev];
                    newCells.splice(index + 1, 0, newCell);
                    return newCells;
                }
            }
            return [...prev, newCell];
        });

        setActiveCellId(newCell.id);
    }, []);

    const deleteCell = useCallback((id: string) => {
        setCells((prev) => {
            if (prev.length <= 1) return prev;
            const index = prev.findIndex((c) => c.id === id);
            const newCells = prev.filter((c) => c.id !== id);

            if (id === activeCellId && newCells.length > 0) {
                const newActiveIndex = Math.min(index, newCells.length - 1);
                setActiveCellId(newCells[newActiveIndex].id);
            }
            return newCells;
        });
    }, [activeCellId]);

    const runCell = useCallback((id: string, code: string) => {
        execute(id, code);

        // Auto-add cell if last
        setCells((prev) => {
            const index = prev.findIndex((c) => c.id === id);
            if (index === prev.length - 1) {
                const newCell: CellData = {
                    id: generateId(),
                    code: '',
                    outputs: [],
                    executionCount: null,
                    isRunning: false,
                };
                setActiveCellId(newCell.id);
                return [...prev, newCell];
            } else {
                setActiveCellId(prev[index + 1].id);
                return prev;
            }
        });
    }, [execute]);

    const updateCellCode = useCallback((id: string, code: string) => {
        setCells((prev) =>
            prev.map((cell) =>
                cell.id === id ? { ...cell, code } : cell
            )
        );
    }, []);

    const applyCodeToActiveCell = useCallback((code: string) => {
        console.log('[useNotebook] applyCodeToActiveCell called', { activeCellId, codeLength: code.length });
        setCells((prev) => {
            const index = prev.findIndex(c => c.id === activeCellId);
            console.log('[useNotebook] active cell index:', index);
            if (index === -1) return prev;

            return prev.map((cell) =>
                cell.id === activeCellId
                    ? { ...cell, code, aiSuggestion: null }
                    : cell
            );
        });
    }, [activeCellId]);

    // WebSocket Handlers
    const handleExecutionStarted = useCallback((cellId: string) => {
        setCells((prev) =>
            prev.map((cell) =>
                cell.id === cellId
                    ? { ...cell, isRunning: true, outputs: [] }
                    : cell
            )
        );
    }, []);

    const handleExecutionResult = useCallback((result: ExecutionResult) => {
        setExecutionCounter((prev) => prev + 1);
        setCells((prev) =>
            prev.map((cell) =>
                cell.id === result.cellId
                    ? {
                        ...cell,
                        isRunning: false,
                        outputs: result.outputs,
                        executionCount: executionCounter + 1,
                    }
                    : cell
            )
        );
        getContext();
    }, [executionCounter, getContext]);

    const handleAIResponse = useCallback((result: AIResponseResult) => {
        setCells((prev) =>
            prev.map((cell) =>
                cell.id === result.cellId
                    ? {
                        ...cell,
                        aiSuggestion: result.success
                            ? { code: result.code, diff: result.diff }
                            : null,
                    }
                    : cell
            )
        );
    }, []);

    const acceptAI = useCallback((id: string, code: string) => {
        setCells((prev) =>
            prev.map((cell) =>
                cell.id === id
                    ? { ...cell, code, aiSuggestion: null }
                    : cell
            )
        );
    }, []);

    const rejectAI = useCallback((id: string) => {
        setCells((prev) =>
            prev.map((cell) =>
                cell.id === id ? { ...cell, aiSuggestion: null } : cell
            )
        );
    }, []);

    return {
        cells,
        activeCellId,
        setActiveCellId,
        addCell,
        deleteCell,
        runCell,
        updateCellCode,
        applyCodeToActiveCell,
        acceptAI,
        rejectAI,
        wsHandlers: {
            onExecutionStarted: handleExecutionStarted,
            onExecutionResult: handleExecutionResult,
            onAIResponse: handleAIResponse,
        }
    };
}
