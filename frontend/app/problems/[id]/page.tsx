'use client';

import { useEffect, useState, use } from 'react';
import { LatexRenderer } from '@/components/LatexRenderer';
import { Loader2, ArrowLeft, ZoomIn, Eye, ChevronDown, ChevronUp, Clock, Trash2, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { fetchWithAuth } from '../../../utils/api';
import Image from 'next/image';

export default function ProblemPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const [problem, setProblem] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const [showHint, setShowHint] = useState(false);
    const [showSolution, setShowSolution] = useState(false);
    const [masteryLevel, setMasteryLevel] = useState<number | null>(null);
    const [showErrorLog, setShowErrorLog] = useState(false);

    // Practice Mode State

    const [practiceProblems, setPracticeProblems] = useState<any[]>([]);
    const [generatingPractice, setGeneratingPractice] = useState(false);
    const [isReanalyzing, setIsReanalyzing] = useState(false);
    const [showPracticeSolutions, setShowPracticeSolutions] = useState<{ [key: string]: boolean }>({});

    // Practice Solution Grading State
    const [practiceFiles, setPracticeFiles] = useState<{ [key: number]: File | null }>({});
    const [isAnalyzingPractice, setIsAnalyzingPractice] = useState<{ [key: number]: boolean }>({});
    const [practiceAnalysisResults, setPracticeAnalysisResults] = useState<{ [key: number]: any }>({});

    // Practice History State
    const [practiceTab, setPracticeTab] = useState<'generate' | 'history'>('generate');
    const [historySessions, setHistorySessions] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [expandedSession, setExpandedSession] = useState<number | null>(null);
    const [sessionProblems, setSessionProblems] = useState<{ [sessionId: number]: any[] }>({});

    // Solution Analysis State
    const [solutionFile, setSolutionFile] = useState<File | null>(null);
    const [isAnalyzingSolution, setIsAnalyzingSolution] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<any>(null);
    const [currentAttemptModel, setCurrentAttemptModel] = useState<string | null>(null);

    // Zoom Modal State
    const [isZoomModalOpen, setIsZoomModalOpen] = useState(false);
    const [zoomImageSrc, setZoomImageSrc] = useState<string>("");

    useEffect(() => {
        async function fetchProblem() {
            try {
                const res = await fetchWithAuth(`/api/problems/${id}`);
                if (res.ok) {
                    const data = await res.json();
                    setProblem(data);
                    if (data.current_mastery_level) {
                        setMasteryLevel(data.current_mastery_level);
                    }
                    // Auto-load latest attempt results if available
                    if (data.solution_attempts && data.solution_attempts.length > 0) {
                        const latest = data.solution_attempts[data.solution_attempts.length - 1];
                        setAnalysisResult(latest.feedback_json);
                        setCurrentAttemptModel(latest.ai_model_used);
                    }
                }
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        }

        async function fetchPracticeProblems() {
            try {
                const res = await fetchWithAuth(`/api/problems/${id}/similar`);
                if (res.ok) {
                    const data = await res.json();
                    setPracticeProblems(data);
                }
            } catch (error) {
                console.error(error);
            }
        }

        async function fetchPracticeHistory() {
            setLoadingHistory(true);
            try {
                const res = await fetchWithAuth(`/api/practices/history?limit=50`);
                if (res.ok) {
                    const all = await res.json();
                    // Filter to only sessions for this problem
                    const filtered = all.filter((s: any) => s.source_problem_id === parseInt(id));
                    setHistorySessions(filtered);
                }
            } catch (error) {
                console.error(error);
            } finally {
                setLoadingHistory(false);
            }
        }

        fetchProblem();
        fetchPracticeProblems();
        fetchPracticeHistory();
    }, [id]);

    const handleDeleteAttempt = async (attemptId: number) => {
        if (!confirm('Are you sure you want to delete this attempt?')) return;

        try {
            const res = await fetchWithAuth(`/api/solution-attempts/${attemptId}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                // Remove attempt from local state
                setProblem((prev: any) => ({
                    ...prev,
                    solution_attempts: prev.solution_attempts.filter((a: any) => a.id !== attemptId)
                }));
            }
        } catch (error) {
            console.error('Failed to delete attempt:', error);
        }
    };

    const handleReanalyzeAttempt = async (attemptId: number) => {
        setIsAnalyzingSolution(true);
        try {
            const res = await fetchWithAuth(`/api/solution-attempts/${attemptId}/reanalyze`, {
                method: 'POST',
            });
            if (res.ok) {
                const data = await res.json();
                setAnalysisResult(data.feedback_json);
                setCurrentAttemptModel(data.ai_model_used);
                // Update local problem state
                setProblem((prev: any) => ({
                    ...prev,
                    solution_attempts: prev.solution_attempts.map((a: any) => a.id === attemptId ? data : a)
                }));
                // Scroll to result
                setTimeout(() => {
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }, 100);
            } else {
                const errData = await res.json().catch(() => ({}));
                alert("Re-analysis failed: " + (errData.detail?.message || errData.detail || "Server error"));
            }
        } catch (error) {
            console.error('Failed to re-analyze attempt:', error);
            alert("Error connecting to server.");
        } finally {
            setIsAnalyzingSolution(false);
        }
    };

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
            </div>
        );
    }

    if (!problem) {
        return <div className="p-8 text-center">Problem not found</div>;
    }

    return (
        <div className="min-h-screen bg-gray-50 p-4 md:p-8">
            <div className="max-w-[1600px] mx-auto space-y-6">
                <Link href="/" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-900 transition-colors">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Upload
                </Link>

                {/* Header Card */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col md:flex-row justify-between items-center gap-4">
                    <div className="flex items-center gap-3 w-full">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-200 shrink-0">
                            #{problem.id}
                        </div>
                        <div className="flex-grow">
                            <h1 className="text-xl font-bold text-gray-900 leading-tight">Problem Analysis</h1>
                            {problem.ai_model && (
                                <span className="text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100 rounded-full px-2 py-0.5 inline-flex items-center gap-1 mt-0.5">
                                    🤖 {problem.ai_model}
                                </span>
                            )}
                        </div>
                        <button
                            onClick={handleReanalyze}
                            disabled={isReanalyzing}
                            className="inline-flex items-center px-4 py-2 bg-gray-50 text-gray-700 rounded-xl hover:bg-gray-100 disabled:opacity-50 transition-all text-sm font-medium border border-gray-200 shadow-sm active:scale-95 whitespace-nowrap"
                        >
                            {isReanalyzing ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Re-analyzing...
                                </>
                            ) : (
                                <>✨ 重新分析 (Re-analyze)</>
                            )}
                        </button>
                    </div>
                </div>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">

                    {/* Left Column: Problem Context (col-span-12 md:col-span-5) */}
                    <div className="md:col-span-12 lg:col-span-5 space-y-6 lg:sticky lg:top-8">
                        {/* Original Scan Card */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                            <div className="p-4 border-b border-gray-50 flex items-center gap-2">
                                <Eye className="w-4 h-4 text-indigo-500" />
                                <h2 className="font-bold text-gray-700 text-sm">Original Scan</h2>
                            </div>
                            <div className="aspect-[3/4] bg-gray-50 relative group">
                                {problem.image_path ? (
                                    <img
                                        src={`${process.env.NEXT_PUBLIC_API_URL || ''}/static/${problem.image_path.split('/').pop()}`}
                                        alt="Problem Scan"
                                        className="w-full h-full object-contain cursor-zoom-in"
                                        onClick={() => {
                                            setZoomImageSrc(`${process.env.NEXT_PUBLIC_API_URL || ''}/static/${problem.image_path.split('/').pop()}`);
                                            setIsZoomModalOpen(true);
                                        }}
                                    />
                                ) : (
                                    <div className="flex items-center justify-center h-full text-gray-400">No Image</div>
                                )}
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors pointer-events-none flex items-center justify-center opacity-0 group-hover:opacity-100">
                                    <ZoomIn className="text-white w-8 h-8 drop-shadow-md" />
                                </div>
                            </div>
                        </div>

                        {/* OCR Recognition Card */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                            <div className="p-4 border-b border-gray-50 flex items-center gap-2">
                                <span className="text-indigo-500 font-bold">📝</span>
                                <h2 className="font-bold text-gray-700 text-sm">识别题干 (OCR Result)</h2>
                            </div>
                            <div className="p-5 bg-gray-50/50">
                                <div className="p-4 bg-white rounded-xl border border-gray-100 text-lg shadow-inner overflow-x-auto min-h-[100px] flex items-center">
                                    <LatexRenderer content={problem.latex_content || "No LaTeX detected"} block />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Analysis & Actions (col-span-12 md:col-span-7) */}
                    <div className="md:col-span-12 lg:col-span-7 space-y-6">

                        {/* Analysis Card */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                            <div className="p-6 border-b border-gray-50 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="text-indigo-500 font-bold">📊</span>
                                    <h2 className="font-bold text-gray-800">题目分析 (Analysis)</h2>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider mr-1">Difficulty</span>
                                    <div className="flex gap-1">
                                        {[1, 2, 3, 4, 5].map(v => (
                                            <div key={v} className={`w-1.5 h-4 rounded-full ${v <= (problem.difficulty || 0) ? 'bg-indigo-500 shadow-sm shadow-indigo-200' : 'bg-gray-100'}`} />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="p-6 space-y-8">
                                {/* Knowledge Points */}
                                {((problem.knowledge_points && problem.knowledge_points.length > 0) || (problem.ai_analysis?.knowledge_points && problem.ai_analysis.knowledge_points.length > 0)) && (
                                    <div className="flex flex-wrap gap-2">
                                        {(problem.knowledge_points || problem.ai_analysis?.knowledge_points || []).map((kp: string, i: number) => (
                                            <span key={i} className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-bold border border-indigo-100 shadow-sm">
                                                #{kp}
                                            </span>
                                        ))}
                                    </div>
                                )}

                                {/* Thinking Process Accordion */}
                                <div className="border border-gray-100 rounded-2xl overflow-hidden group transition-all hover:border-indigo-100 hover:shadow-md">
                                    <button
                                        onClick={() => setShowHint(!showHint)}
                                        className="w-full p-4 flex items-center justify-between bg-white hover:bg-indigo-50/30 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-yellow-100 flex items-center justify-center text-yellow-600">
                                                <span className="text-sm">💡</span>
                                            </div>
                                            <span className="font-bold text-gray-700 text-sm">解题思路 (Thinking Process)</span>
                                        </div>
                                        {showHint ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                                    </button>
                                    {showHint && (
                                        <div className="p-5 bg-yellow-50/30 border-t border-yellow-50 animate-in slide-in-from-top-2 duration-300">
                                            <div className="text-gray-800 leading-relaxed text-[15px]">
                                                <LatexRenderer content={problem.ai_analysis?.thinking_process || "No hint available"} block />
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Detailed Solution Accordion */}
                                <div className="border border-gray-100 rounded-2xl overflow-hidden group transition-all hover:border-indigo-100 hover:shadow-md">
                                    <button
                                        onClick={() => setShowSolution(!showSolution)}
                                        className="w-full p-4 flex items-center justify-between bg-white hover:bg-indigo-50/30 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
                                                <span className="text-sm">📝</span>
                                            </div>
                                            <span className="font-bold text-gray-700 text-sm">详细解答 (Detailed Solution)</span>
                                        </div>
                                        {showSolution ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                                    </button>
                                    {showSolution && (
                                        <div className="p-5 bg-blue-50/30 border-t border-blue-50 animate-in slide-in-from-top-2 duration-300">
                                            <div className="text-gray-800 leading-relaxed text-[15px]">
                                                <LatexRenderer content={problem.ai_analysis?.solution || "No solution available"} block />
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Error Log (if any) */}
                                {problem.ai_analysis && problem.ai_analysis.error && (
                                    <div className="bg-red-50 border border-red-100 p-4 rounded-xl">
                                        <div className="flex justify-between items-center mb-2">
                                            <h3 className="text-red-800 text-xs font-bold uppercase tracking-wider">⚠️ Analysis Error</h3>
                                            <button
                                                onClick={() => setShowErrorLog(!showErrorLog)}
                                                className="text-[10px] bg-red-100 text-red-700 px-2 py-1 rounded font-bold"
                                            >
                                                {showErrorLog ? 'HIDE LOG' : 'SHOW LOG'}
                                            </button>
                                        </div>
                                        {showErrorLog && (
                                            <pre className="mt-2 p-3 bg-red-900/5 text-red-800 text-[10px] font-mono whitespace-pre-wrap rounded-lg">
                                                {problem.ai_analysis.error}
                                            </pre>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* User Answer Zone Card */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                            <div className="p-6 border-b border-gray-50">
                                <div className="flex items-center gap-2">
                                    <span className="text-indigo-500 font-bold">📸</span>
                                    <h2 className="font-bold text-gray-800">上传作答 (Upload Your Work)</h2>
                                </div>
                            </div>

                            <div className="p-6 space-y-6">
                                <div className="flex flex-col md:flex-row gap-4">
                                    <label className="flex-grow group">
                                        <div className="relative flex items-center justify-center border-2 border-dashed border-gray-200 rounded-2xl p-4 transition-all group-hover:border-indigo-300 group-hover:bg-indigo-50/30 cursor-pointer">
                                            <div className="flex flex-col items-center">
                                                <span className="text-xs font-bold text-gray-500 group-hover:text-indigo-600">
                                                    {solutionFile ? solutionFile.name : "Choose a photo of your answer"}
                                                </span>
                                            </div>
                                            <input
                                                type="file"
                                                accept="image/*"
                                                onChange={(e) => setSolutionFile(e.target.files?.[0] || null)}
                                                className="absolute inset-0 opacity-0 cursor-pointer"
                                            />
                                        </div>
                                    </label>
                                    <button
                                        onClick={handleSolutionUpload}
                                        disabled={!solutionFile || isAnalyzingSolution}
                                        className="bg-indigo-600 text-white rounded-2xl px-8 py-4 font-bold text-sm shadow-lg shadow-indigo-100 hover:bg-indigo-700 disabled:opacity-50 transition-all active:scale-95 shrink-0"
                                    >
                                        {isAnalyzingSolution ? (
                                            <span className="flex items-center gap-2">
                                                <Loader2 className="w-4 h-4 animate-spin" /> Batch Processing...
                                            </span>
                                        ) : "Analyze My Answer"}
                                    </button>
                                </div>

                                {/* Past Attempts Thumbnail List */}
                                {problem.solution_attempts && problem.solution_attempts.length > 0 && (
                                    <div className="space-y-4 pt-4 border-t border-gray-50">
                                        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">My Recent Work</p>
                                        <div className="flex flex-wrap gap-4">
                                            {problem.solution_attempts.slice(-3).reverse().map((attempt: any, idx: number) => (
                                                <div
                                                    key={idx}
                                                    className="w-24 h-32 bg-gray-50 rounded-xl border border-gray-200 overflow-hidden relative cursor-pointer hover:ring-2 hover:ring-indigo-500 transition-all group shadow-sm"
                                                    onClick={() => {
                                                        setZoomImageSrc(`${process.env.NEXT_PUBLIC_API_URL || ''}/static/${attempt.image_path}`);
                                                        setAnalysisResult(attempt.feedback_json);
                                                        setCurrentAttemptModel(attempt.ai_model_used);
                                                        setIsZoomModalOpen(true);
                                                    }}
                                                >
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleDeleteAttempt(attempt.id);
                                                        }}
                                                        className="absolute top-1 right-1 z-20 p-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-red-100 text-red-500 opacity-0 group-hover:opacity-100 hover:bg-red-500 hover:text-white transition-all shadow-sm"
                                                        title="Delete attempt"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleReanalyzeAttempt(attempt.id);
                                                        }}
                                                        className="absolute top-1 left-1 z-20 p-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-indigo-100 text-indigo-500 opacity-0 group-hover:opacity-100 hover:bg-indigo-500 hover:text-white transition-all shadow-sm"
                                                        title="Re-analyze attempt"
                                                    >
                                                        <RefreshCw className={`w-3.5 h-3.5 ${isAnalyzingSolution ? 'animate-spin' : ''}`} />
                                                    </button>
                                                    <img
                                                        src={`${process.env.NEXT_PUBLIC_API_URL || ''}/static/${attempt.image_path}`}
                                                        alt="Past attempt"
                                                        className="w-full h-full object-cover"
                                                    />
                                                    <div className="absolute inset-x-0 bottom-0 bg-black/40 p-1 text-[8px] text-white text-center font-bold">
                                                        Attempt #{problem.solution_attempts.length - idx}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Feedback Result Card */}
                                {analysisResult && (
                                    <div className="bg-gray-900 rounded-3xl p-6 text-white shadow-2xl animate-in zoom-in-95 duration-500">
                                        <div className="flex justify-between items-center mb-6">
                                            <div className="flex items-center gap-3">
                                                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-xl font-black ${analysisResult.score >= 80 ? 'bg-green-500' : analysisResult.score >= 60 ? 'bg-yellow-500' : 'bg-red-500 shadow-red-900/50'}`}>
                                                    {analysisResult.score}
                                                </div>
                                                <div>
                                                    <p className="text-[10px] font-black uppercase tracking-widest text-gray-400">Score Assessment</p>
                                                    <p className="text-lg font-bold">AI Grading Report</p>
                                                </div>
                                            </div>
                                            {currentAttemptModel && (
                                                <span className="text-[9px] font-medium text-gray-500 bg-white/5 border border-white/10 rounded-lg px-2 py-1">
                                                    Evaluated by {currentAttemptModel}
                                                </span>
                                            )}
                                        </div>

                                        <div className="space-y-4">
                                            {analysisResult.logic_gaps?.length > 0 && (
                                                <div className="bg-white/10 rounded-2xl p-4 border border-white/5">
                                                    <p className="text-red-400 text-[10px] font-black uppercase mb-2">Internal Logic Issues</p>
                                                    <ul className="space-y-2">
                                                        {analysisResult.logic_gaps.map((gap: string, i: number) => (
                                                            <li key={i} className="text-sm flex gap-2">
                                                                <span className="text-red-500">✕</span> {gap}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}

                                            {/* Formatting Feedback Section */}
                                            {analysisResult.formatting_feedback && (
                                                <div className="bg-orange-500/10 rounded-2xl p-4 border border-orange-500/20">
                                                    <p className="text-orange-400 text-[10px] font-black uppercase mb-2">卷面与规范诊断 (Formatting & Presentation)</p>
                                                    <div className="text-sm text-gray-200 leading-relaxed">
                                                        <span className="text-orange-400 mr-2">🖋️</span>
                                                        {analysisResult.formatting_feedback}
                                                    </div>
                                                </div>
                                            )}
                                            {analysisResult.calculation_errors?.length > 0 && (
                                                <div className="bg-white/10 rounded-2xl p-4 border border-white/5">
                                                    <p className="text-orange-400 text-[10px] font-black uppercase mb-2">Calculation Errors</p>
                                                    <ul className="space-y-2">
                                                        {analysisResult.calculation_errors.map((err: string, i: number) => (
                                                            <li key={i} className="text-sm flex gap-2">
                                                                <span className="text-orange-500">⚠</span> {err}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            {analysisResult.suggestions && (
                                                <div className="bg-indigo-500/20 rounded-2xl p-4 border border-indigo-500/20">
                                                    <p className="text-indigo-300 text-[10px] font-black uppercase mb-2">Learning Path Suggestion</p>
                                                    <div className="text-sm italic text-gray-200">
                                                        <LatexRenderer content={analysisResult.suggestions} block={false} />
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Mastery Confirmation Card */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center justify-between">
                            <h2 className="font-bold text-gray-800 text-sm">掌握程度 (Mastery Status)</h2>
                            <div className="flex gap-2">
                                {[
                                    { level: 1, label: '完全不会', emoji: '🔴' },
                                    { level: 2, label: '半知半解', emoji: '🟡' },
                                    { level: 3, label: '完全掌握', emoji: '🟢' }
                                ].map((item) => (
                                    <button
                                        key={item.level}
                                        onClick={() => updateMastery(item.level)}
                                        className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border ${masteryLevel === item.level
                                            ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-100'
                                            : 'bg-white border-gray-100 text-gray-600 hover:bg-gray-50'
                                            }`}
                                    >
                                        <span>{item.emoji}</span>
                                        {item.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Similar Practice Section (Full Width Bottom) */}
                <div className="bg-indigo-900 rounded-[2.5rem] p-8 md:p-12 text-white overflow-hidden relative">
                    <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500 rounded-full blur-[120px] opacity-20 -mr-48 -mt-48"></div>
                    <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500 rounded-full blur-[100px] opacity-10 -ml-32 -mb-32"></div>

                    <div className="relative z-10">
                        {/* Section Header */}
                        <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-8">
                            <div className="space-y-1 text-center md:text-left">
                                <h2 className="text-3xl font-black tracking-tight bg-gradient-to-r from-white to-indigo-300 bg-clip-text text-transparent">同类练习 (Similar Practice)</h2>
                                <p className="text-indigo-200 text-sm">Generate AI-powered variations to reinforce your understanding.</p>
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0">
                                {/* Tab Switcher */}
                                <div className="flex bg-white/10 rounded-2xl p-1 border border-white/10">
                                    <button
                                        onClick={() => setPracticeTab('generate')}
                                        className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${practiceTab === 'generate' ? 'bg-white text-indigo-900 shadow-lg' : 'text-indigo-200 hover:text-white'}`}
                                    >
                                        🔄 生成练习
                                    </button>
                                    <button
                                        onClick={() => setPracticeTab('history')}
                                        className={`px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-1.5 ${practiceTab === 'history' ? 'bg-white text-indigo-900 shadow-lg' : 'text-indigo-200 hover:text-white'}`}
                                    >
                                        📋 历史记录
                                        {historySessions.length > 0 && (
                                            <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full ${practiceTab === 'history' ? 'bg-indigo-600 text-white' : 'bg-white/20'}`}>
                                                {historySessions.length}
                                            </span>
                                        )}
                                    </button>
                                </div>
                                {practiceTab === 'generate' && (
                                    <button
                                        onClick={generatePractice}
                                        disabled={generatingPractice}
                                        className="bg-white text-indigo-900 px-6 py-3 rounded-2xl font-black text-sm hover:bg-indigo-50 transition-all shadow-xl disabled:opacity-50 active:scale-95 flex items-center gap-2 border-2 border-white/20"
                                    >
                                        {generatingPractice ? <><Loader2 className="w-4 h-4 animate-spin" /> 生成中...</> : <><span>🔄</span> 生成挑战</>}
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Generate Tab */}
                        {practiceTab === 'generate' && (
                            <div>
                                {generatingPractice && (
                                    <div className="flex items-center justify-center gap-3 py-16 text-indigo-200">
                                        <Loader2 className="w-6 h-6 animate-spin" />
                                        <span className="font-medium">AI 正在生成同类练习题...</span>
                                    </div>
                                )}
                                {!generatingPractice && practiceProblems.length === 0 && (
                                    <div className="text-center py-16 text-indigo-300 text-sm">
                                        点击"生成挑战"按钮来获取 AI 生成的同类练习题。
                                    </div>
                                )}
                                {practiceProblems.length > 0 && (
                                    <div className="grid md:grid-cols-2 gap-8">
                                        {practiceProblems.map((p: any, idx: number) => {
                                            const key = p.id || idx;
                                            const aiData = typeof p.ai_analysis === 'string' ? JSON.parse(p.ai_analysis) : (p.ai_analysis || {});
                                            return (
                                                <div key={key} className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-[2rem] p-8 shadow-2xl hover:bg-white/15 transition-all">
                                                    <div className="flex justify-between items-start mb-6">
                                                        <div className="bg-white text-indigo-900 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider">Practice #{idx + 1}</div>
                                                        <button onClick={() => setShowPracticeSolutions({ ...showPracticeSolutions, [key]: !showPracticeSolutions[key] })} className="w-9 h-9 bg-white/10 hover:bg-white/20 rounded-xl flex items-center justify-center transition-all" title="Show Solution">
                                                            <Eye className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                    <div className="bg-white rounded-2xl p-5 text-gray-900 min-h-[100px] flex items-center justify-center mb-6 shadow-inner">
                                                        <LatexRenderer content={p.latex_content || p.latex || ""} block />
                                                    </div>
                                                    <div className="space-y-3">
                                                        <div className="flex gap-2">
                                                            <label className="flex-grow bg-white text-indigo-900 px-4 py-3 rounded-xl cursor-pointer hover:bg-indigo-50 transition-all flex items-center justify-center gap-2 font-bold text-xs shadow-lg active:scale-95">
                                                                <span>📸</span>{practiceFiles[key] ? 'Photo Ready' : 'Upload Answer'}
                                                                <input type="file" accept="image/*" className="hidden" onChange={(e) => setPracticeFiles({ ...practiceFiles, [key]: e.target.files?.[0] || null })} />
                                                            </label>
                                                            <button onClick={() => handlePracticeSolutionUpload(p.id, idx)} disabled={!practiceFiles[key] || isAnalyzingPractice[key]} className="bg-indigo-500 text-white w-12 h-12 rounded-xl hover:bg-indigo-400 disabled:opacity-50 transition-all flex items-center justify-center shadow-lg active:scale-95 shrink-0">
                                                                {isAnalyzingPractice[key] ? <Loader2 className="w-5 h-5 animate-spin" /> : <ZoomIn className="w-5 h-5" />}
                                                            </button>
                                                        </div>
                                                        {practiceAnalysisResults[key] && (
                                                            <div className="bg-black/20 rounded-2xl p-4 border border-white/5">
                                                                <div className="flex items-center justify-between mb-3">
                                                                    <span className="text-[10px] font-black tracking-widest text-indigo-300">AI FEEDBACK</span>
                                                                    <span className="text-xl font-black">{practiceAnalysisResults[key].score}</span>
                                                                </div>
                                                                <div className="p-2 bg-white/5 rounded-lg text-xs text-indigo-50">
                                                                    <LatexRenderer content={practiceAnalysisResults[key].suggestions || ""} block={false} />
                                                                </div>
                                                            </div>
                                                        )}
                                                        {showPracticeSolutions[key] && (
                                                            <div className="bg-indigo-800/50 border border-white/10 rounded-2xl p-5 space-y-4">
                                                                <div>
                                                                    <p className="text-[10px] text-indigo-300 font-bold uppercase tracking-widest mb-2">Answer</p>
                                                                    <div className="font-black text-white">{aiData.answer || "N/A"}</div>
                                                                </div>
                                                                <div>
                                                                    <p className="text-[10px] text-indigo-300 font-bold uppercase tracking-widest mb-2">Solution</p>
                                                                    <div className="text-sm text-indigo-50 leading-relaxed"><LatexRenderer content={aiData.solution || ""} block /></div>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* History Tab */}
                        {practiceTab === 'history' && (
                            <div className="space-y-3">
                                {loadingHistory && (
                                    <div className="flex items-center justify-center gap-3 py-16 text-indigo-200">
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        <span>加载历史记录...</span>
                                    </div>
                                )}
                                {!loadingHistory && historySessions.length === 0 && (
                                    <div className="text-center py-16 text-indigo-300 text-sm">
                                        暂无历史练习记录。切换到"生成练习"生成第一批练习题吧！
                                    </div>
                                )}
                                {!loadingHistory && historySessions.map((session: any) => (
                                    <div key={session.id} className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden">
                                        <button
                                            onClick={async () => {
                                                if (expandedSession === session.id) { setExpandedSession(null); return; }
                                                setExpandedSession(session.id);
                                                if (!sessionProblems[session.id]) {
                                                    try {
                                                        const res = await fetchWithAuth(`/api/practices/sessions/${session.id}`);
                                                        if (res.ok) {
                                                            const data = await res.json();
                                                            setSessionProblems(prev => ({ ...prev, [session.id]: data.problems }));
                                                        }
                                                    } catch (e) { console.error(e); }
                                                }
                                            }}
                                            className="w-full flex items-center justify-between p-5 hover:bg-white/5 transition-colors text-left"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 bg-indigo-500/30 rounded-xl flex items-center justify-center text-indigo-200 font-bold text-sm shrink-0">{session.problem_count}</div>
                                                <div>
                                                    <p className="text-white font-bold text-sm">练习批次 #{session.id}</p>
                                                    <p className="text-indigo-300 text-xs mt-0.5">
                                                        {new Date(session.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                                        {session.ai_model && ` · ${session.ai_model}`}
                                                    </p>
                                                </div>
                                            </div>
                                            <ChevronDown className={`w-5 h-5 text-indigo-300 transition-transform duration-200 ${expandedSession === session.id ? 'rotate-180' : ''}`} />
                                        </button>

                                        {expandedSession === session.id && (
                                            <div className="border-t border-white/10 p-5 space-y-4">
                                                {!sessionProblems[session.id] && <div className="flex justify-center py-4"><Loader2 className="w-5 h-5 animate-spin text-indigo-300" /></div>}
                                                {sessionProblems[session.id]?.map((p: any, idx: number) => {
                                                    const key = `h_${p.id}`;
                                                    const aiData = typeof p.ai_analysis === 'string' ? JSON.parse(p.ai_analysis) : (p.ai_analysis || {});
                                                    return (
                                                        <div key={p.id} className="bg-white/10 border border-white/10 rounded-2xl p-6">
                                                            <div className="flex justify-between items-center mb-4">
                                                                <span className="text-[10px] font-black text-indigo-300 uppercase tracking-wider">题目 #{idx + 1}</span>
                                                                <button onClick={() => setShowPracticeSolutions(prev => ({ ...prev, [key]: !prev[key] }))} className="flex items-center gap-1.5 text-xs text-indigo-300 hover:text-white transition-colors font-medium">
                                                                    <Eye className="w-3.5 h-3.5" /> {showPracticeSolutions[key] ? '隐藏' : '查看'}解析
                                                                </button>
                                                            </div>
                                                            <div className="bg-white rounded-xl p-4 text-gray-900 mb-4 min-h-[60px] flex items-center justify-center">
                                                                <LatexRenderer content={p.latex_content || ""} block />
                                                            </div>
                                                            {showPracticeSolutions[key] && (
                                                                <div className="bg-indigo-800/50 border border-white/10 rounded-xl p-4 space-y-3">
                                                                    <div>
                                                                        <p className="text-[10px] text-indigo-300 font-bold uppercase tracking-widest mb-1">答案</p>
                                                                        <div className="text-white font-bold">{aiData.answer || "N/A"}</div>
                                                                    </div>
                                                                    <div>
                                                                        <p className="text-[10px] text-indigo-300 font-bold uppercase tracking-widest mb-1">解题过程</p>
                                                                        <div className="text-sm text-indigo-100 leading-relaxed"><LatexRenderer content={aiData.solution || "暂无"} block /></div>
                                                                    </div>
                                                                </div>
                                                            )}
                                                            <div className="flex gap-2 mt-3">
                                                                <label className="flex-grow bg-white/10 hover:bg-white/20 text-white px-4 py-2.5 rounded-xl cursor-pointer transition-all flex items-center justify-center gap-2 font-bold text-xs active:scale-95">
                                                                    <span>📸</span>{practiceFiles[p.id] ? 'Ready' : '上传作答'}
                                                                    <input type="file" accept="image/*" className="hidden" onChange={(e) => setPracticeFiles(prev => ({ ...prev, [p.id]: e.target.files?.[0] || null }))} />
                                                                </label>
                                                                <button onClick={() => handlePracticeSolutionUpload(p.id, idx)} disabled={!practiceFiles[p.id] || isAnalyzingPractice[p.id]} className="bg-indigo-500 text-white w-10 h-10 rounded-xl hover:bg-indigo-400 disabled:opacity-50 flex items-center justify-center shrink-0">
                                                                    {isAnalyzingPractice[p.id] ? <Loader2 className="w-4 h-4 animate-spin" /> : <ZoomIn className="w-4 h-4" />}
                                                                </button>
                                                            </div>
                                                            {practiceAnalysisResults[p.id] && (
                                                                <div className="mt-3 bg-black/20 rounded-xl p-3 text-xs">
                                                                    <div className="flex items-center justify-between mb-2">
                                                                        <span className="text-indigo-300 font-bold uppercase tracking-widest text-[10px]">AI FEEDBACK</span>
                                                                        <span className="font-black text-lg">{practiceAnalysisResults[p.id].score}</span>
                                                                    </div>
                                                                    <div className="text-indigo-100"><LatexRenderer content={practiceAnalysisResults[p.id].suggestions || ""} block={false} /></div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Premium Zoom Modal */}
            {isZoomModalOpen && (
                <div
                    className="fixed inset-0 z-50 bg-black/95 backdrop-blur-md flex items-center justify-center p-4 md:p-12 animate-in fade-in duration-300"
                    onClick={() => setIsZoomModalOpen(false)}
                >
                    <div className="relative w-full h-full flex items-center justify-center animate-in zoom-in-95 duration-500">
                        <img
                            src={zoomImageSrc}
                            alt="Zoom Preview"
                            className="max-w-full max-h-full object-contain rounded-lg shadow-[0_0_100px_rgba(0,0,0,0.5)] border border-white/10"
                        />
                        <button
                            className="absolute top-0 right-0 m-4 md:m-8 text-white/50 hover:text-white bg-white/10 hover:bg-white/20 w-12 h-12 rounded-2xl flex items-center justify-center transition-all backdrop-blur-xl border border-white/10 group"
                            onClick={() => setIsZoomModalOpen(false)}
                        >
                            <svg className="w-6 h-6 transition-transform group-hover:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );

    async function handleSolutionUpload() {
        if (!solutionFile) return;
        setIsAnalyzingSolution(true);
        console.log("Analyzing solution for problem:", id);
        const formData = new FormData();
        formData.append('file', solutionFile);

        try {
            const res = await fetchWithAuth(`/api/problems/${id}/submit_solution`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                console.log("Analysis successful:", data);
                setAnalysisResult(data.feedback_json);
                setCurrentAttemptModel(data.ai_model_used);
                // Update local problem state to include the new attempt in thumbnails
                setProblem((prev: any) => ({
                    ...prev,
                    solution_attempts: [...(prev.solution_attempts || []), data]
                }));
                // Clear the file input
                setSolutionFile(null);
                // Scroll to result after a short delay to allow state update
                setTimeout(() => {
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }, 100);
            } else {
                const errData = await res.json().catch(() => ({}));
                console.error("Analysis failed:", errData);
                alert("Analysis failed: " + (errData.detail || "Server error"));
            }
        } catch (e) {
            console.error("Upload error:", e);
            alert("Error uploading solution. Please check your network connection.");
        } finally {
            setIsAnalyzingSolution(false);
        }
    }

    async function handlePracticeSolutionUpload(practiceProblemId: number | undefined, arrayIdx: number) {
        // Fallback to array index if practice problem isn't saved in DB yet (edge case)
        const idKey = practiceProblemId || arrayIdx;
        const file = practiceFiles[idKey];
        if (!file || !practiceProblemId) {
            alert("Cannot analyze: No file selected or problem ID missing. Please refresh and try again.");
            return;
        }

        setIsAnalyzingPractice(prev => ({ ...prev, [idKey]: true }));
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetchWithAuth(`/api/practice-problems/${practiceProblemId}/submit_solution`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                setPracticeAnalysisResults(prev => ({ ...prev, [idKey]: data.feedback_json }));
            } else {
                alert("Practice analysis failed.");
            }
        } catch (e) {
            console.error(e);
            alert("Error uploading practice solution.");
        } finally {
            setIsAnalyzingPractice(prev => ({ ...prev, [idKey]: false }));
        }
    }

    async function updateMastery(level: number) {
        setMasteryLevel(level);
        try {
            await fetchWithAuth(`/api/problems/${id}/mastery`, {
                method: 'POST',
                body: JSON.stringify({ level })
            });
        } catch (e) {
            console.error(e);
            alert("Error updating status.");
        }
    }

    async function generatePractice() {
        setGeneratingPractice(true);
        setPracticeProblems([]);
        try {
            const res = await fetchWithAuth(`/api/problems/${id}/similar`, {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                // Append new generated problems safely, allowing user to keep generating more
                setPracticeProblems(prev => [...prev, ...data]);
            } else {
                alert("Failed to generate practice problems. Try again later.");
            }
        } catch (e) {
            console.error(e);
            alert("Error connecting to AI service.");
        } finally {
            setGeneratingPractice(false);
        }
    }

    async function handleReanalyze() {
        if (!confirm("Are you sure you want to re-run AI analysis? This will overwrite existing results.")) {
            return;
        }
        setIsReanalyzing(true);
        try {
            const res = await fetchWithAuth(`/api/problems/${id}/reanalyze`, {
                method: 'POST'
            });
            if (res.ok) {
                window.location.reload();
            } else {
                alert("Re-analysis failed.");
            }
        } catch (e) {
            console.error(e);
            alert("Error connecting to server.");
        } finally {
            setIsReanalyzing(false);
        }
    }
}
