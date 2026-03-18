'use client';

import React, { useEffect, useState } from 'react';
import { fetchWithAuth } from '@/utils/api';
import { LatexRenderer } from '@/components/LatexRenderer';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import Link from 'next/link';
import { useParams } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

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

export default function ExamDetailPage() {
  const params = useParams();
  const examId = params.id as string;
  const [exam, setExam] = useState<ExamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  useEffect(() => {
    const loadExamDetail = async () => {
      try {
        setLoading(true);
        const res = await fetchWithAuth(`/api/exams/${examId}`);
        if (res.ok) {
          const data = await res.json();
          setExam(data);
        } else {
          console.error('Failed to load exam detail');
        }
      } catch (error) {
        console.error('Error loading exam:', error);
      } finally {
        setLoading(false);
      }
    };

    if (examId) {
      loadExamDetail();
    }
  }, [examId]);

  if (loading) {
    return (
      <main className="p-8 max-w-6xl mx-auto">
        <div className="text-center text-gray-500">加载中...</div>
      </main>
    );
  }

  if (!exam) {
    return (
      <main className="p-8 max-w-6xl mx-auto">
        <div className="text-center text-gray-500">无法加载试卷详情</div>
      </main>
    );
  }

  return (
    <>
      <main className="p-8 max-w-6xl mx-auto">
        <div className="mb-6">
          <Link href="/exams/history" className="text-indigo-600 hover:text-indigo-800 text-sm">
            ← 返回档案库
          </Link>
        </div>

        {/* Header Section */}
        <div className="bg-white rounded-2xl p-6 border mb-6">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-3xl font-bold text-slate-800">{exam.paper_name}</h1>
            <div className="text-right">
              <div className="text-2xl font-black text-indigo-600">{exam.total_score ?? 'N/A'} 分</div>
              <div className="text-sm text-gray-500">{new Date(exam.created_at).toLocaleString()}</div>
            </div>
          </div>

          <div className="flex gap-6 text-sm text-gray-600">
            <div>
              <span className="font-semibold">AI 模型:</span>
              <span className="ml-2">{exam.ai_model || '—'}</span>
            </div>
            <div>
              <span className="font-semibold">创建时间:</span>
              <span className="ml-2">{new Date(exam.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>

        {/* Image Gallery */}
        {exam.image_urls && exam.image_urls.length > 0 && (
          <div className="bg-white rounded-2xl p-6 border mb-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">原卷与答题照片</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {exam.image_urls.map((url, idx) => {
                const src = url && url.startsWith('http') ? url : `${API_URL}${url}`;
                return (
                  <button
                    key={idx}
                    onClick={() => setLightboxSrc(src)}
                    className="group relative overflow-hidden rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
                  >
                    <img
                      src={src}
                      alt={`exam-img-${idx}`}
                      className="w-full h-32 object-cover group-hover:opacity-80 transition-opacity"
                    />
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20">
                      <span className="text-white text-sm font-medium">查看</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Overall Feedback */}
        <div className="bg-white rounded-2xl p-6 border mb-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">综合评价</h2>
          {exam.overall_feedback ? (
            <MarkdownRenderer content={exam.overall_feedback} />
          ) : (
            <div className="text-gray-500 text-sm">暂无综合评价</div>
          )}
        </div>

        {/* Detailed Results */}
        <div className="bg-white rounded-2xl p-6 border">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">逐题详情评价</h2>

          {exam.results && exam.results.length > 0 ? (
            <div className="space-y-6">
              {exam.results.map((result, idx) => {
                const isCorrect = result.score === result.max_score;
                return (
                  <div
                    key={idx}
                    className={`border rounded-lg overflow-hidden ${
                      isCorrect ? 'border-emerald-200 bg-emerald-50' : 'border-rose-200 bg-rose-50'
                    }`}
                  >
                    {/* Question Header */}
                    <div className="bg-gradient-to-r from-slate-700 to-slate-900 px-6 py-4 text-white">
                      <div className="flex justify-between items-center">
                        <div className="text-lg font-bold">第 {result.problem_number} 题</div>
                        <div className="text-2xl font-black">
                          {result.score} <span className="text-sm font-normal">/ {result.max_score}</span>
                        </div>
                      </div>
                      {result.knowledge_tag && (
                        <div className="text-sm text-slate-200 mt-2">📚 知识点: {result.knowledge_tag}</div>
                      )}
                    </div>

                    {/* Question and Answer Section */}
                    <div className="px-6 py-4 space-y-4">
                      {/* Original Question */}
                      <div className="border-l-4 border-slate-400 bg-white rounded p-4">
                        <div className="text-sm font-semibold text-slate-600 mb-2">【原题】</div>
                        {result.original_question_text ? (
                          <MarkdownRenderer content={result.original_question_text} className="text-sm" />
                        ) : (
                          <div className="text-slate-500 text-sm">无题目文本</div>
                        )}
                      </div>

                      {/* User Answer */}
                      <div className="border-l-4 border-blue-400 bg-white rounded p-4">
                        <div className="text-sm font-semibold text-blue-600 mb-2">【你的解答】</div>
                        {result.user_answer_text ? (
                          <MarkdownRenderer content={result.user_answer_text} className="text-sm" />
                        ) : (
                          <div className="text-slate-500 text-sm">无解答文本</div>
                        )}
                      </div>

                      {/* AI Feedback */}
                      <div className="border-l-4 border-indigo-400 bg-white rounded p-4">
                        <div className="text-sm font-semibold text-indigo-600 mb-2">【AI 批改反馈】</div>
                        {result.feedback ? (
                          <MarkdownRenderer content={result.feedback} className="text-sm" />
                        ) : (
                          <div className="text-slate-500 text-sm">无反馈信息</div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-gray-500 text-sm text-center py-8">暂无题目评价数据</div>
          )}
        </div>
      </main>

      {/* Lightbox for Image Preview */}
      {lightboxSrc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          onClick={() => setLightboxSrc(null)}
        >
          <div className="max-w-[90%] max-h-[90%]">
            <img
              src={lightboxSrc}
              alt="preview"
              className="max-w-full max-h-[80vh] rounded-lg shadow-2xl"
            />
          </div>
        </div>
      )}
    </>
  );
}
