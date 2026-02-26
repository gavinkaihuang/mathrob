import { FileUpload } from '@/components/FileUpload';
import { DailyReviewList } from '@/components/DailyReviewList';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-2xl space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
            MathRob AI
          </h1>
          <p className="text-lg leading-8 text-gray-600">
            Upload your math problems. Let AI analyze, solve, and help you master them.
          </p>
        </div>

        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <FileUpload />
        </div>

        {/* Today's Tasks Section */}
        <DailyReviewList />
      </div>
    </main>
  );
}
