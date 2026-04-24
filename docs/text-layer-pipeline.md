# PDF.js：文本层（Text Layer）— 在 canvas 上叠 DOM 的实现

本文说明：**如何用大量 `span`/`br` 盖住 canvas、用百分比定位 + CSS 变量控制缩放/旋转，使可选中文本与已绘制字形对齐**。路径相对于本仓库 `pdf.js` 根目录。

---

## 1. 在 viewer 里谁创建文本层？

**`web/pdf_page_view.js`** 在需要时构造 **`TextLayerBuilder`**，在页面渲染流程里调用 **`this.textLayer.render({ viewport, images, ... })`**，并把 **`textLayer.div`**（根节点）插入到与 **canvas 同尺寸的页面容器**里，使文本层与画布叠在同一视口坐标系中。

（具体插入顺序与 `textLayerMode`、是否保留旧层等有关，见 `pdf_page_view.js` 中 `textLayer` 相关分支。）

---

## 2. `web/text_layer_builder.js` — 壳子与数据源

### 2.1 根 DOM

构造函数里创建 **`div`**，`className = "textLayer"`，并设置 **`tabIndex`** 等，用于后续选择/焦点行为。

### 2.2 `render({ viewport, images, textContentParams })`

核心步骤：

1. **若已渲染过且只需更新**：调用已有 **`TextLayer#update({ viewport, onBefore })`** 并 `show()`，返回。
2. **否则**：
   - **`cancel()`** 清掉上一次。
   - **`new TextLayer({ ... })`**，其中：
     - **`textContentSource`**：`this.pdfPage.streamTextContent(...)` —— 与 Worker 建立的 **文本抽取流**（见 `get-text-content-pipeline.md`）。
     - **`container`**：上面的 **`this.div`**（整个文本层根）。
     - **`viewport`**：当前页的 **`PageViewport`**（缩放、旋转、尺寸与 canvas 一致）。
     - **`images`**：可选，处理文本层里的图片点击等。
   - 把 **`TextLayer` 暴露的 `textDivs`、`textContentItemsStr`** 交给 **Highlighter / TextAccessibilityManager** 做映射。
   - **`await this.#textLayer.render()`** —— **真正往 `div` 里 append 大量 `span`** 在 **`src/display/text_layer.js`** 里完成。
   - 追加 **`div.endOfContent`**，并 **`#bindMouse`**：改善拖选体验、`copy` 时用 `selection.toString()` 写剪贴板等。
   - 调用 **`#onAppend?.(this.div)`**，再 enable 高亮/无障碍。

**要点**：`TextLayerBuilder` 几乎不直接算几何；它负责 **接线、生命周期、选择辅助**；几何在 **`TextLayer`**。

---

## 3. `src/display/text_layer.js` — 每个 `span` 怎么摆、怎么缩

### 3.1 构造函数里与「整页坐标」相关的量

- **`#scale`**：`viewport.scale * OutputScale.pixelRatio`（与 HiDPI 一致）。
- **`#rotation`**：来自 viewport。
- **`#transform`**：由 **`viewport.rawDims`**（`pageWidth, pageHeight, pageX, pageY`）拼出的 **6 元矩阵**，把 **PDF 用户空间** 变到 **文本层使用的 CSS 坐标**（含 **Y 轴翻转** 等，与 canvas 绘制约定一致）：

  `this.#transform = [1, 0, 0, -1, -pageX, pageY + pageHeight]`

- **`setLayerDimensions(container, viewport)`**（`src/display/display_utils.js`）：给 **`.textLayer` 根 `div`** 设 **`width` / `height`**（用 `calc(var(--total-scale-factor) * ${pageWidth}px)` 等形式），保证与 **canvas 页尺寸** 同步；并写 **`data-main-rotation`** 等。

- **`--min-font-size`**：写到容器上，配合 CSS 突破浏览器最小字号限制（见下节 CSS 注释）。

### 3.2 `render()` — 消费 `TextContent` 流

- 若有 **`images`** handler，先把其 DOM append 到容器。
- 对 **`textContentSource`** 用 **`ReadableStreamDefaultReader`** **`read()`** 循环：
  - 每个 chunk 的 **`styles`** 合并进 **`#styleCache`**（按 `fontName` 存 `fontFamily`、`ascent`、`vertical` 等）。
  - 对每个 **`item`** 调用 **`#processItems`** → 有 **`item.str`** 时走 **`#appendText(item)`**。

### 3.3 `#processItems(items)`

- 若 **`item.str === undefined`** 且为 **marked content**，用嵌套 **`span.markedContent`** 改变当前 append 的父节点（结构树），然后 `continue`。
- 否则 **`textContentItemsStr.push(item.str)`**，再 **`#appendText(item)`**。
- 超过 **`MAX_TEXT_DIVS_TO_RENDER`**（10 万）则停止追加并告警，避免页面卡死。

### 3.4 `#appendText(geom)` — 单个文本 item → 一个 `span`

对每个 **`geom`**（即 `TextContent` 里的一项，含 **`str`、`transform`、`width`/`height`、`fontName`、`dir`、`hasEOL`** 等）：

1. **`document.createElement("span")`**，记录 **`textDivProperties`**（角度、是否在 canvas 上量过宽、`fontSize` 等）。
2. **把 PDF 里的 `geom.transform` 乘上页面级 `#transform`**，得到 **`tx`**：

   `const tx = Util.transform(this.#transform, geom.transform);`

