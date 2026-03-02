'use client';

import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/utils/api';
import { Navbar } from '@/components/Navbar';
import { Loader2, Save, ChevronRight, ChevronDown } from 'lucide-react';

interface KnowledgeNode {
    id: number;
    name: string;
    path: string;
}

interface TreeNode extends KnowledgeNode {
    children: TreeNode[];
}

function buildTree(nodes: KnowledgeNode[]): TreeNode[] {
    const nodeMap = new Map<string, TreeNode>();
    const roots: TreeNode[] = [];

    const sortedNodes = [...nodes].sort((a, b) => a.path.length - b.path.length);

    sortedNodes.forEach(node => {
        const treeNode: TreeNode = { ...node, children: [] };
        nodeMap.set(node.path, treeNode);

        const parts = node.path.split('.');
        if (parts.length > 1) {
            const parentPath = parts.slice(0, -1).join('.');
            const parent = nodeMap.get(parentPath);
            if (parent) {
                parent.children.push(treeNode);
            } else {
                roots.push(treeNode);
            }
        } else {
            roots.push(treeNode);
        }
    });

    return roots;
}

const CheckboxTree = ({
    nodes,
    checkedPaths,
    onToggle
}: {
    nodes: TreeNode[],
    checkedPaths: Set<string>,
    onToggle: (path: string, checked: boolean, descendantPaths: string[]) => void
}) => {
    return (
        <div className="space-y-1">
            {nodes.map(node => (
                <TreeNodeComponent
                    key={node.path}
                    node={node}
                    checkedPaths={checkedPaths}
                    onToggle={onToggle}
                />
            ))}
        </div>
    );
};

const TreeNodeComponent = ({
    node,
    checkedPaths,
    onToggle
}: {
    node: TreeNode,
    checkedPaths: Set<string>,
    onToggle: (path: string, checked: boolean, descendantPaths: string[]) => void
}) => {
    const [expanded, setExpanded] = useState(false);

    // Check if fully checked
    const isChecked = checkedPaths.has(node.path);

    // Helper to get all descendant paths
    const getDescendantPaths = (n: TreeNode): string[] => {
        let paths: string[] = [];
        n.children.forEach(c => {
            paths.push(c.path);
            paths = paths.concat(getDescendantPaths(c));
        });
        return paths;
    };

    const handleCheck = (e: React.ChangeEvent<HTMLInputElement>) => {
        const checked = e.target.checked;
        const descendants = getDescendantPaths(node);
        onToggle(node.path, checked, descendants);
    };

    return (
        <div className="ml-4">
            <div className="flex items-center gap-2 py-1.5 hover:bg-gray-50 rounded px-2 -ml-2 transition-colors">
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="p-0.5 text-gray-500 hover:text-gray-900 rounded hover:bg-gray-200 transition-colors"
                >
                    {node.children.length > 0 ? (
                        expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                    ) : (
                        <div className="w-4 h-4" /> // placeholder
                    )}
                </button>
                <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={handleCheck}
                    className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 cursor-pointer"
                />
                <span className="text-sm font-medium text-gray-700 cursor-pointer select-none" onClick={() => setExpanded(!expanded)}>
                    {node.name}
                </span>
                <span className="text-xs text-gray-400 font-mono ml-2">
                    {node.path}
                </span>
            </div>

            {expanded && node.children.length > 0 && (
                <div className="border-l border-gray-200 ml-2 pl-2 mt-1">
                    <CheckboxTree
                        nodes={node.children}
                        checkedPaths={checkedPaths}
                        onToggle={onToggle}
                    />
                </div>
            )}
        </div>
    );
};

export default function ProgressSettings() {
    const [tree, setTree] = useState<TreeNode[]>([]);
    const [checkedPaths, setCheckedPaths] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                // 1. Fetch the full structure
                const nodesRes = await fetchWithAuth('/api/knowledge-nodes');
                if (!nodesRes.ok) throw new Error("Failed to load knowledge nodes");
                const nodesData: KnowledgeNode[] = await nodesRes.json();

                // 2. Fetch user's current learned paths
                const progRes = await fetchWithAuth('/api/progress');
                if (!progRes.ok) throw new Error("Failed to load user progress");
                const progData: string[] = await progRes.json();

                setTree(buildTree(nodesData));
                setCheckedPaths(new Set(progData));

            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    const handleToggle = (path: string, checked: boolean, descendantPaths: string[]) => {
        setCheckedPaths(prev => {
            const next = new Set(prev);
            if (checked) {
                next.add(path);
                descendantPaths.forEach(p => next.add(p));
            } else {
                next.delete(path);
                descendantPaths.forEach(p => next.delete(p));
                // Also optionally uncheck parents if a child is unchecked, but strict synchronization might be annoying.
                // We'll leave parents as-is, user can uncheck manually.
            }
            return next;
        });
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            // Note: DB logic saves descendants automatically anyway if a parent is passed,
            // but we send the exact checked paths strictly from UI state.
            const res = await fetchWithAuth('/api/progress/batch-update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paths: Array.from(checkedPaths) })
            });

            if (!res.ok) throw new Error("Failed to save progress");

            alert("学习进度已成功保存！(Progress Saved)");
        } catch (err: any) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <div className="flex-grow max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-6 flex justify-between items-end">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">学习进度管理 (Curriculum Progress)</h1>
                        <p className="mt-2 text-gray-600">
                            勾选您已经掌握的知识点。系统会自动将考题库、每日复习过滤到您已学的范围内。
                            (Select the knowledge nodes you have learned. The system will restrict practicing and reviewing to these areas.)
                        </p>
                    </div>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg shadow-sm">
                        {error}
                    </div>
                )}

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col h-[70vh]">
                    <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
                        <span className="text-sm font-semibold text-gray-700">知识图谱 (Knowledge Graph)</span>
                        <button
                            onClick={handleSave}
                            disabled={saving || loading}
                            className="bg-indigo-600 text-white px-5 py-2 rounded-lg font-medium hover:bg-indigo-700 transition shadow-sm disabled:opacity-50 flex items-center gap-2"
                        >
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            保存进度 (Save Progress)
                        </button>
                    </div>

                    <div className="p-6 overflow-y-auto flex-grow">
                        {loading ? (
                            <div className="flex justify-center items-center h-full">
                                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                            </div>
                        ) : tree.length > 0 ? (
                            <CheckboxTree
                                nodes={tree}
                                checkedPaths={checkedPaths}
                                onToggle={handleToggle}
                            />
                        ) : (
                            <div className="text-center text-gray-500 mt-10">No knowledge graph data found.</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
