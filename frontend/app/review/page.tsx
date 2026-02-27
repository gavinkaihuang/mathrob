'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/utils/api';
import { motion, AnimatePresence } from 'framer-motion';

interface ReviewItem {
    id: number;
    latex_content: string;
    difficulty: number;
    knowledge_path: string;
    ai_analysis: any;
    trigger_variant: boolean;
}

export default function ReviewPage() {
    const [items, setItems] = useState<ReviewItem[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [showAnswer, setShowAnswer] = useState(false);
    const [loading, setLoading] = useState(true);
    const [completed, setCompleted] = useState(false);
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
            }
            setLoading(false);
        } catch (error) {
            console.error("Failed to load reviews", error);
            setLoading(false);
        }
    };

    const handleMasterySubmit = async (score: number) => {
        const currentItem = items[currentIndex];
        try {
            await fetchWithAuth(`/api/problems/${currentItem.id}/review?score=${score}`, {
                method: 'POST'
            });

            // Move to next or complete
            if (currentIndex + 1 < items.length) {
                setCurrentIndex(prev => prev + 1);
                setShowAnswer(false);
            } else {
                setCompleted(true);
            }
        } catch (error) {
            console.error("Failed to submit feedback", error);
        }
    };

    if (loading) return <div className="min-h-screen flex items-center justify-center">正在加载今日复习内容...</div>;

    if (completed || items.length === 0) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
                <div className="max-w-4xl mx-auto px-4 py-20 text-center">
                    <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-white dark:bg-slate-800 p-12 rounded-2xl shadow-xl border border-blue-100 dark:border-slate-700"
                    >
                        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600 mb-4">
                            🎉 今日复习完成！
                        </h1>
                        <p className="text-gray-600 dark:text-slate-400 text-lg mb-8">
                            {items.length === 0 ? '今天没有待复习的题目，休息一下吧！' : '持之以恒，才是记忆之王。明天见！'}
                        </p>
                        <button
                            onClick={() => router.push('/')}
                            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full transition-all font-semibold"
                        >
                            回首页
                        </button>
                    </motion.div>
                </div>
            </div>
        );
    }

    const currentItem = items[currentIndex];

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-slate-900 font-sans">
            <div className="max-w-3xl mx-auto px-4 py-12">
                {/* Progress Bar */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-blue-600">进度: {currentIndex + 1} / {items.length}</span>
                        <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs rounded-full font-bold">
                            {currentItem.knowledge_path || '综合复习'}
                        </span>
                    </div>
                    <div className="h-2 w-full bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <motion.div
                            className="h-full bg-blue-600"
                            initial={{ width: 0 }}
                            animate={{ width: `${((currentIndex + 1) / items.length) * 100}%` }}
                        />
                    </div>
                </div>

                {/* Flashcard Card */}
                <div className="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl overflow-hidden border border-gray-100 dark:border-slate-700 min-h-[500px] flex flex-col">
                    {/* Question Section */}
                    <div className="p-8 md:p-12 flex-grow">
                        <div className="text-xs uppercase tracking-widest text-gray-400 mb-6 font-bold">题目内容</div>
                        <div className="text-xl md:text-2xl leading-relaxed text-slate-800 dark:text-slate-100 overflow-x-auto">
                            {/* In a real app, use a LaTeX renderer component here */}
                            <pre className="whitespace-pre-wrap font-serif italic text-center py-8">
                                {currentItem.latex_content}
                            </pre>
                        </div>

                        {currentItem.trigger_variant && (
                            <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 text-amber-600 border border-amber-200 dark:border-amber-800 rounded-xl text-sm flex items-center gap-2">
                                💡 提示：您对此知识点已较熟练，建议之后挑战变式训练。
                            </div>
                        )}
                    </div>

                    {/* Answer Section */}
                    <AnimatePresence>
                        {showAnswer && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                className="bg-slate-50 dark:bg-slate-900/50 border-t border-gray-100 dark:border-slate-700 p-8 md:p-12"
                            >
                                <div className="mb-8">
                                    <div className="text-xs uppercase tracking-widest text-blue-600/70 mb-3 font-bold">思路启发</div>
                                    <p className="text-slate-600 dark:text-slate-400 italic leading-relaxed">
                                        {currentItem.ai_analysis?.thinking_process || '暂无思路提示'}
                                    </p>
                                </div>
                                <div>
                                    <div className="text-xs uppercase tracking-widest text-green-600/70 mb-3 font-bold">正确解答</div>
                                    <div className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
                                        {currentItem.ai_analysis?.solution || "暂无详细解析"}
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Interaction Buttons */}
                    <div className="p-6 md:p-8 bg-white dark:bg-slate-800 border-t border-gray-50 dark:border-slate-700 flex justify-center">
                        {!showAnswer ? (
                            <button
                                onClick={() => setShowAnswer(true)}
                                className="w-full max-w-xs py-4 bg-slate-900 dark:bg-blue-600 text-white rounded-2xl font-bold text-lg shadow-lg hover:shadow-blue-500/20 transition-all hover:-translate-y-1 active:scale-95"
                            >
                                查看解析
                            </button>
                        ) : (
                            <div className="w-full flex flex-col md:flex-row gap-4 items-center">
                                <span className="text-sm font-bold text-gray-400 mr-4 whitespace-nowrap">掌握程度：</span>
                                <div className="grid grid-cols-3 gap-3 flex-grow w-full">
                                    <button
                                        onClick={() => handleMasterySubmit(0)}
                                        className="py-3 bg-rose-50 hover:bg-rose-100 dark:bg-rose-900/20 text-rose-600 rounded-xl font-bold transition-colors border border-rose-100 dark:border-rose-900"
                                    >
                                        完全不会
                                    </button>
                                    <button
                                        onClick={() => handleMasterySubmit(1)}
                                        className="py-3 bg-amber-50 hover:bg-amber-100 dark:bg-amber-900/20 text-amber-600 rounded-xl font-bold transition-colors border border-amber-100 dark:border-amber-900"
                                    >
                                        半知半解
                                    </button>
                                    <button
                                        onClick={() => handleMasterySubmit(2)}
                                        className="py-3 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/20 text-emerald-600 rounded-xl font-bold transition-colors border border-emerald-100 dark:border-emerald-900"
                                    >
                                        完全掌握
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Keyboard Shortcuts Tips */}
                <div className="mt-8 text-center text-gray-400 text-xs font-medium uppercase tracking-widest">
                    提示：持之以恒的复习是掌握数学的关键
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
