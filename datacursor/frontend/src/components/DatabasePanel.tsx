/**
 * DatabasePanel - Side panel for database connections and schema browsing.
 */

import { useState, useEffect } from 'react';
import { Database, Plus, RefreshCw, ChevronRight, ChevronDown, Table, Trash2, XCircle } from 'lucide-react';
import { ConnectionModal } from './ConnectionModal';

interface DatabasePanelProps {
    sessionId: string;
    isConnected: boolean;
}

interface DBTable {
    name: string;
    columns: { name: string; type: string }[];
}

interface DBSchema {
    tables: DBTable[];
}

export function DatabasePanel({ sessionId, isConnected }: DatabasePanelProps) {
    const [connections, setConnections] = useState<string[]>([]);
    const [modalOpen, setModalOpen] = useState(false);
    const [expandedDb, setExpandedDb] = useState<string | null>(null);
    const [schemas, setSchemas] = useState<Record<string, DBSchema>>({});
    const [loadingSchema, setLoadingSchema] = useState<string | null>(null);

    useEffect(() => {
        if (isConnected && sessionId) {
            fetchConnections();
        }
    }, [isConnected, sessionId]);

    const fetchConnections = async () => {
        try {
            const response = await fetch(`http://localhost:8000/db/list/${sessionId}`);
            const data = await response.json();
            setConnections(data.databases || []);
        } catch (e) {
            console.error('Failed to fetch DBs', e);
        }
    };

    const handleDbClick = async (name: string) => {
        if (expandedDb === name) {
            setExpandedDb(null);
            return;
        }

        setExpandedDb(name);
        if (!schemas[name]) {
            setLoadingSchema(name);
            try {
                const response = await fetch(`http://localhost:8000/db/schema/${sessionId}/${name}`);
                const data = await response.json();
                setSchemas(prev => ({ ...prev, [name]: data }));
            } catch (e) {
                console.error('Failed to fetch schema', e);
            } finally {
                setLoadingSchema(null);
            }
        }
    };

    const handleDisconnect = async (name: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm(`Disconnect ${name}?`)) return;
        try {
            await fetch(`http://localhost:8000/db/disconnect/${sessionId}/${name}`, { method: 'POST' });
            fetchConnections();
            if (expandedDb === name) setExpandedDb(null);
        } catch (e) {
            console.error('Failed to disconnect', e);
        }
    };

    return (
        <div className="w-80 flex flex-col border-r border-[var(--dc-border)] bg-[var(--dc-bg-secondary)] h-full">
            {/* Header */}
            <div className="p-4 border-b border-[var(--dc-border)] flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Database className="text-[var(--dc-accent)]" size={20} />
                    <span className="font-semibold text-[var(--dc-text-primary)]">Databases</span>
                </div>
                <div className="flex gap-1">
                    <button
                        onClick={fetchConnections}
                        className="p-1.5 rounded hover:bg-[var(--dc-bg-tertiary)] text-[var(--dc-text-secondary)]"
                        title="Refresh"
                    >
                        <RefreshCw size={16} />
                    </button>
                    <button
                        onClick={() => setModalOpen(true)}
                        className="p-1.5 rounded hover:bg-[var(--dc-bg-tertiary)] text-[var(--dc-text-secondary)] hover:text-[var(--dc-accent)]"
                        title="Add Connection"
                    >
                        <Plus size={16} />
                    </button>
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {isConnected ? (
                    connections.length > 0 ? (
                        connections.map(name => (
                            <div key={name} className="rounded overflow-hidden border border-transparent hover:border-[var(--dc-border)] bg-[var(--dc-bg-primary)]">
                                <div
                                    className="flex items-center justify-between p-2 cursor-pointer hover:bg-[var(--dc-bg-tertiary)]"
                                    onClick={() => handleDbClick(name)}
                                >
                                    <div className="flex items-center gap-2">
                                        {expandedDb === name ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                        <Database size={14} className="text-[var(--dc-text-secondary)]" />
                                        <span className="text-sm font-medium">{name}</span>
                                    </div>
                                    <button
                                        onClick={(e) => handleDisconnect(name, e)}
                                        className="p-1 text-[var(--dc-text-secondary)] hover:text-red-400 opacity-0 group-hover:opacity-100"
                                    >
                                        <Trash2 size={12} />
                                    </button>
                                </div>

                                {/* Schema */}
                                {expandedDb === name && (
                                    <div className="pl-4 pr-2 pb-2 bg-[var(--dc-bg-tertiary)]/30 border-t border-[var(--dc-border)]">
                                        {loadingSchema === name ? (
                                            <div className="py-2 text-xs text-[var(--dc-text-secondary)] flex items-center gap-2">
                                                <RefreshCw size={12} className="animate-spin" /> Fetching schema...
                                            </div>
                                        ) : schemas[name] ? (
                                            <div className="mt-1 space-y-1">
                                                {schemas[name].tables.map(table => (
                                                    <div key={table.name} className="group">
                                                        <div className="flex items-center gap-2 py-1 px-2 rounded hover:bg-[var(--dc-bg-secondary)] cursor-default">
                                                            <Table size={12} className="text-[var(--dc-accent)]" />
                                                            <span className="text-xs text-[var(--dc-text-primary)]">{table.name}</span>
                                                            <span className="text-[10px] text-[var(--dc-text-secondary)] ml-auto">
                                                                {table.columns.length} cols
                                                            </span>
                                                        </div>
                                                        {/* Tooltip-like column list could go here, for now simpler */}
                                                    </div>
                                                ))}
                                                {schemas[name].tables.length === 0 && (
                                                    <div className="text-xs text-[var(--dc-text-secondary)] py-1">No tables found</div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="text-xs text-red-400 py-1">Failed to load schema</div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-8">
                            <Database size={32} className="mx-auto text-[var(--dc-border)] mb-2" />
                            <p className="text-sm text-[var(--dc-text-secondary)]">No connections</p>
                            <button
                                onClick={() => setModalOpen(true)}
                                className="mt-2 text-xs text-[var(--dc-accent)] hover:underline"
                            >
                                Connect Database
                            </button>
                        </div>
                    )
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-[var(--dc-text-secondary)] space-y-2 opacity-60">
                        <XCircle size={24} />
                        <span className="text-sm">Kernel disconnected</span>
                    </div>
                )}
            </div>

            <ConnectionModal
                isOpen={modalOpen}
                onClose={() => setModalOpen(false)}
                onConnect={() => {
                    fetchConnections();
                    setModalOpen(false);
                }}
                sessionId={sessionId}
            />
        </div>
    );
}
