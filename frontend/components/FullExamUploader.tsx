'use client';

import React, { useRef, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useExamPolling } from '@/hooks/useExamPolling';

export default function FullExamUploader() {
  const router = useRouter();
  const [examMode, setExamMode] = useState<'separated' | 'combined'>('separated');
  const [selectedExamType, setSelectedExamType] = useState<'custom' | 'diagnostic' | 'midterm' | 'final'>('custom');
  const {
    questionFiles,
    answerFiles,
    combinedFiles,
    handleQuestionFilesChange,
    handleAnswerFilesChange,
    handleCombinedFilesChange,
    uploadFiles,
    isUploading,
    statusResponse,
    error,
    reset
  } = useExamPolling();
  
  const questionFileInputRef = useRef<HTMLInputElement>(null);
  const answerFileInputRef = useRef<HTMLInputElement>(null);
  const combinedFileInputRef = useRef<HTMLInputElement>(null);
  const [questionDragActive, setQuestionDragActive] = useState(false);
  const [answerDragActive, setAnswerDragActive] = useState(false);
  const [combinedDragActive, setCombinedDragActive] = useState(false);

  // 监听上传完成，自动跳转到试卷详情页
  useEffect(() => {
    if (statusResponse?.status === 'completed' && statusResponse?.exam_id) {
      // 延迟以确保所有状态更新完成
      const timer = setTimeout(() => {
        reset();
        router.push(`/exams/${statusResponse.exam_id}`);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [statusResponse?.status, statusResponse?.exam_id, reset, router]);

  // ============================================================
  // Question Images Dropzone
  // ============================================================
  const handleQuestionDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setQuestionDragActive(true);
    } else if (e.type === "dragleave") {
      setQuestionDragActive(false);
    }
  };

  const handleQuestionDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setQuestionDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      handleQuestionFilesChange([...questionFiles, ...droppedFiles]);
    }
  };

  const handleQuestionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFiles = Array.from(e.target.files);
      handleQuestionFilesChange([...questionFiles, ...selectedFiles]);
    }
  };

  const removeQuestionFile = (index: number) => {
    const newFiles = [...questionFiles];
    newFiles.splice(index, 1);
    handleQuestionFilesChange(newFiles);
  };

  // ============================================================
  // Answer Images Dropzone
  // ============================================================
  const handleAnswerDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setAnswerDragActive(true);
    } else if (e.type === "dragleave") {
      setAnswerDragActive(false);
    }
  };

  const handleAnswerDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setAnswerDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      handleAnswerFilesChange([...answerFiles, ...droppedFiles]);
    }
  };

  const handleAnswerChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFiles = Array.from(e.target.files);
      handleAnswerFilesChange([...answerFiles, ...selectedFiles]);
    }
  };

  const removeAnswerFile = (index: number) => {
    const newFiles = [...answerFiles];
    newFiles.splice(index, 1);
    handleAnswerFilesChange(newFiles);
  };

  // ============================================================
  // Combined Mode (Single) Images Dropzone
  // ============================================================
  const handleCombinedDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setCombinedDragActive(true);
    } else if (e.type === "dragleave") {
      setCombinedDragActive(false);
    }
  };

  const handleCombinedDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setCombinedDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      handleCombinedFilesChange([...combinedFiles, ...droppedFiles]);
    }
  };

  const handleCombinedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFiles = Array.from(e.target.files);
      handleCombinedFilesChange([...combinedFiles, ...selectedFiles]);
    }
  };

  const removeCombinedFile = (index: number) => {
    const newFiles = [...combinedFiles];
    newFiles.splice(index, 1);
    handleCombinedFilesChange(newFiles);
  };

  const triggerUpload = () => {
    if (examMode === 'separated') {
      if (questionFiles.length > 0 && answerFiles.length > 0) {
        uploadFiles(questionFiles, answerFiles, 'separated', [], selectedExamType);
      }
    } else {
      if (combinedFiles.length > 0) {
        uploadFiles([], [], 'combined', combinedFiles, selectedExamType);
      }
    }
  };


  // 1. Loading State - 后端正在处理中
  if (isUploading && statusResponse?.status === 'processing') {
    return (
      <div className="flex flex-col items-center justify-center p-16 bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 rounded-2xl border-2 border-dashed border-indigo-200">
        {/* 动画加载指示器 */}
        <div className="relative w-20 h-20 mb-8">
          <div className="absolute inset-0 border-4 border-indigo-200 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-transparent border-t-indigo-600 border-r-indigo-600 rounded-full animate-spin"></div>
        </div>
        
        <h3 className="text-2xl font-black text-indigo-900 mb-2 text-center">
          AI 正在深度阅卷中...
        </h3>
        <p className="text-indigo-600 text-center mb-2">
          多模态大模型正在逐题拆解您的解答
        </p>
        <p className="text-sm text-indigo-500 text-center">
          预计需要 15-30 秒，请勿关闭页面
        </p>
        
        {/* 进度条（装饰性） */}
        <div className="w-full max-w-xs mt-6 h-1 bg-indigo-200 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-indigo-600 to-purple-600 rounded-full animate-pulse" style={{ width: '60%' }}></div>
        </div>
      </div>
    );
  }

  // 2. Completed State - 若异常未跳转时显示此提示
  if (statusResponse?.status === 'completed' && !isUploading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-emerald-50 rounded-2xl border-2 border-emerald-200">
        <div className="text-5xl mb-4">✅</div>
        <h3 className="text-xl font-bold text-emerald-900 mb-2">批阅完成！</h3>
        <p className="text-emerald-700 mb-4">正在为您跳转到详情页...</p>
        <div className="w-full max-w-xs h-1 bg-emerald-200 rounded-full overflow-hidden">
          <div className="h-full bg-emerald-500 rounded-full animate-pulse" style={{ width: '100%' }}></div>
        </div>
      </div>
    );
  }

  // 3. Failed State - 批阅失败时显示错误
  if (statusResponse?.status === 'failed' && !isUploading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-red-50 rounded-2xl border-2 border-red-200">
        <div className="text-5xl mb-4">❌</div>
        <h3 className="text-xl font-bold text-red-900 mb-2">批阅失败</h3>
        <p className="text-red-700 mb-4 text-center">
          {statusResponse.overall_evaluation || '处理过程中出现问题，请重新上传'}
        </p>
        <button 
          onClick={reset}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg"
        >
          返回重试
        </button>
      </div>
    );
  }

  // 4. Setup / Upload State - Mode Selector + Conditional Upload
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6">
      <h2 className="text-xl font-bold text-slate-800 mb-2">整卷智能批阅</h2>
      <p className="text-sm text-slate-500 mb-6">
        选择作答模式，上传相应的试卷照片。批阅完成后，将自动跳转至试卷档案详情页。
      </p>

      {error && (
        <div className="mb-6 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-200">
          发生错误: {error}
        </div>
      )}

      {/* ============================================================ */}
      {/* Exam Type Selector */}
      {/* ============================================================ */}
      <div className="mb-8 p-4 bg-amber-50 rounded-xl border border-amber-200">
        <p className="text-sm font-semibold text-slate-700 mb-3">选择本次试卷类型：<span className="text-red-600">*</span></p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { value: 'custom' as const, label: '📝 日常练习', desc: '常规作业' },
            { value: 'diagnostic' as const, label: '✨ 摸底定级', desc: '摸底测试' },
            { value: 'midterm' as const, label: '🏆 期中评测', desc: '期中考试' },
            { value: 'final' as const, label: '👑 期末评测', desc: '期末考试' },
          ].map((type) => (
            <label key={type.value} className="flex items-start cursor-pointer">
              <input 
                type="radio" 
                name="exam_type" 
                value={type.value}
                checked={selectedExamType === type.value}
                onChange={(e) => setSelectedExamType(type.value)}
                className="mt-1 w-4 h-4 text-indigo-600 cursor-pointer"
              />
              <div className="ml-2">
                <div className="text-sm font-medium text-slate-700">{type.label}</div>
                <div className="text-xs text-slate-500">{type.desc}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* ============================================================ */}
      {/* Mode Selector - Radio Group */}
      {/* ============================================================ */}
      <div className="mb-8 p-4 bg-slate-50 rounded-xl border border-slate-200">
        <p className="text-sm font-semibold text-slate-700 mb-3">选择作答模式：</p>
        <div className="flex gap-6">
          <label className="flex items-center cursor-pointer">
            <input 
              type="radio" 
              name="exam_mode" 
              value="separated" 
              checked={examMode === 'separated'}
              onChange={(e) => {
                setExamMode('separated');
                reset();
              }}
              className="w-4 h-4 text-blue-600 cursor-pointer"
            />
            <span className="ml-2 text-sm text-slate-700 font-medium">分离作答 (原卷 + 答题纸)</span>
          </label>
          <label className="flex items-center cursor-pointer">
            <input 
              type="radio" 
              name="exam_mode" 
              value="combined" 
              checked={examMode === 'combined'}
              onChange={(e) => {
                setExamMode('combined');
                reset();
              }}
              className="w-4 h-4 text-purple-600 cursor-pointer"
            />
            <span className="ml-2 text-sm text-slate-700 font-medium">卷面作答 (题目与解答合一)</span>
          </label>
        </div>
      </div>

      {/* ============================================================ */}
      {/* Separated Mode Upload */}
      {/* ============================================================ */}
      {examMode === 'separated' && (
        <>
          <div className="mb-8">
            <div className="mb-3">
              <h3 className="text-base font-bold text-slate-800 mb-1">【上传试卷原题】📖</h3>
              <p className="text-xs text-slate-500">上传包含题目文本的照片（AI 将从第二区域的答题卡中提取答案）</p>
            </div>

            <form onDragEnter={handleQuestionDrag} onSubmit={(e) => e.preventDefault()} className="mb-4">
              <input ref={questionFileInputRef} type="file" multiple className="hidden" onChange={handleQuestionChange} accept="image/*" />
              <div 
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer
                  ${questionDragActive ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"}`}
                onDragEnter={handleQuestionDrag} onDragLeave={handleQuestionDrag} onDragOver={handleQuestionDrag} onDrop={handleQuestionDrop}
                onClick={() => questionFileInputRef.current?.click()}
              >
                <div className="text-3xl mb-2">📷</div>
                <p className="text-slate-600 font-medium text-sm">点击或拖拽题目照片至此</p>
                <p className="text-xs text-slate-400 mt-1">支持多张图片</p>
              </div>
            </form>

            {questionFiles.length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2">已选择 {questionFiles.length} 张题目照片</h4>
                <div className="flex flex-col gap-2 max-h-32 overflow-y-auto">
                  {questionFiles.map((file, idx) => (
                    <div key={idx} className="flex justify-between items-center bg-blue-50 p-2 rounded-lg border border-blue-200 text-xs">
                      <span className="truncate max-w-[180px] text-slate-700">{file.name}</span>
                      <button onClick={() => removeQuestionFile(idx)} className="text-red-500 hover:text-red-700 font-medium px-2">移除</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mb-8">
            <div className="mb-3">
              <h3 className="text-base font-bold text-slate-800 mb-1">【上传答题卡/答题纸】✍️</h3>
              <p className="text-xs text-slate-500">上传学生手写答题的照片（AI 将仅基于此处内容进行评分）</p>
            </div>

            <form onDragEnter={handleAnswerDrag} onSubmit={(e) => e.preventDefault()} className="mb-4">
              <input ref={answerFileInputRef} type="file" multiple className="hidden" onChange={handleAnswerChange} accept="image/*" />
              <div 
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer
                  ${answerDragActive ? "border-emerald-500 bg-emerald-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"}`}
                onDragEnter={handleAnswerDrag} onDragLeave={handleAnswerDrag} onDragOver={handleAnswerDrag} onDrop={handleAnswerDrop}
                onClick={() => answerFileInputRef.current?.click()}
              >
                <div className="text-3xl mb-2">📝</div>
                <p className="text-slate-600 font-medium text-sm">点击或拖拽答题卡照片至此</p>
                <p className="text-xs text-slate-400 mt-1">支持多张图片</p>
              </div>
            </form>

            {answerFiles.length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2">已选择 {answerFiles.length} 张答题卡照片</h4>
                <div className="flex flex-col gap-2 max-h-32 overflow-y-auto">
                  {answerFiles.map((file, idx) => (
                    <div key={idx} className="flex justify-between items-center bg-emerald-50 p-2 rounded-lg border border-emerald-200 text-xs">
                      <span className="truncate max-w-[180px] text-slate-700">{file.name}</span>
                      <button onClick={() => removeAnswerFile(idx)} className="text-red-500 hover:text-red-700 font-medium px-2">移除</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button 
              onClick={triggerUpload}
              disabled={questionFiles.length === 0 || answerFiles.length === 0 || isUploading}
              className="flex-1 py-3.5 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded-xl shadow-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? '处理中...' : '开始智能批阅'}
            </button>
          </div>

          {(questionFiles.length === 0 || answerFiles.length === 0) && !isUploading && (
            <p className="text-xs text-slate-400 mt-3 text-center">
              💡 提示：请同时上传试卷原题和答题卡才能开始批阅
            </p>
          )}
        </>
      )}

      {/* ============================================================ */}
      {/* Combined Mode Upload */}
      {/* ============================================================ */}
      {examMode === 'combined' && (
        <>
          <div className="mb-8">
            <div className="mb-3">
              <h3 className="text-base font-bold text-slate-800 mb-1">【上传作答后的试卷】🗂️</h3>
              <p className="text-xs text-slate-500">上传学生直接在试卷上作答后的照片（题目与解答在同一张纸上）</p>
            </div>

            <form onDragEnter={handleCombinedDrag} onSubmit={(e) => e.preventDefault()} className="mb-4">
              <input ref={combinedFileInputRef} type="file" multiple className="hidden" onChange={handleCombinedChange} accept="image/*" />
              <div 
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer
                  ${combinedDragActive ? "border-purple-500 bg-purple-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"}`}
                onDragEnter={handleCombinedDrag} onDragLeave={handleCombinedDrag} onDragOver={handleCombinedDrag} onDrop={handleCombinedDrop}
                onClick={() => combinedFileInputRef.current?.click()}
              >
                <div className="text-4xl mb-2">📸</div>
                <p className="text-slate-600 font-medium text-sm">点击或拖拽试卷照片至此</p>
                <p className="text-xs text-slate-400 mt-1">支持多张图片。AI 将自动分离题目与解答部分</p>
              </div>
            </form>

            {combinedFiles.length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2">已选择 {combinedFiles.length} 张试卷照片</h4>
                <div className="flex flex-col gap-2 max-h-32 overflow-y-auto">
                  {combinedFiles.map((file, idx) => (
                    <div key={idx} className="flex justify-between items-center bg-purple-50 p-2 rounded-lg border border-purple-200 text-xs">
                      <span className="truncate max-w-[180px] text-slate-700">{file.name}</span>
                      <button onClick={() => removeCombinedFile(idx)} className="text-red-500 hover:text-red-700 font-medium px-2">移除</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button 
              onClick={triggerUpload}
              disabled={combinedFiles.length === 0 || isUploading}
              className="flex-1 py-3.5 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded-xl shadow-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? '处理中...' : '开始智能批阅'}
            </button>
          </div>

          {combinedFiles.length === 0 && !isUploading && (
            <p className="text-xs text-slate-400 mt-3 text-center">
              💡 提示：请上传作答后的试卷照片才能开始批阅
            </p>
          )}
        </>
      )}
    </div>
  );
}
