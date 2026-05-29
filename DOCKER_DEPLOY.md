# ReadMei Docker 部署指南

## 一、整体架构

```
用户浏览器
    │
    │  http://localhost
    ▼
┌─────────────────────────────────────────────────┐
│  docker-compose                                 │
│                                                 │
│  ┌───────────────────────┐                      │
│  │  frontend (Nginx:80)  │                      │
│  │  静态文件 + 反向代理    │                      │
│  └───────┬───────────────┘                      │
│          │ /api/*                               │
│          ▼                                      │
│  ┌───────────────────────┐                      │
│  │  backend (FastAPI:8000)│                      │
│  └──┬────────┬────────┬──┘                      │
│     │        │        │                         │
│     ▼        ▼        ▼                         │
│  postgres  milvus   redis                       │
│  (:5432)  (:19530)  (:6379)                     │
│              │                                  │
│         ┌────┴────┐                             │
│         ▼         ▼                             │
│       etcd      minio                           │
│      (:2379)   (:9000)                          │
└─────────────────────────────────────────────────┘
```

共 **7 个容器**，分为基础设施层（5 个）和应用层（2 个）。

## 二、容器服务一览

| 服务 | 镜像 | 端口 | 用途 |
|------|------|------|------|
| **frontend** | 多阶段构建 (node:20 → nginx:alpine) | 80 (对外) | Vue 前端静态文件 + Nginx 反向代理 |
| **backend** | python:3.11-slim 自定义构建 | 8000 (内部) | FastAPI 后端 API |
| **postgres** | postgres:16-alpine | 5432 (内部) | 论文元数据持久化 |
| **milvus** | milvusdb/milvus:v2.5.4 | 19530 (内部) | 向量数据库 (RAG 检索) |
| **redis** | redis:7-alpine | 6379 (内部) | 缓存 (翻译/总结/分析结果) |
| **etcd** | quay.io/coreos/etcd:v3.5.18 | 2379 (内部) | Milvus 元数据存储 |
| **minio** | minio/minio | 9000 (内部) | Milvus 对象存储 |

## 三、文件结构

```
ReadMei/
├── docker-compose.yml          # 服务编排
├── .env                        # 环境变量 (填写 API Key)
├── backend/
│   ├── Dockerfile              # 后端镜像构建
│   ├── .dockerignore           # 构建排除规则
│   ├── requirements.txt
│   └── app/
└── frontend/
    ├── Dockerfile              # 前端多阶段镜像构建
    ├── .dockerignore           # 构建排除规则
    ├── nginx.conf              # Nginx 配置 (静态文件 + 反向代理)
    ├── package.json
    └── src/
```

## 四、快速部署

### 前置要求

