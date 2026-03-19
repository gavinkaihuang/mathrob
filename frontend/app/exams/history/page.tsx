"use client";

import React, { useEffect, useState } from 'react';
import { fetchWithAuth, resolveImageUrl } from '@/utils/api';
import { LatexRenderer } from '@/components/LatexRenderer';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import clsx from 'clsx';
import Link from 'next/link';

interface ExamSummary {
  id: number;
  paper_name: string;
  created_at: string;
  ai_model?: string;
  exam_type?: 'custom' | 'diagnostic' | 'midterm' | 'final';
  total_score?: number;
  status?: string;
}

interface ExamDetail {
  id: number;
  paper_name: string;
  created_at: string;
  ai_model?: string;
  exam_type?: 'custom' | 'diagnostic' | 'midterm' | 'final';
  total_score?: number;
  overall_feedback?: string;
  image_urls?: string[];
  results?: Array<{
    problem_number: string;
    original_question_text?: string;
    user_answer_text?: string;
    score?: number;
    max_score?: number;
    knowledge_tag?: string;
    feedback?: string;
  }>;
}

const EXAM_TYPE_CONFIG = {
  custom: {
    label: '📝 日常练习',
    bgColor: 'bg-slate-100',
    textColor: 'text-slate-700',
    borderColor: 'border-slate-200',
    weight: 1.0
  },
  diagnostic: {
    label: '✨ 摸底定级',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200',
    weight: 2.0
  },
  midterm: {
    label: '🏆 期中评测',
    bgColor: 'bg-indigo-100',
    textColor: 'text-indigo-700',
    borderColor: 'border-indigo-200',
    weight: 3.0
  },
  final: {
    label: '👑 期末评测',
    bgColor: 'bg-rose-100',
    textColor: 'text-rose-700',
    borderColor: 'border-rose-200',
    weight: 3.0
  }
};

