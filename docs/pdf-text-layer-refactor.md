# ReadMei：PDF 文本层官方管线重构说明

本文记录将单页 PDF 从「手写 `getTextContent` + `TextLayer` + 自研选词」迁移到 **Vendor `TextLayerBuilder` + 官方 CSS + `streamTextContent`** 的过程与结果，便于后续维护与升级 `pdfjs-dist` 时对照。

---

## 1. 背景与约束

- **`pdfjs-dist` npm 包**只导出 `display` 层 API（如 `TextLayer`、`setLayerDimensions`、`getDocument`），**不包含** Firefox 完整 viewer 下的 `web/text_layer_builder.js`、`web/pdf_page_view.js` 等，无法通过一行 `import` 使用整套官方 viewer。
- 目标是对齐内部文档 [text-layer-pipeline.md](./text-layer-pipeline.md)、[get-text-content-pipeline.md](./get-text-content-pipeline.md) 所描述的管线：**流式文本 → `TextLayer` → 透明 DOM 叠在 canvas 上 → 官方选择与复制辅助**。
- **刻意未移植** `PDFPageView` 整树（EventBus、注释层、RenderingQueue 等），仅在应用内 **vendor 最小子集**。

---

## 2. 新增文件（Vendor）

目录：[frontend/src/vendor/pdfjs-web/](../frontend/src/vendor/pdfjs-web/)。

| 文件 | 来源（mozilla/pdf.js **v5.6.205**，与 `pdfjs-dist` 版本一致） | 说明 |
|------|---------------------------------------------------------------|------|
| `text-layer-builder.ts` | `web/text_layer_builder.js` | 将 `import { … } from "pdfjs-lib"` 改为从 **`pdfjs-dist`** 引入 `TextLayer`、`normalizeUnicode`、`stopEvent`；`images` 传 `undefined` 以满足类型；`AbortSignal.any` 用于合并 `abortSignal`。 |
| `text-layer-builder.css` | `web/text_layer_builder.css` | 规则整体挂在 **`.pdf-page`** 下（如 `.pdf-page .textLayer`），避免与全局样式冲突；去掉上游预处理注释；`::selection` 使用项目可读性较好的半透明蓝。 |
| `remove-null-characters.ts` | `web/ui_utils.js` 中的 `removeNullCharacters` 及 `InvisibleCharsRegExp` | 仅抽取复制路径所需逻辑，不引入整个 `ui_utils`。 |
| `README.txt` | 自建 | 注明与 **v5.6.205** 同步，升级依赖时需重对 vendor。 |

许可：上游文件为 **Apache-2.0**，vendor 内保留 SPDX / 版权说明或 README 指向。

---

## 3. `frontend/src/utils/pdf.ts` 变更

| 变更项 | 说明 |
|--------|------|
| 新增 `getDisplayViewport(page, userScale)` | `page.getViewport({ scale: userScale * PixelsPerInch.PDF_TO_CSS_UNITS })`，与官方 `PDFPageView` 中 viewport 缩放思路一致。 |
| `renderPage` | 使用上述 **同一 viewport**；引入 **`OutputScale`**，按设备像素比设置 `canvas` 位图尺寸与 `page.render({ …, transform })`，使 **CSS 尺寸与文本层 viewport 同源**，消除原先「canvas 用 `scale * dpr`、文本层用另一套 scale」的偏差。 |
| 返回值 | 增加返回 **`page`**（`PDFPageProxy`），供 `TextLayerBuilder` 使用，避免同一渲染流程内重复 `getPage`。 |

---

## 4. `frontend/src/components/pdf/PdfPage.vue` 变更

| 变更项 | 说明 |
|--------|------|
| 移除 | 直接使用 `pdfjs-dist` 的 `TextLayer`、`page.getTextContent()`、`trimSpanWhitespace`、组件内手写 `.textLayer` 大块样式。 |
| 引入 | `import '@/vendor/pdfjs-web/text-layer-builder.css'`；`TextLayerBuilder`、`removeNullCharacters`；`setLayerDimensions`、`normalizeUnicode`。 |
| DOM | **页根** `ref="pageRootRef"`：承载 `setLayerDimensions` 与 CSS 变量；**canvas** 放在 `overflow-hidden` 容器内；**`textLayerSlotRef`** 用于 `onAppend` 时挂载 `builder.div`（官方生成的带 `tabIndex` 的 `.textLayer`）。 |
| 生命周期 | 每次重渲：`textLayerBuilder?.cancel()`、`layerAbort` 换新、`slot.replaceChildren()`；**`onBeforeUnmount`** 再 cancel + abort。 |
| `TextLayerBuilder` 参数 | `highlighter` / `accessibilityManager` 传 `null`；`streamTextContent` 参数与官方默认一致（`includeMarkedContent: true`、`disableNormalization: true`）；`render({ viewport })`，不传 `images`。 |
| `textSelected` | 仅在选区落在 `builder.div` 内时上报；字符串处理与官方 copy 一致：`removeNullCharacters(normalizeUnicode(selection.toString()))`。 |
| `paragraphClick` / 翻译 | 仍在文本层根上 `querySelectorAll('span')` 绑定点击与收集块；译文层 **`pointer-events-none`**，不挡文本层。 |

---

## 5. 删除文件

| 文件 | 原因 |
|------|------|
| [frontend/src/utils/pdfSelectionText.ts](../frontend/src/utils/pdfSelectionText.ts)（已删） | 几何切片选词由官方选区 + 与 copy 一致的规范化替代；若日后发现边缘回归，可再考虑薄层补充。 |

---

## 6. 数据流（重构后）

```text
Worker: streamTextContent（由 pdfPage.streamTextContent 发起）
    ↓
主线程: TextLayerBuilder → new TextLayer({ textContentSource: stream, container, viewport })
    ↓
await textLayer.render() → append spans、endOfContent、#bindMouse、全局 selection 辅助
    ↓
用户: 拖选 / Ctrl+C 作用于 .textLayer DOM；视觉由下层 canvas 呈现
```

页根几何：`setLayerDimensions(pageRoot, viewport, mustFlip=true, mustRotate=false)` + `--total-scale-factor` 等与 `text_layer_builder.css` 中 `var(--total-scale-factor)` 配合。

---

## 7. 升级与回归注意

1. **升级 `pdfjs-dist` 时**：用同 tag 的 mozilla/pdf.js 更新 `vendor/pdfjs-web` 下三份源码，并跑 **`npm run build`**、实际拖选/复制/缩放/翻译模式。
2. **多页**：`TextLayerBuilder` 内部静态 `#textLayers` 用于多页选区；每页 **`cancel()`** 会 `#removeGlobalSelectionListener`，避免监听器泄漏。
3. **手测建议**：拖选、跨行、Ctrl+C、缩放后 canvas 与文字对齐、`isTranslateMode` 下点击与选词。

---

## 8. 与计划文档的对应关系

本实现对应「Vendor TextLayerBuilder」方案：完成 **streamTextContent + Builder + 官方 CSS 变量体系 + setLayerDimensions + OutputScale 绘制**，未引入完整 `PDFPageView`。更细的官方文件索引仍以 [text-layer-pipeline.md](./text-layer-pipeline.md) 为准。
