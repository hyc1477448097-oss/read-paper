import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PdfDoc = any

export async function loadPdfDocument(source: string | ArrayBuffer): Promise<PdfDoc> {
  const loadingTask = pdfjsLib.getDocument(source)
  return await loadingTask.promise
}

export async function renderPage(
  pdf: PdfDoc,
  pageNumber: number,
  canvas: HTMLCanvasElement,
  scale: number,
): Promise<{ width: number; height: number }> {
  const page = await pdf.getPage(pageNumber)
  const dpr = window.devicePixelRatio || 1
  const viewport = page.getViewport({ scale: scale * dpr })

  canvas.width = viewport.width
  canvas.height = viewport.height
  canvas.style.width = `${viewport.width / dpr}px`
  canvas.style.height = `${viewport.height / dpr}px`

  const ctx = canvas.getContext('2d')!
  await page.render({ canvasContext: ctx, viewport }).promise

  return { width: viewport.width / dpr, height: viewport.height / dpr }
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
