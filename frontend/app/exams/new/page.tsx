'use client';

import React, { useRef, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useExamPolling } from '@/hooks/useExamPolling';

export default function FullExamUploadPage() {
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

  // 自动跳转到详情页
  useEffect(() => {
    if (statusResponse?.status === 'completed' && statusResponse?.exam_id) {
      const timer = setTimeout(() => {
        reset();
        router.push(`/exams/${statusResponse.exam_id}`);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [statusResponse?.status, statusResponse?.exam_id, reset, router]);

  // ============================================================
  // Question Drag Handlers
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
  // Answer Drag Handlers
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
  // Combined Drag Handlers
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

  // ============================================================
  // LOADING STATE
  // ============================================================
  if (isUploading && statusResponse?.status === 'processing') {
    return (
      <main className="p-8 max-w-5xl mx-auto">
        <div className="flex flex-col items-center justify-center p-16 bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 rounded-2xl border-2 border-dashed border-indigo-200">
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
          
          <div className="w-full max-w-xs mt-6 h-1 bg-indigo-200 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-indigo-600 to-purple-600 rounded-full animate-pulse" style={{ width: '60%' }}></div>
          </div>
        </div>
      </main>
    );
  }

  // ============================================================
  // COMPLETED STATE
  // ============================================================
  if (statusResponse?.status === 'completed' && !isUploading) {
    return (
      <main className="p-8 max-w-5xl mx-auto">
        <div className="flex flex-col items-center justify-center p-8 bg-emerald-50 rounded-2xl border-2 border-emerald-200">
          <div className="text-5xl mb-4">✅</div>
          <h3 className="text-xl font-bold text-emerald-900 mb-2">批阅完成！</h3>
          <p className="text-emerald-700 mb-4">正在为您跳转到详情页...</p>
          <div className="w-full max-w-xs h-1 bg-emerald-200 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full animate-pulse" style={{ width: '100%' }}></div>
          </div>
        </div>
      </main>
    );
  }

  // ============================================================
  // FAILED STATE
  // ============================================================
  if (statusResponse?.status === 'failed' && !isUploading) {
    return (
      <main className="p-8 max-w-5xl mx-auto">
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
      </main>
    );
  }

  // ============================================================
  // MAIN UPLOAD PAGE
  // ============================================================
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8 pb-16">
      <div className="max-w-5xl mx-auto">
        {/* Back Navigation */}
        <div className="mb-6">
          <Link href="/" className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800 transition-colors">
            <span className="text-lg">←</span>
            <span className="text-sm font-medium">返回控制台</span>
          </Link>
        </div>

        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-black text-slate-900 mb-3">整卷智能批阅</h1>
          <p className="text-lg text-slate-600">
            上传完整的试卷和答题卡，AI 将自动为每一题进行深度评分和分析
          </p>
        </div>

        {/* Main Card Container */}
        <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden">
          
          {/* Step 1: Settings Bar */}
          <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-slate-100 p-6">
            {/* Flex container for both settings */}
            <div className="flex flex-col lg:flex-row gap-8 lg:items-start">
              
              {/* Settings A: Exam Type - Radio Cards */}
              <div className="flex-1">
                <label className="text-sm font-semibold text-slate-700 block mb-3 flex items-center gap-2 h-6">
                  <span className="text-lg">📋</span>
                  <span>试卷类型 <span className="text-red-500">*</span></span>
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { value: 'custom' as const, emoji: '📝', label: '日常练习', color: 'slate' },
                    { value: 'diagnostic' as const, emoji: '✨', label: '摸底定级', color: 'purple' },
                    { value: 'midterm' as const, emoji: '🏆', label: '期中评测', color: 'indigo' },
                    { value: 'final' as const, emoji: '👑', label: '期末评测', color: 'rose' },
                  ].map((type) => {
                    const isSelected = selectedExamType === type.value;
                    const borderColor = {
                      slate: isSelected ? 'border-slate-400 border-2 hover:border-slate-400' : 'border-slate-200 hover:border-slate-300',
                      purple: isSelected ? 'border-purple-400 border-2 hover:border-purple-400' : 'border-slate-200 hover:border-purple-300',
                      indigo: isSelected ? 'border-indigo-400 border-2 hover:border-indigo-400' : 'border-slate-200 hover:border-indigo-300',
                      rose: isSelected ? 'border-rose-400 border-2 hover:border-rose-400' : 'border-slate-200 hover:border-rose-300',
                    }[type.color];
                    const bgColor = {
                      slate: isSelected ? 'bg-slate-50' : 'bg-white',
                      purple: isSelected ? 'bg-purple-50' : 'bg-white',
                      indigo: isSelected ? 'bg-indigo-50' : 'bg-white',
                      rose: isSelected ? 'bg-rose-50' : 'bg-white',
                    }[type.color];
                    const shadowClass = isSelected ? 'shadow-md' : 'shadow-sm hover:shadow-md';
                    return (
                      <button
                        key={type.value}
                        onClick={() => setSelectedExamType(type.value)}
                        className={`relative p-4 rounded-lg border transition-all cursor-pointer min-h-[110px] flex flex-col items-center justify-center ${borderColor} ${bgColor} ${shadowClass}`}
                      >
                        <div className="text-3xl mb-2">{type.emoji}</div>
                        <div className="text-xs font-medium text-slate-700 text-center">{type.label}</div>
                        {isSelected && (
                          <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-green-500 flex items-center justify-center text-white text-xs font-bold">✓</div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Settings B: Exam Mode - Card Style (Matching Height) */}
              <div className="flex-1">
                <label className="text-sm font-semibold text-slate-700 block mb-3 flex items-center gap-2 h-6">
                  <span className="text-lg">📄</span>
                  <span>作答模式 <span className="text-red-500">*</span></span>
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: 'separated' as const, emoji: '📄📄', label: '分离作答', desc: '试卷+答题卡分开' },
                    { value: 'combined' as const, emoji: '📝✏️', label: '卷面作答', desc: '直接在卷面写答案' },
                  ].map((mode) => {
                    const isSelected = examMode === mode.value;
                    return (
                      <button
                        key={mode.value}
                        onClick={() => {
                          setExamMode(mode.value);
                          reset();
                        }}
                        className={`relative p-4 rounded-lg border transition-all cursor-pointer min-h-[110px] flex flex-col items-center justify-center ${
                          isSelected
                            ? 'border-indigo-400 border-2 bg-indigo-50 shadow-md hover:shadow-lg'
                            : 'border-slate-200 bg-white shadow-sm hover:shadow-md hover:border-indigo-300'
                        }`}
                      >
                        <div className="text-2xl mb-2">{mode.emoji}</div>
                        <div className="text-xs font-medium text-slate-800 text-center">{mode.label}</div>
                        <div className="text-xs text-slate-500 text-center mt-1">{mode.desc}</div>
                        {isSelected && (
                          <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">✓</div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Dynamic AI Model Info Alert */}
            <div className="mt-6">
              {selectedExamType === 'custom' && (
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 flex items-start gap-3">
                  <span className="text-lg">📚</span>
                  <div className="text-sm">
                    <div className="font-semibold text-slate-800">标准教学模型</div>
                    <div className="text-slate-700 mt-1">
                      日常练习将使用标准教学模型进行评分，结果按 <span className="font-bold">1倍权重</span> 计入知识图谱。
                    </div>
                  </div>
                </div>
              )}
              {selectedExamType === 'diagnostic' && (
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-200 flex items-start gap-3">
                  <span className="text-lg">✨</span>
                  <div className="text-sm">
                    <div className="font-semibold text-purple-900">高级诊断模型 (Pro)</div>
                    <div className="text-purple-800 mt-1">
                      摸底评测将自动调用 Gemini 3 Pro 引擎，深度识别知识漏洞，结果按 <span className="font-bold">2倍权重</span> 计入知识图谱。
                    </div>
                  </div>
                </div>
              )}
              {selectedExamType === 'midterm' && (
                <div className="p-4 bg-amber-50 rounded-lg border border-amber-200 flex items-start gap-3">
                  <span className="text-lg">🏆</span>
                  <div className="text-sm">
                    <div className="font-semibold text-amber-900">高级诊断模型 (Pro)</div>
                    <div className="text-amber-800 mt-1">
                      期中评测将自动调用 Gemini 3 Pro 引擎，进行全面深度分析，结果按 <span className="font-bold">3倍权重</span> 计入知识图谱。
                    </div>
                  </div>
                </div>
              )}
              {selectedExamType === 'final' && (
                <div className="p-4 bg-rose-50 rounded-lg border border-rose-200 flex items-start gap-3">
                  <span className="text-lg">👑</span>
                  <div className="text-sm">
                    <div className="font-semibold text-rose-900">高级诊断模型 (Pro)</div>
                    <div className="text-rose-800 mt-1">
                      期末评测将自动调用 Gemini 3 Pro 引擎，进行全面深度分析，结果按 <span className="font-bold">3倍权重</span> 计入知识图谱。
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Step 2: Upload Zones */}
          <div className="p-8 lg:p-12">
            {examMode === 'separated' ? (
              // Separated Mode - Two Column Grid
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                
                {/* Question Images Zone */}
                <div>
                  <div className="mb-4">
                    <h3 className="text-lg font-bold text-slate-800 mb-1 flex items-center gap-2">
                      <span>📖</span>
                      <span>上传试卷原题</span>
                    </h3>
                    <p className="text-xs text-slate-500">
                      上传包含题目文本的照片
                    </p>
                  </div>

                  <form onDragEnter={handleQuestionDrag} onSubmit={(e) => e.preventDefault()} className="mb-4">
                    <input 
                      ref={questionFileInputRef} 
                      type="file" 
                      multiple 
                      className="hidden" 
                      onChange={handleQuestionChange} 
                      accept="image/*" 
                    />
                    <div 
                      className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer min-h-[320px] flex flex-col items-center justify-center
                        ${questionDragActive ? "border-blue-500 bg-blue-50 shadow-lg" : "border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"}`}
                      onDragEnter={handleQuestionDrag}
                      onDragLeave={handleQuestionDrag}
                      onDragOver={handleQuestionDrag}
                      onDrop={handleQuestionDrop}
                      onClick={() => questionFileInputRef.current?.click()}
                    >
                      <div className="text-4xl mb-3">📷</div>
                      <p className="text-slate-700 font-semibold text-base">点击或拖拽题目照片</p>
                      <p className="text-xs text-slate-500 mt-1">支持 JPG, PNG, WebP 格式</p>
                    </div>
                  </form>

                  {questionFiles.length > 0 && (
                    <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                      <h4 className="text-xs font-bold text-blue-800 mb-2">已选择 {questionFiles.length} 张题目照片</h4>
                      <div className="flex flex-col gap-1 max-h-24 overflow-y-auto">
                        {questionFiles.map((file, idx) => (
                          <div key={idx} className="flex justify-between items-center bg-white p-2 rounded text-xs border border-blue-100">
                            <span className="truncate text-slate-700">{file.name}</span>
                            <button onClick={() => removeQuestionFile(idx)} className="text-red-500 hover:text-red-700 font-bold px-2">✕</button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Answer Images Zone */}
                <div>
                  <div className="mb-4">
                    <h3 className="text-lg font-bold text-slate-800 mb-1 flex items-center gap-2">
                      <span>✍️</span>
                      <span>上传答题卡/答题纸</span>
                    </h3>
                    <p className="text-xs text-slate-500">
                      上传学生手写答题的照片
                    </p>
                  </div>

                  <form onDragEnter={handleAnswerDrag} onSubmit={(e) => e.preventDefault()} className="mb-4">
                    <input 
                      ref={answerFileInputRef} 
                      type="file" 
                      multiple 
                      className="hidden" 
                      onChange={handleAnswerChange} 
                      accept="image/*" 
                    />
                    <div 
                      className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer min-h-[320px] flex flex-col items-center justify-center
                        ${answerDragActive ? "border-emerald-500 bg-emerald-50 shadow-lg" : "border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"}`}
                      onDragEnter={handleAnswerDrag}
                      onDragLeave={handleAnswerDrag}
                      onDragOver={handleAnswerDrag}
                      onDrop={handleAnswerDrop}
                      onClick={() => answerFileInputRef.current?.click()}
                    >
                      <div className="text-4xl mb-3">📝</div>
                      <p className="text-slate-700 font-semibold text-base">点击或拖拽答题卡照片</p>
                      <p className="text-xs text-slate-500 mt-1">支持 JPG, PNG, WebP 格式</p>
                    </div>
                  </form>

                  {answerFiles.length > 0 && (
                    <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                      <h4 className="text-xs font-bold text-emerald-800 mb-2">已选择 {answerFiles.length} 张答题卡照片</h4>
                      <div className="flex flex-col gap-1 max-h-24 overflow-y-auto">
                        {answerFiles.map((file, idx) => (
                          <div key={idx} className="flex justify-between items-center bg-white p-2 rounded text-xs border border-emerald-100">
                            <span className="truncate text-slate-700">{file.name}</span>
                            <button onClick={() => removeAnswerFile(idx)} className="text-red-500 hover:text-red-700 font-bold px-2">✕</button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              // Combined Mode - Full Width
              <div className="mb-8">
                <div className="mb-4">
                  <h3 className="text-lg font-bold text-slate-800 mb-1 flex items-center gap-2">
                    <span>🗂️</span>
                    <span>上传作答后的试卷</span>
                  </h3>
                  <p className="text-xs text-slate-500">
                    上传学生直接在试卷上作答后的照片（题目与解答在同一张纸上）
                  </p>
                </div>

                <form onDragEnter={handleCombinedDrag} onSubmit={(e) => e.preventDefault()} className="mb-4">
                  <input 
                    ref={combinedFileInputRef} 
                    type="file" 
                    multiple 
                    className="hidden" 
                    onChange={handleCombinedChange} 
                    accept="image/*" 
                  />
                  <div 
                    className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer min-h-[400px] flex flex-col items-center justify-center
                      ${combinedDragActive ? "border-purple-500 bg-purple-50 shadow-lg" : "border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400"}`}
                    onDragEnter={handleCombinedDrag}
                    onDragLeave={handleCombinedDrag}
                    onDragOver={handleCombinedDrag}
                    onDrop={handleCombinedDrop}
                    onClick={() => combinedFileInputRef.current?.click()}
                  >
                    <div className="text-5xl mb-4">📸</div>
                    <p className="text-slate-700 font-bold text-lg">点击或拖拽试卷照片至此</p>
                    <p className="text-slate-500 text-sm mt-2">支持多张图片。AI 将自动分离题目与解答部分</p>
                    <p className="text-xs text-slate-400 mt-3">JPG, PNG, WebP 格式</p>
                  </div>
                </form>

                {combinedFiles.length > 0 && (
                  <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                    <h4 className="text-xs font-bold text-purple-800 mb-2">已选择 {combinedFiles.length} 张试卷照片</h4>
                    <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
                      {combinedFiles.map((file, idx) => (
                        <div key={idx} className="flex justify-between items-center bg-white px-2 py-1 rounded text-xs border border-purple-100">
                          <span className="truncate text-slate-700 max-w-[150px]">{file.name}</span>
                          <button onClick={() => removeCombinedFile(idx)} className="text-red-500 hover:text-red-700 font-bold px-2">✕</button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
                <div className="font-semibold">上传失败</div>
                <div>{error}</div>
              </div>
            )}
          </div>

          {/* Step 3: Submit Button */}
          <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border-t border-slate-100 p-8 flex flex-col items-center gap-4">
            <button 
              onClick={triggerUpload}
              disabled={
                (examMode === 'separated' && (questionFiles.length === 0 || answerFiles.length === 0)) ||
                (examMode === 'combined' && combinedFiles.length === 0) ||
                isUploading
              }
              className="px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold rounded-xl shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed min-w-[300px]"
            >
              {isUploading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  处理中...
                </span>
              ) : (
                <span>🚀 确认提交并开始 AI 批阅</span>
              )}
            </button>

            {examMode === 'separated' && (questionFiles.length === 0 || answerFiles.length === 0) && !isUploading && (
              <p className="text-xs text-slate-500 text-center">
                💡 请上传试卷原题和答题卡才能开始批阅
              </p>
            )}

            {examMode === 'combined' && combinedFiles.length === 0 && !isUploading && (
              <p className="text-xs text-slate-500 text-center">
                💡 请上传作答后的试卷照片才能开始批阅
              </p>
            )}
          </div>
        </div>

        {/* Footer Tips */}
        <div className="mt-8 p-4 bg-yellow-50 rounded-lg border border-yellow-200 text-center">
          <p className="text-xs text-yellow-700">
            <span className="font-semibold">💡 提示：</span> 请确保照片清晰、光线充足，以便 AI 准确识别题目文字和学生作答
          </p>
        </div>
      </div>
    </main>
  );
}
