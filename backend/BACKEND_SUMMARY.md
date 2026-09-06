# ReadMei 后端架构总结

## 一、技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI 0.115 | 异步 REST API 服务 |
| 运行时 | Uvicorn | ASGI 服务器 |
| 关系数据库 | PostgreSQL + SQLAlchemy 2.0 (async) + asyncpg | 论文元数据、章节、引用持久化 |
| 向量数据库 | Milvus 2.5 (pymilvus) | 论文文本切片 Embedding 存储与检索 (RAG) |
| 缓存 | Redis 5.x (redis-py async) | 翻译/总结/分析结果缓存 |
| PDF 解析 | PyMuPDF (fitz) | 提取全文、章节结构、引用列表 |
| LLM/Embedding | DeepSeek API (OpenAI 兼容) + LangChain（答疑 RAG） | deepseek-chat / embedding；`rag_qa.py` |
| 数据校验 | Pydantic 2.10 + pydantic-settings | 请求/响应模型 + 环境变量管理 |

## 二、项目目录结构

```
backend/
├── requirements.txt              # Python 依赖清单
├── .env.example                  # 环境变量模板
├── uploads/                      # PDF 文件存储目录
└── app/
    ├── __init__.py
    ├── main.py                   # FastAPI 入口 (CORS / 生命周期 / 路由注册)
    ├── core/
    │   └── config.py             # Settings: 从 .env 加载所有配置项
    ├── db/
    │   ├── postgres.py           # SQLAlchemy async engine + session + Base
    │   ├── milvus.py             # Milvus 连接 / Collection 管理 / CRUD
    │   └── redis.py              # Redis 异步连接 / cache_get / cache_set
    ├── models/
    │   └── paper.py              # ORM 模型: Paper, PaperSection, Reference
    ├── schemas/
    │   └── paper.py              # Pydantic 模型: 请求体 / 响应体
├── services/
│   ├── pdf_parser.py         # PDF 解析: 标题提取 / 章节识别 / 引用抽取 / 文本切片
│   ├── llm_service.py        # LLM 服务: 翻译 / 总结 / 推荐 / 引用分析 / 契合度等
│   ├── rag_qa.py             # 上下文答疑: LangChain Retriever + Chat 链
│   └── baidu_translate.py    # 百度翻译
    └── api/
        ├── papers.py             # 论文 CRUD 端点
        ├── ai.py                 # AI 功能端点 (翻译/问答/总结/推荐)
        └── analysis.py           # 分析端点 (引用文献分析/契合度分析)
```

## 三、数据模型

### 3.1 PostgreSQL ORM (SQLAlchemy)

#### `papers` 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 自动生成 |
| title | VARCHAR(512) | 论文标题 (PyMuPDF 提取) |
| authors | TEXT | 作者 |
| domain | VARCHAR(128) | 论文领域 |
| file_path | VARCHAR(1024) | PDF 文件存储路径 |
| page_count | INT | 页数 |
| one_sentence_summary | TEXT | 一句话总结 (AI 生成) |
| innovation_points | TEXT | 创新点 (AI 生成) |
| metadata_json | JSONB | 扩展元数据 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

#### `paper_sections` 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 自动生成 |
| paper_id | UUID (FK → papers) | 所属论文 |
| idx | INT | 章节序号 |
| title | VARCHAR(512) | 章节标题 |
| content | TEXT | 章节正文 |
| level | INT | 标题层级 (1=一级, 2=二级) |
| page_start / page_end | INT | 起止页码 |
| category | VARCHAR(64) | 分类: 科普/方法论/创新点/背景/实验/结论 |
| summary | TEXT | 章节摘要 (AI 生成) |

#### `references` 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 自动生成 |
| paper_id | UUID (FK → papers) | 所属论文 |
| idx | INT | 引用序号 |
| raw_text | TEXT | 原始引用文本 |
| title / authors | TEXT | 解析后的标题/作者 |
| year | INT | 发表年份 |
| venue | VARCHAR(512) | 期刊/会议名 |
| venue_type | VARCHAR(64) | journal / conference / preprint / book / other |
| venue_level | VARCHAR(64) | CCF-A/B/C, SCI-Q1~Q4, EI, other, unknown |

