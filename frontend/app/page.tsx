"use client";

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { FileUpload } from '@/components/FileUpload';
import KnowledgeMasteryDashboard from '@/components/KnowledgeMasteryDashboard';
import Link from 'next/link';

export default function Home() {
  const router = useRouter();
  const singleFileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // Drag handlers for mini dropzone
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setUploadedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadedFile(e.target.files[0]);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center p-8 pb-20">
      <div className="w-full max-w-7xl space-y-12 mt-10">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            MathRob AI
          </h1>
          <p className="text-lg leading-8 text-gray-600">
            Upload your math problems. Let AI analyze, solve, and help you master them.
          </p>
        </div>

        {/* Home Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full">
          
          {/* Left: Analytics Dashboard (8 Cols) */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            <KnowledgeMasteryDashboard />
          </div>

          {/* Right: Quick Actions Panel (4 Cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            
            {/* Quick Actions Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">快捷操作</h3>
              
              {/* Mini Dropzone - Single Problem Upload */}
              <div>
                <form onDragEnter={handleDrag} onSubmit={(e) => e.preventDefault()} className="mb-3">
                  <input 
                    ref={singleFileInputRef} 
                    type="file" 
                    className="hidden" 
                    onChange={handleFileChange} 
                    accept="image/*" 
                  />
                  <div 
                    className={`border-2 border-dashed rounded-xl p-4 text-center transition-all cursor-pointer
                      ${dragActive ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100"}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => singleFileInputRef.current?.click()}
                  >
                    <div className="text-2xl mb-1">📸</div>
                    <p className="text-xs font-medium text-slate-700">拖拽或点击上传</p>
                    <p className="text-xs text-slate-500 mt-0.5">单道错题</p>
                  </div>
                </form>

                {uploadedFile && (
                  <div className="mt-2 p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                    <div className="text-xs text-indigo-800 mb-2">
                      <span className="font-semibold">已选择：</span> {uploadedFile.name}
                    </div>
                    <div className="flex gap-2">
                      <button 
                        onClick={() => setUploadedFile(null)}
                        className="flex-1 px-2 py-1 text-xs bg-white hover:bg-indigo-100 text-indigo-600 rounded border border-indigo-200 transition-colors"
                      >
                        更换文件
                      </button>
                      <button 
                        className="flex-1 px-2 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded transition-colors"
                      >
                        立即上传
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="h-px bg-gray-200"></div>

              {/* Banner CTA - Full Exam Upload */}
              <button
                onClick={() => router.push('/exams/new')}
                className="group relative overflow-hidden w-full rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 p-5 text-white transition-all hover:-translate-y-1 hover:shadow-lg active:translate-y-0"
              >
                <div className="relative z-10">
                  <div className="text-2xl font-black mb-1">🚀 整卷智能批阅</div>
                  <div className="text-sm font-medium text-white/90">
                    支持期中/期末考卷，AI 深度评分与学情分析 →
                  </div>
                </div>
                {/* Shine effect on hover */}
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 transform group-hover:translate-x-full transition-transform duration-1000 ease-out"></div>
              </button>
            </div>

            {/* Info Card */}
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl border border-amber-200 p-4 space-y-2">
              <div className="text-sm font-semibold text-amber-900 flex items-center gap-2">
                <span>💡</span>
                <span>使用建议</span>
              </div>
              <ul className="text-xs text-amber-800 space-y-1">
                <li>• 单题上传：快速理解和掌握单个新题</li>
                <li>• 整卷批阅：完整考卷的专业评分与分析</li>
                <li>• 结果自动保存到"试卷档案库"</li>
              </ul>
            </div>

          </div>

        </div>
      </div>
    </main>
  );
}
