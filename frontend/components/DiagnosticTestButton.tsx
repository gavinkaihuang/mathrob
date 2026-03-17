'use client';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/utils/api';

export default function DiagnosticTestButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [daysSinceLast, setDaysSinceLast] = useState<number | null>(0); // 0 means just fetched, won't trigger banner until loaded
  const [hasFetched, setHasFetched] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetchWithAuth('/api/user/assessment_status');
        if (res.ok) {
          const data = await res.json();
          setDaysSinceLast(data.days_since_last_test);
        }
      } catch (err) {
        console.error("Failed to fetch assessment status", err);
      } finally {
        setHasFetched(true);
      }
    };
    fetchStatus();
  }, []);

  const startAssessment = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth('/api/assessment/generate_paper', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        router.push(`/assessment/${data.session_id}`);
      } else {
        try {
          const errData = await res.json();
          alert(`无法生成评测: ${errData.detail || '未知原因'}`);
        } catch {
          alert('生成摸底评测失败，请确保您已标记了一些知识点为“已学”。');
        }
      }
    } catch (err) {
      console.error(err);
      alert('网络错误，请稍后再试。');
    } finally {
      setLoading(false);
    }
  };

  const needsAssessment = hasFetched && (daysSinceLast === null || daysSinceLast > 14);

  return (
    <div className="flex flex-col gap-3">
      {needsAssessment && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4 text-sm font-medium animate-fade-in">
          <div className="flex items-start gap-2">
            <span className="text-amber-500 mt-0.5">⏰</span>
            <p>
              {daysSinceLast === null 
                ? "系统需要一次初始评测来为您建立学习雷达！" 
                : `距离上次全面体检已过去 ${daysSinceLast} 天，系统需要一次新的评测来为您校准学习雷达！`}
            </p>
          </div>
        </div>
      )}

      <button 
        onClick={startAssessment}
        disabled={loading}
        className="w-full py-4 text-white font-bold rounded-xl shadow-lg bg-indigo-600 hover:bg-indigo-700 transition shadow-indigo-500/25 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            正在准备题库...
          </>
        ) : (
          '🔥 开始摸底评测 (Diagnostic Test)'
        )}
      </button>
    </div>
  );
}
