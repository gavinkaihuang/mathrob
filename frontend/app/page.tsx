import { FileUpload } from '@/components/FileUpload';
import KnowledgeMasteryDashboard from '@/components/KnowledgeMasteryDashboard';
import DiagnosticTestButton from '@/components/DiagnosticTestButton';
import FullExamUploader from '@/components/FullExamUploader';
import Link from 'next/link';

export default function Home() {
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
            {/* Quick Upload Action */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 w-full flex flex-col">
              <h2 className="text-xl font-bold text-slate-800 mb-4 text-center">新题理解解答</h2>
              <FileUpload />
            </div>

            {/* Full Exam Upload Action */}
            <FullExamUploader />

            {/* Diagnostic Assessment Button */}
            <DiagnosticTestButton />
          </div>

        </div>
      </div>
    </main>
  );
}
