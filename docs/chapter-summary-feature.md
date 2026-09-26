# 章节总结功能说明（PDF 书签目录 + AI）

本文档概括「结构化总结」面板中 **章节总结** 的实现要点与相关文件，便于维护与排查。

## 功能概述

- 在 **创新点** 与 **阅读推荐** 之间展示 **章节总结** 区块（结构化总结 Tab）。
- **左侧**：从 PDF **嵌入书签（Outlines）** 读取目录，与 `getTextContent` 抽标题无关；数据流对齐 [outline-viewer-pipeline.md](./outline-viewer-pipeline.md) 中的 `getOutline` → `dest` 解析 → 跳转思路。
- **右侧**：点击某条目录后，中间 PDF 滚动到对应页，并调用后端 **大模型** 结合论文 **领域** 与解析库中的 **章节正文**（`PaperSection` 与书签页码区间求交）生成该书签范围的 **中文总结**。
- 无书签或尚未加载完成时，展示空态说明；快速连续点击目录时用请求序号丢弃过期响应，避免旧结果覆盖新选择。

> **`PaperSection` 如何在上传时切分、以及与书签页码如何求交**：见仓库根目录 [结构化总结链路.md](../结构化总结链路.md) **第九部分：切分创新点**（完整过程，此处不重复）。

## 前端文件

| 文件 | 作用 |
|------|------|
| [frontend/src/utils/pdf-outline.ts](../frontend/src/utils/pdf-outline.ts) | `getOutline()`、`dest` → 1-based 页码、`pageEnd`（先序下一子树外节点）、`buildPdfOutlineTree` |
| [frontend/src/stores/paper.ts](../frontend/src/stores/paper.ts) | `pdfOutline`、`setPdfOutline`；切换论文 / 重置时清空 |
| [frontend/src/components/pdf/PdfViewer.vue](../frontend/src/components/pdf/PdfViewer.vue) | PDF 加载成功后构建大纲并写入 store |
| [frontend/src/components/analysis/CoreContribution.vue](../frontend/src/components/analysis/CoreContribution.vue) | 章节总结 UI：目录 + 总结区；`setPage` 跳转；调用 `summarizeChapter`；总结展示时提供「重新生成」 |
| [frontend/src/api/paper.ts](../frontend/src/api/paper.ts) | `summarizeChapter` → `POST /api/papers/{id}/chapter-summary`（可传 `force_refresh`） |

## 后端文件

| 文件 | 作用 |
|------|------|
| [backend/app/schemas/paper.py](../backend/app/schemas/paper.py) | `ChapterSummaryRequest` / `ChapterSummaryResponse` |
| [backend/app/api/ai.py](../backend/app/api/ai.py) | `POST /{paper_id}/chapter-summary`：求交拼正文 → Redis 缓存命中则直接返回；否则 LLM 后写入缓存 |
| [backend/app/services/llm_service.py](../backend/app/services/llm_service.py) | `summarize_outline_chapter`：研究者视角；禁止套话；先总判断（主旨+全文角色）再 1～3 条重点；解析段落可能与书签不完全对齐 |

## 接口约定

- **路径**：`POST /api/papers/{paper_id}/chapter-summary`
- **请求体**：`outline_title`、`page_start`、`page_end`（均为正整数，且 `page_end` ≥ `page_start`）、可选 `domain`（缺省用论文表中的 `domain`）、可选 `force_refresh`（默认 `false`；`true` 时跳过读缓存并强制 LLM 后覆盖）
- **响应**：`summary`（字符串）、`domain`、`cached`（是否命中 Redis）
- **缓存**：Redis 键 `chapter_summary:{paper_id}:{meta_fp}`（meta 含标题、页码、domain、context 指纹）；TTL **7 天**。同章节再次点击默认可命中；「重新生成」传 `force_refresh=true`。

## 依赖与注意

- 章节总结走 **DeepSeek（LLM）**，需配置 `DEEPSEEK_API_KEY` 等环境变量。
- 书签页与解析器写入的 `page_start` / `page_end` 可能不一致时，总结会偏泛或触发「无匹配段落」占位逻辑，属预期边界。

## UI 变更说明

- **一句话总结** 区块已从结构化总结面板移除；**创新点** 仍依赖 `loadOneSentenceSummary()` 拉取的数据（与一句话接口同源），面板挂载时仍会请求该接口以填充创新点列表。
