/**
 * FileManager - Side panel for file management.
 */

import { useState, useEffect, useRef } from 'react';

import { FolderOpen, File, FileText, Upload, Trash2, RefreshCw, Download, Image as ImageIcon, Pencil, Check, X } from 'lucide-react';

interface FileItem {
    name: string;
    path: string;
    type: 'file' | 'directory';
    size: number;
    modified: number;
}

export function FileManager() {
    const [files, setFiles] = useState<FileItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [renaming, setRenaming] = useState<{ path: string; name: string } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const renameInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchFiles();
    }, []);

    const fetchFiles = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/files/list');
            const data = await response.json();
            setFiles(data.items || []);
        } catch (e) {
            console.error('Failed to fetch files', e);
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.length) return;

        const formData = new FormData();
        formData.append('file', e.target.files[0]);

        try {
            const response = await fetch('http://localhost:8000/files/upload', {
                method: 'POST',
                body: formData,
            });
            if (response.ok) {
                fetchFiles();
            }
        } catch (e) {
            console.error('Upload failed', e);
        }
    };

    const handleDelete = async (path: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm(`Delete ${path}?`)) return;

        try {
            await fetch(`http://localhost:8000/files/delete?path=${encodeURIComponent(path)}`, {
                method: 'POST',
            });
            fetchFiles();
        } catch (e) {
            console.error('Delete failed', e);
        }
    };

    const startRenaming = (file: FileItem, e: React.MouseEvent) => {
        e.stopPropagation();
        setRenaming({ path: file.path, name: file.name });
        // Focus will be handled by useEffect or autoFocus
    };

    const submitRename = async () => {
        if (!renaming) return;

        try {
            const response = await fetch(`http://localhost:8000/files/rename?old_path=${encodeURIComponent(renaming.path)}&new_name=${encodeURIComponent(renaming.name)}`, {
                method: 'POST',
            });

            if (response.ok) {
                fetchFiles();
            } else {
                console.error("Rename failed");
            }
        } catch (e) {
            console.error('Rename error', e);
        } finally {
            setRenaming(null);
        }
    };

    // Auto-focus input when renaming starts
    useEffect(() => {
        if (renaming && renameInputRef.current) {
            renameInputRef.current.focus();
        }
    }, [renaming]);

    const getIcon = (name: string, type: 'file' | 'directory') => {
        if (type === 'directory') return <FolderOpen size={16} className="text-[var(--dc-accent)]" />;
        if (name.endsWith('.csv') || name.endsWith('.json')) return <FileText size={16} className="text-[var(--dc-success)]" />;
        if (name.endsWith('.png') || name.endsWith('.jpg')) return <ImageIcon size={16} className="text-purple-400" />;
        return <File size={16} className="text-[var(--dc-text-secondary)]" />;
    };

    return (
        <div className="w-80 flex flex-col border-r border-[var(--dc-border)] bg-[var(--dc-bg-secondary)] h-full">
            {/* Header */}
            <div className="p-4 border-b border-[var(--dc-border)] flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <FolderOpen className="text-[var(--dc-accent)]" size={20} />
                    <span className="font-semibold text-[var(--dc-text-primary)]">Files</span>
                </div>
                <div className="flex gap-1">
                    <button
                        onClick={fetchFiles}
                        className="p-1.5 rounded hover:bg-[var(--dc-bg-tertiary)] text-[var(--dc-text-secondary)]"
                        title="Refresh"
                    >
                        <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="p-1.5 rounded hover:bg-[var(--dc-bg-tertiary)] text-[var(--dc-text-secondary)] hover:text-[var(--dc-accent)]"
                        title="Upload File"
                    >
                        <Upload size={16} />
                    </button>
                    <input
                        type="file"
                        ref={fileInputRef}
                        className="hidden"
                        onChange={handleUpload}
                    />
                </div>
            </div>

            {/* File List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {files.length > 0 ? (
                    files.map((file) => (
                        <div
                            key={file.name}
                            className="group flex items-center justify-between p-2 rounded hover:bg-[var(--dc-bg-tertiary)] cursor-pointer"
                        >
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                                {getIcon(file.name, file.type)}
                                {renaming?.path === file.path ? (
                                    <div className="flex items-center gap-1 flex-1" onClick={e => e.stopPropagation()}>
                                        <input
                                            ref={renameInputRef}
                                            type="text"
                                            value={renaming.name}
                                            onChange={(e) => setRenaming({ ...renaming, name: e.target.value })}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') submitRename();
                                                if (e.key === 'Escape') setRenaming(null);
                                            }}
                                            onBlur={submitRename}
                                            className="w-full text-sm bg-[var(--dc-bg-primary)] border border-[var(--dc-accent)] rounded px-1 py-0.5 outline-none text-[var(--dc-text-primary)]"
                                        />
                                    </div>
                                ) : (
                                    <span className="text-sm text-[var(--dc-text-primary)] truncate" title={file.name}>
                                        {file.name}
                                    </span>
                                )}
                            </div>

                            <div className={`flex items-center ${renaming?.path === file.path ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity gap-1`}>
                                {renaming?.path === file.path ? null : (
                                    <>
                                        <button
                                            onClick={(e) => startRenaming(file, e)}
                                            className="p-1 text-[var(--dc-text-secondary)] hover:text-[var(--dc-accent)]"
                                            title="Rename"
                                        >
                                            <Pencil size={14} />
                                        </button>
                                        {file.type === 'file' && (
                                            <a
                                                href={`http://localhost:8000/files/download?path=${encodeURIComponent(file.path)}`}
                                                download
                                                className="p-1 text-[var(--dc-text-secondary)] hover:text-[var(--dc-accent)]"
                                                title="Download"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                <Download size={14} />
                                            </a>
                                        )}
                                        <button
                                            onClick={(e) => handleDelete(file.path, e)}
                                            className="p-1 text-[var(--dc-text-secondary)] hover:text-red-400"
                                            title="Delete"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="text-center py-8 text-[var(--dc-text-secondary)]">
                        <p className="text-sm">No files found</p>
                        <p className="text-xs mt-1">Upload a dataset to get started</p>
                    </div>
                )}
            </div>

            {/* Drop Zone hint */}
            <div className="p-3 text-xs text-center text-[var(--dc-text-secondary)] border-t border-[var(--dc-border)] bg-[var(--dc-bg-tertiary)]/50">
                Workspace Files
            </div>
        </div>
    );
}
