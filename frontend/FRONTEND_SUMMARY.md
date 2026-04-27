# ReadMei 前端架构总结

## 技术栈

| 类别 | 选型 |
|------|------|
| 框架 | Vue 3 + Vite 8 |
| 语言 | TypeScript 6 |
| 状态管理 | Pinia 3 |
| 样式 | Tailwind CSS 4 |
| UI 组件 | Ant Design Vue 4 |
| PDF 渲染 | pdfjs-dist 5 |
| HTTP 请求 | Axios |
| 路由 | Vue Router 4 |

## 项目结构

```
frontend/src/
├── views/
│   └── WorkspaceView.vue           # 唯一页面，三栏工作台
├── components/
│   ├── catalog/
│   │   └── CatalogPanel.vue        # 左栏：文件目录树（支持拖拽/点击上传 PDF）
│   ├── pdf/
│   │   ├── PdfViewer.vue           # 中栏：PDF 渲染容器（加载/滚动/高亮）
│   │   ├── PdfPage.vue            # 单页渲染 + 文本选择层 + 翻译覆盖层
│   │   └── PdfToolbar.vue         # PDF 工具栏（翻页/缩放/高亮颜色/翻译开关）
│   ├── function/
│   │   └── FunctionPanel.vue       # 右栏：四个功能按钮 + 输出框
│   ├── analysis/
│   │   ├── CoreContribution.vue    # 结构化总结（创新点/章节总结/阅读推荐）
│   │   ├── ReferenceAnalysis.vue   # 引用文献分析（年份分布/来源类型/级别）
│   │   └── RelevancePanel.vue      # 契合度分析（评分/匹配话题/AI 建议）
│   ├── chat/
│   │   └── ChatPanel.vue           # 上下文答疑（对话模式，支持选中文字上下文）
│   └── common/
│       ├── AppHeader.vue           # 顶部导航栏（Logo/搜索/设置/用户）
│       └── SettingsModal.vue       # 设置弹窗（研究方向/关键词，localStorage 持久化）
├── stores/                         # Pinia 状态管理
│   ├── paper.ts                    # 论文状态（PDF/章节/高亮/总结/推荐/缩放/翻译模式）
│   ├── chat.ts                     # 对话状态（多会话/消息列表）
│   ├── translation.ts              # 翻译缓存（按论文+文本缓存，避免重复请求）
│   ├── user.ts                     # 用户信息（研究方向/关键词，持久化到 localStorage）
│   └── index.ts                    # 统一导出
├── types/                          # TypeScript 类型定义
│   ├── paper.ts                    # Paper, PaperSection, SectionSummary, Highlight, InnovationPoint 等
│   ├── chat.ts                     # ChatMessage, ChatContext, ChatSession
│   ├── translation.ts              # TranslationSegment, TranslationCache
│   ├── reference.ts                # Reference, ReferenceAnalysis, YearDistribution 等
│   └── index.ts                    # 统一导出 + RelevanceAnalysis, UserProfile
├── api/                            # 后端 API 请求封装
│   ├── client.ts                   # Axios 实例（baseURL: /api, 超时 120s）
│   ├── paper.ts                    # 所有论文相关 API 函数
│   └── index.ts                    # 统一导出
├── utils/
│   └── pdf.ts                      # PDF.js 工具（加载文档/渲染页面/获取文本/获取选中文字）
├── router/
│   └── index.ts                    # 路由配置（仅 / → WorkspaceView）
├── style.css                       # Tailwind CSS 主题变量 + 全局样式
├── main.ts                         # 应用入口（Pinia + Router + 挂载）
└── App.vue                         # 根组件（Header + RouterView）
```

## 页面布局

打开首页即为三栏并排工作台，位于 Header（56px 高）下方：

```
┌──────────────────────────────────────────────────────────┐
│  Header: Logo | 论文标题 | 搜索栏 | 设置 | 用户头像       │
├─────────┬─────────────────────────┬──────────────────────┤
│         │                         │  [总结][翻译][答疑][引用] │
│  目录    │                         │                      │
│  20%    │      PDF 展示页          │    功能输出框          │
│         │        45%              │      35%             │
│ 文件夹树 │                         │                      │
│ 拖拽上传 │   缩放/翻页/高亮/翻译    │  结果/对话/分析        │
│         │                         │                      │
├─────────┴─────────────────────────┴──────────────────────┤
```

- 左栏/右栏：可拖拽分隔条调整宽度，可折叠关闭（显示窄条 toggle）
- 中栏：不可关闭，自适应占满剩余空间
- 左栏支持拖拽 PDF 文件直接导入到文件夹

## 前端已定义的 API 接口（等待后端实现）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/papers/upload` | 上传 PDF 文件 |
| GET | `/api/papers/:id` | 获取论文信息 |
| GET | `/api/papers/:id/file` | 获取 PDF 文件流 |
| GET | `/api/papers/:id/sections` | 获取论文章节列表 |
| POST | `/api/papers/:id/translate` | 智能翻译（传入文本+页码） |
| POST | `/api/papers/:id/ask` | 上下文问答（传入问题+选中文本上下文） |
| POST | `/api/papers/:id/summarize` | 全文结构化总结 |
| GET | `/api/papers/:id/one-sentence` | 一句话总结 + 创新点提取 |
| POST | `/api/papers/:id/recommend` | 阅读推荐（传入阅读目的） |
| GET | `/api/papers/:id/references` | 引用文献分析 |
| POST | `/api/papers/:id/relevance` | 研究方向契合度分析 |

## 关键数据类型

```typescript
// 论文
interface Paper {
  id: string; title: string; authors: string[]; abstract: string;
  domain: string; uploadedAt: string; pageCount: number; fileName: string;
}

// 章节（含总结）
interface PaperSection {
  id: string; paperId: string; title: string; level: number;
  pageStart: number; pageEnd: number; content: string;
  summary?: { content: string; category: SectionCategory; keywords: string[] };
}
type SectionCategory = 'background' | 'methodology' | 'innovation' | 'experiment' | 'discussion' | 'conclusion' | 'other'

// 阅读目的
type ReadingPurpose = 'innovation' | 'background' | 'writing' | 'preprocessing' | 'visualization' | 'outlook'

// 引用分析
interface ReferenceAnalysis {
  totalCount: number; yearDistribution: {year:number;count:number}[];
  recentThreeYearRatio: number; recentTenYearRatio: number;
  sourceTypeDistribution: {type:string;count:number;ratio:number}[];
  topSources: {source:string;count:number;type:string;level?:string}[];
}

// 契合度
interface RelevanceAnalysis {
  score: number; matchedTopics: string[]; recommendation: string;
  readingValue: 'high' | 'medium' | 'low'; details: string;
}
```

## 开发命令

```bash
cd frontend
npm install        # 安装依赖
npm run dev        # 启动开发服务器（端口 3000，API 代理到 localhost:8000）
npm run build      # 类型检查 + 生产构建
```

## Vite 代理配置

开发模式下，所有 `/api` 请求自动代理到 `http://localhost:8000`，后端服务应在该端口启动。
