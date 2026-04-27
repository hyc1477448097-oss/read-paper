/**
 * PDF.js Outlines（书签）解析：与 docs/outline-viewer-pipeline.md 一致，数据来自 getOutline()。
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PdfDoc = any

export interface PdfOutlineNode {
  title: string
  pageStart: number
  pageEnd: number
  children: PdfOutlineNode[]
}

type RawOutlineItem = {
  title: string
  dest: string | unknown[] | null
  items?: RawOutlineItem[]
}

function isRefProxy(v: unknown): v is { num: number; gen: number } {
  return (
    !!v &&
    typeof v === 'object' &&
    'num' in v &&
    'gen' in v &&
    typeof (v as { num: unknown }).num === 'number'
  )
}

/**
 * 将书签 dest 解析为 1-based 页码；无法解析时返回 null。
 */
export async function destToPageNumber(
  pdf: PdfDoc,
  dest: string | unknown[] | null | undefined,
): Promise<number | null> {
  if (dest == null) return null
  let explicit: unknown[] | null = null
  if (typeof dest === 'string') {
    explicit = await pdf.getDestination(dest)
  } else if (Array.isArray(dest)) {
    explicit = dest
  }
  if (!explicit || explicit.length === 0) return null

  const head = explicit[0]
  if (isRefProxy(head)) {
    const idx = await pdf.getPageIndex(head)
    return idx + 1
  }
  if (typeof head === 'number') {
    // 常见为 0-based 页下标
    const n = pdf.numPages as number
    const page = head + 1
    if (page >= 1 && page <= n) return page
    if (head >= 1 && head <= n) return head
    return null
  }
  return null
}

async function rawToNode(pdf: PdfDoc, raw: RawOutlineItem): Promise<PdfOutlineNode | null> {
  let pageStart = await destToPageNumber(pdf, raw.dest)
  const childNodes: PdfOutlineNode[] = []
  for (const c of raw.items ?? []) {
    const n = await rawToNode(pdf, c)
    if (n) childNodes.push(n)
  }
  if (pageStart == null && childNodes.length > 0) {
    pageStart = childNodes[0].pageStart
  }
  if (pageStart == null) return null
  return {
    title: raw.title || '（无标题）',
    pageStart,
    pageEnd: pdf.numPages as number,
    children: childNodes,
  }
}

function subtreeSize(n: PdfOutlineNode): number {
  return 1 + n.children.reduce((acc, c) => acc + subtreeSize(c), 0)
}

function flattenPreorder(nodes: PdfOutlineNode[], acc: PdfOutlineNode[]): void {
  for (const n of nodes) {
    acc.push(n)
    flattenPreorder(n.children, acc)
  }
}

/**
 * 为每个节点设置 pageEnd：先序序列中「紧挨本节点子树之后」的条目的 pageStart - 1。
 */
function assignPageEndsFromPreorder(flat: PdfOutlineNode[], numPages: number): void {
  const index = new Map<PdfOutlineNode, number>()
  flat.forEach((n, i) => index.set(n, i))
  for (const n of flat) {
    const i = index.get(n)!
    const nextIdx = i + subtreeSize(n)
    if (nextIdx < flat.length) {
      const nextStart = flat[nextIdx].pageStart
      n.pageEnd = Math.max(n.pageStart, Math.min(numPages, nextStart - 1))
    } else {
      n.pageEnd = numPages
    }
  }
}

/**
 * 从 PDF 文档拉取书签并解析页范围。
 */
export async function buildPdfOutlineTree(pdf: PdfDoc): Promise<PdfOutlineNode[] | null> {
  const raw = (await pdf.getOutline()) as RawOutlineItem[] | null
  if (!raw?.length) return null
  const roots: PdfOutlineNode[] = []
  for (const item of raw) {
    const n = await rawToNode(pdf, item)
    if (n) roots.push(n)
  }
  if (!roots.length) return null
  const numPages = pdf.numPages as number
  const flat: PdfOutlineNode[] = []
  flattenPreorder(roots, flat)
  assignPageEndsFromPreorder(flat, numPages)
  return roots
}
