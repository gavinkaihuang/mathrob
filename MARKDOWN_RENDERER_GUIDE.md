# MarkdownRenderer 使用指南

## 快速开始

### 导入组件
```tsx
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
```

### 基本使用
```tsx
const feedback = `# 解题思路
这道题需要使用勾股定理：
$$a^2 + b^2 = c^2$$

## 步骤：
1. 识别直角三角形
2. 应用勾股定理
3. 求解未知边`;

<MarkdownRenderer content={feedback} />
```

---

## 功能对照表

### 数学表达式

| 需求 | Markdown 写法 | 效果 |
|------|-------------|------|
| 行内公式 | `$\sqrt{2}$` | $\sqrt{2}$ |
| 块级公式 | `$$\frac{a}{b}$$` | $$\frac{a}{b}$$ |
| 分式 | `$\frac{1}{2}$` | $\frac{1}{2}$ |
| 根号 | `$\sqrt[3]{8}$` | $\sqrt[3]{8}$ |
| 求和 | `$$\sum_{i=1}^{n}$$` | 求和符号 |
| 积分 | `$$\int_0^\infty$$` | 积分符号 |

### 文本格式

| 需求 | Markdown 写法 | 显示效果 |
|------|-------------|---------|
| 粗体 | `**文本**` | **文本** |
| 斜体 | `*文本*` | *文本* |
| 删除线 | `~~文本~~` | ~~文本~~ |
| 行内代码 | `` `code` `` | `code` |

### 结构元素

#### 标题
```markdown
# 一级标题
## 二级标题
### 三级标题
```

#### 列表
```markdown
- 无序项 1
- 无序项 2

1. 有序项 1
2. 有序项 2
```

#### 表格
```markdown
| 列1 | 列2 |
|-----|-----|
| 数据1 | 数据2 |
```

#### 代码块
```markdown
\`\`\`python
def solve(n):
    return n * 2
\`\`\`
```

#### 引用
```markdown
> 这是一个重要提示
> 可以多行
```

---

## 实际示例

### 示例 1：批改反馈
```tsx
const feedback = `## 解答分析

### ✓ 正确部分
- 正确识别了三角形的类型
- 准确应用了正弦定理：$$\frac{a}{\sin A} = \frac{b}{\sin B}$$

### ✗ 错误部分
计算过程中：
\`\`\`
sin 60° = √3/2 ≈ 0.866
\`\`\`
这个值是正确的。

### 改进建议
在最后一步计算 $x = \frac{10 \times 0.866}{0.5} = 17.32$ 时，
需要检查数值精度。`;

<MarkdownRenderer content={feedback} />
```

### 示例 2：综合评价
```tsx
const overallFeedback = `# 试卷成绩分析

## 总体评分：85/100

### 知识掌握度

| 知识点 | 掌握度 | 备注 |
|--------|--------|------|
| 三角函数 | 90% | 很好 |
| 解析几何 | 75% | 需改进 |
| 微积分 | 85% | 良好 |

### 主要优点
1. 基础概念理解扎实
2. 计算过程清晰准确
3. 答题思路逻辑严密

### 改进方向

#### 1. 时间管理
需要提高做题速度，合理分配时间。

#### 2. 细节处理
在涉及小数或分数计算时要更加谨慎：
$$P(\text{精确}) = \frac{\text{正确答案数}}{\text{总题数}} \times 100\%$$

#### 3. 知识应用  
加强在实际问题中应用解析几何的能力。`;

<MarkdownRenderer content={overallFeedback} />
```

### 示例 3：个别题目反馈
```tsx
const problemFeedback = `## 第 3 题 - 不完全

你的答案虽然结果正确，但推导过程不完整。

### 完整解法

设二次函数为 $f(x) = ax^2 + bx + c$

给定条件：
- $f(0) = 2$，故 $c = 2$
- $f(1) = 4$，故 $a + b + 2 = 4$，即 $a + b = 2$
- $f(-1) = 3$，故 $a - b + 2 = 3$，即 $a - b = 1$

求解：
$$\begin{cases}
a + b = 2 \\
a - b = 1
\end{cases}$$

解得：$a = 1.5, b = 0.5$

因此：$$f(x) = 1.5x^2 + 0.5x + 2$$

### 你的不足
缺少上述的详细推导步骤。`;

<MarkdownRenderer content={problemFeedback} />
```

---

## 组件 Props

```tsx
interface MarkdownRendererProps {
  // 必需：Markdown 内容
  content: string;
  
  // 可选：额外的 CSS 类名
  className?: string;
}
```

### 常用 Props 组合

#### 紧凑显示（用于侧边栏）
```tsx
<MarkdownRenderer 
  content={feedback} 
  className="text-sm prose-sm max-w-md"
/>
```

#### 标准显示（用于主要内容区）
```tsx
<MarkdownRenderer 
  content={feedback} 
  className="prose-base max-w-3xl"
