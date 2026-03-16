'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/utils/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2, ArrowLeft, CheckCircle2, XCircle, MinusCircle, PenLine, Star } from 'lucide-react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts';
import 'katex/dist/katex.min.css';

interface GradedProblem {
  problem_id: string | number;
  score: number;
  max_score: number;
  feedback: string;
  knowledge_tag: string;
  is_correct: boolean;
}

interface ReportData {
  overall_score: number;
  report_markdown: string;
  formatting_feedback: string;
  graded_problems: GradedProblem[];
  status: string;
}

export default function AssessmentReportPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params?.session_id as string;

  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    fetchWithAuth(`/api/assessment/${sessionId}`)
      .then(async res => {
        if (res.ok) {
          const json = await res.json();
          setData(json);
        } else {
          setError(`无法加载报告 [${res.status}]`);
        }
      })
      .catch(() => setError('网络错误'))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mx-auto" />
        <p className="text-gray-700 font-medium">加载诊断报告中…</p>
      </div>
    </div>
  );

  if (error || !data) return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="border border-red-200 rounded-2xl p-8 max-w-md text-center space-y-4 bg-red-50">
        <XCircle className="w-10 h-10 text-red-400 mx-auto" />
        <p className="text-red-600">{error || '数据异常'}</p>
        <button onClick={() => router.back()} className="px-6 py-2 border border-gray-200 rounded-xl text-gray-600 hover:bg-gray-50 text-sm">返回</button>
      </div>
    </div>
  );

  const graded = data.graded_problems || [];
  const totalScore = graded.reduce((s, p) => s + (p.score || 0), 0);
  const maxScore = graded.reduce((s, p) => s + (p.max_score || 10), 0);
  const pct = maxScore > 0 ? Math.round(totalScore / maxScore * 100) : 0;

  // Radar data
  const radarData = graded.map(p => ({
    subject: p.knowledge_tag || `第${p.problem_id}题`,
    score: p.max_score > 0 ? Math.round(p.score / p.max_score * 100) : 0,
    fullMark: 100,
  }));

  const scoreColor = pct >= 80 ? 'text-green-400' : pct >= 60 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button onClick={() => router.push('/')} className="flex items-center gap-1.5 text-gray-500 hover:text-gray-800 transition text-sm">
            <ArrowLeft className="w-4 h-4" /> 返回主页
          </button>
          <h1 className="text-gray-900 font-bold text-base">AI 批改报告</h1>
          <div />
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-6 space-y-8">
        {/* Score Banner */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-8 text-center">
          <p className="text-indigo-500 text-sm mb-2">本次摸底评测总分</p>
          <p className={`text-7xl font-black mb-2 ${scoreColor}`}>{pct}<span className="text-3xl">分</span></p>
          <p className="text-gray-500 text-sm">{totalScore} / {maxScore} 分 · {graded.length} 道题</p>
        </div>

        {/* Radar + Formatting feedback */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {radarData.length > 2 && (
            <div className="border border-gray-200 rounded-2xl p-6 bg-white">
              <h3 className="text-gray-900 font-bold mb-4 text-sm">知识点能力雷达图</h3>
              <ResponsiveContainer width="100%" height={240}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(0,0,0,0.08)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#6366f1', fontSize: 11 }} />
                  <Radar dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} />
                  <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', color: '#111' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}
          {data.formatting_feedback && (
            <div className="border border-gray-200 rounded-2xl p-6 bg-white">
              <div className="flex items-center gap-2 mb-3">
                <PenLine className="w-4 h-4 text-indigo-500" />
                <h3 className="text-gray-900 font-bold text-sm">卷面评价</h3>
              </div>
              <p className="text-gray-600 text-sm leading-relaxed">{data.formatting_feedback}</p>
            </div>
          )}
        </div>

        {/* Per-question breakdown */}
        <div className="border border-gray-200 rounded-2xl overflow-hidden bg-white">
          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-gray-900 font-bold text-base">逐题批改详情</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {graded.map((p, i) => {
              const pctScore = p.max_score > 0 ? Math.round(p.score / p.max_score * 100) : 0;
              return (
                <div key={i} className="px-6 py-5 flex gap-4">
                  <div className="flex-shrink-0 mt-0.5">
                    {p.is_correct
                      ? <CheckCircle2 className="w-6 h-6 text-green-500" />
                      : p.score > 0
                        ? <MinusCircle className="w-6 h-6 text-yellow-500" />
                        : <XCircle className="w-6 h-6 text-red-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-gray-900 font-semibold text-sm">第 {p.problem_id} 题</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">{p.knowledge_tag}</span>
                      <span className={`text-xs font-bold ${pctScore >= 80 ? 'text-green-600' : pctScore >= 60 ? 'text-yellow-600' : 'text-red-500'}`}>
                        {p.score}/{p.max_score} 分
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm leading-relaxed">{p.feedback}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Comprehensive Report */}
        {data.report_markdown && (
          <div className="border border-gray-200 rounded-2xl p-6 bg-white">
            <div className="flex items-center gap-2 mb-4">
              <Star className="w-5 h-5 text-yellow-500" />
              <h2 className="text-gray-900 font-bold text-base">全局学情诊断报告</h2>
            </div>
            <div className="prose prose-sm max-w-none text-gray-700">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {data.report_markdown}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