- 安装 [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/)
- 获取 [DeepSeek API Key](https://platform.deepseek.com/)

### 步骤

```bash
# 1. 进入项目根目录
cd ReadMei

# 2. 编辑 .env 文件，填入 DeepSeek API Key
#    将 sk-your-key-here 替换为你的真实密钥
notepad .env

# 3. 一键构建并启动所有服务
docker-compose up -d --build

# 4. 查看启动状态 (等待所有服务变为 healthy/running)
docker-compose ps

# 5. 访问应用
#    浏览器打开 http://localhost
```

### 停止与重启

```bash
# 停止所有服务 (保留数据)
docker-compose down

# 停止并删除 compose 声明的数据卷（若 compose 未声明 volume，见第六节 6.7）
docker compose down -v

# 重启
docker-compose up -d
```

## 五、环境变量说明

`.env` 文件位于项目根目录，仅需配置外部 API 密钥：

| 变量 | 必填 | 默认值 | 说明 |
|------|:---:|--------|------|
| `DEEPSEEK_API_KEY` | 是 | — | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com/v1` | 自定义 API 地址 |

三个数据库的连接配置：

| 配置项 | Docker 内部值 | 本地开发（`backend/.env`） |
|--------|---------------|---------------------------|
| `POSTGRES_HOST` | `postgres` | `localhost` |
| `POSTGRES_PASSWORD` | `readmei123` | `readmei123`（须与 compose 一致） |
| `MILVUS_HOST` | `milvus` | `localhost` |
| `REDIS_HOST` | `redis` | `localhost` |

表结构与重建步骤见 **第六节**。

## 六、数据库模型与重建

> **Schema 唯一真相来源**：以下结构与 `backend/app/models/`、`backend/app/db/` 中的代码保持同步。  
> 修改模型后须重建数据库，或引入 Alembic 迁移；`create_all()` **只建表、不改表**。

### 6.1 Schema 初始化机制

后端启动时（`backend/app/main.py` lifespan）自动执行：

1. **PostgreSQL**：`Base.metadata.create_all()` — 表不存在时创建，**不会**增删改已有列
2. **Milvus**：`init_milvus()` — 集合 `paper_chunks` 不存在时创建并建索引
3. **Redis**：`init_redis()` — 仅建立连接，无固定表结构（键值缓存）

模型定义文件：

| 存储 | 代码文件 |
|------|----------|
| PostgreSQL | `backend/app/models/paper.py` |
| Milvus | `backend/app/db/milvus.py` |
| Redis | `backend/app/db/redis.py` |

### 6.2 PostgreSQL（`readmei` 库）

连接参数（与 `docker-compose.yml` / `backend/.env` 一致）：

| 变量 | Docker 内部 | 本地开发 |
|------|-------------|----------|
| Host | `postgres` | `localhost` |
| Port | `5432` | `5432` |
| User | `readmei` | `readmei` |
| Password | `readmei123` | `readmei123` |
| Database | `readmei` | `readmei` |

#### 表 `papers`（论文元数据）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK | 论文 ID |
| `title` | VARCHAR(512) | NOT NULL | 标题 |
| `authors` | TEXT | NULL | 作者 |
| `domain` | VARCHAR(128) | NULL | 领域/关键词 |
| `file_path` | VARCHAR(1024) | NOT NULL | PDF 相对路径，如 `uploads/{id}/xxx.pdf` |
| `page_count` | INTEGER | NOT NULL, default 0 | 页数 |
| `one_sentence_summary` | TEXT | NULL | 一句话总结 |
| `innovation_points` | TEXT | NULL | 创新点 |
| `metadata_json` | JSONB | NULL | 扩展元数据 |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | 创建时间 |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now() | 更新时间 |

#### 表 `paper_sections`（论文章节）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK | 章节 ID |
| `paper_id` | UUID | FK → `papers.id` ON DELETE CASCADE | 所属论文 |
| `idx` | INTEGER | NOT NULL | 章节序号 |
| `title` | VARCHAR(512) | NULL | 章节标题 |
| `content` | TEXT | NOT NULL | 章节正文 |
| `level` | INTEGER | NOT NULL, default 1 | 标题层级 |
| `page_start` | INTEGER | NULL | 起始页 |
| `page_end` | INTEGER | NULL | 结束页 |
| `category` | VARCHAR(64) | NULL | 章节分类 |
| `summary` | TEXT | NULL | 章节摘要 |

#### 表 `references`（参考文献）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK | 引用 ID |
| `paper_id` | UUID | FK → `papers.id` ON DELETE CASCADE | 所属论文 |
| `idx` | INTEGER | NOT NULL | 引用序号 |
| `raw_text` | TEXT | NOT NULL | 原始引用文本 |
| `title` | VARCHAR(1024) | NULL | 文献标题 |
| `authors` | TEXT | NULL | 作者 |
| `year` | INTEGER | NULL | 年份 |
| `venue` | VARCHAR(512) | NULL | 发表 venue |
| `venue_type` | VARCHAR(64) | NULL | venue 类型 |
| `venue_level` | VARCHAR(64) | NULL | venue 级别 |

关系：`papers` 1 ── N `paper_sections`，`papers` 1 ── N `references`。

### 6.3 Milvus（集合 `paper_chunks`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT64, PK, auto_id | 向量记录 ID |
| `paper_id` | VARCHAR(64) | 论文 ID |
| `section_idx` | INT32 | 对应章节 `idx` |
| `chunk_text` | VARCHAR(65535) | 文本分块 |
| `embedding` | FLOAT_VECTOR(1536) | DeepSeek embedding 向量 |

索引：`embedding` 字段，**COSINE** + **IVF_FLAT**（`nlist=128`），搜索参数 `nprobe=16`。

上传论文时由 `insert_chunks()` 写入；删除论文时由 `delete_paper_chunks()` 按 `paper_id` 清除。

### 6.4 Redis（键值缓存，无固定 Schema）

默认 TTL 3600s；各 API 缓存键约定：

| 键模式 | TTL | 用途 |
|--------|-----|------|
| `translate:{paper_id}:{engine}:{hash}` | 7200s | 翻译结果 |
| `summarize:{paper_id}` | 3600s | 总结结果 |
| `ref_analysis:{paper_id}` | 3600s | 参考文献分析 |
| `relevance:{paper_id}:{hash}` | 1800s | 相关性分析 |

连接：`redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}`，默认 `redis://redis:6379/0`（Docker）/ `redis://localhost:6379/0`（本地）。

