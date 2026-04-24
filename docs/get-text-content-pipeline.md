# PDF.js：文本抽取管线（getTextContent / streamTextContent）

本文说明：**从页面内容流中抽出「带仿射变换矩阵的文本片段」** 的实现位置与执行步骤。路径相对于本仓库 `pdf.js` 根目录（`src/`）。

---

## 总览

| 层次 | 文件 | 职责 |
|------|------|------|
| API / 流 | `src/display/api.js` | `streamTextContent` / `getTextContent` |
| Worker 分发 | `src/core/worker.js` | 处理 `GetTextContent` → 调用 `page.extractTextContent` |
| 页面组装 | `src/core/document.js` | `extractTextContent`：取内容流、合并资源、调用 `PartialEvaluator.getTextContent` |
| **核心抽取** | **`src/core/evaluator.js`** | **`PartialEvaluator#getTextContent`**：解释算子、维护文字状态、计算 `transform`、生成 `items`、分块 `sink.enqueue` |

**要点**：主线程不解析 PDF；解析与拼 `TextContent` 在 **Worker** 中完成，结果经 **MessageHandler 流** 回主线程，供 `TextLayer` 等叠 DOM。

---

## 1. 主线程入口：`display/api.js`

### `streamTextContent`

通过 transport 向 Worker 发送消息 **`GetTextContent`**，返回 **`ReadableStream`**，按块接收 `TextContent`（含 `items`、`styles` 等）。

```javascript
// 摘要：api.js 中 PDFPageProxy.streamTextContent
streamTextContent({ includeMarkedContent = false, disableNormalization = false } = {}) {
  const TEXT_CONTENT_CHUNK_SIZE = 100;
  return this._transport.messageHandler.sendWithStream(
    "GetTextContent",
    {
      pageId: this.#pagesMapper.getPageId(this._pageIndex + 1) - 1,
      pageIndex: this._pageIndex,
      includeMarkedContent: includeMarkedContent === true,
      disableNormalization: disableNormalization === true,
    },
    {
      highWaterMark: TEXT_CONTENT_CHUNK_SIZE,
      size(textContent) {
        return textContent.items.length;
      },
    }
  );
}
```

### `getTextContent`

- 若为 **XFA** 且 `_htmlForXfa` 等条件满足，走 **`XfaText.textContent(xfa)`**（与常规内容流路径不同）。
- 否则 **`for await` 消费 `streamTextContent`**，合并所有 chunk 的 `items` 与 `styles`。

---

## 2. Worker 接消息：`core/worker.js`

注册 **`GetTextContent`**：

1. 用 `pageId` 取 **`pdfManager.getPage(pageId)`**。
2. 创建 **`WorkerTask`**。
3. 调用 **`page.extractTextContent({ handler, task, sink, includeMarkedContent, disableNormalization })`**。
4. 成功结束时 **`sink.close()`**；错误时 **`sink.error(reason)`**。

**`sink`** 用于把 `TextContent` **分块 enqueue** 回主线程（流式传输）。

---

## 3. 页面对象组装：`core/document.js` — `Page#extractTextContent`

主要步骤：

1. **`getContentStream()`**  
   获取该页的 **内容流**（待解释的 PDF 指令序列）。

2. **`loadResources(RESOURCES_KEYS_TEXT_CONTENT)`** 与 **`#getMergedResources`**  
   加载文本抽取所需资源（如 **Font**、与文本相关的 **ExtGState** 等）。

3. **`ensureCatalog("lang")`**  
   将目录中的语言（若有）带入最终 `TextContent`。

4. **`#createPartialEvaluator(handler)`** 后调用：

   ```javascript
   partialEvaluator.getTextContent({
     stream: contentStream,
     task,
     resources,
     includeMarkedContent,
     disableNormalization,
     sink,
     viewBox: this.view,
     lang,
     intersector,
   });
   ```

**`viewBox`**：用于裁剪/判断字形是否在页框内，影响是否输出某些片段。

---

