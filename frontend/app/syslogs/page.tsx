"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { Loader2, AlertCircle, ChevronDown, ChevronUp, Activity, ShieldAlert, Cpu, Key, CheckCircle, XCircle, Zap } from 'lucide-react';
import { fetchWithAuth } from '@/utils/api';

type TabType = 'errors' | 'calls' | 'operations';

export default function SysLogsPage() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<TabType>('errors');
    const [errorLogs, setErrorLogs] = useState<any[]>([]);
    const [callLogs, setCallLogs] = useState<any[]>([]);
    const [operationLogs, setOperationLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedRows, setExpandedRows] = useState<{ [key: number]: boolean }>({});

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/');
            return;
        }

        async function fetchAllLogs() {
            setLoading(true);
            try {
                const [errRes, callRes, opRes] = await Promise.all([
                    fetchWithAuth('/api/logs/system?limit=100'),
                    fetchWithAuth('/api/logs/calls?limit=100'),
                    fetchWithAuth('/api/logs/operations?skip=0&limit=100')
                ]);

                if (errRes.ok) {
                    const data = await errRes.json();
                    setErrorLogs(data);
                }
                if (callRes.ok) {
                    const data = await callRes.json();
                    setCallLogs(data);
                }
                if (opRes.ok) {
                    const data = await opRes.json();
                    setOperationLogs(data);
                }
            } catch (error) {
                console.error("Failed to fetch logs:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchAllLogs();
    }, [isAuthenticated, router]);

    const toggleRow = (id: number) => {
        setExpandedRows(prev => ({
            ...prev,
            [id]: !prev[id]
        }));
    };

    const getActionLabel = (action: string, targetId?: number) => {
        const labels: { [key: string]: string } = {
            'PARSE_PROBLEM': '解析题目',
            'GRADE_SOLUTION': '批改解答',
            'GENERATE_SIMILAR': '生成变式'
        };
        const base = labels[action] || action;
        return targetId ? `${base} #${targetId}` : base;
    };

    const getCategoryStyles = (category: string) => {
        const styles: { [key: string]: string } = {
            'VISION': 'bg-blue-100 text-blue-700 border-blue-200',
            'TEACHING': 'bg-purple-100 text-purple-700 border-purple-200',
            'UTILITY': 'bg-emerald-100 text-emerald-700 border-emerald-200',
            'SYSTEM': 'bg-gray-100 text-gray-700 border-gray-200'
        };
        return styles[category.toUpperCase()] || styles['SYSTEM'];
    };

    /**
     * 解析operation details并渲染为徽章
     * 根据action_type和details的字段动态渲染不同的徽章
     */
    const renderOperationDetails = (actionType: string, details: any) => {
        if (!details) return null;

        const badges: JSX.Element[] = [];
        
        // 单题批阅 (单题智能批阅)
        if (actionType === '单题智能批阅') {
            if (details.model_used) {
                badges.push(
                    <span key="model" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-indigo-100 text-indigo-700 rounded-md border border-indigo-200">
                        <Cpu className="w-3 h-3" />
                        {details.model_used}
                    </span>
                );
            }
            if (details.cost_time_ms) {
                badges.push(
                    <span key="time" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-orange-100 text-orange-700 rounded-md border border-orange-200">
                        <Zap className="w-3 h-3" />
                        {details.cost_time_ms}ms
                    </span>
                );
            }
            if (details.problem_id) {
                badges.push(
                    <span key="problem" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-gray-100 text-gray-700 rounded-md border border-gray-200">
                        题目 #{details.problem_id}
                    </span>
                );
            }
        }
        // 整卷批阅 (整卷智能批阅)
        else if (actionType === '整卷智能批阅') {
            if (details.exam_type) {
                const examTypeLabels: { [key: string]: string } = {
                    'CUSTOM': '自定义',
                    'DIAGNOSTIC': '诊断',
                    'MIDTERM': '期中',
                    'FINAL': '期末'
                };
                badges.push(
                    <span key="exam_type" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-rose-100 text-rose-700 rounded-md border border-rose-200">
                        类型: {examTypeLabels[details.exam_type] || details.exam_type}
                    </span>
                );
            }
            if (details.model_used) {
                badges.push(
                    <span key="model" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-indigo-100 text-indigo-700 rounded-md border border-indigo-200">
                        <Cpu className="w-3 h-3" />
                        {details.model_used}
                    </span>
                );
            }
            if (details.weight_applied) {
                badges.push(
                    <span key="weight" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-purple-100 text-purple-700 rounded-md border border-purple-200">
                        权重: {details.weight_applied}x
                    </span>
                );
            }
            if (details.total_problems) {
                badges.push(
                    <span key="problems" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-green-100 text-green-700 rounded-md border border-green-200">
                        {details.total_problems} 题
                    </span>
                );
            }
            if (details.cost_time_ms) {
                badges.push(
                    <span key="time" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-orange-100 text-orange-700 rounded-md border border-orange-200">
                        <Zap className="w-3 h-3" />
                        {details.cost_time_ms}ms
                    </span>
                );
            }
            if (details.exam_id) {
                badges.push(
                    <span key="exam" className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-bold bg-gray-100 text-gray-700 rounded-md border border-gray-200">
                        考试 #{details.exam_id}
                    </span>
                );
            }
        }

        return badges.length > 0 ? (
            <div className="flex flex-wrap gap-2">
                {badges}
            </div>
        ) : null;
    };

    /**
     * Render table based on active tab
     */
    const renderTableContent = () => {
        if (activeTab === 'errors') {
            return (
                <table className="min-w-full divide-y divide-gray-100">
                    <thead className="bg-gray-50/80">
                        <tr>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-12 text-center">+/-</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-24">ID</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-32">Category</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-44 text-center">Time</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest">Error Message</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {errorLogs.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-20 text-center">
                                    <div className="flex flex-col items-center opacity-40">
                                        <span className="text-4xl mb-4">🛡️</span>
                                        <p className="text-sm font-bold text-gray-500">当前没有记录到的系统异常</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            errorLogs.map((log) => (
                                <React.Fragment key={log.id}>
                                    <tr
                                        className={`group hover:bg-gray-50 transition-all cursor-pointer ${expandedRows[log.id] ? 'bg-red-50/30' : ''}`}
                                        onClick={() => toggleRow(log.id)}
                                    >
                                        <td className="px-6 py-4 text-center text-gray-300">
                                            {expandedRows[log.id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-400">#{log.id}</td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2.5 py-1 text-[10px] font-black rounded-lg border uppercase tracking-tight ${getCategoryStyles(log.category)}`}>
                                                {log.category || 'SYSTEM'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500 font-medium text-center">
                                            {new Date(log.created_at).toLocaleString('zh-CN')}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-700 font-semibold truncate max-w-xl">
                                            {log.message}
                                        </td>
                                    </tr>
                                    {expandedRows[log.id] && (
                                        <tr className="bg-gray-900">
                                            <td colSpan={5} className="px-12 py-8">
                                                <div className="space-y-4">
                                                    <div className="flex items-center gap-2 text-red-400 text-[10px] font-black uppercase tracking-widest">
                                                        <ShieldAlert className="w-3 h-3" /> Traceback Payload
                                                    </div>
                                                    <pre className="text-[11px] text-gray-400 font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed select-all">
                                                        {log.details ? JSON.stringify(log.details, null, 2) : "No details provided."}
                                                    </pre>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))
                        )}
                    </tbody>
                </table>
            );
        } else if (activeTab === 'calls') {
            return (
                <table className="min-w-full divide-y divide-gray-100">
                    <thead className="bg-gray-50/80">
                        <tr>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-44 text-center">Time</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-32">Category</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-48">Action</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-48">Model Used</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest">Token Pair</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {callLogs.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-20 text-center">
                                    <div className="flex flex-col items-center opacity-40">
                                        <span className="text-4xl mb-4">📡</span>
                                        <p className="text-sm font-bold text-gray-500">尚无成功的 AI 调用记录</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            callLogs.map((log) => (
                                <tr key={log.id} className="hover:bg-gray-50 transition-all">
                                    <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500 font-medium text-center">
                                        {new Date(log.created_at).toLocaleString('zh-CN')}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2.5 py-1 text-[10px] font-black rounded-lg border uppercase tracking-tight ${getCategoryStyles(log.category)}`}>
                                            {log.category}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm font-bold text-gray-800">
                                            {getActionLabel(log.action_type, log.target_id)}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2 text-xs font-semibold text-gray-600 bg-gray-100 px-2 py-1 rounded-md w-fit">
                                            <Cpu className="w-3 h-3 text-indigo-500" />
                                            {log.model_used}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2 text-xs font-semibold text-gray-400">
                                            <Key className="w-3 h-3" />
                                            {log.token_name || 'N/A'}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            );
        } else if (activeTab === 'operations') {
            return (
                <table className="min-w-full divide-y divide-gray-100">
                    <thead className="bg-gray-50/80">
                        <tr>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-44 text-center">时间 (Time)</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-48">动作 (Action)</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-28">状态 (Status)</th>
                            <th className="px-6 py-4 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest">执行详情 (Details)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {operationLogs.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="px-6 py-20 text-center">
                                    <div className="flex flex-col items-center opacity-40">
                                        <span className="text-4xl mb-4">⚡</span>
                                        <p className="text-sm font-bold text-gray-500">暂无业务运行日志</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            operationLogs.map((log) => (
                                <tr key={log.id} className="hover:bg-gray-50 transition-all">
                                    <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500 font-medium text-center">
                                        {new Date(log.created_at).toLocaleString('zh-CN', {
                                            year: 'numeric',
                                            month: '2-digit',
                                            day: '2-digit',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                            second: '2-digit'
                                        })}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm font-bold text-gray-800">
                                            {log.action_type}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2">
                                            {log.status === 'success' ? (
                                                <>
                                                    <CheckCircle className="w-4 h-4 text-green-500" />
                                                    <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-1 rounded-md">成功</span>
                                                </>
                                            ) : (
                                                <>
                                                    <XCircle className="w-4 h-4 text-red-500" />
                                                    <span className="text-xs font-bold text-red-700 bg-red-100 px-2 py-1 rounded-md">失败</span>
                                                </>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        {renderOperationDetails(log.action_type, log.details)}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            );
        }
        return null;
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
                {/* Header */}
                <div className="mb-8 flex justify-between items-center bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
                    <div>
                        <h1 className="text-3xl font-black tracking-tight text-gray-900 flex items-center gap-3">
                            <Activity className="text-indigo-600 w-8 h-8" />
                            日志管理中心
                        </h1>
                        <p className="mt-2 text-sm text-gray-500 font-medium">
                            全站运行监控。包含 AI 模型调用埋点记录与底层系统异常排查。
                        </p>
                    </div>
                </div>

                {/* Tab Switcher */}
                <div className="flex p-1.5 bg-gray-200/50 backdrop-blur-sm rounded-2xl w-fit mb-6 border border-gray-200/50">
                    <button
                        onClick={() => setActiveTab('errors')}
                        className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 ${activeTab === 'errors'
                            ? 'bg-white text-red-600 shadow-sm'
                            : 'text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        <ShieldAlert className="w-4 h-4" />
                        异常日志 (Error Logs)
                        {errorLogs.length > 0 && (
                            <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full ml-1 animate-pulse">
                                {errorLogs.length}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('calls')}
                        className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 ${activeTab === 'calls'
                            ? 'bg-white text-indigo-600 shadow-sm'
                            : 'text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        <Cpu className="w-4 h-4" />
                        调用记录 (Call Logs)
                        <span className="bg-indigo-100 text-indigo-600 text-[10px] px-1.5 py-0.5 rounded-full ml-1">
                            {callLogs.length}
                        </span>
                    </button>
                    <button
                        onClick={() => setActiveTab('operations')}
                        className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 ${activeTab === 'operations'
                            ? 'bg-white text-emerald-600 shadow-sm'
                            : 'text-gray-500 hover:text-gray-700'
                            }`}
                    >
                        <Zap className="w-4 h-4" />
                        业务日志 (Operation Logs)
                        {operationLogs.length > 0 && (
                            <span className="bg-emerald-100 text-emerald-600 text-[10px] px-1.5 py-0.5 rounded-full ml-1">
                                {operationLogs.length}
                            </span>
                        )}
                    </button>
                </div>

                {/* Content Area */}
                <div className="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 overflow-hidden">
                    <div className="overflow-x-auto">
                        {renderTableContent()}
                    </div>
                </div>
            </div>
        </div>
    );
}