### 3.2 Milvus 向量集合

**Collection: `paper_chunks`**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT64 (PK, auto) | 自增主键 |
| paper_id | VARCHAR(64) | 所属论文 ID |
| section_idx | INT32 | 所属章节序号 |
| chunk_text | VARCHAR(65535) | 文本片段 |
| embedding | FLOAT_VECTOR(1536) | DeepSeek Embedding 向量 |

- 索引: IVF_FLAT, metric = COSINE, nlist = 128
- 查询时 nprobe = 16

### 3.3 Redis 缓存

| Key 模式 | TTL | 内容 |
|----------|-----|------|
| `translate:{paper_id}:{hash}` | 2h | 翻译结果 |
| `summarize:{paper_id}` | 1h | 结构化总结 |
| `ref_analysis:{paper_id}` | 1h | 引用分析 |
| `relevance:{paper_id}:{hash}` | 30min | 契合度分析 |

## 四、API 端点一览

所有端点统一挂载在 `/api/papers` 前缀下，与前端 Axios `baseURL: '/api'` 对齐。

### 4.1 论文管理 (papers.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/papers/upload` | 上传 PDF → 解析 → 存库 → 建向量索引 |
| `GET` | `/api/papers/` | 获取论文列表 (按时间倒序) |
| `GET` | `/api/papers/{paper_id}` | 获取论文详情 |
| `GET` | `/api/papers/{paper_id}/file` | 下载原始 PDF 文件 |
| `GET` | `/api/papers/{paper_id}/sections` | 获取章节列表 |
| `GET` | `/api/papers/{paper_id}/references` | 获取引用列表 (原始) |
| `DELETE` | `/api/papers/{paper_id}` | 删除论文 (同时清理文件和向量) |

### 4.2 AI 功能 (ai.py)

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| `POST` | `/{paper_id}/translate` | `{text, page_number?, domain?}` | 领域智能翻译 |
| `POST` | `/{paper_id}/ask` | `{question, context?}` | 上下文问答 (RAG: 向量检索+LLM) |
| `POST` | `/{paper_id}/summarize` | 无 body | 结构化总结 (逐章分析+全文一句话) |
| `GET` | `/{paper_id}/one-sentence` | — | 获取一句话总结 + 创新点 |
| `POST` | `/{paper_id}/recommend` | `{purpose}` | 阅读推荐 (根据目的推荐章节) |

**阅读目的 (purpose) 可选值:**
- `innovation` — 寻找创新点灵感
- `background` — 了解研究背景
- `writing` — 学习写作方法
- `preprocessing` — 学习预处理方法
- `visualization` — 学习画图技巧
- `conclusion` — 了解总结展望

### 4.3 分析功能 (analysis.py)

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| `GET` | `/{paper_id}/references` | — | 引用文献分析 (年份/来源/级别分布) |
| `POST` | `/{paper_id}/relevance` | `{research_direction, keywords[]}` | 研究方向契合度分析 (0-100评分) |

## 五、核心服务层

### 5.1 PDF 解析服务 (`pdf_parser.py`)

- **标题提取**: 分析首页文本块的字号，取最大字号文本作为标题
- **章节识别**: 双策略 — ① 正则匹配学术标准标题格式 (如 "1. Introduction") ② 检测加粗+大字号文本
- **引用抽取**: 从 References 节用 `[n]` 格式正则切分，自动提取年份
- **文本切片**: 512 词/片段，64 词重叠，用于生成 Embedding

### 5.2 LLM 服务 (`llm_service.py`)

通过 OpenAI 兼容客户端调用 DeepSeek API，提供以下功能:

