'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { fetchWithAuth } from '@/utils/api';

interface FileUploadProps {
    onUploadSuccess?: (id: number) => void;
}

export function FileUpload({ onUploadSuccess }: FileUploadProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const router = useRouter();

    const handleFile = async (file: File) => {
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetchWithAuth(`/api/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();

            if (onUploadSuccess) {
                onUploadSuccess(data.id);
            } else {
                router.push(`/problems/${data.id}`);
            }
        } catch (error) {
            console.error(error);
            alert('Upload failed. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files?.[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            handleFile(e.target.files[0]);
        }
    };

    return (
        <div
            className={cn(
                "border-2 border-dashed rounded-xl p-10 transition-colors flex flex-col items-center justify-center cursor-pointer min-h-[300px]",
                isDragging ? "border-blue-500 bg-blue-50/50" : "border-gray-200 hover:border-gray-300 hover:bg-gray-50/50",
                isUploading && "opacity-50 pointer-events-none"
            )}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-upload')?.click()}
        >
            <input
                id="file-upload"
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleChange}
                disabled={isUploading}
            />

            {isUploading ? (
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                    <p className="text-lg font-medium text-gray-700">AI is thinking...</p>
                    <p className="text-sm text-gray-500">Extracting content and analyzing difficulty</p>
                </div>
            ) : (
                <div className="flex flex-col items-center gap-4">
                    <div className="p-4 bg-gray-100 rounded-full">
                        <Upload className="w-8 h-8 text-gray-500" />
                    </div>
                    <div className="text-center">
                        <p className="text-lg font-medium text-gray-700">
                            Click to upload or drag and drop
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                            Supports JPG, PNG (Max 10MB)
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
