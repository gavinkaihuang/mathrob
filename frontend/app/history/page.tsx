'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, Filter, Loader2 } from 'lucide-react';

interface Problem {
    id: number;
    image_path: string;
    ai_analysis?: {
        knowledge_points?: string[];
        [key: string]: unknown;
    };
    current_mastery_level?: number;
    created_at: string;
    knowledge_points?: string[]; // The API might return it here depending on previous logic, but schema says ai_analysis
}

import { fetchWithAuth, resolveImageUrl } from '../../utils/api';

// ... class Problem ...

export default function HistoryPage() {
    const [problems, setProblems] = useState<Problem[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterMastery, setFilterMastery] = useState<number | 'all' | 'recent'>('all');
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const pageSize = 20;

    useEffect(() => {
        setCurrentPage(1);
    }, [filterMastery]);

    const getVisiblePages = (): Array<number | '...'> => {
        if (totalPages <= 7) {
            return Array.from({ length: totalPages }, (_, i) => i + 1);
        }

        const pages: Array<number | '...'> = [1];
        const start = Math.max(2, currentPage - 1);
        const end = Math.min(totalPages - 1, currentPage + 1);

        if (start > 2) {
            pages.push('...');
        }

        for (let page = start; page <= end; page += 1) {
            pages.push(page);
        }

        if (end < totalPages - 1) {
            pages.push('...');
        }

        pages.push(totalPages);
        return pages;
    };

    useEffect(() => {
        async function fetchProblems() {
            setLoading(true);
            try {
                const params = new URLSearchParams({
                    page: String(currentPage),
                    page_size: String(pageSize),
                });

                if (filterMastery === 'recent') {
                    params.set('recent_days', '7');
                } else if (filterMastery !== 'all') {
                    params.set('mastery', String(filterMastery));
                }

                const url = `/api/problems/wrong?${params.toString()}`;

                const res = await fetchWithAuth(url);
                if (res.ok) {
                    const data = await res.json();
                    setProblems(data.items || []);
                    setTotalPages(data.total_pages || 1);
                    setTotalItems(data.total || 0);
                } else {
                    setProblems([]);
                    setTotalPages(1);
                    setTotalItems(0);
                }
            } catch (error) {
                console.error("Failed to fetch history", error);
                setProblems([]);
                setTotalPages(1);
                setTotalItems(0);
            } finally {
                setLoading(false);
            }
        }
        fetchProblems();
    }, [filterMastery, currentPage]);

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
                            <h1 className="text-2xl font-bold text-gray-900">错题本 (Mistake Book)</h1>
                        </div>
                    </div>

                    {/* Filter */}
                    <div className="flex items-center gap-3 bg-white p-1 rounded-lg border border-gray-200 shadow-sm">
                        <Filter className="w-4 h-4 text-gray-400 ml-2" />
                        <select
                            value={filterMastery}
                            onChange={(e) => {
                                const value = e.target.value;
                                if (value === 'all' || value === 'recent') {
                                    setFilterMastery(value);
                                } else {
                                    setFilterMastery(Number(value));
                                }
                                setCurrentPage(1);
                            }}
                            className="bg-transparent border-none text-sm font-medium focus:ring-0 text-gray-700 py-1 pr-8 cursor-pointer"
                        >
                            <option value="all">所有题目 (All)</option>
                            <option value="recent">🕐 最近复习 (Recently Reviewed)</option>
                            <option value="1">🔴 未掌握 (Not Understood)</option>
                            <option value="2">🟡 半掌握 (Half Understood)</option>
                            <option value="3">🟢 已掌握 (Mastered)</option>
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
                    <>
                        <div className="flex items-center justify-between">
                            <p className="text-sm text-gray-500">共 {totalItems} 道错题 · 第 {currentPage} / {totalPages} 页</p>
                        </div>

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
                                            src={resolveImageUrl(problem.image_path)}
                                            alt={`Problem ${problem.id}`}
                                            className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-300"
                                            loading="lazy"
                                        />
                                    </div>

                                    {/* Content */}
                                    <div className="p-4 flex flex-col flex-1">
                                        <div className="flex-1 space-y-2">
                                            <div className="flex flex-wrap gap-1.5">
                                                {(problem.knowledge_points || problem.ai_analysis?.knowledge_points || []).slice(0, 3).map((tag: string, i: number) => (
                                                    <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-md">
                                                        {tag}
                                                    </span>
                                                ))}
                                                {(problem.knowledge_points || []).length > 3 && (
                                                    <span className="text-xs text-gray-400">+{(problem.knowledge_points || []).length - 3}</span>
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

                        {totalPages > 1 && (
                            <div className="flex items-center justify-center gap-2 pt-4">
                                <button
                                    onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                                    disabled={currentPage === 1}
                                    className="px-3 py-2 text-sm rounded-lg border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    上一页
                                </button>

                                {getVisiblePages().map((pageToken, idx) =>
                                    pageToken === '...' ? (
                                        <span key={`ellipsis-${idx}`} className="px-2 text-gray-400">...</span>
                                    ) : (
                                        <button
                                            key={pageToken}
                                            onClick={() => setCurrentPage(pageToken)}
                                            className={`min-w-10 px-3 py-2 text-sm rounded-lg border transition-colors ${
                                                currentPage === pageToken
                                                    ? 'bg-indigo-600 text-white border-indigo-600'
                                                    : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                                            }`}
                                        >
                                            {pageToken}
                                        </button>
                                    )
                                )}

                                <button
                                    onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                                    disabled={currentPage === totalPages}
                                    className="px-3 py-2 text-sm rounded-lg border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    下一页
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