### 6.5 文件存储（PDF）

| 环境 | 路径 |
|------|------|
| 本地开发 | `backend/uploads/{paper_id}/{filename}.pdf` |
| Docker 后端 | 容器内 `UPLOAD_DIR`（默认 `/data/uploads`） |

数据库 `papers.file_path` 存相对路径；**PDF 文件与 PostgreSQL 记录须同时保留**，否则 `/api/papers/{id}/file` 返回 404。

### 6.6 数据持久化（Docker Volume）

当前 `docker-compose.yml` 仅编排基础设施，**未声明 named volume**，Docker 会为各服务自动创建匿名/项目卷，例如：

| 常见 Volume 名 | 内容 |
|----------------|------|
| `readmei_pgdata` 或匿名卷 | PostgreSQL 数据 |
| `readmei_milvusdata` | Milvus 数据 |
| 容器内 `/data` 等 | Redis、etcd、MinIO 数据 |

> `docker compose down` 不会删除已存在的 volume；`docker compose down -v` 仅删除 **compose 文件中声明的** volume。  
> 若需彻底清空 PostgreSQL，须额外执行 `docker volume rm readmei_pgdata`（卷名以 `docker volume ls` 为准）。

### 6.7 完全重建数据库

适用场景：模型变更后 schema 不一致、上传报 `file_name` 等列约束错误、开发环境数据损坏。

```bash
# 1. 进入项目根目录
cd readmei

# 2. 停止容器
docker compose down

# 3. 删除 PostgreSQL 数据卷（卷名以 docker volume ls 为准）
docker volume rm readmei_pgdata

# （可选）一并清空 Milvus / Redis 等
# docker volume rm readmei_milvusdata

# 4. 重新启动基础设施
docker compose up -d

# 5. 等待 PostgreSQL 就绪后，重启后端以执行 create_all / init_milvus
#    本地开发：
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. 验证表结构（应仅有 papers / paper_sections / references，无 file_name、folders 等旧列）
docker exec readmei-postgres-1 psql -U readmei -d readmei -c "\dt"
docker exec readmei-postgres-1 psql -U readmei -d readmei -c "\d papers"
```

**本地开发额外步骤**：

```bash
# 清理孤儿 PDF（数据库已空但磁盘仍有旧文件时）
rm -rf backend/uploads/*

# 浏览器控制台清除上次打开的论文 ID
# localStorage.removeItem('readmei_last_paper_id'); location.reload()
```

**验证 API**：

```bash
curl http://localhost:8000/api/health          # {"status":"ok"}
curl http://localhost:8000/api/papers/         # []
```

重建后需重新上传 PDF；Milvus 向量与 Redis 缓存会随卷删除或 TTL 过期而清空。

## 七、启动顺序与健康检查

通过 `depends_on` + `healthcheck` 保证服务按依赖顺序启动：

```
etcd ──────┐
           ├──→ milvus ──┐
minio ─────┘              │
                          ├──→ backend ──→ frontend
postgres ─────────────────┤
                          │
redis ────────────────────┘
```

每个基础设施服务都配置了健康检查，backend 会在 PostgreSQL、Redis、Milvus 全部就绪后才启动。

## 八、Nginx 配置要点

`frontend/nginx.conf` 的关键配置：

- **静态文件服务**: `try_files $uri $uri/ /index.html` — 支持 Vue Router history 模式
- **反向代理**: `/api/*` 请求转发到 `http://backend:8000`
- **超时设置**: `proxy_read_timeout 300s` — 适配 LLM 长时间推理调用
- **上传限制**: `client_max_body_size 50m` — 支持较大 PDF 文件上传

## 九、常见问题

### Schema 与代码不一致

若上传论文报错（如 `null value in column "file_name"`），说明 PostgreSQL 中残留了旧版表结构。按 **第六节 6.7** 完全重建数据库，并确保 `backend/.env` 中 `POSTGRES_PASSWORD=readmei123`。

### 端口冲突

如果本机 80 端口被占用，修改 `docker-compose.yml` 中 frontend 的端口映射：

```yaml
frontend:
  ports:
    - "8080:80"   # 改为 8080 或其他可用端口
```

然后同步更新 backend 的 `CORS_ORIGINS`：

```yaml
CORS_ORIGINS: '["http://localhost:8080"]'
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看指定服务日志 (实时跟踪)
docker-compose logs -f backend

# 查看最近 100 行
docker-compose logs --tail 100 backend
```

### 重新构建单个服务

```bash
docker-compose up -d --build backend    # 只重建后端
docker-compose up -d --build frontend   # 只重建前端
```
