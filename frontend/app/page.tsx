"use client";

import { useState } from 'react';
import { FileUpload } from '@/components/FileUpload';
import KnowledgeMasteryDashboard from '@/components/KnowledgeMasteryDashboard';
import FullExamUploader from '@/components/FullExamUploader';
import Link from 'next/link';

export default function Home() {
  const [tab, setTab] = useState<'single' | 'exam'>('single');

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center p-8 pb-20">
      <div className="w-full max-w-7xl space-y-12 mt-10">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            MathRob AI
          </h1>
          <p className="text-lg leading-8 text-gray-600">
            Upload your math problems. Let AI analyze, solve, and help you master them.
          </p>
        </div>

        {/* Home Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full">
          
          {/* Left: Analytics Dashboard (8 Cols) */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            <KnowledgeMasteryDashboard />
          </div>

          {/* Right: Action Center (4 Cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            {/* Tabbed Actions: 新题理解解答 / 整卷智能批阅 */}
            <div className="bg-white p-1 rounded-2xl shadow-sm border border-gray-100 w-full">
              <div className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-700">操作中心</h3>
                  <div className="text-sm text-slate-400">快速上传与智能阅卷</div>
                </div>
                <div className="border-b border-slate-100 mb-4">
                  <TabButtons tab={tab} setTab={setTab} />
                </div>

                <div>
                  <TabPanels tab={tab} />
                </div>
              </div>
            </div>

            
          </div>

        </div>
      </div>
    </main>
  );
}

function TabButtons({ tab, setTab }: { tab: 'single' | 'exam'; setTab: (t: 'single' | 'exam') => void }) {
  return (
    <div className="flex gap-2">
      <button
        onClick={() => setTab('single')}
        className={`px-3 py-1 rounded-md text-sm font-medium ${tab === 'single' ? 'bg-slate-800 text-white' : 'text-slate-600 bg-slate-50'}`}>
        新题理解解答
      </button>
      <button
        onClick={() => setTab('exam')}
        className={`px-3 py-1 rounded-md text-sm font-medium ${tab === 'exam' ? 'bg-slate-800 text-white' : 'text-slate-600 bg-slate-50'}`}>
        整卷智能批阅
      </button>
    </div>
  );
}

function TabPanels({ tab }: { tab: 'single' | 'exam' }) {
  return (
    <div>
      {tab === 'single' ? (
        <div className="bg-white p-6 rounded-xl shadow-none border border-gray-50">
          <h2 className="text-xl font-bold text-slate-800 mb-4 text-center">新题理解解答</h2>
          <FileUpload />
        </div>
      ) : (
        <div>
          <FullExamUploader />
        </div>
      )}
    </div>
  );
}