## 4. 核心实现：`core/evaluator.js` — `PartialEvaluator#getTextContent`

### 4.1 状态与输出

- **`StateManager` + `TextState`**：跟踪 PDF 文本状态（CTM、文字矩阵 `Tm`、字号、`Tf` 等）。
- **`EvaluatorPreprocessor`**：从 **`stream`** 中 **`read()`** 出 **`operation`**（操作符 + 参数）；**save/restore/变换** 等由 preprocessor 处理。
- 累积 **`textContentItem`**：当前段的字符数组 **`str`**、**`transform`**（6 元矩阵）、宽高、竖排标志、字体名等。
- 最终每个 item 大致为：`{ str, dir, width, height, transform, fontName, hasEOL }`，经 **`runBidiTransform`** 做 Unicode 规范化与 **bidi** 方向。

### 4.2 变换矩阵：`getCurrentTextTransform`

按 PDF **9.4.4 Text Space**，构造字体缩放矩阵 **`tsm`**，再与 **`textState.textMatrix`**、**`textState.ctm`** 链式 **`Util.transform`**，得到 **文本空间 → 用户空间** 的仿射变换，用于定位每个 glyph / 每段文本。

### 4.3 解释内容流：对大 `switch` 处理 PDF 算子

典型分支（逻辑概括）：

| 算子类型 | 作用 |
|----------|------|
| `beginText` | 重置文字矩阵 |
| `setTextMatrix`、`moveText`、`nextLine` 等 | 更新 `textState` |
| `setFont` | **异步 `loadFont`**，解析字体，供后续量宽 |
| `showText`、`showSpacedText` | 把字符串与 **TJ 中的数字间距** 交给 **`buildTextContentItem`**；内部根据 glyph 宽度、与上一字符的几何关系、`viewBox` 等决定合并或 **flush** 为新 item，并可能插入「假空格」以贴近 canvas 视觉间距 |
| Form XObject 等 | 需要时 **递归 `getTextContent`** 处理子流 |

主循环形态：**`while (preprocessor.read(operation))`** → 根据 **`operation.fn`**（如 `OPS.showText`）分支处理。

### 4.4 刷出 item 与流式回传

- **`flushTextContentItem`**：对当前 **`textContentItem`** 做最终宽度累计，**`runBidiTransform`** 后 **`push` 到 `textContent.items`**。
- **`enqueueChunk`**：当 **`items` 长度达到阈值**（或批处理策略满足）时调用 **`sink.enqueue(textContent, length)`**，将块发给主线程，然后 **清空 `items` / `styles`**，继续解析，控制内存峰值。

---

## 5. 与渲染管线的关系

- **同一页内容流**，**渲染**走 **`getOperatorList` → CanvasGraphics 画 canvas**。
- **抽文本**走 **`getTextContent`**：只处理与文字、矩阵、字体相关的算子，**不从 canvas 像素做 OCR**。
- 字体量宽等与 **`core/fonts.js`** 中供 **`PartialEvaluator.getTextContent`** 使用的逻辑相关。

---

## 6. 下游用途（简述）

主线程拿到 **`TextContent`** 后，**`display/text_layer.js`** / **`web/text_layer_builder.js`** 在 canvas 上方用 **绝对定位的 DOM** 叠字，浏览器拖选作用于该 DOM，而非 canvas 像素。

---

## 参考源码位置（便于跳转）

| 符号 / 主题 | 文件 |
|-------------|------|
| `streamTextContent` / `getTextContent` | `src/display/api.js` |
| `GetTextContent` 处理 | `src/core/worker.js` |
| `extractTextContent` | `src/core/document.js` |
| `getTextContent`（大函数） | `src/core/evaluator.js` |
| `getCurrentTextTransform`、`flushTextContentItem`、`enqueueChunk`、算子 `switch` | 同上 `evaluator.js` |

---

*文档由开发说明整理而成，与具体引擎版本一致；若上游重构类名/行号，请以当前 `src` 为准。*
