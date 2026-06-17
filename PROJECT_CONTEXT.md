# MathRob 项目上下文文档

> 自动生成于 2026-06-17，供 AI 协作开发时快速了解项目

## 项目概述

**MathRob** 是一个 AI 驱动的高中数学学习系统，面向上海高中数学考纲，核心功能包括：
- OCR 扫描识别数学题目
- AI 分析（Google Gemini Pro/Flash）提取 LaTeX、难度、知识点
- SM-2 间隔重复算法驱动的每日复习
- 整卷智能批阅与学情诊断
- 知识点掌握度加权评估

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端 | Python FastAPI | ≥0.115 |
| ORM | SQLAlchemy 2.x + Alembic | |
| 数据库 | PostgreSQL (NAS 外部) | |
| 前端 | Next.js (App Router) | 16.1.6 |
| UI | Tailwind CSS v4 + shadcn 风格 | |
| 数学渲染 | KaTeX + react-markdown + remark-math | |
| 图表 | Recharts | |
| 文件存储 | MinIO (S3 兼容) | |
| AI | Google Gemini (多模型/多 Token 轮换) | |
| 认证 | JWT (python-jose) + bcrypt | |

## 启动命令

```bash
# 后端 (从项目根目录)
source backend/venv/bin/activate && uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm run dev  # 端口 3006
```

## 环境变量

```
DATABASE_URL=postgresql://gavin:huang@192.168.44.130:5442/mathrob?sslmode=disable
NEXT_PUBLIC_API_URL=http://localhost:8000
S3_ENDPOINT_URL=http://192.168.44.130:3008
S3_ACCESS_KEY=admin
S3_SECRET_KEY=deve123loper
S3_BUCKET_NAME=mathrob
```

---

## 后端架构

