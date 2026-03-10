'use client';

import { InlineMath, BlockMath } from 'react-katex';

interface LatexRendererProps {
    content: string;
    block?: boolean;
}

export function LatexRenderer({ content, block = false }: LatexRendererProps) {
    if (!content) return null;

    // If no $ delimiters are present, we look for common LaTeX commands
    if (!content.includes('$')) {
        const looksLikeLatex = /[\\]|[\^]|[_]|[{]|[}]/.test(content);
        if (looksLikeLatex) {
            return block ? (
                <div className="latex-block py-2 flex justify-center w-full overflow-x-auto">
                    <BlockMath math={content} />
                </div>
            ) : (
                <InlineMath math={content} />
            );
        }
        // Fallback for non-latex content
        return block ? <div className="py-2">{content}</div> : <span>{content}</span>;
    }

    const parts = content.split('$');
    const elements = parts.map((part, index) => {
        // Even index is text, Odd index is math
        if (index % 2 === 0) {
            // Handle newlines in text
            return part.split('\n').map((line, i, arr) => (
                <span key={`${index}-${i}`}>
                    {line}
                    {i < arr.length - 1 && <br />}
                </span>
            ));
        } else {
            return <InlineMath key={index} math={part} />;
        }
    });

    if (block) {
        return <div className="latex-block">{elements}</div>;
    }
    return <span>{elements}</span>;
}
