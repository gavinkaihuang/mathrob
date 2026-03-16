import { FileUpload } from '@/components/FileUpload';
import KnowledgeMasteryDashboard from '@/components/KnowledgeMasteryDashboard';
import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center p-8 pb-20">
      <div className="w-full max-w-5xl space-y-12 mt-10">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            MathRob AI
          </h1>
          <p className="text-lg leading-8 text-gray-600">
            Upload your math problems. Let AI analyze, solve, and help you master them.
          </p>
        </div>

        {/* Global Dashboard */}
        <div className="w-full">
          <KnowledgeMasteryDashboard />
        </div>

        {/* Quick Upload Action */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 max-w-2xl mx-auto">
          <h2 className="text-xl font-bold text-slate-800 mb-4 text-center">新题目解析</h2>
          <FileUpload />
        </div>
      </div>
    </main>
  );
}