### 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口，CORS，路由注册
│   ├── config.py             # S3 配置 (dataclass)
│   ├── database.py           # SQLAlchemy engine + session + retry
│   ├── models.py             # 25 个 ORM 模型 (311 行)
│   ├── auth_deps.py          # JWT 认证依赖 (get_current_user, get_current_active_admin)
│   ├── routers/
│   │   ├── api.py            # 主 API 路由 (3100+ 行，核心业务)
│   │   ├── auth.py           # /api/token 登录
│   │   ├── upload.py         # /api/upload 单题上传
│   │   ├── users.py          # /api/users CRUD
│   │   ├── settings.py       # /api/settings 模型/Token 管理
│   │   └── logs.py           # /api/logs 系统日志+操作日志
│   ├── services/
│   │   ├── ai_service.py     # Gemini 调用 + fallback + 日志 (884 行)
│   │   ├── upload_service.py # S3/MinIO 上传 + 预签名 URL
│   │   ├── auth_service.py   # JWT 创建/验证 + bcrypt
│   │   ├── token_manager.py  # Gemini API Key 轮换 + 冷却
│   │   ├── model_manager.py  # 按角色/试卷类型选模型
│   │   ├── srs_logic.py      # SM-2 间隔重复算法
│   │   ├── knowledge_mastery_service.py  # 加权掌握度计算
│   │   ├── report_service.py # 周报 PDF 生成 (ReportLab)
│   │   ├── taxonomy_service.py # 知识点大纲服务 (DB 查询构建树)
│   │   └── file_watcher.py   # Watchdog 文件监控
│   ├── api/v1/endpoints/
│   │   └── taxonomy.py       # 外部接口: /api/v1/taxonomy/tags + /tree
│   └── schemas/
│       └── taxonomy.py       # Taxonomy Pydantic 模型
├── alembic/                  # 数据库迁移
├── uploads/                  # 旧文件存储 (已迁移到 S3)
└── reference_docs/           # 考纲标准文档
```

### 数据库模型 (25 个)

**核心业务模型**:
- `User` - 用户 (含 is_admin)
- `Problem` - 题目 (图片/latex/AI分析/难度/知识点路径)
- `LearningRecord` - 学习记录 (SM-2 字段: ease_factor/interval/repetitions)
- `SolutionAttempt` - 解题尝试 (AI评分/反馈)
- `PracticeSession` / `PracticeProblem` - 练习会话与题目
- `ExamRecord` / `ExamProblemResult` - 试卷批阅记录
- `AssessmentSession` / `AssessmentProblem` - 诊断评测

**知识点模型**:
- `KnowledgeNode` - 知识点节点 (ltree path)
- `KnowledgePoint` - 旧知识点 (parent_id 层级)
- `UserKnowledgeMastery` - 用户知识点掌握度 (加权评分)
- `UserProgress` - 用户学习进度

**系统模型**:
- `GeminiToken` - API Key 管理 (冷却/错误计数)
- `ModelConfig` - 模型角色配置 (vision/routine_teaching/advanced_assessment/utility)
- `SystemLog` / `OperationLog` / `APICallLog` - 日志
- `DailyReview` / `WeeklyReport` - 每日复习/周报
- `ExamType` enum - 试卷类型 (custom/diagnostic/midterm/final)

### API 端点总览

**认证**: `POST /api/token`

**题目管理** (需认证):
- `GET /api/problems` - 题目列表
- `GET /api/problems/wrong` - 错题本 (分页)
- `GET /api/problems/{id}` - 题目详情
- `POST /api/problems/{id}/mastery` - 更新掌握度
- `POST /api/problems/{id}/review` - 提交复习
- `POST /api/problems/{id}/reanalyze` - 重新AI分析
- `POST /api/problems/{id}/similar` - 生成相似题
- `POST /api/problems/{id}/submit_solution` - 提交解答

**上传**:
- `POST /api/upload` - 单题上传 + AI 分析

**试卷批阅**:
- `POST /api/exams/upload_and_grade` - 整卷上传批阅
- `GET /api/exams/history` - 试卷历史
- `GET /api/exams/{exam_id}` - 试卷详情
- `GET /api/exams/task_status/{task_id}` - 异步任务状态

**复习系统**:
- `GET /api/daily-review` - 每日复习题
- `GET /api/reviews/today` / `history` - 复习记录
- `POST /api/practices/generate_daily` - 生成每日练习

**诊断评测**:
- `POST /api/assessment/generate_paper` - 生成诊断试卷
- `POST /api/assessment/generate_test` - 生成测试
- `POST /api/assessment/{session_id}/submit_full_paper` - 提交整卷
- `POST /api/assessment/{session_id}/finalize` - 完成评测

**管理**:
- `GET/POST/PUT/DELETE /api/users` - 用户 CRUD (管理员)
- `GET/POST /api/settings/models/config` - 模型配置
- `GET/POST/PUT/DELETE /api/settings/tokens` - Token 管理
- `GET /api/logs/system` / `/operations` - 日志查看
- `GET /api/progress` - 学习进度

**外部接口 (v1)**:
- `GET /api/v1/taxonomy/tags` - 扁平知识点标签
- `GET /api/v1/taxonomy/tree` - 知识点树

### 核心服务逻辑

**AI 服务** (`ai_service.py`):
- `call_gemini_with_fallback()` - 带 Token 轮换和重试的 Gemini 调用
- `analyze_image()` - 图片 -> LaTeX + 难度 + 知识点
- `analyze_solution()` - 解答评分
- `generate_similar_problem()` - 生成相似题
- `grade_full_paper()` - 整卷批阅 (多图 + 标准答案)
- 按 category (vision/teaching/utility) 选择模型

**Token 管理** (`token_manager.py`):
- Round-robin 轮换可用 Token
- 429 错误自动冷却 60 分钟
- DB 持久化状态

**模型选择** (`model_manager.py`):
- 按角色 (vision/routine_teaching/advanced_assessment/utility) 从 DB 读模型名
- 日常练习用 Flash，期中/期末用 Pro

**掌握度计算** (`knowledge_mastery_service.py`):
- 加权移动平均: `new_rating = (current * current_weight + new * exam_weight) / total_weight`
- 权重: custom=1.0, diagnostic=2.0, midterm=3.0, final=3.0

**SM-2 间隔重复** (`srs_logic.py`):
- 0分: 重置，ease -0.5
- 1分: interval x1.2, ease -0.2
- 2分: interval x ease_factor, ease +0.1

---

## 前端架构

### 目录结构

```
frontend/
├── app/
│   ├── layout.tsx            # 根布局 (AuthProvider + Navbar)
│   ├── page.tsx              # 首页 (仪表盘 + 快捷上传)
│   ├── login/page.tsx        # 登录页
│   ├── problems/[id]/        # 题目详情
│   ├── review/page.tsx       # 每日复习
│   ├── review-history/       # 复习历史
│   ├── history/page.tsx      # 题目历史
│   ├── exams/
│   │   ├── new/page.tsx      # 新建试卷批阅
│   │   ├── [id]/page.tsx     # 试卷详情 (MarkdownRenderer)
│   │   └── history/page.tsx  # 试卷历史
│   ├── assessment/[session_id]/  # 诊断评测
│   │   ├── page.tsx
│   │   ├── report/page.tsx
│   │   └── print/page.tsx
│   ├── reports/page.tsx      # 周报
│   ├── settings/
│   │   ├── page.tsx          # 模型设置
│   │   ├── tokens/page.tsx   # Token 管理
│   │   └── progress/page.tsx # 学习进度
│   ├── users/page.tsx        # 用户管理 (管理员)
│   └── syslogs/page.tsx      # 系统日志
├── components/
│   ├── Navbar.tsx            # 导航栏
│   ├── FileUpload.tsx        # 文件上传
│   ├── FullExamUploader.tsx  # 整卷上传
│   ├── MarkdownRenderer.tsx  # Markdown+LaTeX 渲染
│   ├── LatexRenderer.tsx     # LaTeX 渲染
│   ├── KnowledgeMasteryDashboard.tsx  # 知识掌握度仪表盘
│   ├── DailyReviewList.tsx   # 每日复习列表
│   ├── DiagnosticTestButton.tsx  # 诊断测试按钮
│   └── SystemErrorBanner.tsx # 系统错误提示
├── context/
│   └── AuthContext.tsx        # 认证上下文 (token/user/login/logout)
├── utils/
│   └── api.ts                # fetchWithAuth + resolveImageUrl
├── hooks/
│   └── useExamPolling.ts     # 试卷批阅轮询
└── lib/
    └── utils.ts              # 工具函数
