/**
 * DataCursor - AI-Native Data Science IDE
 * Main Application Entry Point
 */

import { useState, useEffect, useCallback } from 'react';
import { Bot, Database, Settings as SettingsIcon, FolderOpen } from 'lucide-react';
import { Notebook } from './components/Notebook';
import { AIChat } from './components/AIChat';
import { DatabasePanel } from './components/DatabasePanel';
import { FileManager } from './components/FileManager';
import { Settings } from './components/Settings';
import { useWebSocket, type RuntimeContext } from './hooks/useWebSocket';
import { useNotebook } from './hooks/useNotebook';
import './index.css';

function App() {
  const {
    isConnected,
    sessionId,
    execute,
    requestAI,
    getContext,
    onExecutionResult,
    onExecutionStarted,
    onAIResponse,
    onContext,
  } = useWebSocket();

  const notebook = useNotebook(execute, getContext);

  // Wire up WebSocket handlers to Notebook state
  useEffect(() => {
    onExecutionStarted(notebook.wsHandlers.onExecutionStarted);
    onExecutionResult(notebook.wsHandlers.onExecutionResult);
    const unsubAI = onAIResponse(notebook.wsHandlers.onAIResponse);

    return () => {
      unsubAI();
    };
  }, [onExecutionStarted, onExecutionResult, onAIResponse, notebook.wsHandlers]);

  const [context, setContext] = useState<RuntimeContext | null>(null);
  const [activePanel, setActivePanel] = useState<'ai' | 'database' | 'files' | null>('ai');
  const [showSettings, setShowSettings] = useState(false);
  const [activeProvider, setActiveProvider] = useState<string>('google');

  // Handle context updates
  useEffect(() => {
    onContext((ctx) => {
      setContext(ctx);
    });
  }, [onContext]);

  // Fetch initial context and provider when connected
  useEffect(() => {
    if (isConnected) {
      getContext();
      // Fetch active provider
      fetch('/api/settings/providers')
        .then(res => res.json())
        .then(data => setActiveProvider(data.active))
        .catch(console.error);
    }
  }, [isConnected, getContext]);

  const handleSendChatMessage = useCallback((message: string) => {
    // Get current code from active cell if available
    let currentCode = "";
    if (notebook.activeCellId) {
      const cell = notebook.cells.find(c => c.id === notebook.activeCellId);
      if (cell) {
        currentCode = cell.code;
      }
    }

    // Send request to AI
    requestAI(notebook.activeCellId || "chat", message, currentCode);
  }, [requestAI, notebook.activeCellId, notebook.cells]);

  const handleProviderChange = useCallback((provider: string) => {
    setActiveProvider(provider);
  }, []);

  return (
    <div className="h-screen flex bg-[var(--dc-bg-primary)] overflow-hidden">
      {/* Activity Bar */}
      <div className="w-12 flex flex-col items-center py-4 border-r border-[var(--dc-border)] bg-[var(--dc-bg-tertiary)] z-10">
        <button
          onClick={() => setActivePanel(activePanel === 'ai' ? null : 'ai')}
          className={`p-2 mb-2 rounded-lg transition-colors ${activePanel === 'ai'
            ? 'bg-[var(--dc-accent)] text-white'
            : 'text-[var(--dc-text-secondary)] hover:text-[var(--dc-text-primary)] hover:bg-[var(--dc-bg-secondary)]'
            }`}
          title="AI Assistant"
        >
          <Bot size={24} />
        </button>

        <button
          onClick={() => setActivePanel(activePanel === 'database' ? null : 'database')}
          className={`p-2 mb-2 rounded-lg transition-colors ${activePanel === 'database'
            ? 'bg-[var(--dc-accent)] text-white'
            : 'text-[var(--dc-text-secondary)] hover:text-[var(--dc-text-primary)] hover:bg-[var(--dc-bg-secondary)]'
            }`}
          title="Databases"
        >
          <Database size={24} />
        </button>

        <button
          onClick={() => setActivePanel(activePanel === 'files' ? null : 'files')}
          className={`p-2 mb-2 rounded-lg transition-colors ${activePanel === 'files'
            ? 'bg-[var(--dc-accent)] text-white'
            : 'text-[var(--dc-text-secondary)] hover:text-[var(--dc-text-primary)] hover:bg-[var(--dc-bg-secondary)]'
            }`}
          title="File Manager"
        >
          <FolderOpen size={24} />
        </button>

        <div className="mt-auto">
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 rounded-lg text-[var(--dc-text-secondary)] hover:text-[var(--dc-text-primary)] hover:bg-[var(--dc-bg-secondary)] transition-colors"
            title="Settings"
          >
            <SettingsIcon size={24} />
          </button>
        </div>
      </div>

      {/* Side Panel */}
      {activePanel === 'ai' && (
        <AIChat
          context={context}
          onSendMessage={handleSendChatMessage}
          isConnected={isConnected}
          activeProvider={activeProvider}
          onApplyCode={notebook.applyCodeToActiveCell}
          onAIResponse={onAIResponse}
        />
      )}

      {activePanel === 'database' && (
        <DatabasePanel
          sessionId={sessionId || ''}
          isConnected={isConnected}
        />
      )}

      {activePanel === 'files' && (
        <FileManager />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <Notebook
          cells={notebook.cells}
          activeCellId={notebook.activeCellId}
          isConnected={isConnected}
          onRunCell={notebook.runCell}
          onAddCell={notebook.addCell}
          onDeleteCell={notebook.deleteCell}
          onUpdateCellCode={notebook.updateCellCode}
          onFocusCell={notebook.setActiveCellId}
          onAcceptAI={notebook.acceptAI}
          onRejectAI={notebook.rejectAI}
          requestAI={requestAI}
        />
      </div>

      {/* Settings Modal */}
      <Settings
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        onProviderChange={handleProviderChange}
      />
    </div>
  );
}

export default App;
