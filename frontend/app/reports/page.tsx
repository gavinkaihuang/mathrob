'use client';

import { useEffect, useState } from 'react';
import { Loader2, FileText, Download, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { fetchWithAuth } from '../../utils/api';

interface WeeklyReport {
    id: number;
    week_start: string;
    pdf_path: string;
    summary_json: any;
    created_at: string;
}

export default function ReportsPage() {
    const [reports, setReports] = useState<WeeklyReport[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        fetchReports();
    }, []);

    // ...

    const fetchReports = async () => {
        try {
            const res = await fetchWithAuth('/api/reports');
            if (res.ok) {
                const data = await res.json();
                setReports(data);
            }
        } catch (error) {
            console.error("Failed to fetch reports", error);
        } finally {
            setLoading(false);
        }
    };

    const generateReport = async () => {
        setGenerating(true);
        try {
            const res = await fetchWithAuth('/api/reports/generate', {
                method: 'POST'
            });
            if (res.ok) {
                await fetchReports(); // Refresh list
            } else {
                alert("Failed to generate report");
            }
        } catch (error) {
            console.error("Error generating report", error);
            alert("Error generating report");
        } finally {
            setGenerating(false);
        }
    };

    const handleDownload = async (id: number, path: string) => {
        try {
            const res = await fetchWithAuth(`/api/reports/${id}/download`);
            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = path.split('/').pop() || 'report.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                alert("Failed to download report");
            }
        } catch (error) {
            console.error("Download error", error);
            alert("Error downloading report");
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-[1200px] mx-auto space-y-8">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Weekly Learning Reports</h1>
                        <p className="text-gray-500 mt-1">Review your weekly progress summaries and analysis</p>
                    </div>
                    <button
                        onClick={generateReport}
                        disabled={generating}
                        className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-sm font-medium"
                    >
                        {generating ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Generating...
                            </>
                        ) : (
                            <>
                                <RefreshCw className="w-4 h-4" />
                                Generate New Report
                            </>
                        )}
                    </button>
                </div>

                {loading ? (
                    <div className="flex justify-center p-12">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                ) : reports.length === 0 ? (
                    <div className="text-center py-20 bg-white rounded-2xl border border-gray-100 shadow-sm">
                        <div className="bg-indigo-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                            <FileText className="w-8 h-8 text-indigo-400" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">No Reports Yet</h3>
                        <p className="text-gray-500 mt-1">Generate your first weekly report to see your progress.</p>
                    </div>
                ) : (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {reports.map((report) => (
                            <div key={report.id} className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="p-3 bg-red-50 rounded-xl">
                                        <FileText className="w-6 h-6 text-red-500" />
                                    </div>
                                    <span className="text-xs font-medium text-gray-400 bg-gray-50 px-2 py-1 rounded-full">
                                        Week of {report.week_start}
                                    </span>
                                </div>

                                <h3 className="font-bold text-gray-900 mb-2">Weekly Summary</h3>

                                {report.summary_json && (
                                    <div className="space-y-2 mb-6">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-500">Problems Uploaded</span>
                                            <span className="font-medium">{report.summary_json.uploaded}</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-500">Reviews Done</span>
                                            <span className="font-medium">{report.summary_json.reviews}</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-500">Mastered Items</span>
                                            <span className="font-medium text-green-600">{report.summary_json.mastery?.['3'] || 0}</span>
                                        </div>
                                    </div>
                                )}

                                <button
                                    onClick={() => handleDownload(report.id, report.pdf_path)}
                                    className="flex items-center justify-center gap-2 w-full py-2.5 border border-indigo-100 text-indigo-600 rounded-xl hover:bg-indigo-50 font-medium transition-colors cursor-pointer"
                                >
                                    <Download className="w-4 h-4" />
                                    Download PDF
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
