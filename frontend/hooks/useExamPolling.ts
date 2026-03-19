'use client';
import { useState, useCallback, useRef } from 'react';
import { fetchWithAuth } from '@/utils/api';

export interface ExamProblemResult {
  problem_number: string;
  score: number;
  max_score: number;
  knowledge_tag: string;
  feedback: string;
}

export interface ExamStatusResponse {
  exam_id: number;  // 新增：试卷 ID
  id: number;
  status: 'processing' | 'completed' | 'failed';
  total_score?: number;
  overall_evaluation?: string;
  created_at?: string;
  results: ExamProblemResult[];
}

export function useExamPolling() {
  const [questionFiles, setQuestionFiles] = useState<File[]>([]);
  const [answerFiles, setAnswerFiles] = useState<File[]>([]);
  const [combinedFiles, setCombinedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [taskId, setTaskId] = useState<number | null>(null);
  const [statusResponse, setStatusResponse] = useState<ExamStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onCompletionCallback, setOnCompletionCallback] = useState<((examId: number) => void) | null>(null);
  
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const startPolling = useCallback((id: number) => {
    // Clear any existing interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    const poll = async () => {
      try {
        const res = await fetchWithAuth(`/api/exams/task_status/${id}`);
        if (!res.ok) throw new Error('Failed to fetch status');
        
        const data: ExamStatusResponse = await res.json();
        setStatusResponse(data);
        
        // 新增：当完成时，调用回调函数
        if (data.status === 'completed' && onCompletionCallback) {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsUploading(false);
          // 延迟 100ms 确保状态更新完成后再回调
          setTimeout(() => {
            onCompletionCallback(data.exam_id);
          }, 100);
        } else if (data.status === 'failed') {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsUploading(false);
        }
      } catch (err: any) {
        console.error("Polling error", err);
        setError(err.message || 'Error checking status');
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        setIsUploading(false);
      }
    };

    // Poll every 3 seconds
    pollingIntervalRef.current = setInterval(poll, 3000);
    poll(); // immediate first call
  }, [onCompletionCallback]);

  const uploadFiles = async (
    selectedQuestionFiles: File[], 
    selectedAnswerFiles: File[], 
    examMode: 'separated' | 'combined' = 'separated',
    selectedCombinedFiles: File[] = [],
    examType: 'custom' | 'diagnostic' | 'midterm' | 'final' = 'custom'
  ) => {
    if (examMode === 'separated' && (selectedQuestionFiles.length === 0 || selectedAnswerFiles.length === 0)) return;
    if (examMode === 'combined' && selectedCombinedFiles.length === 0) return;
    
    setIsUploading(true);
    setError(null);
    setStatusResponse(null);
    setTaskId(null);
    
    const formData = new FormData();
    
    // Add exam_mode parameter
    formData.append('exam_mode', examMode);
    
    // Add exam_type parameter
    formData.append('exam_type', examType);
    
    if (examMode === 'separated') {
      // Add question images
      selectedQuestionFiles.forEach(file => {
        formData.append('question_images', file);
      });
      
      // Add answer images
      selectedAnswerFiles.forEach(file => {
        formData.append('answer_images', file);
      });
    } else {
      // Combined mode: all images go into combined_images
      selectedCombinedFiles.forEach(file => {
        formData.append('combined_images', file);
      });
    }

    try {
      const res = await fetchWithAuth('/api/exams/upload_and_grade', {
        method: 'POST',
        // Omit Content-Type so browser sets boundary for multipart/form-data
        body: formData,
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }
      
      const data = await res.json();
      setTaskId(data.task_id);
      
      // Start polling for this new task
      startPolling(data.task_id);
      
    } catch (err: any) {
      console.error("Upload error", err);
      setError(err.message || "Failed to upload files");
      setIsUploading(false);
    }
  };

  const handleQuestionFilesChange = (newFiles: File[]) => {
    setQuestionFiles(newFiles);
  };

  const handleAnswerFilesChange = (newFiles: File[]) => {
    setAnswerFiles(newFiles);
  };

  const handleCombinedFilesChange = (newFiles: File[]) => {
    setCombinedFiles(newFiles);
  };
  
  const reset = () => {
    setQuestionFiles([]);
    setAnswerFiles([]);
    setCombinedFiles([]);
    setIsUploading(false);
    setTaskId(null);
    setStatusResponse(null);
    setError(null);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
  };

  return {
    questionFiles,
    answerFiles,
    combinedFiles,
    handleQuestionFilesChange,
    handleAnswerFilesChange,
    handleCombinedFilesChange,
    uploadFiles,
    isUploading,
    statusResponse,
    error,
    reset,
    setOnCompletionCallback  // 新增：设置完成回调的函数
  };
}
