# PDF 渲染问题修复记录

## 问题 1：PDF 渲染模糊

### 现象

PDF 页面在高分屏（如 2K/4K 显示器、Retina 屏）上显示模糊，文字和图形边缘不清晰，影响阅读体验。

### 原因

`renderPage` 函数将 `<canvas>` 的物理像素尺寸直接设为 viewport 的 CSS 逻辑尺寸，没有考虑 `window.devicePixelRatio`（高分屏通常为 2 或 3）。

```typescript
// 修复前
canvas.width = viewport.width   // e.g. 816
canvas.height = viewport.height // e.g. 1056
```

浏览器在一个 CSS 逻辑像素上只用了一个物理像素来绘制，导致 canvas 内容被拉伸后模糊。

### 解决方法

在 `renderPage` 中引入 `devicePixelRatio`，让 canvas 的物理分辨率按倍率放大渲染，再通过 CSS `style.width/height` 缩回到逻辑显示尺寸。

```typescript
// 修复后
const dpr = window.devicePixelRatio || 1
const viewport = page.getViewport({ scale: scale * dpr })

canvas.width = viewport.width                       // 物理像素 (e.g. 1632)
canvas.height = viewport.height                     // 物理像素 (e.g. 2112)
canvas.style.width = `${viewport.width / dpr}px`    // CSS 显示尺寸 (e.g. 816px)
canvas.style.height = `${viewport.height / dpr}px`

await page.render({ canvasContext: ctx, viewport }).promise
return { width: viewport.width / dpr, height: viewport.height / dpr }
```

涉及文件：`frontend/src/utils/pdf.ts`

---

## 问题 2：文本选择时每行最后的单词无法选中

### 现象

在 PDF 视图中用鼠标框选文字时，部分行的末尾单词无法被选中，会被遗漏。

### 原因

原有的 `buildTextLayer` 手工计算每个 text item 的坐标和宽度，用绝对定位的 `<span>` 模拟文本层。存在两个问题：

1. **`item.width` 估算值偏小**：pdf.js 的 `textContent.items` 中 `width` 字段是估算值，在字距调整（kerning）或特殊字体下容易偏窄。`<span>` 的 CSS 宽度比实际文字渲染宽度小时，末尾文字超出可选区域。
2. **text item 拆分导致间隙**：pdf.js 将一行文字按空格或字距断开为多个 item，每个独立定位。坐标/宽度的微小偏差累积后，相邻 item 之间出现间隙。

```typescript
// 修复前 — 手工计算坐标，width 不准确
blocks.push({
  text: item.str,
  x: tx[4] * scale,
  y: pageHeight - tx[5] * scale - item.height * scale,
  width: item.width * scale,    // 此值经常偏小
  height: item.height * scale,
  fontSize: Math.abs(tx[0]) * scale,
})
```

### 解决方法

放弃手工坐标计算，改用 pdf.js 官方的 `TextLayer` API。它内部精确处理字距、字体度量和坐标，是 pdf.js 推荐的文本层实现方式。

```typescript
// 修复后
import { TextLayer } from 'pdfjs-dist'

const page = await rawPdf.getPage(pageNumber)
const viewport = page.getViewport({ scale })
const textContent = await page.getTextContent()

const textLayer = new TextLayer({
  textContentSource: textContent,
  container: textLayerRef,
  viewport,
})
await textLayer.render()
```

同时为 `.textLayer` 容器提供官方所需的 CSS 样式（透明文字、绝对定位、选区高亮）。

涉及文件：`frontend/src/components/pdf/PdfPage.vue`


###右边栏ui修改需求1：

智能分析这一栏里需要修改的问题是：结构化总结、智能分析、上下文答疑、引用分析这四个按钮只会根据用户点击而改变：
1，点击结构化分析时，在论文中选取的部分最小单位为自然段，这部分的总结性叙述会被展示在“段落总结”下，如果选取部分不包含一个完整的自然段，界面先不反应。
2，点击智能翻译时，无最小选取单位，都可以翻译，显示区自动化为两部分，上面是原文，下面是自动翻译内容。
3，点击上下文答疑时，前端界面和目前上下文答疑一致；

问题：
两种翻译是一样的流程，domain没有值

我需要你
1，在智能翻译按钮点击后的展示框里放一个输入框，用户可以输入值作为domain的值；
2，如果用户没有输入的话，解析论文的“keywords”部分的内容作为domain的值
如果上面两种情况都没有发生的话，domain为默认值null
+为领域输入框加一个箭头，输入后点击enter键字体变灰，同时存入论文信息的domain字段，下次从后端获取信息、智能翻译都可以获取

问题：
全文翻译不用大模型，用翻译器组件
智能翻译/结构化总价在翻译器组件的结果上加工