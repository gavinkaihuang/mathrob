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
    ChevronDown
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { SystemErrorBanner } from './SystemErrorBanner';

export function Navbar() {
    const [isReviewOpen, setIsReviewOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const pathname = usePathname();
    const { isAuthenticated, logout, isAdmin } = useAuth();

    const reviewLinks = [
        { href: '/review', label: '今日复习', icon: <BookOpen className="w-4 h-4" /> },
        { href: '/history', label: '错题本', icon: <History className="w-4 h-4" /> },
    ];

    const mainLinks = [
        { href: '/', label: '首页', icon: <Home className="w-4 h-4" /> },
        { href: '/reports', label: '周报', icon: <BarChart3 className="w-4 h-4" /> },
        { href: '/settings', label: '系统设置', icon: <Settings className="w-4 h-4" /> },
        { href: '/syslogs', label: '运行日志', icon: <Terminal className="w-4 h-4" /> },
    ];

    if (isAdmin) {
        mainLinks.push({ href: '/users', label: '用户管理', icon: <Users className="w-4 h-4" /> });
    }

    // Close dropdown on click outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsReviewOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Close dropdown on pathname change
    useEffect(() => {
        setIsReviewOpen(false);
    }, [pathname]);

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

                                {/* Review Library Dropdown */}
                                <div className="relative flex items-center" ref={dropdownRef}>
                                    <button
                                        onClick={() => setIsReviewOpen(!isReviewOpen)}
                                        className={`inline-flex items-center px-4 py-2 text-sm font-semibold transition-all duration-200 rounded-xl my-2 gap-2 ${pathname.startsWith('/review') || pathname.startsWith('/history') || pathname.startsWith('/problems')
                                            ? 'bg-indigo-50 text-indigo-600 shadow-sm shadow-indigo-100/50'
                                            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                                            }`}
                                    >
                                        <BookOpen className="w-4 h-4" />
                                        <span>复习题库</span>
                                        <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isReviewOpen ? 'rotate-180' : ''}`} />
                                    </button>

                                    {isReviewOpen && (
                                        <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                                            {reviewLinks.map((link) => {
                                                const isActive = pathname.startsWith(link.href) || (link.href === '/history' && pathname.startsWith('/problems'));
                                                return (
                                                    <Link
                                                        key={link.href}
                                                        href={link.href}
                                                        className={`flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors ${isActive
                                                            ? 'text-indigo-600 bg-indigo-50/50'
                                                            : 'text-gray-600 hover:bg-gray-50 hover:text-indigo-600'
                                                            }`}
                                                    >
                                                        {link.icon}
                                                        {link.label}
                                                    </Link>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>

                                {/* Main Links */}
                                {mainLinks.filter(l => l.href !== '/').map((link) => {
                                    const isActive = pathname.startsWith(link.href);
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