| 函数 | 用途 | temperature |
|------|------|-------------|
| `translate_text_llm()` | 领域感知翻译，保留术语 | 0.1 |
| `answer_question()` | 委托 `rag_qa.answer_from_chunks`（LangChain） | 0.2 |
| `summarize_section()` | 段落分析 → JSON {summary, category} | 0.1 |
| `summarize_outline_chapter()` | 书签章节总结（纯文本） | 0.25 |
| `one_sentence_summary()` | 全文总结 → JSON {one_sentence, innovation_points} | 0.1 |
| `recommend_sections()` | 根据阅读目的推荐章节 | 0.2 |
| `analyze_references()` | 解析引用元数据 (标题/年份/来源/级别) | 0.0 |
| `analyze_relevance()` | 论文-方向契合度评分 | 0.1 |
| `get_embeddings()` | 批量文本向量化 | — |

### 5.3 上下文答疑 RAG (`rag_qa.py`)

基于 **LangChain** 的答疑链路（API 契约仍为 `AskResponse`）:

| 组件 | 说明 |
|------|------|
| `PaperMilvusRetriever` | 自定义 Retriever：选中文本优先 + `get_embedding` + `search_chunks`；无命中则用段落降级 |
| `ask_with_langchain` | 检索 → Prompt → `ChatOpenAI`(DeepSeek) → `StrOutputParser` |
| `answer_from_chunks` | 仅生成侧，复用同一 Prompt 链 |
| `RAG_TOP_K` / `settings.rag_top_k` | Milvus 检索条数，默认 5 |

向量写入与检索入口仍为章程约定的 `app.db.milvus`；LangChain 只负责编排与生成。

## 六、数据流

### 6.1 上传论文流程

```
用户上传 PDF
    ↓
FastAPI 接收文件 → 保存到 uploads/{paper_id}/
    ↓
PyMuPDF 解析 → 提取标题/章节/引用
    ↓
存入 PostgreSQL (papers + paper_sections + references)
    ↓
文本切片 → DeepSeek Embedding → 存入 Milvus (paper_chunks)
    ↓
返回 PaperOut 响应
```

### 6.2 上下文问答流程 (RAG)

```
用户提问 + (可选) 选中文本
    ↓
ai.ask → 准备 fallback 段落
    ↓
rag_qa.ask_with_langchain
    ↓
PaperMilvusRetriever:
  选中文本(可选) + 问题 Embedding → Milvus top-k (限定 paper_id)
  若仍无文档 → PostgreSQL 前几段降级
    ↓
LangChain: ChatPromptTemplate | ChatOpenAI(DeepSeek) | StrOutputParser
    ↓
返回 {answer, sources}
```

### 6.3 引用文献分析流程

```
从 PostgreSQL 读取 references
    ↓
首次分析时: LLM 解析原始文本 → 填充 title/venue/level 字段 → 回写数据库
    ↓
统计: 近3年/10年占比, 来源分布 (journal/conference/...), 级别分布 (CCF-A/SCI-Q1/...)
    ↓
缓存到 Redis (1h TTL) → 返回 ReferenceAnalysis
```

## 七、应用生命周期

```python
@asynccontextmanager
async def lifespan(app):
    # Startup
    PostgreSQL: create_all tables
    Milvus: connect + ensure collection + load
    Redis: create connection pool
    
    yield  # 应用运行中
    
    # Shutdown
    PostgreSQL: dispose engine
    Milvus: release collection + disconnect
    Redis: close pool
```

## 八、环境变量

参见 `.env.example`，关键配置项:

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 (必填) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | API 地址 |
| `DEEPSEEK_LLM_MODEL` | `deepseek-chat` | LLM 模型名 |
| `DEEPSEEK_EMBED_MODEL` | `deepseek-embedding` | Embedding 模型名 |
| `POSTGRES_*` | `localhost:5432/readmei` | PostgreSQL 连接信息 |
| `MILVUS_HOST/PORT` | `localhost:19530` | Milvus 连接信息 |
| `REDIS_HOST/PORT/DB` | `localhost:6379/0` | Redis 连接信息 |
| `UPLOAD_DIR` | `./uploads` | PDF 存储路径 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 前端跨域白名单 |

## 九、启动方式

```bash
cd backend
cp .env.example .env   # 编辑 .env 填入实际配置
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 `http://localhost:8000/docs` 查看自动生成的 Swagger API 文档。
