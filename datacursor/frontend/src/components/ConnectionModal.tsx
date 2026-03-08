/**
 * ConnectionModal - Database connection form.
 */

import { useState } from 'react';
import { X, Database, Server, Loader2, AlertCircle } from 'lucide-react';

interface ConnectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConnect: () => void;
    sessionId: string;
}

const DB_TYPES = [
    { id: 'postgres', name: 'PostgreSQL', icon: Database, color: '#336791' },
    { id: 'mysql', name: 'MySQL', icon: Database, color: '#00758f' },
    { id: 'snowflake', name: 'Snowflake', icon: Server, color: '#29b5e8' },
    { id: 'sqlite', name: 'SQLite', icon: Database, color: '#dddddd' },
];

export function ConnectionModal({ isOpen, onClose, onConnect, sessionId }: ConnectionModalProps) {
    const [selectedType, setSelectedType] = useState('postgres');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        name: '',
        host: 'localhost',
        port: '5432',
        user: '',
        password: '',
        database: '',
        account: '',    // Snowflake
        warehouse: '',  // Snowflake
        schema_: 'PUBLIC', // Snowflake
    });

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/db/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    type: selectedType,
                    ...formData,
                }),
            });

            const data = await response.json();
            if (response.ok && data.success) {
                onConnect();
                onClose();
            } else {
                setError(data.detail || 'Connection failed');
            }
        } catch (e) {
            setError('Failed to connect to backend');
        } finally {
            setLoading(false);
        }
    };

    const handleTypeChange = (type: string) => {
        setSelectedType(type);
        // Reset defaults based on type
        if (type === 'postgres') setFormData(prev => ({ ...prev, port: '5432' }));
        if (type === 'mysql') setFormData(prev => ({ ...prev, port: '3306' }));
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-[var(--dc-bg-secondary)] rounded-xl shadow-2xl w-full max-w-lg border border-[var(--dc-border)] overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-[var(--dc-border)]">
                    <div className="flex items-center gap-2">
                        <Database className="text-[var(--dc-accent)]" size={20} />
                        <h2 className="text-lg font-semibold text-[var(--dc-text-primary)]">Connect Database</h2>
                    </div>
                    <button onClick={onClose} className="p-2 rounded hover:bg-[var(--dc-bg-tertiary)] text-[var(--dc-text-secondary)]">
                        <X size={20} />
                    </button>
                </div>

                <div className="flex">
                    {/* Sidebar - Type Selection */}
                    <div className="w-1/3 border-r border-[var(--dc-border)] bg-[var(--dc-bg-tertiary)] p-2 space-y-1">
                        {DB_TYPES.map((type) => (
                            <button
                                key={type.id}
                                onClick={() => handleTypeChange(type.id)}
                                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${selectedType === type.id
                                        ? 'bg-[var(--dc-accent)] text-white shadow-md'
                                        : 'text-[var(--dc-text-secondary)] hover:bg-[var(--dc-bg-secondary)] hover:text-[var(--dc-text-primary)]'
                                    }`}
                            >
                                <type.icon size={16} />
                                {type.name}
                            </button>
                        ))}
                    </div>

                    {/* Form */}
                    <div className="flex-1 p-5">
                        {error && (
                            <div className="mb-4 p-3 rounded bg-red-500/10 border border-red-500/20 flex items-start gap-2 text-xs text-red-400">
                                <AlertCircle size={14} className="mt-0.5 shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Display Name</label>
                                <input
                                    type="text"
                                    required
                                    placeholder="My Database"
                                    className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                />
                            </div>

                            {/* Dynamic Fields based on Type */}
                            {selectedType === 'sqlite' ? (
                                <div>
                                    <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">File Path</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="/path/to/db.sqlite"
                                        className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                        value={formData.database}
                                        onChange={e => setFormData({ ...formData, database: e.target.value })}
                                    />
                                    <p className="text-[10px] text-[var(--dc-text-secondary)] mt-1">Use ':memory:' for in-memory database</p>
                                </div>
                            ) : (
                                <>
                                    {selectedType === 'snowflake' ? (
                                        <div>
                                            <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Account</label>
                                            <input
                                                type="text"
                                                required
                                                placeholder="xy12345.us-east-1"
                                                className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                                value={formData.account}
                                                onChange={e => setFormData({ ...formData, account: e.target.value })}
                                            />
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-3 gap-2">
                                            <div className="col-span-2">
                                                <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Host</label>
                                                <input
                                                    type="text"
                                                    required
                                                    className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                                    value={formData.host}
                                                    onChange={e => setFormData({ ...formData, host: e.target.value })}
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Port</label>
                                                <input
                                                    type="text"
                                                    required
                                                    className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                                    value={formData.port}
                                                    onChange={e => setFormData({ ...formData, port: e.target.value })}
                                                />
                                            </div>
                                        </div>
                                    )}

                                    <div className="grid grid-cols-2 gap-2">
                                        <div>
                                            <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">User</label>
                                            <input
                                                type="text"
                                                required
                                                className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                                value={formData.user}
                                                onChange={e => setFormData({ ...formData, user: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Password</label>
                                            <input
                                                type="password"
                                                className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                                value={formData.password}
                                                onChange={e => setFormData({ ...formData, password: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Database Name</label>
                                        <input
                                            type="text"
                                            required
                                            className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                            value={formData.database}
                                            onChange={e => setFormData({ ...formData, database: e.target.value })}
                                        />
                                    </div>

                                    {selectedType === 'snowflake' && (
                                        <div className="grid grid-cols-2 gap-2">
                                            <div>
                                                <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Warehouse</label>
                                                <input
                                                    type="text"
                                                    className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                                    value={formData.warehouse}
                                                    onChange={e => setFormData({ ...formData, warehouse: e.target.value })}
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-medium text-[var(--dc-text-secondary)] mb-1">Schema</label>
                                                <input
                                                    type="text"
                                                    required
                                                    className="w-full px-3 py-2 rounded bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)] text-sm text-[var(--dc-text-primary)] focus:border-[var(--dc-accent)] focus:outline-none"
                                                    value={formData.schema_}
                                                    onChange={e => setFormData({ ...formData, schema_: e.target.value })}
                                                />
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}

                            <div className="pt-2">
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full btn btn-primary flex items-center justify-center gap-2 py-2"
                                >
                                    {loading ? <Loader2 size={16} className="animate-spin" /> : 'Test & Connect'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}