```

### 前端关键依赖

- `next` 16.1.6 + `react` 19.2.3 (App Router)
- `tailwindcss` v4 + `@tailwindcss/typography`
- `react-markdown` + `remark-gfm` + `remark-math` + `rehype-katex`
- `katex` + `react-katex`
- `recharts` (图表)
- `framer-motion` (动画)
- `lucide-react` (图标)

### 前端认证流程

1. 登录 -> `POST /api/token` -> JWT 存 localStorage
2. `AuthProvider` 包裹整个应用，自动校验 token
3. `fetchWithAuth()` 自动注入 Authorization header
4. 未认证自动跳转 `/login`
5. 429/401/503 触发 `ai-system-error` 事件 -> `SystemErrorBanner`

---

## 已知设计决策 & 约定

1. **图片存储**: 已从本地 `backend/uploads/` 迁移到 MinIO (S3)，通过预签名 URL 访问
2. **知识点体系**: 使用 ltree path 格式 (如 `101.10101.1010101`)，存储在 `knowledge_nodes` 表
3. **AI 模型管理**: 通过 DB 的 `model_configs` 表动态配置，不依赖环境变量
4. **Token 池**: 多 Gemini API Key 轮换，429 自动冷却
5. **试卷类型权重**: 影响掌握度计算 (custom=1, diagnostic=2, midterm/final=3)
6. **CORS**: 当前 `allow_origins=["*"]`，开发环境配置
7. **JWT SECRET**: 硬编码默认值，生产环境需替换
8. **api.py 巨大**: 3100+ 行，包含几乎所有业务端点，后续可能需要拆分
9. **alembic**: 数据库迁移已配置
10. **端口**: 后端 8000，前端 3006

---

## 近期 Git 提交 (关键变更)

- `e5ae1cb` 添加知识图谱查询接口
- `f845cd0` 修复每日练习出题逻辑
- `1f6713e` 修复单题上传问题
- `c2308d9` 图片上传迁移到 NAS (S3)
- `479a96e` 试卷类型->不同模型+权重
- `969d162` 试卷/答题卡分开批阅+自动跳转+美化
