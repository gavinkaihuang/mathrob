'use client';

import { useEffect, useState, use } from 'react';
import { LatexRenderer } from '@/components/LatexRenderer';
import { Loader2, ArrowLeft } from 'lucide-react';
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

    // Practice Mode State

    const [practiceProblems, setPracticeProblems] = useState<any[]>([]);
    const [generatingPractice, setGeneratingPractice] = useState(false);
    const [isReanalyzing, setIsReanalyzing] = useState(false);
    const [practiceAnswers, setPracticeAnswers] = useState<{ [key: number]: string }>({});
    const [showPracticeSolutions, setShowPracticeSolutions] = useState<{ [key: number]: boolean }>({});

    // Solution Analysis State
    const [solutionFile, setSolutionFile] = useState<File | null>(null);
    const [isAnalyzingSolution, setIsAnalyzingSolution] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<any>(null);

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
                }
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        }
        fetchProblem();
    }, [id]);

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
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-[1800px] mx-auto space-y-6">
                <Link href="/" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-900">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Upload
                </Link>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                        <h1 className="text-2xl font-bold text-gray-900">Problem Analysis #{problem.id}</h1>
                        <button
                            onClick={handleReanalyze}
                            disabled={isReanalyzing}
                            className="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors text-sm font-medium border border-gray-200"
                        >
                            {isReanalyzing ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Re-analyzing...
                                </>
                            ) : (
                                <>
                                    ✨ 重新分析 (Re-analyze)
                                </>
                            )}
                        </button>
                    </div>

                    <div className="grid md:grid-cols-[1fr_2fr] gap-8 p-6">
                        {/* Left: Image */}
                        <div className="space-y-4">
                            <h2 className="font-semibold text-gray-700">Original Scan</h2>
                            <div className="aspect-[3/4] bg-gray-100 rounded-lg overflow-hidden relative border border-gray-200">
                                {problem.image_path ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img
                                        src={`http://localhost:8000/static/${problem.image_path.split('/').pop()}`}
                                        alt="Problem Scan"
                                        className="w-full h-full object-contain"
                                    />
                                ) : (
                                    <div className="flex items-center justify-center h-full text-gray-400">
                                        No Image Available
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Right: Analysis */}
                        <div className="space-y-6">
                            <div>
                                <h2 className="font-semibold text-gray-700 mb-2">Recognized LaTeX</h2>
                                <div className="p-4 bg-gray-50 rounded-lg text-lg overflow-x-auto">
                                    <LatexRenderer content={problem.latex_content || "No LaTeX detected"} block />
                                </div>
                            </div>

                            {/* Hint Section */}
                            <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <h2 className="font-semibold text-gray-700">Hint & Analysis</h2>
                                    {!showHint && (
                                        <button
                                            onClick={() => setShowHint(true)}
                                            className="px-4 py-2 bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition-colors text-sm font-medium"
                                        >
                                            💡 获取思路提示 (Get Hint)
                                        </button>
                                    )}
                                </div>
                                {showHint && (
                                    <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100 animate-in fade-in slide-in-from-top-2 duration-300">
                                        <p className="text-sm text-yellow-800 font-semibold mb-2">解题思路 (Thinking Process):</p>
                                        <div className="text-gray-800">
                                            <LatexRenderer content={problem.ai_analysis?.thinking_process || "No hint available"} block />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Full Solution Section */}
                            <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <h2 className="font-semibold text-gray-700">Detailed Solution</h2>
                                    {!showSolution && (
                                        <button
                                            onClick={() => setShowSolution(true)}
                                            className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors text-sm font-medium"
                                        >
                                            📝 查看详细过程 (View Solution)
                                        </button>
                                    )}
                                </div>
                                {showSolution && (
                                    <div className="p-4 bg-blue-50 rounded-lg border border-blue-100 animate-in fade-in slide-in-from-top-2 duration-300">
                                        <div className="text-gray-800">
                                            <LatexRenderer content={problem.ai_analysis?.solution || "No solution available"} block />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Knowledge Points */}
                            {/* Knowledge Points */}
                            {((problem.knowledge_points && problem.knowledge_points.length > 0) || (problem.ai_analysis?.knowledge_points && problem.ai_analysis.knowledge_points.length > 0)) && (
                                <div>
                                    <h2 className="font-semibold text-gray-700 mb-2">Knowledge Points</h2>
                                    <div className="flex flex-wrap gap-2">
                                        {(problem.knowledge_points || problem.ai_analysis?.knowledge_points || []).map((kp: string, i: number) => (
                                            <span key={i} className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium border border-indigo-100">
                                                {kp}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-500">Difficulty:</span>
                                <div className="flex gap-1">
                                    {[1, 2, 3, 4, 5].map(v => (
                                        <div key={v} className={`w-2 h-6 rounded-full ${v <= (problem.difficulty || 0) ? 'bg-blue-500' : 'bg-gray-200'}`} />
                                    ))}
                                </div>
                            </div>

                            {/* Solution Analysis Section */}
                            <div className="mt-8 pt-6 border-t border-gray-100">
                                <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                                    📸 Upload Your Answer (AI Correction)
                                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">New</span>
                                </h2>

                                <div className="space-y-4">
                                    <div className="flex gap-4">
                                        <input
                                            type="file"
                                            accept="image/*"
                                            onChange={(e) => setSolutionFile(e.target.files?.[0] || null)}
                                            className="block w-full text-sm text-gray-500
                                                file:mr-4 file:py-2 file:px-4
                                                file:rounded-full file:border-0
                                                file:text-sm file:font-semibold
                                                file:bg-indigo-50 file:text-indigo-700
                                                hover:file:bg-indigo-100"
                                        />
                                        <button
                                            onClick={handleSolutionUpload}
                                            disabled={!solutionFile || isAnalyzingSolution}
                                            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium whitespace-nowrap"
                                        >
                                            {isAnalyzingSolution ? (
                                                <div className="flex items-center gap-2">
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    Checking...
                                                </div>
                                            ) : (
                                                "Analyze"
                                            )}
                                        </button>
                                    </div>

                                    {analysisResult && (
                                        <div className="bg-white border rounded-xl overflow-hidden animate-in fade-in slide-in-from-top-4">
                                            <div className="bg-indigo-50 p-4 border-b border-indigo-100 flex justify-between items-center">
                                                <h3 className="font-bold text-indigo-900">Analysis Result</h3>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm text-indigo-600">Score:</span>
                                                    <span className={`text-xl font-bold ${analysisResult.score >= 80 ? 'text-green-600' : analysisResult.score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                                                        {analysisResult.score}/100
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="p-4 space-y-4">
                                                {analysisResult.logic_gaps && analysisResult.logic_gaps.length > 0 && (
                                                    <div>
                                                        <h4 className="flex items-center gap-2 text-sm font-semibold text-red-700 mb-2">
                                                            🚫 Logic Gaps / Issues
                                                        </h4>
                                                        <ul className="list-disc list-inside text-sm text-gray-700 space-y-1 bg-red-50 p-3 rounded-lg">
                                                            {analysisResult.logic_gaps.map((gap: string, i: number) => (
                                                                <li key={i}>{gap}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}

                                                {analysisResult.calculation_errors && analysisResult.calculation_errors.length > 0 && (
                                                    <div>
                                                        <h4 className="flex items-center gap-2 text-sm font-semibold text-orange-700 mb-2">
                                                            ⚠️ Calculation Errors
                                                        </h4>
                                                        <ul className="list-disc list-inside text-sm text-gray-700 space-y-1 bg-orange-50 p-3 rounded-lg">
                                                            {analysisResult.calculation_errors.map((err: string, i: number) => (
                                                                <li key={i}>{err}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}

                                                {analysisResult.suggestions && (
                                                    <div>
                                                        <h4 className="flex items-center gap-2 text-sm font-semibold text-blue-700 mb-2">
                                                            💡 Suggestions
                                                        </h4>
                                                        <div className="text-sm text-gray-700 bg-blue-50 p-3 rounded-lg">
                                                            <LatexRenderer content={analysisResult.suggestions} block={false} />
                                                        </div>
                                                    </div>
                                                )}

                                                {/* If perfect */}
                                                {analysisResult.score === 100 && (
                                                    <div className="text-center p-4 text-green-600 font-medium">
                                                        🎉 Excellent work! No errors found.
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Mastery Buttons */}
                            <div className="mt-8 pt-6 border-t border-gray-100">
                                <h2 className="font-semibold text-gray-700 mb-4 text-center">Mastery Confirmation</h2>
                                <div className="grid grid-cols-3 gap-4">
                                    <button
                                        onClick={() => updateMastery(1)}
                                        className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all duration-200 ${masteryLevel === 1
                                            ? 'bg-red-100 border-red-500 ring-2 ring-red-200 scale-[1.02] shadow-sm'
                                            : 'bg-red-50 border-red-100 text-red-600 hover:bg-red-100'
                                            }`}
                                    >
                                        <span className="text-2xl mb-1">🔴</span>
                                        <span className={`font-medium text-sm ${masteryLevel === 1 ? 'text-red-800 font-bold' : ''}`}>完全不会</span>
                                        <span className="text-xs opacity-75">Not Understood</span>
                                    </button>
                                    <button
                                        onClick={() => updateMastery(2)}
                                        className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all duration-200 ${masteryLevel === 2
                                            ? 'bg-yellow-100 border-yellow-500 ring-2 ring-yellow-200 scale-[1.02] shadow-sm'
                                            : 'bg-yellow-50 border-yellow-100 text-yellow-700 hover:bg-yellow-100'
                                            }`}
                                    >
                                        <span className="text-2xl mb-1">🟡</span>
                                        <span className={`font-medium text-sm ${masteryLevel === 2 ? 'text-yellow-900 font-bold' : ''}`}>半知半解</span>
                                        <span className="text-xs opacity-75">Half Understood</span>
                                    </button>
                                    <button
                                        onClick={() => updateMastery(3)}
                                        className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all duration-200 ${masteryLevel === 3
                                            ? 'bg-green-100 border-green-500 ring-2 ring-green-200 scale-[1.02] shadow-sm'
                                            : 'bg-green-50 border-green-100 text-green-700 hover:bg-green-100'
                                            }`}
                                    >
                                        <span className="text-2xl mb-1">🟢</span>
                                        <span className={`font-medium text-sm ${masteryLevel === 3 ? 'text-green-900 font-bold' : ''}`}>完全掌握</span>
                                        <span className="text-xs opacity-75">Mastered</span>
                                    </button>
                                </div>
                            </div>
                        </div>


                    </div>
                </div>
            </div>

            {/* Practice Section - Moved outside grid for full width */}
            <div className="p-6 border-t border-gray-100 bg-gray-50/50">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-gray-800">Similar Practice</h2>
                    <button
                        onClick={generatePractice}
                        disabled={generatingPractice}
                        className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium shadow-sm"
                    >
                        {generatingPractice ? (
                            <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Generating...
                            </>
                        ) : (
                            <>
                                🔄 生成同类练习 (Generate Practice)
                            </>
                        )}
                    </button>
                </div>

                {practiceProblems.length > 0 && (
                    <div className="grid md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        {practiceProblems.map((p, idx) => (
                            <div key={idx} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col">
                                <div className="flex justify-between mb-3">
                                    <span className="text-xs font-bold text-indigo-500 uppercase tracking-wider">Practice #{idx + 1}</span>
                                </div>

                                {/* Problem Content */}
                                <div className="mb-4 text-gray-800 flex-grow">
                                    <LatexRenderer content={p.latex} block />
                                </div>

                                {/* Input Area */}
                                <div className="space-y-3 mt-4">
                                    <textarea
                                        placeholder="Write your answer here..."
                                        className="w-full p-3 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-100 focus:border-indigo-400 outline-none transition-all"
                                        rows={3}
                                        value={practiceAnswers[idx] || ''}
                                        onChange={(e) => setPracticeAnswers({ ...practiceAnswers, [idx]: e.target.value })}
                                    />

                                    <div className="flex justify-between items-center">
                                        <div className="flex gap-2">
                                            <button className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-md text-xs font-medium hover:bg-gray-200">
                                                📸 Photo
                                            </button>
                                            <button
                                                onClick={() => setShowPracticeSolutions({ ...showPracticeSolutions, [idx]: !showPracticeSolutions[idx] })}
                                                className="px-3 py-1.5 text-indigo-600 hover:bg-indigo-50 rounded-md text-xs font-medium transition-colors"
                                            >
                                                {showPracticeSolutions[idx] ? 'Hide' : '👁 Solution'}
                                            </button>
                                        </div>
                                        <button className="px-4 py-1.5 bg-gray-900 text-white rounded-md text-xs font-medium hover:bg-gray-800 shadow-sm">
                                            Submit
                                        </button>
                                    </div>

                                    {/* Solution Reveal */}
                                    {showPracticeSolutions[idx] && (
                                        <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-100 text-sm animate-in fade-in zoom-in-95">
                                            <p className="font-semibold text-green-800 mb-1">Answer:</p>
                                            <div className="text-gray-800 mb-2">{p.answer}</div>
                                            <p className="font-semibold text-green-800 mb-1">Solution:</p>
                                            <div className="text-gray-700">
                                                <LatexRenderer content={p.solution} block />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );

    async function handleSolutionUpload() {
        if (!solutionFile) return;
        setIsAnalyzingSolution(true);
        const formData = new FormData();
        formData.append('file', solutionFile);

        try {
            const res = await fetchWithAuth(`/api/problems/${id}/submit_solution`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                setAnalysisResult(data.feedback_json);
            } else {
                alert("Analysis failed.");
            }
        } catch (e) {
            console.error(e);
            alert("Error uploading solution.");
        } finally {
            setIsAnalyzingSolution(false);
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
                setPracticeProblems(data);
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
