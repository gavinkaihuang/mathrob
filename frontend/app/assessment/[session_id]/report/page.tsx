'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/utils/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { LatexRenderer } from '@/components/LatexRenderer';
import { Loader2, ArrowLeft, CheckCircle2 } from 'lucide-react';
import KnowledgeMasteryDashboard from '@/components/KnowledgeMasteryDashboard';

export default function AssessmentReportPage() {
    const router = useRouter();
    const params = useParams();
    const sessionId = params?.session_id as string;
    
    const [report, setReport] = useState<string | null>(null);
    const [score, setScore] = useState<number>(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (sessionId) {
            loadReport(sessionId);
        }
    }, [sessionId]);

    const loadReport = async (sid: string) => {
        // Technically this should be GET /api/assessment/{id}/report
        // Since we didn't specify building a GET endpoint in the prompt request,
        // we will simulate fetching it. In a real scenario, this data would either
        // be passed down or fetched from a dedicated endpoint.
        
        // Simulating the API returning the finalized markdown.
        setTimeout(() => {
            setReport(`
# 🌟 总体评价 (Overall Assessment)
太棒了！你已经完成了本次数学摸底测验。从结果来看，你在**集合的概念与运算**等基础模块展现出了扎实的功底。但随着难度梯度的上升，在综合应用题上暴露了一些短板，没关系，这正是我们接下来努力的方向。

# 📊 核心表现诊断 (Performance Breakdown)
- **集合与逻辑**: 表现优异，概念清晰。
- **函数性质**: 对于奇偶性与单调性的结合应用，逻辑推导存在断层。
- **立体几何**: 空间想象力不错，但在求二面角时的**计算错误**频发，需多加检查。

# ⚠️ 重灾区预警 (Priority Weaknesses)
根据 AI 阅卷引擎深度比对发现，你有以下几个高频失分点：
1. **二次函数的极值探讨**：分类讨论不完整，丢失了一类解。
2. **三角恒等变换公式**：降幂公式记忆不牢固。

# 📝 卷面与考学习惯 (Presentation & Habits)
**卷面规范度：良好**。
解题步骤清晰，LaTeX 连词和因果关系词（如“因为...所以...”）书写规范。但请注意等号对齐。

# 🚀 下一步突击计划 (Actionable Next Steps)
针对你今天的表现，明天的「今日复习」模块已经被我们安排得满满的！系统将为你优先推送**函数性质**和**三角恒等变换**的变式训练题，让我们一起逐个击破！
            `);
            setScore(85);
            setLoading(false);
        }, 1000);
    };

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50">
                 <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mb-6" />
                 <h2 className="text-xl font-black text-slate-800 tracking-wider">正在生成学情诊断报告...</h2>
                 <p className="text-sm text-slate-500 mt-2">AI 教研专家正在查阅你的答卷</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto space-y-8">
                
                {/* Header Actions */}
                <div className="flex items-center justify-between">
                    <button 
                        onClick={() => router.push('/')}
                        className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 transition-colors font-bold"
                    >
                        <ArrowLeft className="w-5 h-5" /> 返回控制台
                    </button>
                    <div className="px-4 py-1.5 bg-emerald-100 text-emerald-700 rounded-full text-sm font-black flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" /> 测验已归档
                    </div>
                </div>

                {/* Score Card */}
                <div className="bg-white rounded-[2rem] p-10 shadow-sm border border-slate-200 text-center relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-500"></div>
                    <h1 className="text-3xl font-black text-slate-800 mb-6">本次综合得分</h1>
                    <div className="inline-flex items-baseline justify-center px-12 py-6 bg-slate-50 rounded-3xl border-2 border-slate-100 shadow-inner mb-4">
                        <span className="text-7xl font-black text-indigo-600">{score}</span>
                        <span className="text-2xl font-bold text-slate-400 ml-2">/ 100</span>
                    </div>
                    <p className="text-slate-500 font-medium">综合表现评估已同步更新至您的知识图谱底表。</p>
                </div>

                {/* Dashboard Pre-view */}
                <div className="mb-8">
                    <KnowledgeMasteryDashboard />
                </div>

                {/* Report Content */}
                <div className="bg-white rounded-[2rem] p-8 md:p-12 shadow-sm border border-slate-200 prose prose-slate max-w-none prose-headings:font-black prose-h1:text-2xl prose-h1:text-indigo-900 prose-h1:pb-4 prose-h1:border-b prose-h1:border-slate-100 prose-li:marker:text-indigo-500">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {report || ''}
                    </ReactMarkdown>
                </div>

            </div>
            
            <style jsx global>{`
                .prose p { margin-bottom: 1.5em; line-height: 1.8; color: #475569; }
                .prose strong { color: #1e293b; }
            `}</style>
        </div>
    );
}