3. **`angle = atan2(tx[1], tx[0])`**；若字体 **`vertical`**，再加 **90°**。
4. **`fontHeight = hypot(tx[2], tx[3])`**；用隐藏 canvas **`measureText`** + 字体度量算 **ascent**，得到 **`left, top`**（无旋转时用 `tx[4], tx[5] - fontAscent`；有旋转时用三角函数把基线角点算到左上角）。
5. **写 `span.style`**（此时尚未插入 DOM）：
   - **`left` / `top`**：用 **相对整页的百分比**  
     `((100 * left) / this.#pageWidth).toFixed(2) + '%'`  
     这样在 **缩放 `--total-scale-factor`** 时与 canvas 同步。
   - **`--font-height`**：像素高度，供 CSS `font-size: calc(...)` 使用。
   - **`fontFamily`**：来自 **`#styleCache[geom.fontName]`**（PDF 字体到 CSS 族名的映射）。
6. **`textDiv.textContent = geom.str`**，**`textDiv.dir = geom.dir`**（含竖排 `ttb`）。
7. **决定是否要做横向缩放 `shouldScaleText`**：多字符一般要做；单字符在纵横缩放差异大时也要，以便高亮框更贴 canvas。
8. 若需要缩放： **`textDivProperties.canvasWidth`** 取 **`geom.width` 或 `geom.height`**（竖排）。
9. **`#textDivProperties.set(textDiv, textDivProperties)`**。
10. **`#layout(this.#layoutTextParams)`**（见下）。
11. 若有真实文字：**`this.#container.append(textDiv)`**。
12. 若 **`hasEOL`**：再 append 一个 **`br`**。

### 3.5 `#layout({ div, properties, ctx })` — `measureText` + CSS 变量

- 若 **`canvasWidth !== 0` 且 `hasText`**：
  - 在隐藏 **`canvas` 2d context** 上设置与 **`#scale`** 一致的 **`ctx.font`**。
  - **`ctx.measureText(div.textContent).width`** 得到 **浏览器实际渲染宽度**。
  - 若 **`width > 0`**：设置 CSS 变量 **`--scale-x = (canvasWidth * #scale) / width`**  
    即把 **DOM 字符串宽度** 缩放到与 **PDF 几何宽度**（乘设备比）一致，从而与 **canvas 上字形宽度** 对齐。
- 若 **`angle !== 0`**：设置 **`--rotate`**（度数）。

**注意**：具体 **`transform: rotate(...) scaleX(...) scale(...)`** 写在 **`web/text_layer_builder.css`** 里（见下一节），JS 只负责 **`left`/`top`/`font-size` 相关变量** 等。

### 3.6 隐藏测量用 canvas

**`TextLayer.#getCtx(lang)`**：在 **`document.body`** 上挂一个 **`class="hiddenCanvasElement"`** 的 **`canvas`**，用 **`measureText`** 和 **字体的 bounding box** 算 ascent 等；避免用 OffscreenCanvas 的原因写在源码注释里（与 **`lang` / 系统区域** 导致字体不一致有关）。

---

## 4. `web/text_layer_builder.css` — 「透明字」与变换

### 4.1 `.textLayer` 容器

- **`position: absolute; inset: 0`**：铺满 **与 canvas 同大的父区域**。
- **`transform-origin: 0 0`**、**`z-index`** 等与页面 stacking 配合。

### 4.2 `.textLayer :is(span, br)`

- **`color: transparent`**：**字不可见**，但仍可被 **拖选 / 复制**（视觉上只看到下层 canvas）。
- **`position: absolute`**：**每个 `span` 用 `left`/`top` 百分比定位**。
- **`white-space: pre`**：保留空格/换行语义。
- **`cursor: text`**。

### 4.3 子 `span` 的 `font-size` 与 `transform`

对 **直接子级**（及 `.markedContent` 内的 span）：

- **`font-size: calc(var(--text-scale-factor) * var(--font-height))`**：与页面缩放、最小字号修正一致。
- **`transform: rotate(var(--rotate)) scaleX(var(--scale-x)) scale(var(--min-font-size-inv))`**：  
  把 JS 写入的 **`--rotate`、`--scale-x`** 与 **`--min-font-size`** 策略接起来，完成 **旋转 + 水平拉伸到 PDF 宽度 + 抵消浏览器最小字号**。

---

## 5. 数据流小结

```text
Worker: streamTextContent → TextContent { items[], styles }
        ↓
主线程: TextLayer.render() 逐块 read()
        ↓
每个 item: #appendText
  → Util.transform(页面矩阵, item.transform)
  → left/top → style 百分比
  → #layout → measureText → --scale-x, --rotate
  → append <span>（透明）到 .textLayer
        ↓
用户: 拖选的是这些 span 的文本节点；视觉上由下层 canvas 呈现。
```

---

## 6. 源码索引

| 主题 | 文件 |
|------|------|
| 谁在页面里挂文本层 | `web/pdf_page_view.js` |
| Builder：根 `div`、`streamTextContent`、`new TextLayer`、`render`、copy/选择辅助 | `web/text_layer_builder.js` |
| 几何、流消费、`span` 创建、`#layout`、`measureText` | `src/display/text_layer.js` |
| 文本层容器宽高与 viewport | `src/display/display_utils.js` → `setLayerDimensions` |
| 透明字、绝对定位、`transform` / `font-size` | `web/text_layer_builder.css` |
| 上游文本项从哪来 | `docs/get-text-content-pipeline.md` |

---

*若上游调整类名或 CSS 变量名，请以当前 `src` / `web` 为准。*
