"use client";

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { Loader2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchWithAuth } from '@/utils/api';

export default function SysLogsPage() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [logs, setLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedRows, setExpandedRows] = useState<{ [key: number]: boolean }>({});

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/');
            return;
        }

        async function fetchLogs() {
            try {
                const res = await fetchWithAuth('/api/logs/system?limit=100');
                if (res.ok) {
                    const data = await res.json();
                    setLogs(data);
                }
            } catch (error) {
                console.error("Failed to fetch logs:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchLogs();
    }, [isAuthenticated, router]);

    const toggleRow = (id: number) => {
        setExpandedRows(prev => ({
            ...prev,
            [id]: !prev[id]
        }));
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-screen bg-gray-50">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8">
                <div className="mb-8 flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
                            <AlertCircle className="text-red-500" />
                            系统运行日志
                        </h1>
                        <p className="mt-2 text-sm text-gray-500 max-w-2xl">
                            这里记录了后台 AI 大模型调用过程中发生的底层错误或异常，包括解析失败、Token 消耗完毕或网络连接超时。
                        </p>
                    </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-16">

                                    </th>
                                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-24">
                                        ID
                                    </th>
                                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-32">
                                        Category
                                    </th>
                                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-40">
                                        Time
                                    </th>
                                    <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider flex-grow">
                                        Message
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {logs.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-12 text-center text-sm text-gray-500">
                                            🎉 恭喜！当前系统运行良好，没有任何报错记录。
                                        </td>
                                    </tr>
                                ) : (
                                    logs.map((log) => (
                                        <div key={log.id} style={{ display: 'contents' }}>
                                            <tr
                                                className={`hover:bg-gray-50 transition-colors cursor-pointer ${log.level === 'CRITICAL' ? 'bg-red-50/10' : ''}`}
                                                onClick={() => toggleRow(log.id)}
                                            >
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                                    {expandedRows[log.id] ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                    #{log.id}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-indigo-100 text-indigo-800 uppercase tracking-wide">
                                                        {log.category || 'SYSTEM'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {new Date(log.created_at).toLocaleString('zh-CN', {
                                                        year: 'numeric', month: '2-digit', day: '2-digit',
                                                        hour: '2-digit', minute: '2-digit', second: '2-digit'
                                                    })}
                                                </td>
                                                <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-xl">
                                                    {log.message}
                                                </td>
                                            </tr>
                                            {/* Expandable Details Row */}
                                            {expandedRows[log.id] && (
                                                <tr className="bg-gray-50/50">
                                                    <td colSpan={5} className="px-6 py-6 border-l-4 border-red-500">
                                                        <div className="pl-4">
                                                            <h4 className="text-sm font-semibold text-gray-900 mb-2">Error Details Payload</h4>
                                                            <pre className="text-xs text-gray-300 bg-gray-900 p-4 rounded-xl overflow-x-auto shadow-inner w-full whitespace-pre-wrap">
                                                                {log.details ? JSON.stringify(log.details, null, 2) : "No details provided."}
                                                            </pre>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </div>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
