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

export interface DuplicateFoundResponse {
  status: 'duplicate_found';
  existing_exam_id: number;
  title: string;
}

export interface UploadTaskResponse {
  task_id: number;
  status: string;
}

export function useExamPolling() {
  const getErrorMessage = (value: unknown, fallback: string): string => {
    if (value instanceof Error && value.message) {
      return value.message;
    }
    return fallback;
  };

  const [questionFiles, setQuestionFiles] = useState<File[]>([]);
  const [answerFiles, setAnswerFiles] = useState<File[]>([]);
  const [combinedFiles, setCombinedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [statusResponse, setStatusResponse] = useState<ExamStatusResponse | null>(null);
  const [duplicateResponse, setDuplicateResponse] = useState<DuplicateFoundResponse | null>(null);
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
      } catch (err: unknown) {
        console.error("Polling error", err);
        setError(getErrorMessage(err, 'Error checking status'));
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
    examType: 'custom' | 'diagnostic' | 'midterm' | 'final' = 'custom',
    options?: {
      forceRegrade?: boolean;
      existingExamId?: number;
    }
  ) => {
    if (examMode === 'separated' && (selectedQuestionFiles.length === 0 || selectedAnswerFiles.length === 0)) return;
    if (examMode === 'combined' && selectedCombinedFiles.length === 0) return;
    
    setIsUploading(true);
    setError(null);
    setStatusResponse(null);
    setDuplicateResponse(null);
    
    const formData = new FormData();
    
    // Add exam_mode parameter
    formData.append('exam_mode', examMode);
    
    // Add exam_type parameter
    formData.append('exam_type', examType);

    if (options?.forceRegrade) {
      formData.append('force_regrade', 'true');
    }
    if (options?.existingExamId !== undefined) {
      formData.append('existing_exam_id', String(options.existingExamId));
    }
    
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

      if (data?.status === 'duplicate_found') {
        setDuplicateResponse(data as DuplicateFoundResponse);
        setIsUploading(false);
        return data as DuplicateFoundResponse;
      }

      const taskResponse = data as UploadTaskResponse;
      
      // Start polling for this new task
      startPolling(taskResponse.task_id);
      return taskResponse;
      
    } catch (err: unknown) {
      console.error("Upload error", err);
      setError(getErrorMessage(err, "Failed to upload files"));
      setIsUploading(false);
      return null;
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
    setStatusResponse(null);
    setDuplicateResponse(null);
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
    duplicateResponse,
    error,
    reset,
    setDuplicateResponse,
    setOnCompletionCallback  // 新增：设置完成回调的函数
  };
}
