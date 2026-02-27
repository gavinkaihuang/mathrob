"use client";

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

interface ModelConfig {
    MODEL_VISION_PRIMARY: string;
    MODEL_VISION_FALLBACK: string;
    MODEL_TEACHING_PRIMARY: string;
    MODEL_TEACHING_FALLBACK: string;
    MODEL_UTILITY_PRIMARY: string;
    MODEL_UTILITY_FALLBACK: string;
}

export default function SettingsPage() {
    const { isAuthenticated, isAdmin } = useAuth();
    const router = useRouter();
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [config, setConfig] = useState<ModelConfig>({
        MODEL_VISION_PRIMARY: '',
        MODEL_VISION_FALLBACK: '',
        MODEL_TEACHING_PRIMARY: '',
        MODEL_TEACHING_FALLBACK: '',
        MODEL_UTILITY_PRIMARY: '',
        MODEL_UTILITY_FALLBACK: ''
    });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/login');
            return;
        }
        if (!isAdmin) {
            router.push('/'); // Redirect non-admins
            return;
        }

        const fetchSettings = async () => {
            try {
                const [modelsRes, configRes] = await Promise.all([
                    fetch('http://localhost:8000/api/settings/models/available'),
                    fetch('http://localhost:8000/api/settings/models/config')
                ]);

                if (modelsRes.ok && configRes.ok) {
                    const modelsData = await modelsRes.json();
                    const configData = await configRes.json();
                    setAvailableModels(modelsData.models);
                    setConfig(configData);
                } else {
                    console.error('Failed to fetch settings');
                }
            } catch (error) {
                console.error('Error fetching settings:', error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchSettings();
    }, [isAuthenticated, isAdmin, router]);

    const handleSelectChange = (key: keyof ModelConfig, value: string) => {
        setConfig(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        setIsSaving(true);
        setSaveMessage(null);
        try {
            const response = await fetch('http://localhost:8000/api/settings/models/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                setSaveMessage({ type: 'success', text: '保存成功 / Saved successfully!' });
                setTimeout(() => setSaveMessage(null), 3000);
            } else {
                throw new Error('Save failed');
            }
        } catch (error) {
            console.error('Error saving config:', error);
            setSaveMessage({ type: 'error', text: '保存失败 / Failed to save.' });
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) return <div className="p-8 text-center text-gray-500">Loading settings...</div>;
    if (!isAdmin) return null; // Fallback in case redirect takes a moment

    const categories = [
        {
            title: '扫描识别模型 (Vision)',
            desc: '用于图像理解和题目提取',
            primaryKey: 'MODEL_VISION_PRIMARY' as keyof ModelConfig,
            fallbackKey: 'MODEL_VISION_FALLBACK' as keyof ModelConfig
        },
        {
            title: '深度教学模型 (Teaching)',
            desc: '用于作业批改和详细步骤推理',
            primaryKey: 'MODEL_TEACHING_PRIMARY' as keyof ModelConfig,
            fallbackKey: 'MODEL_TEACHING_FALLBACK' as keyof ModelConfig
        },
        {
            title: '数据处理模型 (Utility)',
            desc: '用于生成相似题目等常规处理',
            primaryKey: 'MODEL_UTILITY_PRIMARY' as keyof ModelConfig,
            fallbackKey: 'MODEL_UTILITY_FALLBACK' as keyof ModelConfig
        }
    ];

    return (
        <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">系统设置 (System Settings)</h1>
            <p className="text-gray-500 mb-8">在这里配置系统运行所需的各种基础参数，例如大语言模型选择等。</p>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="p-6 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                    <div>
                        <h2 className="text-xl font-semibold text-gray-800">Gemini 模型配置</h2>
                        <p className="text-sm text-gray-500 mt-1">为主力和备用情况选择合适的 API 模型</p>
                    </div>
                </div>

                <div className="p-6 space-y-8">
                    {categories.map((cat, idx) => (
                        <div key={idx} className="bg-gray-50 p-5 rounded-lg border border-gray-100">
                            <h3 className="text-lg font-medium text-gray-900">{cat.title}</h3>
                            <p className="text-sm text-gray-500 mb-4">{cat.desc}</p>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">主模型 (Primary Model)</label>
                                    <select
                                        value={config[cat.primaryKey] || ''}
                                        onChange={(e) => handleSelectChange(cat.primaryKey, e.target.value)}
                                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md shadow-sm border bg-white"
                                    >
                                        <option value="" disabled>--- 请选择 / Select ---</option>
                                        {availableModels.map(m => (
                                            <option key={m} value={m}>{m}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">备用模型 (Fallback Model)</label>
                                    <select
                                        value={config[cat.fallbackKey] || ''}
                                        onChange={(e) => handleSelectChange(cat.fallbackKey, e.target.value)}
                                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md shadow-sm border bg-white"
                                    >
                                        <option value="" disabled>--- 请选择 / Select ---</option>
                                        {availableModels.map(m => (
                                            <option key={m} value={m}>{m}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="p-6 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
                    <div>
                        {saveMessage && (
                            <span className={`text-sm ${saveMessage.type === 'success' ? 'text-green-600' : 'text-red-600'} font-medium`}>
                                {saveMessage.text}
                            </span>
                        )}
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className={`inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${isSaving ? 'opacity-70 cursor-not-allowed' : ''}`}
                    >
                        {isSaving ? '保存中 / Saving...' : '保存更改 / Save Changes'}
                    </button>
                </div>
            </div>
        </div>
    );
}
