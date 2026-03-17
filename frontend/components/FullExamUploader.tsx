'use client';

import React, { useRef, useState } from 'react';
import { useExamPolling } from '@/hooks/useExamPolling';

export default function FullExamUploader() {
  const {
    files,
    handleFilesChange,
    uploadFiles,
    isUploading,
    statusResponse,
    error,
    reset
  } = useExamPolling();
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

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
      const droppedFiles = Array.from(e.dataTransfer.files);
      handleFilesChange([...files, ...droppedFiles]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFiles = Array.from(e.target.files);
      handleFilesChange([...files, ...selectedFiles]);
    }
  };

  const removeFile = (index: number) => {
    const newFiles = [...files];
    newFiles.splice(index, 1);
    handleFilesChange(newFiles);
  };

  const triggerUpload = () => {
    if (files.length > 0) {
      uploadFiles(files);
    }
  };

  // 1. Loading State
  if (isUploading && statusResponse?.status === 'processing') {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-indigo-50/50 rounded-2xl border-2 border-dashed border-indigo-200">
        <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-6"></div>
        <h3 className="text-xl font-bold text-indigo-900 mb-2">AI 正在深度阅卷中...</h3>
        <p className="text-indigo-600">多模态大模型正在逐题拆解您的解答，预计需要 15-30 秒</p>
      </div>
    );
  }

  // 2. Completed State
  if (statusResponse?.status === 'completed') {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 overscroll-none">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-black text-slate-800">📊 阅卷报告</h2>
          <button onClick={reset} className="text-indigo-600 font-medium hover:underline text-sm">重新上传</button>
        </div>
        
        <div className="bg-indigo-50 rounded-xl p-6 text-center mb-8 border border-indigo-100">
          <div className="text-4xl font-black text-indigo-600 mb-2">{statusResponse.total_score} 分</div>
          <p className="text-sm text-indigo-800">{statusResponse.overall_evaluation}</p>
        </div>

        <div className="space-y-4">
          <h3 className="font-bold text-slate-700">逐题批改详情</h3>
          {statusResponse.results.map((res, idx) => (
            <div key={idx} className="bg-slate-50 border border-slate-200 p-4 rounded-xl">
              <div className="flex justify-between items-center mb-2">
                <span className="font-bold text-lg text-slate-800">第 {res.problem_number} 题</span>
                <span className={`font-black ${res.score === res.max_score ? 'text-emerald-500' : 'text-rose-500'}`}>
                  {res.score} / {res.max_score} 分
                </span>
              </div>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold px-2 py-1 bg-indigo-100 text-indigo-700 rounded-md">
                  {res.knowledge_tag}
                </span>
              </div>
              <p className="text-sm text-slate-600 border-l-2 border-slate-300 pl-3">
                {res.feedback}
              </p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 3. Setup / Upload State
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6">
      <h2 className="text-xl font-bold text-slate-800 mb-4">整卷智能批阅</h2>
      <p className="text-sm text-slate-500 mb-6">
        请上传您的试卷原题和手写解答照片。建议**先传题目，再传答题纸**。
      </p>

      <form onDragEnter={handleDrag} onSubmit={(e) => e.preventDefault()} className="mb-6">
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleChange} accept="image/*" />
        <div 
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer
            ${dragActive ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"}`}
          onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="text-4xl mb-3">📸</div>
          <p className="text-slate-600 font-medium">点击或拖拽照片至此</p>
          <p className="text-xs text-slate-400 mt-1">支持多张图片同时上传</p>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-200">
          发生错误: {error}
        </div>
      )}

      {files.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-bold text-slate-700 mb-3">已选择照片 ({files.length})</h4>
          <div className="flex flex-col gap-2">
            {files.map((file, idx) => (
              <div key={idx} className="flex justify-between items-center bg-slate-50 p-2 rounded-lg border border-slate-200 text-sm">
                <span className="truncate max-w-[200px] text-slate-600">{file.name}</span>
                <button onClick={() => removeFile(idx)} className="text-rose-500 hover:text-rose-700 font-medium px-2">移除</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <button 
        onClick={triggerUpload}
        disabled={files.length === 0 || isUploading}
        className="w-full py-3.5 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded-xl shadow-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isUploading ? '处理中...' : '提交阅卷'}
      </button>
    </div>
  );
}
