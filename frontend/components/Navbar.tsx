"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    LogOut,
    Home,
    BookOpen,
    History,
    BarChart3,
    Settings,
    Terminal,
    Users,
    Library
} from 'lucide-react';
import { SystemErrorBanner } from './SystemErrorBanner';

export function Navbar() {
    const pathname = usePathname();
    const { isAuthenticated, logout, isAdmin } = useAuth();

    const mainLinks = [
        { href: '/', label: '首页', icon: <Home className="w-4 h-4" /> },
        { href: '/history', label: '错题本', icon: <History className="w-4 h-4" /> },
        { href: '/exams/history', label: '试卷档案', icon: <BookOpen className="w-4 h-4" /> },
        { href: '/review', label: '今日复习', icon: <BookOpen className="w-4 h-4" /> },
        { href: '/review-history', label: '复习题库', icon: <Library className="w-4 h-4" /> },
        { href: '/reports', label: '周报', icon: <BarChart3 className="w-4 h-4" /> },
        { href: '/settings', label: '系统设置', icon: <Settings className="w-4 h-4" /> },
        { href: '/syslogs', label: '运行日志', icon: <Terminal className="w-4 h-4" /> },
    ];

    if (isAdmin) {
        mainLinks.push({ href: '/users', label: '用户管理', icon: <Users className="w-4 h-4" /> });
    }



    if (!isAuthenticated) return null; // Don't show navbar if not logged in (e.g. login page)

    return (
        <>
            <SystemErrorBanner />
            <nav className="bg-white border-b border-gray-200 sticky top-0 z-40">
                <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex">
                            <div className="flex-shrink-0 flex items-center">
                                <Link href="/" className="text-xl font-bold text-indigo-600 flex items-center gap-2">
                                    <img src="/logo.png" alt="Logo" className="w-8 h-8 rounded-lg shadow-sm" />
                                    <span>MathRob AI</span>
                                </Link>
                            </div>
                            <div className="hidden sm:ml-6 sm:flex sm:space-x-4">
                                {/* Home Link */}
                                <Link
                                    href="/"
                                    className={`inline-flex items-center px-4 py-2 text-sm font-semibold transition-all duration-200 rounded-xl my-2 ${pathname === '/'
                                        ? 'bg-indigo-50 text-indigo-600 shadow-sm shadow-indigo-100/50'
                                        : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                                        }`}
                                >
                                    <div className="flex items-center gap-2">
                                        <Home className="w-4 h-4" />
                                        <span>首页</span>
                                    </div>
                                </Link>

                                {/* Main Links */}
                                {mainLinks.filter(l => l.href !== '/').map((link) => {
                                    const isActive = 
                                        pathname === link.href || 
                                        pathname.startsWith(`${link.href}/`) ||
                                        (link.href === '/history' && pathname.startsWith('/problems'));
                                        
                                    return (
                                        <Link
                                            key={link.href}
                                            href={link.href}
                                            className={`inline-flex items-center px-4 py-2 text-sm font-semibold transition-all duration-200 rounded-xl my-2 ${isActive
                                                ? 'bg-indigo-50 text-indigo-600 shadow-sm shadow-indigo-100/50'
                                                : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                                                }`}
                                        >
                                            <div className="flex items-center gap-2">
                                                {link.icon}
                                                <span>{link.label}</span>
                                            </div>
                                        </Link>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="flex items-center">
                            <button
                                onClick={logout}
                                className="flex items-center gap-2 text-gray-500 hover:text-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                            >
                                <LogOut className="w-4 h-4" />
                                <span className="hidden sm:inline">Logout</span>
                            </button>
                        </div>
                    </div>
                </div>
            </nav>
        </>
    );
}
