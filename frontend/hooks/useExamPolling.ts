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
  id: number;
  status: 'processing' | 'completed' | 'failed';
  total_score?: number;
  overall_evaluation?: string;
  created_at?: string;
  results: ExamProblemResult[];
}

export function useExamPolling() {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [taskId, setTaskId] = useState<number | null>(null);
  const [statusResponse, setStatusResponse] = useState<ExamStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  
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
        
        if (data.status === 'completed' || data.status === 'failed') {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsUploading(false); // Done
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
  }, []);

  const uploadFiles = async (selectedFiles: File[]) => {
    if (selectedFiles.length === 0) return;
    
    setIsUploading(true);
    setError(null);
    setStatusResponse(null);
    setTaskId(null);
    
    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });

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

  const handleFilesChange = (newFiles: File[]) => {
    setFiles(newFiles);
  };
  
  const reset = () => {
    setFiles([]);
    setIsUploading(false);
    setTaskId(null);
    setStatusResponse(null);
    setError(null);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
  };

  return {
    files,
    handleFilesChange,
    uploadFiles,
    isUploading,
    statusResponse,
    error,
    reset
  };
}
