"use client";

import React, { useMemo } from 'react';
import DiagnosticTestButton from './DiagnosticTestButton';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend
} from 'recharts';

interface KnowledgeData {
  subject: string;
  aiScore: number;
  selfScore: number;
  comprehensive: number;
}

interface KnowledgeMasteryDashboardProps {
  data?: KnowledgeData[];
}

export default function KnowledgeMasteryDashboard({ data }: KnowledgeMasteryDashboardProps) {
  // Use mock data if no data provided
  const dashboardData = data || [
    { subject: "对数运算", aiScore: 85, selfScore: 90, comprehensive: 87 },
    { subject: "二次函数", aiScore: 60, selfScore: 85, comprehensive: 70 },
    { subject: "圆锥曲线", aiScore: 40, selfScore: 30, comprehensive: 36 },
    { subject: "立体几何", aiScore: 95, selfScore: 90, comprehensive: 93 },
    { subject: "导数应用", aiScore: 55, selfScore: 50, comprehensive: 53 }
  ];

  // Get lowest comprehensive scores
  const weaknesses = useMemo(() => {
    return [...dashboardData]
      .sort((a, b) => a.comprehensive - b.comprehensive)
      .slice(0, 3);
  }, [dashboardData]);

  const getProgressBarColor = (score: number) => {
    if (score < 60) return "bg-rose-500";
    if (score <= 80) return "bg-amber-400";
    return "bg-emerald-500";
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 md:p-8 w-full flex flex-col md:flex-row gap-8">
      {/* Overview Section - Core Radar Chart */}
      <div className="flex-1 min-w-[300px]">
        <h3 className="text-xl font-black text-slate-800 mb-6 flex items-center gap-2">
          <span className="text-indigo-600">🕸️</span> 主客观掌握度对比
        </h3>
        <p className="text-xs font-medium text-slate-500 mb-2">
          清晰识别“认知盲区”。当自评区（紫）完全覆盖 AI区（蓝）但出现巨大断层时，意味着高估了自身实力。
        </p>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={dashboardData}>
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis 
                dataKey="subject" 
                tick={{ fill: '#475569', fontSize: 13, fontWeight: 600 }} 
              />
              <PolarRadiusAxis 
                angle={30} 
                domain={[0, 100]} 
                tick={{ fill: '#94a3b8', fontSize: 11 }} 
              />
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }}
                itemStyle={{ fontWeight: 'bold' }}
              />
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                iconType="circle"
              />
              {/* AI Objective Score */}
              <Radar
                name="AI 客观评分"
                dataKey="aiScore"
                stroke="#3b82f6"
                fill="#bfdbfe"
                fillOpacity={0.6}
              />
              {/* User Subjective Score */}
              <Radar
                name="主观自评分"
                dataKey="selfScore"
                stroke="#8b5cf6"
                fill="#ddd6fe"
                fillOpacity={0.6}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Auxiliary View - Weaknesses */}
      <div className="w-full md:w-80 flex flex-col pt-2 md:pt-0">
        <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
          <span className="text-rose-500">🎯</span> 重点突破领域
        </h3>
        <div className="space-y-6 flex-1">
          {weaknesses.map((item, index) => (
            <div key={item.subject} className="flex flex-col gap-2">
              <div className="flex justify-between items-end">
                <span className="text-sm font-bold text-slate-700">{index + 1}. {item.subject}</span>
                <span className={`text-sm font-black ${item.comprehensive < 60 ? 'text-rose-600' : 'text-amber-600'}`}>
                  {item.comprehensive} 分
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-2.5 rounded-full ${getProgressBarColor(item.comprehensive)} transition-all duration-1000 ease-out`}
                  style={{ width: `${item.comprehensive}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-8 bg-indigo-50 rounded-xl p-4 border border-indigo-100 text-sm">
          <p className="text-indigo-800 font-medium">
            💡 <strong>学习规划建议:</strong>
            <br />
            明天的「今日复习」将优先为您推送以上领域的专项练习。
          </p>
        </div>
        <div className="mt-4">
          <DiagnosticTestButton />
        </div>

      </div>
    </div>
  );
}
