/**
 * WebSocket hook for communicating with the DataCursor backend.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WSMessage {
    type: string;
    [key: string]: unknown;
}

export interface ExecutionResult {
    cellId: string;
    status: 'ok' | 'error';
    outputs: Array<{
        type: string;
        text?: string;
        data?: Record<string, unknown>;
        name?: string;
        ename?: string;
        evalue?: string;
        traceback?: string[];
    }>;
    error?: {
        message: string;
    };
}

export interface AIResponseResult {
    cellId: string;
    success: boolean;
    code: string;
    diff: Array<{
        type: 'unchanged' | 'added' | 'removed';
        line: string;
    }>;
    error?: string;
}

export interface RuntimeContext {
    variables: Array<{
        name: string;
        type: string;
        length?: string;
        shape?: string;
    }>;
    dataframes: Array<{
        name: string;
        type: string;
        shape?: string;
        columns?: string[];
        dtypes?: Record<string, string>;
    }>;
    imports: string[];
    last_output?: Record<string, unknown>;
}

interface UseWebSocketReturn {
    isConnected: boolean;
    sessionId: string | null;
    execute: (cellId: string, code: string) => void;
    requestAI: (cellId: string, prompt: string, currentCode: string) => void;
    interrupt: () => void;
    getContext: () => void;
    onExecutionResult: (callback: (result: ExecutionResult) => void) => void;
    onExecutionStarted: (callback: (cellId: string) => void) => void;
    onAIResponse: (callback: (result: AIResponseResult) => void) => () => void;
    onContext: (callback: (context: RuntimeContext) => void) => void;
}

export function useWebSocket(): UseWebSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const callbacksRef = useRef<{
        onExecutionResult?: (result: ExecutionResult) => void;
        onExecutionStarted?: (cellId: string) => void;
        onAIResponse: Set<(result: AIResponseResult) => void>;
        onContext?: (context: RuntimeContext) => void;
    }>({
        onAIResponse: new Set(),
    });

    // ... (skipped, will use multi_replace or manual chunking if needed)
    // Actually simpler to just replace initialization and the method.


    // Initialize connection
    useEffect(() => {
        const connect = async () => {
            try {
                // Start kernel first
                const response = await fetch('/api/kernel/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}),
                });

                const data = await response.json();
                const sid = data.session_id;
                setSessionId(sid);

                // Connect WebSocket
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${sid}`);

                ws.onopen = () => {
                    console.log('WebSocket connected');
                    setIsConnected(true);
                };

                ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    setIsConnected(false);
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };

                ws.onmessage = (event) => {
                    const msg = JSON.parse(event.data) as WSMessage;

                    switch (msg.type) {
                        case 'execution_result':
                            callbacksRef.current.onExecutionResult?.(msg as unknown as ExecutionResult);
                            break;
                        case 'execution_started':
                            callbacksRef.current.onExecutionStarted?.(msg.cellId as string);
                            break;
                        case 'ai_response':
                            callbacksRef.current.onAIResponse.forEach(cb => cb(msg as unknown as AIResponseResult));
                            break;
                        case 'context':
                            callbacksRef.current.onContext?.(msg as unknown as RuntimeContext);
                            break;
                    }
                };

                wsRef.current = ws;
            } catch (error) {
                console.error('Failed to connect:', error);
            }
        };

        connect();

        return () => {
            wsRef.current?.close();
        };
    }, []);

    const send = useCallback((message: WSMessage) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        }
    }, []);

    const execute = useCallback((cellId: string, code: string) => {
        send({ type: 'execute', cellId, code });
    }, [send]);

    const requestAI = useCallback((cellId: string, prompt: string, currentCode: string) => {
        send({ type: 'ai_request', cellId, prompt, currentCode });
    }, [send]);

    const interrupt = useCallback(() => {
        send({ type: 'interrupt' });
    }, [send]);

    const getContext = useCallback(() => {
        send({ type: 'get_context' });
    }, [send]);

    const onExecutionResult = useCallback((callback: (result: ExecutionResult) => void) => {
        callbacksRef.current.onExecutionResult = callback;
    }, []);

    const onExecutionStarted = useCallback((callback: (cellId: string) => void) => {
        callbacksRef.current.onExecutionStarted = callback;
    }, []);

    const onAIResponse = useCallback((callback: (result: AIResponseResult) => void) => {
        callbacksRef.current.onAIResponse.add(callback);
        return () => {
            callbacksRef.current.onAIResponse.delete(callback);
        };
    }, []);

    const onContext = useCallback((callback: (context: RuntimeContext) => void) => {
        callbacksRef.current.onContext = callback;
    }, []);

    return {
        isConnected,
        sessionId,
        execute,
        requestAI,
        interrupt,
        getContext,
        onExecutionResult,
        onExecutionStarted,
        onAIResponse,
        onContext,
    };
}
