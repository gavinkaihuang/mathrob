"use client";

import React, { useEffect, useState } from 'react';
import { fetchWithAuth } from '@/utils/api';
const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
import Link from 'next/link';

interface ExamSummary {
  id: number;
  paper_name: string;
  created_at: string;
  ai_model?: string;
  total_score?: number;
  status?: string;
}

interface ExamDetail {
  id: number;
  paper_name: string;
  created_at: string;
  ai_model?: string;
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

export default function ExamHistoryPage() {
  const [exams, setExams] = useState<ExamSummary[]>([]);
  const [selected, setSelected] = useState<ExamDetail | null>(null);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
            {exams.map(ex => (
              <div key={ex.id} className="bg-white p-4 rounded-xl border cursor-pointer hover:shadow" onClick={() => openDetail(ex.id)}>
                <div className="flex justify-between items-start">
                  <div>
                    <div className="text-sm text-gray-400">{new Date(ex.created_at).toLocaleString()}</div>
                    <div className="font-bold text-slate-800">{ex.paper_name}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-indigo-600 font-semibold">{ex.ai_model || '—'}</div>
                    <div className="text-xs text-gray-500">{ex.status}</div>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="text-sm text-slate-700">分数: {ex.total_score ?? 'N/A'}</div>
                  <Link href="#" onClick={(e) => { e.preventDefault(); openDetail(ex.id); }} className="text-sm text-indigo-600">查看</Link>
                </div>
              </div>
            ))}
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
                      const src = u && u.startsWith('http') ? u : `${API_URL}${u}`;
                      return (
                        <button key={u} onClick={() => setLightboxSrc(src)} className="shrink-0">
                          <img src={src} alt={`img-${idx}`} className="w-36 h-24 object-cover rounded-md border" />
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              <div className="prose max-w-none mb-6">
                <h3 className="text-lg font-semibold">综合评价</h3>
                <div className="text-sm text-slate-700 whitespace-pre-wrap">{selected.overall_feedback || '无'}</div>
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
                            <div className="whitespace-pre-wrap">{r.original_question_text || '无'}</div>
                          </div>

                          <div className="bg-blue-50 p-3 rounded-md text-sm text-slate-700">
                            <div className="font-semibold text-sm text-blue-600 mb-1">【你的解答】</div>
                            <div className="whitespace-pre-wrap">{r.user_answer_text || '无'}</div>
                          </div>

                          <div className={`p-3 rounded-md text-sm ${r.score === r.max_score ? 'border border-emerald-200 bg-emerald-50' : 'border border-rose-200 bg-rose-50'}`}>
                            <div className="flex justify-between items-center mb-2">
                              <div className="font-semibold">AI 批改反馈</div>
                              <div className="font-bold">得分: {r.score} / {r.max_score}</div>
                            </div>
                            <div className="text-sm text-slate-700 whitespace-pre-wrap">{r.feedback || '无'}</div>
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
