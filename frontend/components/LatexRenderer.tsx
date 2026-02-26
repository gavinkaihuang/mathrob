'use client';

import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

interface LatexRendererProps {
    content: string;
    block?: boolean;
}

export function LatexRenderer({ content, block = false }: LatexRendererProps) {
    if (!content) return null;

    // Split by $ delimiter to handle mixed text and inline math
    // Example: "Let $x$ be..." -> ["Let ", "x", " be..."]
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
