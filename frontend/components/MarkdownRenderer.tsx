'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm sm:prose-base prose-blue max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Custom heading styles
          h1: ({ node, ...props }) => (
            <h1 className="text-2xl font-bold mt-6 mb-4 text-slate-800" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xl font-semibold mt-5 mb-3 text-slate-700" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-lg font-semibold mt-4 mb-2 text-slate-700" {...props} />
          ),
          // Custom list styles
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-inside my-3 space-y-1" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-inside my-3 space-y-1" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="text-slate-700" {...props} />
          ),
          // Custom table styles
          table: ({ node, ...props }) => (
            <table className="min-w-full border-collapse border border-slate-300 my-4" {...props} />
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-slate-100" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="border border-slate-300 px-4 py-2 text-left text-slate-700 font-semibold" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="border border-slate-300 px-4 py-2 text-slate-700" {...props} />
          ),
          // Custom code styles
          code: (props: any) => {
            const { node, inline, ...rest } = props;
            if (inline) {
              return (
                <code className="bg-slate-100 text-red-600 px-2 py-1 rounded text-sm font-mono" {...rest} />
              );
            }
            return (
              <code className="block bg-slate-900 text-slate-100 p-4 rounded my-3 overflow-x-auto font-mono text-sm" {...rest} />
            );
          },
          // Custom paragraph styles
          p: ({ node, ...props }) => (
            <p className="text-slate-700 leading-relaxed my-3" {...props} />
          ),
          // Custom blockquote styles
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-4 border-indigo-500 pl-4 py-2 my-3 bg-indigo-50 text-slate-700 italic" {...props} />
          ),
          // Custom link styles
          a: ({ node, ...props }) => (
            <a className="text-indigo-600 underline hover:text-indigo-800" {...props} />
          ),
          // Custom horizontal rule
          hr: ({ node, ...props }) => (
            <hr className="my-6 border-t-2 border-slate-300" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
