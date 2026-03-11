'use client';

import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/utils/api';
import { LatexRenderer } from '@/components/LatexRenderer';
import { Loader2, Calendar, ChevronDown, CheckCircle2, AlertCircle } from 'lucide-react';
import { SystemErrorBanner } from '@/components/SystemErrorBanner';

export default function ReviewHistoryPage() {
    const [sessions, setSessions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedSession, setExpandedSession] = useState<number | null>(null);
    const [sessionDetails, setSessionDetails] = useState<{ [key: number]: any[] }>({});
    const [loadingDetails, setLoadingDetails] = useState<{ [key: number]: boolean }>({});
    const [showAnswers, setShowAnswers] = useState<{ [problemId: number]: boolean }>({});
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        try {
            const res = await fetchWithAuth('/api/reviews/history?limit=50');
            if (res.ok) {
                const data = await res.json();
                setSessions(data);
            } else {
                setError('无法加载历史记录');
            }
        } catch (err: any) {
            setError(err.message || '网络错误');
        } finally {
            setLoading(false);
        }
    };

    const toggleSession = async (sessionId: number) => {
        if (expandedSession === sessionId) {
            setExpandedSession(null);
            return;
        }

        setExpandedSession(sessionId);

        // Fetch details if not already loaded
        if (!sessionDetails[sessionId]) {
            setLoadingDetails(prev => ({ ...prev, [sessionId]: true }));
            try {
                const res = await fetchWithAuth(`/api/reviews/history/${sessionId}`);
                if (res.ok) {
                    const data = await res.json();
                    setSessionDetails(prev => ({ ...prev, [sessionId]: data.problems }));
                }
            } catch (err) {
                console.error("Failed to fetch session details", err);
            } finally {
                setLoadingDetails(prev => ({ ...prev, [sessionId]: false }));
            }
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 pb-20">
            <SystemErrorBanner />
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="mb-10 text-center md:text-left">
                    <h1 className="text-4xl font-black text-slate-900 tracking-tight mb-3">复习题库</h1>
                    <p className="text-slate-500 text-lg">回顾你过去的"今日复习"历史记录和错题攻坚情况</p>
                </div>

                {error && (
                    <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-8 flex items-center gap-3">
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <span className="font-medium">{error}</span>
                    </div>
                )}

                {sessions.length === 0 && !error ? (
                    <div className="bg-white rounded-3xl p-12 text-center shadow-sm border border-slate-100 flex flex-col items-center">
                        <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6">
                            <Calendar className="w-10 h-10 text-slate-300" />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 mb-2">暂无复习记录</h3>
                        <p className="text-slate-500 max-w-sm">
                            你还没有完成过任何"今日复习"。<br />
                            赶快去"今日复习"模块开始你的第一次打卡吧！
                        </p>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {sessions.map((session) => {
                            const isExpanded = expandedSession === session.id;
                            const isDetailsLoading = loadingDetails[session.id];
                            const details = sessionDetails[session.id];

                            return (
                                <div key={session.id} className="bg-white rounded-[2rem] shadow-sm hover:shadow-md transition-shadow duration-300 border border-slate-100 overflow-hidden group">
                                    {/* Card Header (Clickable) */}
                                    <button 
                                        onClick={() => toggleSession(session.id)}
                                        className="w-full flex items-center justify-between p-6 sm:p-8 text-left transition-colors hover:bg-slate-50/50"
                                    >
                                        <div className="flex items-center gap-6">
                                            <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 shrink-0 group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300">
                                                <Calendar className="w-6 h-6" />
                                            </div>
                                            <div>
                                                <h3 className="text-xl font-bold text-slate-900 mb-1">
                                                    {new Date(session.review_date).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })} 复习任务
                                                </h3>
                                                <div className="flex items-center gap-3 text-sm text-slate-500 font-medium">
                                                    <span className="bg-slate-100 px-3 py-1 rounded-full">{session.problem_count} 道题目</span>
                                                    <span>生成于 {new Date(session.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="w-10 h-10 rounded-full bg-slate-50 flex items-center justify-center group-hover:bg-white shrink-0">
                                            <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`} />
                                        </div>
                                    </button>

                                    {/* Expanded Details Area */}
                                    <div className={`transition-all duration-300 ease-in-out ${isExpanded ? 'opacity-100' : 'max-h-0 opacity-0'} overflow-hidden`}>
                                        <div className="p-6 sm:p-8 pt-0 border-t border-slate-100 bg-slate-50/30">
                                            
                                            {isDetailsLoading && (
                                                <div className="flex items-center justify-center py-12 text-indigo-600">
                                                    <Loader2 className="w-6 h-6 animate-spin" />
                                                </div>
                                            )}

                                            {!isDetailsLoading && details && (
                                                <div className="space-y-8 mt-8">
                                                    {details.map((problem: any, idx: number) => {
                                                        const isCorrect = problem.review_history_status === 'correct';
                                                        let aiData = typeof problem.ai_analysis === 'string' ? JSON.parse(problem.ai_analysis) : (problem.ai_analysis || {});
                                                        
                                                        return (
                                                            <div key={problem.id} className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200/60 relative">
                                                                
                                                                <div className="flex justify-between items-start mb-6">
                                                                    <div className="flex items-center gap-3">
                                                                        <span className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm">
                                                                            {idx + 1}
                                                                        </span>
                                                                        <div className="flex gap-2">
                                                                            <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-md text-xs font-bold uppercase tracking-wider">
                                                                                ID: {problem.id}
                                                                            </span>
                                                                            {problem.knowledge_path && problem.knowledge_path !== 'unknown' && (
                                                                                <span className="px-3 py-1 bg-green-50 text-green-700 rounded-md text-xs font-bold tracking-wider truncate max-w-[200px]">
                                                                                    {problem.knowledge_node_name || problem.knowledge_path.split('/').pop()}
                                                                                </span>
                                                                            )}
                                                                            {problem.mastery_level > 0 && (
                                                                                <span className={`px-3 py-1 rounded-md text-xs font-bold tracking-wider ${
                                                                                    problem.mastery_level === 1 ? 'bg-rose-100 text-rose-700' :
                                                                                    problem.mastery_level === 2 ? 'bg-amber-100 text-amber-700' :
                                                                                    'bg-emerald-100 text-emerald-700'
                                                                                }`}>
                                                                                    {problem.mastery_level === 1 ? '完全不会' : problem.mastery_level === 2 ? '半知半解' : '完全掌握'}
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                    
                                                                    {isCorrect && (
                                                                        <div className="flex items-center gap-1.5 text-sm font-bold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full">
                                                                            <CheckCircle2 className="w-4 h-4" /> 已战胜
                                                                        </div>
                                                                    )}
                                                                </div>

                                                                {/* Problem Content */}
                                                                <div className="text-slate-800 text-lg mb-8 p-4 bg-slate-50 rounded-xl">
                                                                    <LatexRenderer content={problem.latex_content} block />
                                                                </div>

                                                                {/* Answer & Solution Toggle */}
                                                                <div className="flex justify-center mb-6">
                                                                    <button
                                                                        onClick={() => setShowAnswers(prev => ({ ...prev, [problem.id]: !prev[problem.id] }))}
                                                                        className="px-6 py-2.5 rounded-full bg-indigo-50 text-indigo-700 font-bold text-sm tracking-wide shadow-sm hover:bg-indigo-100 transition-colors"
                                                                    >
                                                                        {showAnswers[problem.id] ? "隐藏解析" : "查看解析"}
                                                                    </button>
                                                                </div>

                                                                {/* Answer & Solution */}
                                                                {showAnswers[problem.id] && (
                                                                    <div className="grid sm:grid-cols-2 gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
                                                                        {aiData.answer && (
                                                                            <div className="bg-indigo-50/50 rounded-xl p-5 border border-indigo-100/50">
                                                                                <h4 className="text-xs font-black text-indigo-400 uppercase tracking-widest mb-3">Model Answer</h4>
                                                                                <div className="text-indigo-900 font-bold">
                                                                                    <LatexRenderer content={aiData.answer} block={false} />
                                                                                </div>
                                                                            </div>
                                                                        )}
                                                                        {aiData.solution && (
                                                                            <div className="bg-slate-50 rounded-xl p-5 border border-slate-200/50 sm:col-span-2">
                                                                                <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Detailed Solution</h4>
                                                                                <div className="text-slate-700 text-sm leading-relaxed whitespace-pre-line">
                                                                                    <LatexRenderer content={aiData.solution} block />
                                                                                </div>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
