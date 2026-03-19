'use client';

import React, { useEffect, useState } from 'react';
import { fetchWithAuth } from '@/utils/api';
import { LatexRenderer } from '@/components/LatexRenderer';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

// 试卷类型徽章配置
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

interface ExamDetail {
  id: number;
  paper_name: string;
  exam_type?: 'custom' | 'diagnostic' | 'midterm' | 'final';
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
          const errorText = await res.text();
          console.error(`Failed to load exam detail: ${res.status} ${res.statusText}`, errorText);
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
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-900 font-bold text-lg mb-2">无法加载试卷详情</h2>
          <p className="text-red-700 mb-4">试卷 ID: {examId}</p>
          <p className="text-red-600 text-sm mb-4">可能的原因：</p>
          <ul className="text-red-600 text-sm list-disc list-inside mb-4 space-y-1">
            <li>试卷不存在或已被删除</li>
            <li>您没有权限访问此试卷</li>
            <li>网络连接可能有问题</li>
            <li>后端 API 可能未正确配置</li>
          </ul>
          <Link href="/exams/history" className="text-indigo-600 hover:text-indigo-800 text-sm">
            ← 返回档案库
          </Link>
        </div>
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
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-slate-800">{exam.paper_name}</h1>
                {exam.exam_type && (
                  <div
                    className={clsx(
                      'inline-flex items-center px-3 py-1 rounded-full text-xs sm:text-sm font-medium border',
                      EXAM_TYPE_CONFIG[exam.exam_type].bgColor,
                      EXAM_TYPE_CONFIG[exam.exam_type].textColor,
                      EXAM_TYPE_CONFIG[exam.exam_type].borderColor
                    )}
                  >
                    {EXAM_TYPE_CONFIG[exam.exam_type].label}
                  </div>
                )}
              </div>
            </div>
            <div className="text-right ml-4">
              <div className="text-2xl font-black text-indigo-600">{exam.total_score ?? 'N/A'} 分</div>
              <div className="text-sm text-gray-500">{new Date(exam.created_at).toLocaleString()}</div>
            </div>
          </div>

          <div className="flex flex-col gap-3 text-sm border-t pt-4">
            {/* AI Model Provenance */}
            {exam.ai_model && (
              <div className="flex items-center gap-2 text-gray-700">
                <span className="text-lg">🤖</span>
                <span className="font-semibold">批阅引擎:</span>
                <code className="bg-slate-100 px-2.5 py-1 rounded text-slate-700 font-mono text-xs">
                  {exam.ai_model}
                </code>
              </div>
            )}
            <div>
              <span className="font-semibold">创建时间:</span>
              <span className="ml-2 text-gray-600">{new Date(exam.created_at).toLocaleDateString()}</span>
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

        {/* Weight Indicator - for weighted exams */}
        {exam.exam_type && exam.exam_type !== 'custom' && (
          <div
            className={clsx(
              'rounded-2xl p-4 mb-6 border-l-4 flex items-start gap-3',
              exam.exam_type === 'diagnostic' ? 'bg-purple-50 border-purple-400' : 'bg-amber-50 border-amber-400'
            )}
          >
            <span className="text-2xl">⚖️</span>
            <div className="flex-1">
              <div className="font-semibold text-slate-800">
                {exam.exam_type === 'diagnostic'
                  ? '本次摸底测验按 2 倍权重计入知识掌握度'
                  : '本次大考结果按 3 倍权重深度计入知识掌握度'}
              </div>
              <div className="text-sm text-slate-700 mt-1">
                权重系数影响您的长期知识掌握度评估，高权重考试结果将获得更多关注。
              </div>
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
                const score = Number(result.score ?? 0);
                const maxScore = Number(result.max_score ?? 0);
                const isFull = maxScore > 0 && score === maxScore;
                const isZero = score === 0;
                const isPartial = score > 0 && score < maxScore;

                const theme = isFull
                  ? {
                      headerBg: 'bg-emerald-50',
                      headerText: 'text-emerald-700',
                      border: 'border-emerald-200',
                      scoreText: 'text-emerald-700',
                      badgeBg: 'bg-emerald-100',
                      badgeText: 'text-emerald-800',
                      accent: 'border-emerald-500',
                      icon: '✅',
                    }
                  : isZero
                  ? {
                      headerBg: 'bg-rose-50',
                      headerText: 'text-rose-700',
                      border: 'border-rose-200',
                      scoreText: 'text-rose-700',
                      badgeBg: 'bg-rose-100',
                      badgeText: 'text-rose-800',
                      accent: 'border-rose-500',
                      icon: '❌',
                    }
                  : {
                      headerBg: 'bg-amber-50',
                      headerText: 'text-amber-700',
                      border: 'border-amber-200',
                      scoreText: 'text-amber-700',
                      badgeBg: 'bg-amber-100',
                      badgeText: 'text-amber-800',
                      accent: 'border-amber-500',
                      icon: '⚠️',
                    };

                const outerClass = twMerge('border rounded-lg overflow-hidden', theme.border, 'bg-white');
                const headerClass = clsx('px-6 py-4', theme.headerBg);
                const titleClass = clsx('text-lg font-bold', theme.headerText);
                const scoreClass = clsx('text-2xl font-black flex items-center gap-2', theme.scoreText);
                const badgeClass = clsx('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', theme.badgeBg, theme.badgeText);

                return (
                  <div key={idx} className={outerClass}>
                    {/* Question Header */}
                    <div className={headerClass}>
                      <div className="flex justify-between items-center">
                        <div className={titleClass}>第 {result.problem_number} 题</div>
                        <div className={scoreClass}>
                          <span aria-hidden>{theme.icon}</span>
                          <span>{score}</span>
                          <span className="text-sm font-normal">/ {maxScore}</span>
                        </div>
                      </div>
                      {result.knowledge_tag && (
                        <div className={clsx('text-sm mt-2', theme.headerText)}>
                          <span className={badgeClass}>📚 {result.knowledge_tag}</span>
                        </div>
                      )}
                    </div>

                    {/* Question and Answer Section */}
                    <div className="px-6 py-4 space-y-4">
                      {/* Original Question */}
                      <div className={clsx('border-l-4 bg-white rounded p-4', theme.accent)}>
                        <div className="text-sm font-semibold text-slate-600 mb-2">【原题】</div>
                        {result.original_question_text ? (
                          <MarkdownRenderer content={result.original_question_text} className="text-sm" />
                        ) : (
                          <div className="text-slate-500 text-sm">无题目文本</div>
                        )}
                      </div>

                      {/* User Answer */}
                      <div className={clsx('border-l-4 bg-white rounded p-4', theme.accent)}>
                        <div className="text-sm font-semibold text-blue-600 mb-2">【你的解答】</div>
                        {result.user_answer_text ? (
                          <MarkdownRenderer content={result.user_answer_text} className="text-sm" />
                        ) : (
                          <div className="text-slate-500 text-sm">无解答文本</div>
                        )}
                      </div>

                      {/* AI Feedback */}
                      <div className={clsx('border-l-4 bg-white rounded p-4', theme.accent)}>
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
