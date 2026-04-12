'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchWithAuth, resolveImageUrl } from '@/utils/api';
import { motion, AnimatePresence } from 'framer-motion';
import { LatexRenderer } from '@/components/LatexRenderer';
import { CheckCircle2, Circle, HelpCircle, XCircle, ChevronRight, Loader2, ArrowRight } from 'lucide-react';

interface ReviewItem {
    id: number;
    latex_content: string;
    difficulty: number;
    knowledge_path: string;
    knowledge_node_name?: string;
    comprehensive_score?: number;
    ai_analysis: any;
    trigger_variant: boolean;
    mastery_level: number;
    original_id?: number;
    image_path?: string;
    is_variant?: boolean;
    variant_loading?: boolean;
}

export default function ReviewPage() {
    const [items, setItems] = useState<ReviewItem[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [showAnswer, setShowAnswer] = useState(false);
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [reports, setReports] = useState<Record<number, any>>({});
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        loadTodayReviews();
    }, []);

    const loadTodayReviews = async () => {
        try {
            const res = await fetchWithAuth('/api/reviews/today');
            if (res.ok) {
                const data = await res.json();
                setItems(data);
                // Find first unassessed item to select
                const firstUnassessed = data.findIndex((item: ReviewItem) => !item.mastery_level || item.mastery_level === 0);
                setCurrentIndex(firstUnassessed !== -1 ? firstUnassessed : 0);
            } else {
                const errText = await res.text();
                setError(`服务器返回错误 (${res.status}): ${errText.slice(0, 100)}`);
            }
        } catch (error: any) {
            console.error("Failed to load reviews", error);
            setError(`网络错误: ${error.message || '未知错误'}`);
        } finally {
            setLoading(false);
        }
    };

    const handleMasterySubmit = async (level: number) => {
        if (!items[currentIndex]) return;
        setUpdating(true);
        const problemId = items[currentIndex].original_id || items[currentIndex].id;

        try {
            const res = await fetchWithAuth(`/api/reviews/problems/${problemId}/mastery`, {
                method: 'POST',
                body: JSON.stringify({ mastery_level: level })
            });

            if (res.ok) {
                // Update local list
                const newItems = [...items];
                newItems[currentIndex].mastery_level = level;
                setItems(newItems);

                // Auto jump to next unassessed
                const nextUnassessed = newItems.findIndex((item, idx) =>
                    idx > currentIndex && (!item.mastery_level || item.mastery_level === 0)
                );

                if (nextUnassessed !== -1) {
                    setTimeout(() => {
                        setCurrentIndex(nextUnassessed);
                        setShowAnswer(false);
                    }, 400); // Small delay for user to see the color change
                } else {
                    // Look from beginning if none after
                    const firstUnassessed = newItems.findIndex((item) => !item.mastery_level || item.mastery_level === 0);
                    if (firstUnassessed !== -1) {
                        setTimeout(() => {
                            setCurrentIndex(firstUnassessed);
                            setShowAnswer(false);
                        }, 400);
                    }
                }
            } else {
                console.error("Failed to update mastery level");
            }
        } catch (err) {
            console.error("Error updating mastery", err);
        } finally {
            setUpdating(false);
        }
    };

    const handleGenerateVariant = async (index: number) => {
        const item = items[index];
        if (item.variant_loading || item.is_variant) return;

        // Set loading state
        const newItems = [...items];
        newItems[index] = { ...item, variant_loading: true };
        setItems(newItems);

        try {
            const originalId = item.original_id || item.id;
            const res = await fetchWithAuth(`/api/problems/${originalId}/similar`, {
                method: 'POST'
            });

            if (res.ok) {
                const variants = await res.json();
                if (variants && variants.length > 0) {
                    const variant = variants[0];
                    const nextItems = [...items];
                    nextItems[index] = {
                        ...nextItems[index],
                        original_id: originalId,
                        id: variant.id,
                        latex_content: variant.latex_content,
                        ai_analysis: variant.ai_analysis,
                        is_variant: true,
                        variant_loading: false
                    };
                    setItems(nextItems);
                    return;
                }
            }
            alert('生成变式失败，请重试');
        } catch (err) {
            console.error('Error generating variant', err);
            alert('网络错误');
        } finally {
            setItems(prevItems => {
                const updated = [...prevItems];
                // Only reset loading if we didn't succeed and replace the object entirely
                if (!updated[index].is_variant) {
                    updated[index] = { ...updated[index], variant_loading: false };
                }
                return updated;
            });
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0 || !items[currentIndex]) return;

        const file = e.target.files[0];
        const item = items[currentIndex];
        const problemId = item.id;

        const formData = new FormData();
        formData.append('file', file);

        setUploading(true);
        try {
            const endpoint = item.is_variant
                ? `/api/practice-problems/${problemId}/submit_solution`
                : `/api/reviews/0/problems/${problemId}/submit_homework`;

            const res = await fetchWithAuth(endpoint, {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                setReports(prev => ({ ...prev, [problemId]: data }));
                // Re-fetch to update comprehensive_score from backend
                await loadTodayReviews();
            } else {
                alert('上传作业或批改失败');
            }
        } catch (err) {
            console.error('Upload Error:', err);
            alert('网络错误');
        } finally {
            setUploading(false);
            if (e.target) e.target.value = '';
        }
    };

    const selectQuestion = (index: number) => {
        setCurrentIndex(index);
        setShowAnswer(false);
    };

    const getMasteryIcon = (level: number) => {
        switch (level) {
            case 1: return <XCircle className="w-5 h-5 text-rose-500 bg-rose-50 rounded-full" />;
            case 2: return <HelpCircle className="w-5 h-5 text-amber-500 bg-amber-50 rounded-full" />;
            case 3: return <CheckCircle2 className="w-5 h-5 text-emerald-500 bg-emerald-50 rounded-full" />;
            default: return <Circle className="w-5 h-5 text-slate-300" />;
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
                <Loader2 className="w-10 h-10 animate-spin text-indigo-600 mb-4" />
                <p className="text-slate-500">正在生成今日专属复习任务...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="bg-white p-8 rounded-2xl shadow-sm text-center max-w-md">
                    <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-slate-800 mb-2">加载失败</h2>
                    <p className="text-slate-600 mb-6">{error}</p>
                    <button onClick={() => { setError(null); setLoading(true); loadTodayReviews(); }} className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-bold">
                        重试
                    </button>
                </div>
            </div>
        );
    }

    if (items.length === 0) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="bg-white p-12 rounded-3xl shadow-sm text-center max-w-lg border border-slate-100">
                    <div className="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6">
                        <CheckCircle2 className="w-10 h-10 text-indigo-600" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-900 mb-4">🎉 今日无待复习题目</h1>
                    <p className="text-slate-500 mb-8 max-w-sm mx-auto">
                        太棒了！你已经清空了今日的复习队列。保持好习惯，明天继续挑战！
                    </p>
                    <button onClick={() => router.push('/')} className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full font-bold transition-all shadow-md hover:shadow-indigo-500/25">
                        返回首页
                    </button>
                </div>
            </div>
        );
    }

    const currentItem = items[currentIndex];
    const unassessedCount = items.filter(i => !i.mastery_level || i.mastery_level === 0).length;

    return (
        <div className="h-screen bg-slate-50 flex overflow-hidden font-sans">
            {/* Left Sidebar (Master) */}
            <div className="w-80 lg:w-96 bg-white border-r border-slate-200 flex flex-col shrink-0 shadow-sm z-10">
                <div className="p-6 border-b border-slate-100 bg-white">
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-2">今日复习</h2>
                    <p className="text-sm text-slate-500 font-medium">
                        共 {items.length} 题 <span className="mx-2">·</span> 剩余 <span className="text-indigo-600 font-bold">{unassessedCount}</span> 题未评估
                    </p>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-2 pb-24 scrollbar-thin scrollbar-thumb-slate-200">
                    {items.map((item, index) => {
                        const isActive = index === currentIndex;
                        return (
                            <button
                                key={item.id}
                                onClick={() => selectQuestion(index)}
                                className={`w-full text-left p-4 rounded-2xl transition-all duration-200 border-2 group ${isActive ? 'bg-indigo-50 border-indigo-500 shadow-sm' : 'bg-white border-transparent hover:border-slate-200 hover:bg-slate-50'}`}
                            >
                                <div className="flex items-start gap-4">
                                    <div className="mt-0.5 shrink-0 transition-transform group-hover:scale-110">
                                        {getMasteryIcon(item.mastery_level || 0)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`text-sm font-black ${isActive ? 'text-indigo-900' : 'text-slate-700'}`}>
                                                第 {index + 1} 题
                                            </span>
                                            {item.mastery_level > 0 && (
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${item.mastery_level === 1 ? 'bg-rose-100 text-rose-700' :
                                                    item.mastery_level === 2 ? 'bg-amber-100 text-amber-700' :
                                                        'bg-emerald-100 text-emerald-700'
                                                    }`}>
                                                    {item.mastery_level === 1 ? '完全不会' : item.mastery_level === 2 ? '半知半解' : '完全掌握'}
                                                </span>
                                            )}
                                        </div>
                                        {(() => {
                                            const score = item.comprehensive_score;
                                            let badgeColor = 'bg-slate-100 text-slate-500';
                                            if (score !== undefined && score !== null) {
                                                if (score < 6) badgeColor = 'bg-red-100 text-red-600';
                                                else if (score <= 8) badgeColor = 'bg-yellow-100 text-yellow-600';
                                                else badgeColor = 'bg-green-100 text-green-600';
                                            }
                                            return (
                                                <div className={`text-xs font-bold truncate w-fit px-2 py-1 rounded ${badgeColor} transition-colors`}>
                                                    {item.knowledge_node_name || item.knowledge_path.split('/').pop() || '综合考点'}
                                                    {score !== undefined && score !== null && ` (${score.toFixed(1)}分)`}
                                                </div>
                                            );
                                        })()}
                                    </div>
                                    {isActive && (
                                        <ChevronRight className="w-5 h-5 text-indigo-400 self-center" />
                                    )}
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Right Detail View */}
            <div className="flex-1 flex flex-col relative bg-slate-50/50">
                <div className="flex-1 overflow-y-auto pb-40">
                    <div className="max-w-4xl mx-auto px-8 py-10 xl:px-12">
                        {/* Status Bar */}
                        <div className="flex items-center justify-between mb-8">
                            <div className="flex items-center gap-3">
                                <span className="w-10 h-10 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center font-black text-lg shadow-inner">
                                    {currentIndex + 1}
                                </span>
                                <span className="px-4 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-black tracking-wider">
                                    ID: {currentItem.id}
                                </span>
                            </div>

                            {!currentItem.is_variant && (
                                <button
                                    onClick={() => handleGenerateVariant(currentIndex)}
                                    disabled={currentItem.variant_loading}
                                    className="px-4 py-2 bg-indigo-100 text-indigo-700 hover:bg-indigo-200 rounded-lg text-sm font-bold flex items-center gap-2 shadow-sm border border-indigo-200 transition-colors disabled:opacity-50"
                                >
                                    {currentItem.variant_loading ? (
                                        <><Loader2 className="w-4 h-4 animate-spin" /> 生成中...</>
                                    ) : (
                                        <>✨ 点击生成专属变式新题</>
                                    )}
                                </button>
                            )}
                            {currentItem.is_variant && (
                                <div className="px-4 py-2 bg-emerald-100 text-emerald-700 rounded-lg text-sm font-bold flex items-center gap-2 shadow-sm border border-emerald-200">
                                    🎯 已为你生成专属变式题
                                </div>
                            )}
                        </div>

                        {/* Problem Card */}
                        <motion.div
                            key={currentItem.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white rounded-[2rem] shadow-sm border border-slate-200 p-8 md:p-12 mb-8 relative overflow-hidden"
                        >
                            <div className="text-xs font-black uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-slate-400"></div> {currentItem.is_variant ? '智能变式试题' : '题目原题'}
                            </div>
                            <div className="text-xl md:text-2xl leading-relaxed text-slate-800">
                                <LatexRenderer content={currentItem.latex_content} block />
                            </div>

                            {currentItem.image_path && (
                                <div className="mt-8 pt-6 border-t border-slate-100 flex justify-center">
                                    <div className="relative group">
                                        <div className="text-xs font-black uppercase tracking-widest text-slate-400 mb-3 text-center">题目原图截取参考</div>
                                        <img src={resolveImageUrl(currentItem.image_path)} alt="Original Reference" className="max-w-full max-h-[300px] object-contain rounded-xl shadow-sm border border-slate-200 group-hover:shadow-md transition-shadow" />
                                    </div>
                                </div>
                            )}
                        </motion.div>

                        {/* Homework Upload and Report Area */}
                        <div className="mb-8">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                    <span className="text-indigo-600">📝</span> AI 智能批改
                                </h3>
                                <div>
                                    <input
                                        type="file"
                                        id="homework-upload"
                                        className="hidden"
                                        accept="image/*"
                                        onChange={handleFileUpload}
                                        disabled={uploading}
                                    />
                                    <label
                                        htmlFor="homework-upload"
                                        className={`cursor-pointer px-5 py-2 rounded-xl font-bold text-sm transition-all shadow-sm border ${uploading ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed' : 'bg-white text-indigo-600 border-indigo-200 hover:bg-indigo-50 hover:border-indigo-300'}`}
                                    >
                                        {uploading ? "正在批改中..." : "上传我的解答"}
                                    </label>
                                </div>
                            </div>

                            {/* AI Grading Report Card */}
                            {reports[currentItem.id] && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    className="bg-indigo-50/50 rounded-2xl p-6 border border-indigo-100 mb-6"
                                >
                                    <div className="flex items-center justify-between border-b border-indigo-100 pb-4 mb-4">
                                        <h4 className="font-black text-indigo-900">AI 批改报告</h4>
                                        <div className="text-xl font-black text-indigo-600 bg-white px-3 py-1 rounded-lg border border-indigo-100 shadow-sm">
                                            {reports[currentItem.id].ai_score?.toFixed(0) || 0} <span className="text-sm text-indigo-400">分</span>
                                        </div>
                                    </div>

                                    <div className="space-y-4">
                                        {reports[currentItem.id].formatting_feedback && (
                                            <div className="bg-white rounded-xl p-4 border border-indigo-50 shadow-sm">
                                                <h5 className="text-xs font-black text-slate-500 uppercase mb-2">卷面与规范</h5>
                                                <p className="text-sm text-slate-700 leading-relaxed">{reports[currentItem.id].formatting_feedback}</p>
                                            </div>
                                        )}

                                        {reports[currentItem.id].ai_evaluation?.logic_gaps && reports[currentItem.id].ai_evaluation.logic_gaps.length > 0 && (
                                            <div className="bg-white rounded-xl p-4 border border-rose-50 shadow-sm">
                                                <h5 className="text-xs font-black text-rose-500 uppercase mb-2">逻辑漏洞</h5>
                                                <ul className="list-disc pl-5 text-sm text-rose-700 leading-relaxed space-y-1">
                                                    {reports[currentItem.id].ai_evaluation.logic_gaps.map((gap: string, i: number) => (
                                                        <li key={i}>{gap}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {reports[currentItem.id].ai_evaluation?.calculation_errors && reports[currentItem.id].ai_evaluation.calculation_errors.length > 0 && (
                                            <div className="bg-white rounded-xl p-4 border border-amber-50 shadow-sm">
                                                <h5 className="text-xs font-black text-amber-500 uppercase mb-2">计算错误</h5>
                                                <ul className="list-disc pl-5 text-sm text-amber-700 leading-relaxed space-y-1">
                                                    {reports[currentItem.id].ai_evaluation.calculation_errors.map((err: string, i: number) => (
                                                        <li key={i}>{err}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            )}
                        </div>

                        {/* Analysis & Solution Toggle */}
                        <div className="flex justify-center mb-8">
                            <button
                                onClick={() => setShowAnswer(!showAnswer)}
                                className={`px-8 py-3 rounded-full font-bold text-sm tracking-widest uppercase transition-all shadow-sm flex items-center gap-2 ${showAnswer ? 'bg-slate-200 text-slate-600 hover:bg-slate-300' : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-500/30'}`}
                            >
                                {showAnswer ? "▲ 隐藏答题卡" : "▼ 查看思路与答案"}
                            </button>
                        </div>

                        {/* Analysis & Solution Content */}
                        <AnimatePresence>
                            {showAnswer && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    <div className="grid lg:grid-cols-1 gap-6 mb-8">
                                        <div className="bg-white rounded-[2rem] p-8 shadow-sm border border-slate-200 relative overflow-hidden">
                                            <div className="absolute top-0 left-0 w-2 h-full bg-indigo-500"></div>
                                            <h4 className="text-xs font-black text-indigo-500 uppercase tracking-widest mb-4">思路启发</h4>
                                            <div className="text-slate-600 italic text-sm leading-relaxed">
                                                <LatexRenderer content={currentItem.ai_analysis?.thinking_process || '自主思考，回想相关公式...'} />
                                            </div>
                                        </div>
                                        <div className="bg-white rounded-[2rem] p-8 md:p-10 shadow-sm border border-slate-200 relative overflow-hidden">
                                            <div className="absolute top-0 left-0 w-2 h-full bg-emerald-400"></div>
                                            <h4 className="text-xs font-black text-emerald-600 uppercase tracking-widest mb-6">正确解答</h4>
                                            <div className="text-slate-800 font-medium leading-relaxed">
                                                <LatexRenderer content={currentItem.ai_analysis?.solution || "暂无详细解析"} block />
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>

                {/* Sticky Bottom Bar for Mastery Evaluation */}
                <div className="absolute bottom-0 left-0 w-full bg-white/80 backdrop-blur-xl border-t border-slate-200 p-6 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.05)] z-20">
                    <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
                        <div className="text-center sm:text-left">
                            <h3 className="text-sm font-black text-slate-800 uppercase tracking-widest mb-1">评估本次掌握度</h3>
                            <p className="text-xs text-slate-500 font-medium">真实的反馈能让记忆算法更精准</p>
                        </div>
                        <div className="flex items-center gap-3 w-full sm:w-auto">
                            <button
                                disabled={updating}
                                onClick={() => handleMasterySubmit(1)}
                                className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-bold tracking-wide transition-all border-2 ${currentItem.mastery_level === 1 ? 'bg-rose-500 text-white border-rose-600 shadow-lg shadow-rose-500/30' : 'bg-white text-rose-600 border-rose-100 hover:border-rose-300 hover:bg-rose-50'} disabled:opacity-50`}
                            >
                                <XCircle className="w-5 h-5" />
                                完全不会
                            </button>
                            <button
                                disabled={updating}
                                onClick={() => handleMasterySubmit(2)}
                                className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-bold tracking-wide transition-all border-2 ${currentItem.mastery_level === 2 ? 'bg-amber-500 text-white border-amber-600 shadow-lg shadow-amber-500/30' : 'bg-white text-amber-600 border-amber-100 hover:border-amber-300 hover:bg-amber-50'} disabled:opacity-50`}
                            >
                                <HelpCircle className="w-5 h-5" />
                                半知半解
                            </button>
                            <button
                                disabled={updating}
                                onClick={() => handleMasterySubmit(3)}
                                className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-bold tracking-wide transition-all border-2 ${currentItem.mastery_level === 3 ? 'bg-emerald-500 text-white border-emerald-600 shadow-lg shadow-emerald-500/30' : 'bg-white text-emerald-600 border-emerald-100 hover:border-emerald-300 hover:bg-emerald-50'} disabled:opacity-50`}
                            >
                                <CheckCircle2 className="w-5 h-5" />
                                完全掌握
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <style jsx global>{`
                pre {
                    font-family: 'STIX Two Text', serif;
                }
            `}</style>
        </div>
    );
}
