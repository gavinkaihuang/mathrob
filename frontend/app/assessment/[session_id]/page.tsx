'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/utils/api';
import { motion, AnimatePresence } from 'framer-motion';
import { LatexRenderer } from '@/components/LatexRenderer';
import { ChevronRight, Loader2, XCircle, CheckCircle2, AlertCircle } from 'lucide-react';

export default function AssessmentPage() {
    const router = useRouter();
    const params = useParams();
    const sessionId = params?.session_id as string;

    const [items, setItems] = useState<any[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [finalizing, setFinalizing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (sessionId) {
            loadAssessmentData(sessionId);
        }
    }, [sessionId]);

    const loadAssessmentData = async (sid: string) => {
        try {
            const res = await fetchWithAuth(`/api/assessment/${sid}`);
            if (res.ok) {
                const data = await res.json();
                setItems(data.problems || []);
            } else {
                const text = await res.text();
                setError(`获取题目失败 [${res.status}]: ${text}`);
            }
        } catch (err) {
            console.error("Failed to load assessment:", err);
            setError("网络错误");
        } finally {
            setLoading(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0 || !items[currentIndex]) return;
        
        const file = e.target.files[0];
        const problemId = items[currentIndex].id;
        
        const formData = new FormData();
        formData.append('file', file);
        
        setUploading(true);
        try {
            const res = await fetchWithAuth(`/api/assessment/${sessionId}/problems/${problemId}/submit`, {
                method: 'POST',
                body: formData
            });
            
            if (res.ok) {
                const data = await res.json();
                
                // Update local state to show it's submitted
                const newItems = [...items];
                newItems[currentIndex] = {
                    ...newItems[currentIndex],
                    is_submitted: true,
                    ai_score: data.ai_score,
                    ai_feedback: data.ai_feedback
                };
                setItems(newItems);
                
                // Auto advance
                if (currentIndex < items.length - 1) {
                    setTimeout(() => setCurrentIndex(currentIndex + 1), 600);
                }
            } else {
                alert('上传并批改失败，请重试');
            }
        } catch (err) {
            console.error('Upload Error:', err);
            alert('网络错误');
        } finally {
            setUploading(false);
            if (e.target) e.target.value = '';
        }
    };

    const handleFinalize = async () => {
        setFinalizing(true);
        try {
            const res = await fetchWithAuth(`/api/assessment/${sessionId}/finalize`, {
                method: 'POST'
            });
            if (res.ok) {
                router.push(`/assessment/${sessionId}/report`);
            } else {
                alert('试卷提交失败，请重试');
                setFinalizing(false);
            }
        } catch (err) {
            console.error('Finalize error', err);
            alert('网络错误');
            setFinalizing(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
                 <Loader2 className="w-10 h-10 animate-spin text-indigo-600 mb-4" />
                 <p className="text-slate-500">正在进入测验环境...</p>
            </div>
        );
    }

    if (error || items.length === 0) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
               <AlertCircle className="w-12 h-12 text-amber-500 mb-4" />
               <h2 className="text-xl font-bold text-slate-800 mb-2">获取题目失败</h2>
               <p className="text-slate-500 mb-6 max-w-md text-center">{error || "可能该测试并不存在或网络出了问题。"}</p>
               <button onClick={() => router.push('/')} className="px-6 py-2 bg-indigo-600 text-white rounded-lg">
                   返回首页
               </button>
            </div>
        );
    }

    const currentItem = items[currentIndex];
    const allSubmitted = items.every(i => i.is_submitted);
    const submittedCount = items.filter(i => i.is_submitted).length;

    return (
        <div className="h-screen bg-slate-50 flex overflow-hidden font-sans">
            {/* Left Sidebar */}
            <div className="w-80 lg:w-96 bg-white border-r border-slate-200 flex flex-col shrink-0 shadow-sm z-10">
                <div className="p-6 border-b border-slate-100 bg-white">
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-2">摸底评测</h2>
                    <p className="text-sm text-slate-500 font-medium flex justify-between">
                        <span>共 {items.length} 题</span>
                        <span className="text-indigo-600 font-bold">已完成 {submittedCount}/{items.length}</span>
                    </p>
                    
                    <div className="w-full bg-slate-100 rounded-full h-2 mt-4 overflow-hidden">
                        <div 
                         className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
                         style={{ width: `${(submittedCount / items.length) * 100}%` }}
                        ></div>
                    </div>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                    {items.map((item, index) => {
                        const isActive = index === currentIndex;
                        return (
                            <button
                                key={item.id}
                                onClick={() => setCurrentIndex(index)}
                                className={`w-full text-left p-4 rounded-2xl transition-all duration-200 border-2 group ${isActive ? 'bg-indigo-50 border-indigo-500 shadow-sm' : 'bg-white border-transparent hover:border-slate-200 hover:bg-slate-50'}`}
                            >
                                <div className="flex items-center gap-4">
                                    <div className="shrink-0 flex items-center justify-center">
                                        {item.is_submitted ? (
                                            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                                        ) : (
                                            <div className="w-6 h-6 rounded-full border-2 border-slate-200" />
                                        )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="font-bold text-slate-700">第 {index + 1} 题</div>
                                    </div>
                                    {isActive && <ChevronRight className="w-5 h-5 text-indigo-400" />}
                                </div>
                            </button>
                        );
                    })}
                </div>
                
                {/* Submit Action */}
                <div className="p-6 border-t border-slate-100 bg-white">
                    <button
                        onClick={handleFinalize}
                        disabled={finalizing || !allSubmitted}
                        className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all ${
                            allSubmitted && !finalizing 
                                ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md shadow-indigo-500/25' 
                                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                        }`}
                    >
                        {finalizing ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
                        {finalizing ? '正在生成诊断报告...' : '提交测卷并生成报告'}
                    </button>
                    {!allSubmitted && (
                        <p className="text-xs text-center text-slate-400 mt-3">需完成所有题目上传后方可交卷</p>
                    )}
                </div>
            </div>

            {/* Right Detail View */}
            <div className="flex-1 flex flex-col relative bg-slate-50/50 overflow-y-auto">
                <div className="max-w-4xl mx-auto px-8 py-10 w-full xl:px-12">
                     <div className="flex items-center justify-between mb-8">
                        <span className="px-4 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-black tracking-wider">
                            当前题目: {currentIndex + 1}
                        </span>
                     </div>

                     <motion.div
                        key={currentItem?.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-[2rem] shadow-sm border border-slate-200 p-8 md:p-12 mb-8"
                     >
                         <div className="text-xl md:text-2xl leading-relaxed text-slate-800 mb-10">
                             <LatexRenderer content={currentItem?.latex_content || ""} block />
                         </div>
                         
                         {/* Upload Action */}
                         {!currentItem?.is_submitted ? (
                             <div className="mt-8 pt-8 border-t border-slate-100">
                                 <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                                     <span className="text-indigo-600">📸</span> 上传解答
                                 </h3>
                                 <input
                                     type="file"
                                     id="assessment-upload"
                                     className="hidden"
                                     accept="image/*"
                                     onChange={handleFileUpload}
                                     disabled={uploading}
                                 />
                                 <label
                                     htmlFor="assessment-upload"
                                     className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                                         uploading ? 'bg-slate-50 border-slate-300' : 'border-indigo-200 bg-indigo-50/50 hover:bg-indigo-50 hover:border-indigo-300'
                                     }`}
                                 >
                                     {uploading ? (
                                         <div className="flex items-center gap-2 text-indigo-600 font-bold">
                                             <Loader2 className="w-5 h-5 animate-spin" />
                                             AI正在批改中...
                                         </div>
                                     ) : (
                                         <div className="flex flex-col items-center justify-center p-5 space-y-2">
                                             <p className="text-sm text-indigo-600 font-bold">点击拍照或上传图片</p>
                                             <p className="text-xs text-slate-400">支持 jpg, png 格式</p>
                                         </div>
                                     )}
                                 </label>
                             </div>
                         ) : (
                             <div className="mt-8 pt-8 border-t border-slate-100">
                                 <div className="px-6 py-4 bg-emerald-50 text-emerald-700 rounded-xl font-bold flex items-center border border-emerald-100">
                                     <CheckCircle2 className="w-6 h-6 mr-3 text-emerald-500" />
                                     本题已成功上传并由 AI 完成批阅。
                                     <span className="ml-auto bg-white px-3 py-1 rounded text-emerald-600 shadow-sm text-sm border border-emerald-100">
                                         得分: {currentItem.ai_score}
                                     </span>
                                 </div>
                             </div>
                         )}
                     </motion.div>
                </div>
            </div>
        </div>
    );
}
