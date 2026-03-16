'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/utils/api';
import { Loader2, PrinterIcon, Upload, CheckCircle2, X, FileImage, ArrowLeft } from 'lucide-react';
import 'katex/dist/katex.min.css';
import katex from 'katex';

interface PaperQuestion {
  num: number;
  knowledge_tag: string;
  latex_content: string;
  answer: string;
  explanation: string;
  score: number;
}

type Stage = 'loading' | 'paper_ready' | 'uploading' | 'submitted' | 'error';

/**
 * Renders a string that may contain inline ($...$) and display ($$...$$) LaTeX.
 * Falls back to plain text if KaTeX fails.
 */
function MathText({ text }: { text: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !text) return;

    // Replace $$...$$ (display) then $...$ (inline)
    let html = text
      .replace(/\n/g, '<br/>')
      .replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
        try {
          return `<span class="katex-display-inline">${katex.renderToString(math.trim(), { displayMode: true, throwOnError: false })}</span>`;
        } catch { return `$$${math}$$`; }
      })
      .replace(/\$([^$\n]+?)\$/g, (_, math) => {
        try {
          return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
        } catch { return `$${math}$`; }
      });

    ref.current.innerHTML = html;
  }, [text]);

  return <div ref={ref} className="math-text" />;
}

export default function AssessmentPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params?.session_id as string;

  const [stage, setStage] = useState<Stage>('loading');
  const [paper, setPaper] = useState<PaperQuestion[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadSession = async (sid: string) => {
    setStage('loading');
    try {
      const res = await fetchWithAuth(`/api/assessment/${sid}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'completed') {
          router.replace(`/assessment/${sid}/report`);
          return;
        }
        setPaper(data.paper_snapshot || []);
        setStage('paper_ready');
      } else {
        setError(`获取题目失败 [${res.status}]: ${await res.text()}`);
        setStage('error');
      }
    } catch {
      setError('网络错误，请检查后端服务');
      setStage('error');
    }
  };

  useEffect(() => {
    if (!sessionId) return;
    loadSession(sessionId);
  }, [sessionId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setSelectedFiles(Array.from(e.target.files));
  };

  const removeFile = (idx: number) =>
    setSelectedFiles(prev => prev.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    if (!selectedFiles.length || !sessionId) return;
    setUploading(true);
    const formData = new FormData();
    selectedFiles.forEach(f => formData.append('files', f));
    try {
      const res = await fetchWithAuth(`/api/assessment/${sessionId}/submit_full_paper`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        setStage('submitted');
        setTimeout(() => router.push(`/assessment/${sessionId}/report`), 1200);
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'AI 批改失败，请稍后重试');
        setUploading(false);
      }
    } catch {
      setError('网络错误');
      setUploading(false);
    }
  };

  /* ── Loading ── */
  if (stage === 'loading') return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mx-auto" />
        <p className="text-gray-700 font-medium">AI 正在生成试卷…</p>
        <p className="text-gray-400 text-sm">根据您的学习进度量身定制，请稍候</p>
      </div>
    </div>
  );

  /* ── Error ── */
  if (stage === 'error') return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="max-w-md w-full border border-red-200 rounded-2xl p-8 text-center space-y-4 bg-red-50">
        <X className="w-10 h-10 text-red-400 mx-auto" />
        <p className="text-red-600 font-medium">{error}</p>
        <button onClick={() => router.back()}
          className="px-6 py-2 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 transition text-sm">
          返回
        </button>
      </div>
    </div>
  );

  /* ── Submitted ── */
  if (stage === 'submitted') return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center space-y-3">
        <CheckCircle2 className="w-14 h-14 text-green-500 mx-auto" />
        <p className="text-gray-800 text-xl font-bold">提交成功！</p>
        <p className="text-gray-500 text-sm">正在跳转至 AI 批改报告…</p>
      </div>
    </div>
  );

  /* ── Paper Ready ── */
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <button onClick={() => router.back()}
            className="flex items-center gap-1.5 text-gray-500 hover:text-gray-800 transition text-sm">
            <ArrowLeft className="w-4 h-4" /> 返回
          </button>
          <h1 className="text-gray-900 font-bold text-base">摸底评测试卷</h1>
          <button
            onClick={() => router.push(`/assessment/${sessionId}/print`)}
            className="flex items-center gap-1.5 text-sm px-4 py-2 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition">
            <PrinterIcon className="w-4 h-4" /> 打印试卷
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto p-6 space-y-8">
        {/* Questions */}
        <div className="border border-gray-200 rounded-2xl overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-gray-900 font-bold text-base">试卷预览</h2>
            <p className="text-gray-500 text-sm mt-0.5">
              共 {paper.length} 道题 · 总分 {paper.reduce((a, q) => a + q.score, 0)} 分
            </p>
          </div>
          <div className="divide-y divide-gray-100">
            {paper.map((q, i) => (
              <div key={i} className="p-6 flex gap-4">
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-xs">
                  {q.num || i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {q.knowledge_tag}
                    </span>
                    <span className="text-xs text-gray-400">{q.score} 分</span>
                  </div>
                  <div className="text-gray-800 text-sm leading-relaxed">
                    <MathText text={q.latex_content} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upload section */}
        <div className="border border-gray-200 rounded-2xl p-6 space-y-4">
          <h2 className="text-gray-900 font-bold text-base">上传手写答卷</h2>
          <p className="text-gray-500 text-sm">
            打印试卷 → 纸笔完成解答 → 拍照上传。可一次上传多张图片（如多页答卷）。
          </p>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-indigo-200 rounded-xl p-8 text-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/50 transition space-y-3">
            <Upload className="w-9 h-9 text-indigo-400 mx-auto" />
            <p className="text-gray-700 font-medium text-sm">点击选择答卷图片</p>
            <p className="text-gray-400 text-xs">支持 JPG / PNG / HEIC，可多选</p>
            <input ref={fileInputRef} type="file" multiple accept="image/*" className="hidden" onChange={handleFileChange} />
          </div>

          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              {selectedFiles.map((f, i) => (
                <div key={i} className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
                  <FileImage className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                  <span className="text-gray-700 text-sm flex-1 truncate">{f.name}</span>
                  <span className="text-gray-400 text-xs">{(f.size / 1024).toFixed(0)} KB</span>
                  <button onClick={() => removeFile(i)} className="text-gray-300 hover:text-red-400 transition">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={!selectedFiles.length || uploading}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition flex items-center justify-center gap-2 text-sm">
            {uploading
              ? <><Loader2 className="w-4 h-4 animate-spin" /> AI 正在批改中，请耐心等待…</>
              : <><CheckCircle2 className="w-4 h-4" /> 提交答卷，开始 AI 批改</>
            }
          </button>
        </div>
      </div>
    </div>
  );
}
