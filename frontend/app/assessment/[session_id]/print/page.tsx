'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/utils/api';
import { Loader2 } from 'lucide-react';
import 'katex/dist/katex.min.css';
import katex from 'katex';

function MathText({ text }: { text: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !text) return;
    let html = text.replace(/\n/g, '<br/>')
      .replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => {
        try { return `<span>${katex.renderToString(m.trim(), { displayMode: true, throwOnError: false })}</span>`; }
        catch { return `$$${m}$$`; }
      })
      .replace(/\$([^$\n]+?)\$/g, (_, m) => {
        try { return katex.renderToString(m.trim(), { displayMode: false, throwOnError: false }); }
        catch { return `$${m}$`; }
      });
    ref.current.innerHTML = html;
  }, [text]);
  return <div ref={ref} />;
}

interface PaperQuestion {
  num: number;
  knowledge_tag: string;
  latex_content: string;
  answer: string;
  explanation: string;
  score: number;
}

export default function PrintPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.session_id as string;
  const [paper, setPaper] = useState<PaperQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [examDate] = useState(() => new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }));

  useEffect(() => {
    if (!sessionId) return;
    fetchWithAuth(`/api/assessment/${sessionId}`)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setPaper(data.paper_snapshot || []);
        } else {
          setError('加载试卷失败');
        }
      })
      .catch(() => setError('网络错误'))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex items-center justify-center text-red-500">{error}</div>
  );

  const totalScore = paper.reduce((s, q) => s + q.score, 0);

  return (
    <>
      {/* Print-only styles injected */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { font-family: 'SimSun', 'Times New Roman', serif; color: #000; background: #fff; }
          .paper-page { padding: 20mm 20mm 20mm 30mm; }
          .question-box { page-break-inside: avoid; }
        }
        @media screen {
          body { background: #f3f4f6; }
          .paper-page { max-width: 210mm; margin: 0 auto; background: #fff; padding: 40px; box-shadow: 0 4px 24px rgba(0,0,0,0.12); }
        }
      `}</style>

      {/* Screen-only toolbar */}
      <div className="no-print fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
        <button onClick={() => router.back()} className="text-gray-600 hover:text-gray-900 text-sm flex items-center gap-1">
          ← 返回
        </button>
        <span className="text-gray-700 font-medium text-sm">打印预览</span>
        <button
          onClick={() => window.print()}
          className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg transition"
        >
          🖨️ 打印 / 导出 PDF
        </button>
      </div>

      {/* Paper body */}
      <div className="paper-page" style={{ paddingTop: '80px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '24px', borderBottom: '2px solid #000', paddingBottom: '12px' }}>
          <h1 style={{ fontSize: '22px', fontWeight: 'bold', margin: '0 0 6px' }}>高中数学 · 个人摸底评测试卷</h1>
          <div style={{ fontSize: '13px', color: '#444', display: 'flex', justifyContent: 'center', gap: '40px', marginTop: '8px' }}>
            <span>日期：{examDate}</span>
            <span>总分：<strong>{totalScore}</strong> 分</span>
            <span>得分：＿＿＿＿ 分</span>
          </div>
        </div>

        {/* Instructions */}
        <p style={{ fontSize: '12px', color: '#555', marginBottom: '20px', lineHeight: '1.6' }}>
          注意事项：本卷共 {paper.length} 道解答题，每题满分 {paper[0]?.score ?? 10} 分，作答时请写出完整解题过程。
        </p>

        {/* Questions */}
        {paper.map((q, i) => (
          <div key={i} className="question-box" style={{ marginBottom: '36px' }}>
            {/* Question title row */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginBottom: '10px' }}>
              <span style={{ fontWeight: 'bold', fontSize: '15px', flexShrink: 0 }}>
                {q.num || i + 1}.（{q.score} 分）
              </span>
              <div style={{ flex: 1, fontSize: '14px', lineHeight: '1.8' }}>
                <span style={{ fontSize: '11px', background: '#efefef', borderRadius: '3px', padding: '1px 6px', marginRight: '8px', color: '#555' }}>
                  {q.knowledge_tag}
                </span>
                <MathText text={q.latex_content} />
              </div>
            </div>

            {/* Answer space */}
            <div style={{
              minHeight: '220px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              padding: '8px',
              backgroundImage: 'repeating-linear-gradient(transparent, transparent 31px, #d9d9d9 32px)',
              backgroundSize: '100% 32px',
            }} />
          </div>
        ))}

        {/* Signature */}
        <div style={{ marginTop: '40px', borderTop: '1px solid #ccc', paddingTop: '12px', fontSize: '12px', color: '#888', textAlign: 'right' }}>
          MathRob · AI 个性化学习平台 · Session #{sessionId}
        </div>
      </div>
    </>
  );
}
