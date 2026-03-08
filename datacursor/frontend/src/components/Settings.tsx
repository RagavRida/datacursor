/**
 * Settings Component - LLM provider selection and configuration.
 */

import { useState, useEffect } from 'react';
import { X, Settings as SettingsIcon, Bot, Cloud, Server, Check, AlertCircle, Sparkles, Zap, Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

export interface ProviderStatus {
    configured: boolean;
    active: boolean;
}

export interface ProvidersResponse {
    providers: {
        openai: ProviderStatus;
        anthropic: ProviderStatus;
        google: ProviderStatus;
        ollama: ProviderStatus;
        groq: ProviderStatus;
        openrouter: ProviderStatus;
    };
    active: string;
    data_scientist_mode: boolean;
}

interface SettingsProps {
    isOpen: boolean;
    onClose: () => void;
    onProviderChange: (provider: string) => void;
}

const PROVIDERS = [
    {
        id: 'openai',
        name: 'OpenAI',
        icon: Cloud,
        models: ['gpt-4o', 'gpt-4', 'gpt-3.5-turbo'],
        description: 'GPT-4 and GPT-4o - Best for complex reasoning',
        color: '#10a37f',
    },
    {
        id: 'anthropic',
        name: 'Anthropic',
        icon: Bot,
        models: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
        description: 'Claude 3.5 Sonnet - Excellent for code generation',
        color: '#cc785c',
    },
    {
        id: 'google',
        name: 'Google',
        icon: Sparkles,
        models: ['gemini-1.5-pro', 'gemini-1.5-flash'],
        description: 'Gemini 1.5 - Fast and capable',
        color: '#4285f4',
    },
    {
        id: 'ollama',
        name: 'Ollama (Local)',
        icon: Server,
        models: [],  // Fetched dynamically
        description: 'Run models locally - Private and offline',
        color: '#ffffff',
        isLocal: true,
    },
    {
        id: 'groq',
        name: 'Groq',
        icon: Zap,
        models: ['llama3-70b-8192', 'mixtral-8x7b-32768'],
        description: 'LPU Inference Engine - Ultra fast',
        color: '#f55036',
    },
    {
        id: 'openrouter',
        name: 'OpenRouter',
        icon: Sparkles,
        models: ['google/gemini-2.0-flash-exp:free', 'anthropic/claude-3-opus'],
        description: 'Access to all top LLMs',
        color: '#7f5af0',
    },
];


export function Settings({ isOpen, onClose, onProviderChange }: SettingsProps) {
    const { theme, toggleTheme } = useTheme();
    const [providers, setProviders] = useState<ProvidersResponse | null>(null);
    const [activeProvider, setActiveProvider] = useState<string>('google');
    const [apiKeys, setApiKeys] = useState<Record<string, string>>({
        openai: '',
        anthropic: '',
        google: '',
        groq: '',
        openrouter: '',
    });
    const [ollamaModels, setOllamaModels] = useState<string[]>([]);
    const [selectedOllamaModel, setSelectedOllamaModel] = useState<string>('codellama');
    const [dataScienceMode, setDataScienceMode] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch provider status on mount
    useEffect(() => {
        if (isOpen) {
            fetchProviderStatus();
            fetchOllamaModels();
        }
    }, [isOpen]);

    const fetchProviderStatus = async () => {
        try {
            const response = await fetch('/api/settings/providers');
            if (response.ok) {
                const data = await response.json();
                setProviders(data);
                setActiveProvider(data.active);
                setDataScienceMode(data.data_scientist_mode);
            }
        } catch (e) {
            console.error('Failed to fetch providers:', e);
        }
    };

    const fetchOllamaModels = async () => {
        try {
            const response = await fetch('/api/settings/ollama/models');
            if (response.ok) {
                const data = await response.json();
                setOllamaModels(data.models || []);
            }
        } catch (e) {
            console.error('Failed to fetch Ollama models:', e);
        }
    };

    const handleProviderSelect = async (providerId: string) => {
        setLoading(true);
        setError(null);

        try {
            const body: Record<string, unknown> = { provider: providerId };

            // Include API key if provided
            if (apiKeys[providerId]) {
                body.api_key = apiKeys[providerId];
            }

            // Include model for Ollama
            if (providerId === 'ollama' && selectedOllamaModel) {
                body.model = selectedOllamaModel;
            }

            const response = await fetch('/api/settings/provider', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            if (response.ok) {
                const data = await response.json();
                setActiveProvider(providerId);
                onProviderChange(providerId);

                if (!data.configured) {
                    setError(`${providerId} is not configured. Please provide an API key.`);
                }
            } else {
                const err = await response.json();
                setError(err.detail || 'Failed to set provider');
            }
        } catch (e) {
            setError('Failed to connect to backend');
        } finally {
            setLoading(false);
        }
    };

    const handleDataScienceModeToggle = async () => {
        try {
            await fetch(`/api/settings/data-scientist-mode?enabled=${!dataScienceMode}`, {
                method: 'POST',
            });
            setDataScienceMode(!dataScienceMode);
        } catch (e) {
            console.error('Failed to toggle mode:', e);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-[var(--dc-bg-secondary)] rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden border border-[var(--dc-border)]">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-[var(--dc-border)]">
                    <div className="flex items-center gap-3">
                        <SettingsIcon className="text-[var(--dc-accent)]" size={24} />
                        <h2 className="text-lg font-semibold text-[var(--dc-text-primary)]">LLM Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-[var(--dc-bg-tertiary)] text-[var(--dc-text-secondary)]"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-4 overflow-y-auto max-h-[calc(90vh-120px)]">
                    {/* Error Display */}
                    {error && (
                        <div className="mb-4 p-3 rounded-lg bg-[rgba(248,81,73,0.1)] border border-[var(--dc-error)] flex items-center gap-2">
                            <AlertCircle size={18} className="text-[var(--dc-error)]" />
                            <span className="text-sm text-[var(--dc-error)]">{error}</span>
                        </div>
                    )}

                    {/* Data Scientist Mode Toggle */}

                    {/* Appearance Settings */}
                    <div className="mb-4 p-4 rounded-lg bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)]">
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    {theme === 'dark' ? <Moon size={18} className="text-[var(--dc-accent)]" /> : <Sun size={18} className="text-[var(--dc-accent)]" />}
                                    <span className="font-medium text-[var(--dc-text-primary)]">Appearance</span>
                                </div>
                                <p className="text-sm text-[var(--dc-text-secondary)]">
                                    Switch between dark and light themes
                                </p>
                            </div>
                            <button
                                onClick={toggleTheme}
                                className={`relative w-12 h-6 rounded-full transition-colors ${theme === 'dark' ? 'bg-[var(--dc-bg-primary)] border border-[var(--dc-border)]' : 'bg-[var(--dc-accent)]'}`}
                            >
                                <span
                                    className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${theme === 'light' ? 'left-7' : 'left-1'
                                        }`}
                                />
                            </button>
                        </div>
                    </div>

                    <div className="mb-6 p-4 rounded-lg bg-[var(--dc-bg-tertiary)] border border-[var(--dc-border)]">
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <Bot size={18} className="text-[var(--dc-accent)]" />
                                    <span className="font-medium text-[var(--dc-text-primary)]">Data Scientist Mode</span>
                                </div>
                                <p className="text-sm text-[var(--dc-text-secondary)]">
                                    Enable domain-specific persona for data science, ML, and Kaggle workflows
                                </p>
                            </div>
                            <button
                                onClick={handleDataScienceModeToggle}
                                className={`relative w-12 h-6 rounded-full transition-colors ${dataScienceMode ? 'bg-[var(--dc-accent)]' : 'bg-[var(--dc-border)]'
                                    }`}
                            >
                                <span
                                    className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${dataScienceMode ? 'left-7' : 'left-1'
                                        }`}
                                />
                            </button>
                        </div>
                    </div>

                    {/* Provider Selection */}
                    <h3 className="text-sm font-medium text-[var(--dc-text-secondary)] mb-3">SELECT LLM PROVIDER</h3>

                    <div className="grid gap-3">
                        {PROVIDERS.map((provider) => {
                            const isActive = activeProvider === provider.id;
                            const status = providers?.providers[provider.id as keyof typeof providers.providers];
                            const isConfigured = status?.configured;
                            const Icon = provider.icon;

                            return (
                                <div
                                    key={provider.id}
                                    className={`p-4 rounded-lg border transition-all cursor-pointer ${isActive
                                        ? 'border-[var(--dc-accent)] bg-[rgba(88,166,255,0.1)]'
                                        : 'border-[var(--dc-border)] hover:border-[var(--dc-text-secondary)]'
                                        }`}
                                    onClick={() => !loading && handleProviderSelect(provider.id)}
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-center gap-3">
                                            <div
                                                className="w-10 h-10 rounded-lg flex items-center justify-center"
                                                style={{ backgroundColor: `${provider.color}20` }}
                                            >
                                                <Icon size={20} style={{ color: provider.color }} />
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium text-[var(--dc-text-primary)]">
                                                        {provider.name}
                                                    </span>
                                                    {provider.isLocal && (
                                                        <span className="text-xs px-2 py-0.5 rounded bg-[var(--dc-success)] text-white">
                                                            LOCAL
                                                        </span>
                                                    )}
                                                    {isConfigured && (
                                                        <Check size={16} className="text-[var(--dc-success)]" />
                                                    )}
                                                </div>
                                                <p className="text-sm text-[var(--dc-text-secondary)]">
                                                    {provider.description}
                                                </p>
                                            </div>
                                        </div>

                                        {isActive && (
                                            <span className="text-xs px-2 py-1 rounded bg-[var(--dc-accent)] text-white">
                                                ACTIVE
                                            </span>
                                        )}
                                    </div>

                                    {/* API Key Input (for cloud providers) */}
                                    {!provider.isLocal && isActive && (
                                        <div className="mt-4 pt-4 border-t border-[var(--dc-border)]">
                                            <label className="block text-sm text-[var(--dc-text-secondary)] mb-2">
                                                API Key
                                            </label>
                                            <input
                                                type="password"
                                                value={apiKeys[provider.id] || ''}
                                                onChange={(e) =>
                                                    setApiKeys((prev) => ({ ...prev, [provider.id]: e.target.value }))
                                                }
                                                onBlur={() => handleProviderSelect(provider.id)}
                                                placeholder={isConfigured ? '••••••••••••••••' : 'Enter API key'}
                                                className="w-full px-3 py-2 bg-[var(--dc-bg-primary)] border border-[var(--dc-border)] rounded-lg text-sm text-[var(--dc-text-primary)] placeholder:text-[var(--dc-text-secondary)] focus:outline-none focus:border-[var(--dc-accent)]"
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        </div>
                                    )}

                                    {/* Ollama Model Selection */}
                                    {provider.isLocal && isActive && (
                                        <div className="mt-4 pt-4 border-t border-[var(--dc-border)]">
                                            <label className="block text-sm text-[var(--dc-text-secondary)] mb-2">
                                                Model
                                            </label>
                                            {ollamaModels.length > 0 ? (
                                                <select
                                                    value={selectedOllamaModel}
                                                    onChange={(e) => {
                                                        setSelectedOllamaModel(e.target.value);
                                                        handleProviderSelect('ollama');
                                                    }}
                                                    className="w-full px-3 py-2 bg-[var(--dc-bg-primary)] border border-[var(--dc-border)] rounded-lg text-sm text-[var(--dc-text-primary)] focus:outline-none focus:border-[var(--dc-accent)]"
                                                    onClick={(e) => e.stopPropagation()}
                                                >
                                                    {ollamaModels.map((model) => (
                                                        <option key={model} value={model}>
                                                            {model}
                                                        </option>
                                                    ))}
                                                </select>
                                            ) : (
                                                <div className="p-3 rounded bg-[var(--dc-bg-primary)] text-sm text-[var(--dc-text-secondary)]">
                                                    Ollama not running. Start Ollama and pull a model:
                                                    <code className="block mt-2 text-xs text-[var(--dc-accent)]">
                                                        ollama pull codellama
                                                    </code>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-4 border-t border-[var(--dc-border)] bg-[var(--dc-bg-tertiary)]">
                    <span className="text-xs text-[var(--dc-text-secondary)]">
                        Active: <strong className="text-[var(--dc-accent)]">{activeProvider}</strong>
                    </span>
                    <button
                        onClick={onClose}
                        className="btn btn-primary"
                        disabled={loading}
                    >
                        {loading ? 'Saving...' : 'Done'}
                    </button>
                </div>
            </div>
        </div>
    );
}
