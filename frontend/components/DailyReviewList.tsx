"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

import { fetchWithAuth } from '../utils/api';

export function DailyReviewList() {
    const [problems, setProblems] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDaily = async () => {
            try {
                const res = await fetchWithAuth('/api/daily-review');
                if (res.ok) {
                    const data = await res.json();
                    setProblems(data);
                }
            } catch (e) {
                console.error("Failed to fetch daily review", e);
            } finally {
                setLoading(false);
            }
        };
        fetchDaily();
    }, []);

    if (loading) return <div className="text-gray-500 text-center py-4">Loading today's tasks...</div>;

    return (
        <div className="space-y-4">
            <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                📅 Today's Tasks
                {problems.length > 0 && (
                    <span className="bg-red-100 text-red-600 text-sm px-2 py-0.5 rounded-full">
                        {problems.length} Due
                    </span>
                )}
            </h2>

            {problems.length === 0 ? (
                <div className="bg-green-50 p-6 rounded-xl border border-green-100 text-center">
                    <h3 className="text-lg font-semibold text-green-800">🎉 All caught up!</h3>
                    <p className="text-green-600 mt-1">No pending reviews for today.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4">
                    {problems.map((p) => (
                        <div key={p.id} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between hover:shadow-md transition-shadow">
                            <div className="flex-1 min-w-0 mr-4">
                                <div className="text-sm text-gray-500 mb-1">
                                    Problem #{p.id} • Level: {p.current_mastery_level || 'N/A'}
                                </div>
                                <div className="text-gray-800 line-clamp-2 max-h-16 overflow-hidden">
                                    {p.latex_content ? (
                                        <span className="latex-preview text-sm">
                                            <InlineMath math={p.latex_content.slice(0, 100) + (p.latex_content.length > 100 ? "..." : "")} />
                                        </span>
                                    ) : (
                                        <span className="text-gray-400 italic">No content preview</span>
                                    )}
                                </div>
                            </div>
                            <Link
                                href={`/problems/${p.id}`}
                                className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 whitespace-nowrap"
                            >
                                Review
                            </Link>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
