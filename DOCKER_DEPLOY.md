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
| **milvus** | milvusdb/milvus:v2.5-latest | 19530 (内部) | 向量数据库 (RAG 检索) |
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

# 停止并删除所有数据卷 (完全重置)
docker-compose down -v

# 重启
docker-compose up -d
```

## 五、环境变量说明

`.env` 文件位于项目根目录，仅需配置外部 API 密钥：

| 变量 | 必填 | 默认值 | 说明 |
|------|:---:|--------|------|
| `DEEPSEEK_API_KEY` | 是 | — | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com/v1` | 自定义 API 地址 |

三个数据库的连接配置已在 `docker-compose.yml` 中内置（使用 Docker 服务名互联），无需手动配置：

| 配置项 | Docker 内部值 |
|--------|---------------|
| `POSTGRES_HOST` | `postgres` |
| `MILVUS_HOST` | `milvus` |
| `REDIS_HOST` | `redis` |

## 六、数据持久化

所有有状态数据通过 Docker Named Volume 持久化：

| Volume 名称 | 挂载路径 | 内容 |
|-------------|---------|------|
| `postgres_data` | `/var/lib/postgresql/data` | PostgreSQL 数据库文件 |
| `redis_data` | `/data` | Redis 持久化数据 |
| `milvus_data` | `/var/lib/milvus` | Milvus 向量索引 |
| `etcd_data` | `/etcd` | etcd 元数据 |
| `minio_data` | `/minio_data` | MinIO 对象存储 |
| `uploads_data` | `/data/uploads` | 用户上传的 PDF 文件 |

> `docker-compose down` 不会删除 volume 数据；如需完全重置，使用 `docker-compose down -v`。

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
