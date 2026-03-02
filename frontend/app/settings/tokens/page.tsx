'use client';

import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/utils/api';
import { Loader2, Plus, Trash2, RefreshCw, Key } from 'lucide-react';

interface GeminiToken {
    id: number;
    name: string;
    api_key: string;
    is_active: boolean;
    error_count: number;
    cooldown_until: string | null;
}

export default function TokenSettings() {
    const [tokens, setTokens] = useState<GeminiToken[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Form state
    const [isAdding, setIsAdding] = useState(false);
    const [newName, setNewName] = useState('');
    const [newKey, setNewKey] = useState('');

    const loadTokens = async () => {
        try {
            const res = await fetchWithAuth('/api/settings/tokens');
            if (!res.ok) throw new Error("Failed to load tokens");
            const data = await res.json();
            setTokens(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadTokens();
    }, []);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newName || !newKey) return;

        try {
            const res = await fetchWithAuth('/api/settings/tokens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName, api_key: newKey })
            });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to add token");
            }
            await loadTokens();
            setIsAdding(false);
            setNewName('');
            setNewKey('');
        } catch (err: any) {
            alert(err.message);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to delete this token?")) return;
        try {
            const res = await fetchWithAuth(`/api/settings/tokens/${id}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error("Failed to delete token");
            await loadTokens();
        } catch (err: any) {
            alert(err.message);
        }
    };

    const handleClearCooldown = async (id: number) => {
        try {
            const res = await fetchWithAuth(`/api/settings/tokens/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ clear_cooldown: true })
            });
            if (!res.ok) throw new Error("Failed to clear cooldown");
            await loadTokens();
        } catch (err: any) {
            alert(err.message);
        }
    };

    const handleToggleActive = async (id: number, current_status: boolean) => {
        try {
            const res = await fetchWithAuth(`/api/settings/tokens/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: !current_status })
            });
            if (!res.ok) throw new Error("Failed to update status");
            await loadTokens();
        } catch (err: any) {
            alert(err.message);
        }
    };

    const isTokenInCooldown = (cooldown_until: string | null) => {
        if (!cooldown_until) return false;
        return new Date(cooldown_until) > new Date();
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <div className="flex-grow max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-6 flex justify-between items-end">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Gemini Auth Tokens</h1>
                        <p className="mt-2 text-gray-600">
                            管理调用大模型服务的 API 密钥池 (Round-Robin & Fallback Pool)。
                        </p>
                    </div>
                    {!isAdding && (
                        <button
                            onClick={() => setIsAdding(true)}
                            className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 transition shadow-sm flex items-center gap-2 text-sm"
                        >
                            <Plus className="w-4 h-4" /> 添加 Token
                        </button>
                    )}
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg shadow-sm">
                        {error}
                    </div>
                )}

                {isAdding && (
                    <div className="mb-6 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">新增配置 (Add New Token)</h3>
                        <form onSubmit={handleAdd} className="flex flex-col gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">名称标识 (Alias Name) *</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    placeholder="e.g. key-01, backup-key-02"
                                    value={newName}
                                    onChange={e => setNewName(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">API Key *</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono"
                                    placeholder="AIzaSy..."
                                    value={newKey}
                                    onChange={e => setNewKey(e.target.value)}
                                />
                            </div>
                            <div className="flex justify-end gap-3 mt-2">
                                <button
                                    type="button"
                                    onClick={() => setIsAdding(false)}
                                    className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium transition"
                                >
                                    取消
                                </button>
                                <button
                                    type="submit"
                                    className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700 transition shadow-sm flex items-center gap-2"
                                >
                                    <Plus className="w-4 h-4" /> 保存提交
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    {loading ? (
                        <div className="p-12 flex justify-center items-center">
                            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Preview Key</th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Errors</th>
                                        <th scope="col" className="relative px-6 py-3"><span className="sr-only">Actions</span></th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {tokens.map((token) => (
                                        <tr key={token.id} className={!token.is_active ? 'bg-gray-50' : ''}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                <div className="flex items-center gap-2">
                                                    <Key className="w-4 h-4 text-gray-400" /> {token.name}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                                                ...{token.api_key.slice(-6)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {!token.is_active ? (
                                                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                                                        Disabled
                                                    </span>
                                                ) : isTokenInCooldown(token.cooldown_until) ? (
                                                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800" title={`Cooldown until: ${new Date(token.cooldown_until!).toLocaleString()}`}>
                                                        Cooldown
                                                    </span>
                                                ) : (
                                                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                        Active
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {token.error_count}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <div className="flex justify-end gap-3">
                                                    {isTokenInCooldown(token.cooldown_until) && token.is_active && (
                                                        <button
                                                            onClick={() => handleClearCooldown(token.id)}
                                                            title="Clear Cooldown"
                                                            className="text-indigo-600 hover:text-indigo-900 disabled:opacity-50"
                                                        >
                                                            <RefreshCw className="w-4 h-4" />
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => handleToggleActive(token.id, token.is_active)}
                                                        className={`${token.is_active ? 'text-amber-600 hover:text-amber-900' : 'text-green-600 hover:text-green-900'}`}
                                                    >
                                                        {token.is_active ? 'Disable' : 'Enable'}
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(token.id)}
                                                        className="text-red-600 hover:text-red-900 ml-2"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                    {tokens.length === 0 && !loading && (
                                        <tr>
                                            <td colSpan={5} className="px-6 py-8 text-center text-sm text-gray-500">
                                                No tokens configured. System will fail AI calls.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
