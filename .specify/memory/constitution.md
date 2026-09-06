<!--
Sync Impact Report
Version change: 2.0.0 -> 2.0.1
Modified principles:
- 全部原则标题与正文翻译为简体中文（语义不变）
Added sections:
- None
Removed sections:
- None
Templates requiring updates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
Follow-up TODOs:
- None
-->
# ReadMei 项目章程

## 核心原则

### I. 仅使用 Vue Composition API
所有 Vue 组件 MUST 使用 Composition API 与 `<script setup>` 单文件组件实现。视图、布局及所有可复用
UI 组件中，禁止 Options API 组件与 class 风格 Vue 组件，无例外。

理由：统一的 Vue 编写模式使前端与 Vue 3 最佳实践保持一致，避免多种组件写法并存。

### II. FastAPI 路由处理器
所有 API 端点 MUST 在 `backend/app/api/` 下以 FastAPI 路由实现，并在 `backend/app/main.py` 中以
`/api/` 前缀挂载。路由处理器 MUST 返回合适的 HTTP 状态码，并在错误与成功路径中使用 `HTTPException`
或类型化响应模型。

理由：将 API 表面集中在 FastAPI 路由中，使路由、校验与部署语义统一于单一后端入口。

### III. 仅通过 SQLAlchemy 访问数据库
所有 PostgreSQL 操作 MUST 通过 `backend/app/db/postgres.py` 提供的 SQLAlchemy 异步会话执行。禁止
原始 SQL 字符串、直接 `asyncpg` 连接及临时数据库驱动。Schema 变更 MUST 在 SQLAlchemy 模型中表达，
并通过 Alembic 迁移应用。

理由：SQLAlchemy 集中管理类型安全的持久化、Schema 演进与可审查的数据库变更，减少隐藏的数据访问路径。

### IV. Pydantic 服务端校验
所有请求与响应载荷 MUST 在 `backend/app/schemas/` 中用 Pydantic 模型定义，并由 FastAPI 路由处理器
消费。客户端校验 MAY 改善用户体验，但 MUST NOT 作为安全边界。

理由：Pydantic 校验使信任边界明确，并将 Schema 定义置于消费它们的代码附近。

### V. 结构化 API 错误处理
每个 API 路由处理器 MUST 对预期失败抛出带合适状态码的 `HTTPException`：校验或错误输入用 `400`，
资源不存在用 `404`，冲突用 `409`，上游服务失败用 `502`，意外失败用 `500`。错误 `detail` MUST 为
人类可读字符串或适合客户端展示的结构化对象。

理由：一致的错误契约简化 Vue 客户端，并使运维故障可诊断，同时不泄露实现细节。

### VI. 约定式提交（Conventional Commits）
所有提交信息 MUST 遵循 Conventional Commits 前缀：`feat:`、`fix:`、`docs:`、`chore:`、
`refactor:`、`test:`、`style:`、`perf:`、`ci:` 或 `build:`。无有效前缀的提交 MUST 被拒绝。

理由：一致的提交元数据支持可读历史、自动化发布说明与可预测的变更分类。

### VII. 类型安全与构建门禁
前端变更在合并前 MUST 通过 `vue-tsc --noEmit`。后端新增或修改的文件 MUST 使用 Python 类型注解及
`from __future__ import annotations`。未通过前端类型检查或引入未类型化公开 API 的 PR MUST NOT
被接受。

理由：静态类型检查使评审聚焦行为，并防止可避免缺陷进入代码库。

## 技术约束

应用栈限定为：Vue 3 Composition API、TypeScript、Vite、Pinia、FastAPI、SQLAlchemy 异步
PostgreSQL、Alembic、通过 `pymilvus` 的 Milvus、Redis、Pydantic，以及前端 Axios HTTP 调用。任何
需要冲突技术或绕过上述工具的特性计划 MUST 在计划的「章程检查」中记录违规项，且在章程修订前 MUST NOT
继续推进。

向量检索 MUST 使用 `backend/app/db/milvus.py` 中的 Milvus 辅助函数。缓存访问 MUST 使用
`backend/app/db/redis.py` 中的 Redis 辅助函数。在这些模块之外直接使用驱动不是可接受的实现捷径。

## 开发流程与质量门禁

特性规格 MUST 识别变更是否涉及 Vue 组件、FastAPI 路由、PostgreSQL 访问、Milvus 或 Redis 使用、
用户输入或提交/发布流程。实施计划 MUST 在 Phase 0 调研前及 Phase 1 设计后各包含一次覆盖全部七项
核心原则的章程检查。

任务列表 MUST 在相关范围内明确包含 Pydantic Schema、FastAPI 路由处理器、SQLAlchemy 模型或会话、
Milvus 或 Redis 集成、结构化 API 错误响应，以及类型检查/构建验证等工作。合并前，贡献者 MUST 对
前端变更运行或验证 `vue-tsc --noEmit`，并对后端变更验证受影响的 API 路径。

## 治理

本章程优先于冲突的开发实践、模板与非正式约定。修订 MUST 通过更新本文档、记录同步影响报告，并将
变更规则传播至受影响的 Spec Kit 模板与运行时指南完成。

版本遵循语义化版本：MAJOR 以不兼容方式移除或重定义原则，MINOR 新增原则或实质性扩展治理，PATCH
仅澄清措辞而不改变含义。每次特性评审 MUST 验证与当前章程的合规性；任何例外在实施前 MUST 获得
已批准的章程修订。

**Version**: 2.0.1 | **Ratified**: 2026-05-07 | **Last Amended**: 2026-05-31
