'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, Filter, Loader2 } from 'lucide-react';

interface Problem {
    id: number;
    image_path: string;
    ai_analysis?: {
        knowledge_points?: string[];
        [key: string]: any;
    };
    current_mastery_level?: number;
    created_at: string;
    knowledge_points?: any; // The API might return it here depending on previous logic, but schema says ai_analysis
}

import { fetchWithAuth } from '../../utils/api';

// ... class Problem ...

export default function HistoryPage() {
    const [problems, setProblems] = useState<Problem[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterMastery, setFilterMastery] = useState<number | 'all'>('all');

    useEffect(() => {
        async function fetchProblems() {
            setLoading(true);
            try {
                let url = `/api/problems?limit=50`;
                if (filterMastery !== 'all') {
                    url += `&mastery=${filterMastery}`;
                }

                const res = await fetchWithAuth(url);
                if (res.ok) {
                    const data = await res.json();
                    setProblems(data);
                }
            } catch (error) {
                console.error("Failed to fetch history", error);
            } finally {
                setLoading(false);
            }
        }
        fetchProblems();
    }, [filterMastery]);

    return (
        <div className="min-h-screen bg-gray-50 p-6 md:p-8">
            <div className="max-w-[1600px] mx-auto space-y-8">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                            <ArrowLeft className="w-6 h-6 text-gray-600" />
                        </Link>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Problem History</h1>
                            <p className="text-sm text-gray-500">Review your past scans and mastery progress</p>
                        </div>
                    </div>

                    {/* Filter */}
                    <div className="flex items-center gap-3 bg-white p-1 rounded-lg border border-gray-200 shadow-sm">
                        <Filter className="w-4 h-4 text-gray-400 ml-2" />
                        <select
                            value={filterMastery}
                            onChange={(e) => setFilterMastery(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                            className="bg-transparent border-none text-sm font-medium focus:ring-0 text-gray-700 py-1 pr-8 cursor-pointer"
                        >
                            <option value="all">All Problems</option>
                            <option value="1">🔴 Not Understood</option>
                            <option value="2">🟡 Half Understood</option>
                            <option value="3">🟢 Mastered</option>
                        </select>
                    </div>
                </div>

                {/* Grid */}
                {loading ? (
                    <div className="flex h-64 items-center justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                ) : problems.length === 0 ? (
                    <div className="text-center py-20 bg-white rounded-3xl border border-dashed border-gray-200">
                        <p className="text-gray-500 text-lg">No problems found matching filters.</p>
                        <Link href="/" className="text-blue-600 font-medium hover:underline mt-2 inline-block">
                            Upload a new problem
                        </Link>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {problems.map(problem => (
                            <Link
                                key={problem.id}
                                href={`/problems/${problem.id}`}
                                className="group bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col"
                            >
                                {/* Thumbnail */}
                                <div className="aspect-[4/3] bg-gray-50 relative border-b border-gray-50 p-4">
                                    <div className="absolute top-3 right-3 z-10">
                                        {problem.current_mastery_level === 3 && <span className="text-2xl drop-shadow-sm">🟢</span>}
                                        {problem.current_mastery_level === 2 && <span className="text-2xl drop-shadow-sm">🟡</span>}
                                        {problem.current_mastery_level === 1 && <span className="text-2xl drop-shadow-sm">🔴</span>}
                                    </div>
                                    <img
                                        src={`http://localhost:8000/static/${problem.image_path.split('/').pop()}`}
                                        alt={`Problem ${problem.id}`}
                                        className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-300"
                                        loading="lazy"
                                    />
                                </div>

                                {/* Content */}
                                <div className="p-4 flex flex-col flex-1">
                                    <div className="flex-1 space-y-2">
                                        <div className="flex flex-wrap gap-1.5">
                                            {/* Try extracting knowledge points from either root (if API change) or ai_analysis */}
                                            {/* Note: In previous steps we saw knowledge_points being saved to ai_analysis JSON column, 
                                                but also there is a knowledge_points table. 
                                                The API returns ProblemSchema which sends the raw JSON or filtered fields.
                                                Based on page.tsx, knowledge_points is likely directly on problem object if backend puts it there, 
                                                or inside ai_analysis. Let's handle both safely. */}
                                            {((problem as any).knowledge_points || problem.ai_analysis?.knowledge_points || []).slice(0, 3).map((tag: string, i: number) => (
                                                <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-md">
                                                    {tag}
                                                </span>
                                            ))}
                                            {((problem as any).knowledge_points || []).length > 3 && (
                                                <span className="text-xs text-gray-400">+{((problem as any).knowledge_points || []).length - 3}</span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="mt-4 pt-3 border-t border-gray-50 flex justify-between items-center">
                                        <span className="text-xs text-gray-400">
                                            {new Date(problem.created_at).toLocaleDateString()}
                                        </span>
                                        <span className="text-xs font-medium text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                            View Details →
                                        </span>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