export default function ExamHistoryPage() {
  const [exams, setExams] = useState<ExamSummary[]>([]);
  const [selected, setSelected] = useState<ExamDetail | null>(null);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const activeExamId = selected?.id ?? null;

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const res = await fetchWithAuth('/api/exams/history');
      if (res.ok) {
        const data = await res.json();
        setExams(data);
      }
      setLoading(false);
    };
    load();
  }, []);

  const openDetail = async (id: number) => {
    setSelected(null);
    const res = await fetchWithAuth(`/api/exams/${id}`);
    if (res.ok) {
      const data = await res.json();
      setSelected(data);
    } else {
      alert('无法加载试卷详情');
    }
  };

  return (
    <>
    <main className="p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">试卷档案库</h1>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="col-span-1">
          <div className="space-y-4">
            {loading && <div>加载中...</div>}
            {!loading && exams.length === 0 && <div className="text-sm text-gray-500">暂无记录</div>}
            {exams.map((exam) => {
              const isActive = exam.id === activeExamId;
              return (
              <div
                key={exam.id}
                className={clsx(
                  'rounded-xl border p-4 cursor-pointer transition-all duration-200 relative',
                  isActive
                    ? 'bg-indigo-50/50 border-indigo-500 ring-1 ring-indigo-500 shadow-md'
                    : 'bg-white border-slate-200 hover:border-indigo-300 hover:shadow-sm'
                )}
                onClick={() => openDetail(exam.id)}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-indigo-600 rounded-r-md" />
                )}
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="text-xs text-gray-400 mb-2">{new Date(exam.created_at).toLocaleString()}</div>
                    <div className="font-bold text-slate-800 mb-2">{exam.paper_name}</div>
                    {exam.exam_type && (
                      <div
                        className={clsx(
                          'inline-block px-2 py-1 rounded text-xs font-medium',
                          EXAM_TYPE_CONFIG[exam.exam_type].bgColor,
                          EXAM_TYPE_CONFIG[exam.exam_type].textColor
                        )}
                      >
                        {EXAM_TYPE_CONFIG[exam.exam_type].label}
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-black text-indigo-600">{exam.total_score ?? 'N/A'} 分</div>
                    <div className="text-xs text-gray-500 mt-1">{exam.ai_model ? '🤖 ' + exam.ai_model : '—'}</div>
                  </div>
                </div>
                <div className="flex items-center justify-end">
                  <Link href="#" onClick={(e) => { e.preventDefault(); openDetail(exam.id); }} className="text-xs text-indigo-600 hover:text-indigo-800">查看详情 →</Link>
                </div>
              </div>
            )})}
          </div>
        </div>

        <div className="col-span-1 lg:col-span-3">
          {selected ? (
            <div className="bg-white rounded-2xl p-6 border">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">{selected.paper_name}</h2>
                <div className="text-sm text-gray-500">{new Date(selected.created_at).toLocaleString()}</div>
              </div>
              <div className="mb-4">
                <div className="text-sm text-gray-600">AI 模型: <span className="font-medium">{selected.ai_model || '—'}</span></div>
                <div className="text-sm text-gray-600">总分: <span className="font-medium">{selected.total_score ?? 'N/A'}</span></div>
              </div>

              {/* Image gallery */}
              {selected.image_urls && selected.image_urls.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">原卷与答题照片</h4>
                  <div className="flex gap-3 overflow-x-auto py-2">
                    {selected.image_urls.map((u, idx) => {
                      const src = resolveImageUrl(u);
                      return (
                        <button key={u} onClick={() => setLightboxSrc(src)} className="shrink-0">
                          <img src={src} alt={`img-${idx}`} className="w-36 h-24 object-cover rounded-md border" />
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">综合评价</h3>
                {selected.overall_feedback ? (
                  <MarkdownRenderer content={selected.overall_feedback} />
                ) : (
                  <div className="text-sm text-slate-500">无综合评价</div>
                )}
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-3">逐题详情</h3>
                <div className="space-y-3">
                  {selected.results && selected.results.length > 0 ? (
                    selected.results.map((r) => (
                      <div key={r.problem_number} className="p-3 border rounded-lg bg-white">
                        <div className="flex justify-between items-center mb-2">
                          <div className="font-bold">第 {r.problem_number} 题</div>
                          <div className="font-black">{r.score} / {r.max_score}</div>
                        </div>

                        <div className="space-y-3">
                          <div className="bg-gray-50 p-3 rounded-md text-sm text-slate-700">
                            <div className="font-semibold text-sm text-gray-600 mb-1">【原题】</div>
                            <div>
                              <LatexRenderer content={r.original_question_text || '无'} />
                            </div>
                          </div>

                          <div className="bg-blue-50 p-3 rounded-md text-sm text-slate-700">
                            <div className="font-semibold text-sm text-blue-600 mb-1">【你的解答】</div>
                            <div>
                              <LatexRenderer content={r.user_answer_text || '无'} />
                            </div>
                          </div>

                          <div className={`p-3 rounded-md text-sm ${r.score === r.max_score ? 'border border-emerald-200 bg-emerald-50' : 'border border-rose-200 bg-rose-50'}`}>
                            <div className="flex justify-between items-center mb-2">
                              <div className="font-semibold">AI 批改反馈</div>
                              <div className="font-bold">得分: {r.score} / {r.max_score}</div>
                            </div>
                            {r.feedback ? (
                              <MarkdownRenderer content={r.feedback} className="text-sm" />
                            ) : (
                              <div className="text-sm text-slate-500">无反馈</div>
                            )}
                            <div className="text-xs text-gray-500 mt-2">知识点: {r.knowledge_tag}</div>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-gray-500">无逐题数据</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl p-8 border text-center text-gray-400">选择一份试卷查看详情</div>
          )}
        </div>
      </div>
    </main>
      {lightboxSrc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setLightboxSrc(null)}>
          <div className="max-w-[90%] max-h-[90%]">
              <img src={lightboxSrc} alt="preview" className="max-w-full max-h-[80vh] rounded-md shadow-lg" />
            </div>
        </div>
      )}
    </>
  );
}
