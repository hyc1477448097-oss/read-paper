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
  const viewport = page.getViewport({ scale })

  canvas.width = viewport.width
  canvas.height = viewport.height

  const ctx = canvas.getContext('2d')!
  await page.render({ canvasContext: ctx, viewport, canvas }).promise

  return { width: viewport.width, height: viewport.height }
}

export async function getPageTextContent(
  pdf: PdfDoc,
  pageNumber: number,
) {
  const page = await pdf.getPage(pageNumber)
  return await page.getTextContent()
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