/>
```

#### 大号显示（用于突出展示）
```tsx
<MarkdownRenderer 
  content={feedback} 
  className="prose-lg max-w-4xl"
/>
```

---

## 集成到试卷详情页

### 更新考试历史页面
```tsx
import { MarkdownRenderer } from '@/components/MarkdownRenderer';

// 综合评价部分
<div className="mb-6">
  <h3 className="text-lg font-semibold mb-3">综合评价</h3>
  {exam.overall_feedback ? (
    <MarkdownRenderer content={exam.overall_feedback} />
  ) : (
    <div className="text-gray-500 text-sm">无综合评价</div>
  )}
</div>

// 每题反馈部分
<div className="border-l-4 border-indigo-400 bg-white rounded p-4">
  <div className="text-sm font-semibold text-indigo-600 mb-2">【AI 批改反馈】</div>
  {result.feedback ? (
    <MarkdownRenderer content={result.feedback} className="text-sm" />
  ) : (
    <div className="text-gray-500 text-sm">无反馈</div>
  )}
</div>
```

### 创建新的详情页面
```tsx
'use client';

import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import React, { useEffect, useState } from 'react';

interface ExamDetail {
  overall_feedback?: string;
  results?: Array<{ feedback?: string; }>;
}

export default function ExamDetailPage() {
  const [exam, setExam] = useState<ExamDetail | null>(null);

  return (
    <div>
      {/* 综合反馈 */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold mb-4">综合评价</h2>
        {exam?.overall_feedback && (
          <MarkdownRenderer content={exam.overall_feedback} />
        )}
      </section>

      {/* 逐题反馈 */}
      <section>
        <h2 className="text-2xl font-bold mb-4">逐题详情</h2>
        {exam?.results?.map((result, idx) => (
          <div key={idx} className="mb-6 border-l-4 border-blue-500 pl-4">
            <MarkdownRenderer content={result.feedback || ''} />
          </div>
        ))}
      </section>
    </div>
  );
}
```

---

## 常见问题

### Q: LaTeX 公式不显示怎么办？
**A**: 检查以下几点：
- 确保使用了正确的分隔符 `$...$`（行内）或 `$$...$$`（块级）
- 检查反斜杠转义：`\\` 而不是 `\`
- 在 TypeScript 模板字符串中使用反引号：`` `content` ``

### Q: 怎样显示特殊字符（如 `$` 或 `\`）？
**A**: 
- 显示 `$`：使用 `\$`
- 显示 `\`：使用 `\\`
- 示例：`` `$50` 显示为 \$50 ``

### Q: 可以自定义样式吗？
**A**: 可以，通过 `className` prop：
```tsx
<MarkdownRenderer 
  content={feedback}
  className="text-lg text-red-600 max-w-2xl"
/>
```

### Q: 怎样处理很长的反馈？
**A**: 组件自动处理长内容，添加 `max-w-*` 类来限制宽度：
```tsx
<MarkdownRenderer 
  content={longFeedback}
  className="prose-sm max-w-2xl"
/>
```

### Q: 支持哪些 Markdown 特性？
**A**: 完整支持 GitHub Flavored Markdown，包括：
- 表格
- 删除线
- 任务清单
- 自动link detection
- 代码块语言标记

---

## 最佳实践

### ✅ 推荐做法
```tsx
// 为每个反馈区域提供清晰的标题
<h2 className="font-bold mb-3">AI 建议</h2>
<MarkdownRenderer content={feedback} />

// 根据容器大小选择合适的 prose 大小
<MarkdownRenderer 
  content={feedback}
  className={isMobile ? 'prose-sm' : 'prose-base'}
/>

// 提供回退方案处理空反馈
{feedback ? (
  <MarkdownRenderer content={feedback} />
) : (
  <p className="text-gray-500">暂无建议</p>
)}
```

### ❌ 避免做法
```tsx
// 不要在公式中混用 $ 和 $$
"$\frac{a}{b}$$"  // 错误

// 不要忘记转义特殊字符
"价格: $100"  // 应该是 "价格: \$100"

// 不要在 Markdown 中直接混入 HTML（不支持）
"<strong>bold</strong>"  // 应该用 **bold**
```

---

## 文件清单

✅ 已创建：
- `frontend/components/MarkdownRenderer.tsx`
- `frontend/tailwind.config.ts`
- `frontend/app/exams/[id]/page.tsx`

✅ 已更新：
- `frontend/app/exams/history/page.tsx`
- `frontend/app/layout.tsx`（已有 KaTeX CSS）
- `frontend/package.json`（已添加依赖）

---

## 总结

`MarkdownRenderer` 组件提供了完整的 Markdown + LaTeX 渲染方案。

**核心优势**：
- 📐 完整的数学公式支持
- 📝 丰富的文本格式
- 🎨 优美的默认样式
- ⚡ 高性能的客户端渲染
- 📱 响应式设计

现在你可以在试卷档案库和详情页中看到格式精美的反馈！
