"use client";

import { useState, useEffect } from 'react';
import { AlertTriangle, X, Settings, ShieldAlert, WifiOff } from 'lucide-react';
import Link from 'next/link';

interface ErrorDetail {
    status: number;
    error_type?: string;
    message?: string;
    retry_seconds?: number;
}

export function SystemErrorBanner() {
    const [errorDetail, setErrorDetail] = useState<ErrorDetail | null>(null);

    useEffect(() => {
        const handleSystemError = (event: Event) => {
            const customEvent = event as CustomEvent<ErrorDetail>;
            setErrorDetail(customEvent.detail);
        };

        // Listen for the custom event dispatched by fetchWithAuth
        window.addEventListener('ai-system-error', handleSystemError);

        return () => {
            window.removeEventListener('ai-system-error', handleSystemError);
        };
    }, []);

    if (!errorDetail) return null;

    // Determine UI state based on error type
    let bgColor = "bg-red-500";
    let icon = <AlertTriangle className="w-5 h-5 flex-shrink-0" />;
    let title = "系统响应受限";
    let description = "AI 模型调用失败，请稍后重试。";

    if (errorDetail.status === 429 || errorDetail.error_type === 'rate_limit') {
        bgColor = "bg-red-500";
        title = "请求频率受限 (429)";
        description = errorDetail.retry_seconds
            ? `API 配额已抵达上限。请等待 ${errorDetail.retry_seconds} 秒后重试，或立即切换备用模型。`
            : "AI 模型请求过于频繁，已被触发限流机制。请暂停操作以避免 API 被长期封禁，或前往设置切换模型。";
        icon = <AlertTriangle className="w-5 h-5 flex-shrink-0" />;
    } else if (errorDetail.status === 401 || errorDetail.error_type === 'auth_error') {
        bgColor = "bg-orange-600";
        title = "开发者认证失败 (401)";
        description = "配置的 API Key 可能已经失效或被吊销。前往【系统设置】重新配置有效的认证令牌。";
        icon = <ShieldAlert className="w-5 h-5 flex-shrink-0" />;
    } else if (errorDetail.status === 503 || errorDetail.error_type === 'service_error') {
        bgColor = "bg-yellow-600";
        title = "云端服务不可用 (503)";
        description = "AI 云端节点当前出现大面积抖动或断连。请检查网络环境或在稍后进行重试。";
        icon = <WifiOff className="w-5 h-5 flex-shrink-0" />;
    }

    return (
        <div className={`${bgColor} w-full relative z-50 animate-in slide-in-from-top-4 fade-in duration-300`}>
            <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-3">
                <div className="flex items-center justify-between flex-wrap gap-2 text-white">
                    <div className="flex items-center gap-2 font-medium text-sm">
                        {icon}
                        <span>
                            <strong className="font-bold mr-1">{title}：</strong>
                            {description}
                        </span>
                    </div>
                    <div className="flex items-center gap-3">
                        <Link
                            href="/settings"
                            onClick={() => setErrorDetail(null)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-black/20 hover:bg-black/30 active:bg-black/40 rounded-md text-xs font-semibold transition-colors border border-white/20"
                        >
                            <Settings className="w-3.5 h-3.5" />
                            前往配置
                        </Link>
                        <button
                            onClick={() => setErrorDetail(null)}
                            className="p-1 hover:bg-black/20 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-white"
                            aria-label="Dismiss"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
