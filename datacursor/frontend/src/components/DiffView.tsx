/**
 * DiffView Component - Shows code changes with accept/reject buttons.
 */

import { Check, X } from 'lucide-react';

export interface DiffLine {
    type: 'unchanged' | 'added' | 'removed';
    line: string;
}

interface DiffViewProps {
    diff: DiffLine[];
    onAccept: () => void;
    onReject: () => void;
}

export function DiffView({ diff, onAccept, onReject }: DiffViewProps) {
    return (
        <div className="border border-[var(--dc-border)] rounded-lg overflow-hidden bg-[var(--dc-bg-secondary)]">
            {/* Header */}
            <div className="flex items-center justify-between p-3 border-b border-[var(--dc-border)] bg-[var(--dc-bg-tertiary)]">
                <span className="text-sm font-medium text-[var(--dc-text-primary)]">
                    AI Suggestion
                </span>
                <div className="flex items-center gap-2">
                    <button
                        onClick={onReject}
                        className="btn btn-ghost"
                    >
                        <X size={14} />
                        Reject
                    </button>
                    <button
                        onClick={onAccept}
                        className="btn btn-success"
                    >
                        <Check size={14} />
                        Accept
                    </button>
                </div>
            </div>

            {/* Diff Content */}
            <div className="max-h-64 overflow-y-auto">
                {diff.map((item, index) => (
                    <div
                        key={index}
                        className={`diff-line ${item.type}`}
                    >
                        <span className="inline-block w-4 text-[var(--dc-text-secondary)] mr-2">
                            {item.type === 'added' ? '+' : item.type === 'removed' ? '-' : ' '}
                        </span>
                        {item.line || '\u00A0'}
                    </div>
                ))}
            </div>
        </div>
    );
}
