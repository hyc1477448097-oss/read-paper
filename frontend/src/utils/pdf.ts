import * as pdfjsLib from 'pdfjs-dist'
import { OutputScale, PixelsPerInch } from 'pdfjs-dist'
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PdfDoc = any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PdfPage = any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PageViewport = any

export async function loadPdfDocument(source: string | ArrayBuffer): Promise<PdfDoc> {
  const loadingTask = pdfjsLib.getDocument(source)
  return await loadingTask.promise
}

/** Display viewport: same formula as mozilla/pdf.js PDFPageView (CSS px). */
export function getDisplayViewport(page: PdfPage, userScale: number): PageViewport {
  return page.getViewport({
    scale: userScale * PixelsPerInch.PDF_TO_CSS_UNITS,
  })
}

const activeRenderTasks = new WeakMap<HTMLCanvasElement, { cancel(): void }>()

export async function renderPage(
  pdf: PdfDoc,
  pageNumber: number,
  canvas: HTMLCanvasElement,
  userScale: number,
): Promise<{
  width: number
  height: number
  viewport: PageViewport
  page: PdfPage
}> {
  const prev = activeRenderTasks.get(canvas)
  if (prev) {
    prev.cancel()
    activeRenderTasks.delete(canvas)
  }

  const page = await pdf.getPage(pageNumber)
  const viewport = getDisplayViewport(page, userScale)
  const outputScale = new OutputScale()

  const canvasWidth = Math.round(viewport.width * outputScale.sx)
  const canvasHeight = Math.round(viewport.height * outputScale.sy)
  canvas.width = Math.max(1, canvasWidth)
  canvas.height = Math.max(1, canvasHeight)
  canvas.style.width = `${viewport.width}px`
  canvas.style.height = `${viewport.height}px`

  const ctx = canvas.getContext('2d')!
  const renderTask = page.render({
    canvasContext: ctx,
    viewport,
    transform: outputScale.scaled ? [outputScale.sx, 0, 0, outputScale.sy, 0, 0] : null,
  })
  activeRenderTasks.set(canvas, renderTask)

  try {
    await renderTask.promise
  } finally {
    if (activeRenderTasks.get(canvas) === renderTask) {
      activeRenderTasks.delete(canvas)
    }
  }

  return {
    width: viewport.width,
    height: viewport.height,
    viewport,
    page,
  }
}

export function getSelectedText(): {
  text: string
  range: Range | null
} {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) {
    return { text: '', range: null }
  }
  return {
    text: selection.toString().trim(),
    range: selection.getRangeAt(0),
  }
}
