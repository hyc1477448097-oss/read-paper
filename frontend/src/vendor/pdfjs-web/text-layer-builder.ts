/* SPDX-License-Identifier: Apache-2.0 */
/* Adapted from mozilla/pdf.js v5.6.205 web/text_layer_builder.js — imports from pdfjs-dist. */

import {
  normalizeUnicode,
  stopEvent,
  TextLayer,
  type TextLayerImages,
} from 'pdfjs-dist'
import { removeNullCharacters } from './remove-null-characters'

/** pdfjs-dist PageViewport / PDFPageProxy (not all re-exported as types from entry). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PdfPageViewport = any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PdfPageProxy = any

export interface TextLayerBuilderOptions {
  pdfPage: PdfPageProxy
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  highlighter?: any | null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  accessibilityManager?: any | null
  enablePermissions?: boolean
  onAppend?: ((div: HTMLDivElement) => void) | null
  abortSignal?: AbortSignal | null
}

export interface TextLayerBuilderRenderOptions {
  viewport: PdfPageViewport
  images?: TextLayerImages | null
  textContentParams?: {
    includeMarkedContent?: boolean
    disableNormalization?: boolean
  } | null
}

/**
 * Official text layer builder: streamTextContent → TextLayer, selection/copy helpers.
 */
export class TextLayerBuilder {
  pdfPage: PdfPageProxy
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  highlighter: any | null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  accessibilityManager: any | null
  div: HTMLDivElement

  #abortSignal: AbortSignal | null = null
  #enablePermissions = false
  #onAppend: ((div: HTMLDivElement) => void) | null = null
  #renderingDone = false
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  #textLayer: InstanceType<typeof TextLayer> | null = null

  static #textLayers = new Map<HTMLDivElement, HTMLDivElement>()
  static #selectionChangeAbortController: AbortController | null = null

  constructor({
    pdfPage,
    highlighter = null,
    accessibilityManager = null,
    enablePermissions = false,
    onAppend = null,
    abortSignal = null,
  }: TextLayerBuilderOptions) {
    this.pdfPage = pdfPage
    this.highlighter = highlighter
    this.accessibilityManager = accessibilityManager
    this.#enablePermissions = enablePermissions === true
    this.#onAppend = onAppend ?? null
    this.#abortSignal = abortSignal ?? null

    this.div = document.createElement('div')
    this.div.tabIndex = 0
    this.div.className = 'textLayer'
  }

  async render({
    viewport,
    images = undefined,
    textContentParams = null,
  }: TextLayerBuilderRenderOptions): Promise<void> {
    if (this.#renderingDone && this.#textLayer) {
      this.#textLayer.update({
        viewport,
        onBefore: this.hide.bind(this),
      })
      this.show()
      return
    }

    this.cancel()
    this.#textLayer = new TextLayer({
      textContentSource: this.pdfPage.streamTextContent(
        textContentParams || {
          includeMarkedContent: true,
          disableNormalization: true,
        },
      ),
      images: images ?? undefined,
      container: this.div,
      viewport,
    })

    const { textDivs, textContentItemsStr } = this.#textLayer
    this.highlighter?.setTextMapping(textDivs, textContentItemsStr)
    this.accessibilityManager?.setTextMapping(textDivs)

    await this.#textLayer.render()
    this.#renderingDone = true

    const endOfContent = document.createElement('div')
    endOfContent.className = 'endOfContent'
    this.div.append(endOfContent)

    this.#bindMouse(endOfContent)
    this.#onAppend?.(this.div)
    this.highlighter?.enable()
    this.accessibilityManager?.enable()
  }

  hide(): void {
    if (!this.div.hidden && this.#renderingDone) {
      this.highlighter?.disable()
      this.div.hidden = true
    }
  }

  show(): void {
    if (this.div.hidden && this.#renderingDone) {
      this.div.hidden = false
      this.highlighter?.enable()
    }
  }

  cancel(): void {
    this.#textLayer?.cancel()
    this.#textLayer = null

    this.highlighter?.disable()
    this.accessibilityManager?.disable()
    TextLayerBuilder.#removeGlobalSelectionListener(this.div)
  }

  #bindMouse(end: HTMLDivElement): void {
    const { div } = this
    const abortSignal = this.#abortSignal
    const opts = abortSignal ? { signal: abortSignal } : undefined

    div.addEventListener(
      'mousedown',
      () => {
        div.classList.add('selecting')
      },
      opts,
    )

    div.addEventListener(
      'copy',
      (event: ClipboardEvent) => {
        if (!this.#enablePermissions) {
          const selection = document.getSelection()
          event.clipboardData?.setData(
            'text/plain',
            removeNullCharacters(normalizeUnicode(selection?.toString() ?? '')),
          )
        }
        stopEvent(event)
      },
      opts,
    )

    TextLayerBuilder.#textLayers.set(div, end)
    TextLayerBuilder.#enableGlobalSelectionListener(abortSignal)
  }

  static #removeGlobalSelectionListener(textLayerDiv: HTMLDivElement): void {
    this.#textLayers.delete(textLayerDiv)

    if (this.#textLayers.size === 0) {
      this.#selectionChangeAbortController?.abort()
      this.#selectionChangeAbortController = null
    }
  }

  static #enableGlobalSelectionListener(globalAbortSignal: AbortSignal | null): void {
    if (this.#selectionChangeAbortController) {
      return
    }
    this.#selectionChangeAbortController = new AbortController()
    const ownSignal = this.#selectionChangeAbortController.signal
    const signal = globalAbortSignal
      ? AbortSignal.any([ownSignal, globalAbortSignal])
      : ownSignal

    const reset = (endDiv: HTMLDivElement, textLayer: HTMLDivElement) => {
      textLayer.append(endDiv)
      endDiv.style.width = ''
      endDiv.style.height = ''
      textLayer.classList.remove('selecting')
    }

    let isPointerDown = false
    document.addEventListener(
      'pointerdown',
      () => {
        isPointerDown = true
      },
      { signal },
    )
    document.addEventListener(
      'pointerup',
      () => {
        isPointerDown = false
        this.#textLayers.forEach(reset)
      },
      { signal },
    )
    window.addEventListener(
      'blur',
      () => {
        isPointerDown = false
        this.#textLayers.forEach(reset)
      },
      { signal },
    )
    document.addEventListener(
      'keyup',
      () => {
        if (!isPointerDown) {
          this.#textLayers.forEach(reset)
        }
      },
      { signal },
    )

    let isFirefox: boolean | undefined
    let prevRange: Range | undefined

    document.addEventListener(
      'selectionchange',
      () => {
        const selection = document.getSelection()
        if (!selection || selection.rangeCount === 0) {
          this.#textLayers.forEach(reset)
          return
        }

        const activeTextLayers = new Set<HTMLDivElement>()
        for (let i = 0; i < selection.rangeCount; i++) {
          const range = selection.getRangeAt(i)
          for (const textLayerDiv of this.#textLayers.keys()) {
            if (
              !activeTextLayers.has(textLayerDiv) &&
              range.intersectsNode(textLayerDiv)
            ) {
              activeTextLayers.add(textLayerDiv)
            }
          }
        }

        for (const [textLayerDiv, endDiv] of this.#textLayers) {
          if (activeTextLayers.has(textLayerDiv)) {
            textLayerDiv.classList.add('selecting')
          } else {
            reset(endDiv, textLayerDiv)
          }
        }

        const firstLayer = this.#textLayers.keys().next().value
        if (!firstLayer) {
          return
        }
        isFirefox ??=
          getComputedStyle(firstLayer).getPropertyValue('-moz-user-select') === 'none'

        if (isFirefox) {
          return
        }

        const range = selection.getRangeAt(0)
        const modifyStart =
          prevRange &&
          (range.compareBoundaryPoints(Range.END_TO_END, prevRange) === 0 ||
            range.compareBoundaryPoints(Range.START_TO_END, prevRange) === 0)
        let anchor: Node | null = modifyStart ? range.startContainer : range.endContainer
        if (anchor.nodeType === Node.TEXT_NODE) {
          anchor = anchor.parentNode
        }
        if (
          anchor instanceof HTMLElement &&
          anchor.classList?.contains('highlight')
        ) {
          anchor = anchor.parentNode
        }
        if (!modifyStart && range.endOffset === 0 && anchor) {
          do {
            while (anchor && !anchor.previousSibling) {
              anchor = anchor.parentNode
            }
            anchor = anchor?.previousSibling ?? null
          } while (anchor && !anchor.childNodes.length)
        }

        const parentTextLayer =
          anchor instanceof Node
            ? (anchor as ChildNode).parentElement?.closest('.textLayer')
            : null
        const endDiv = parentTextLayer
          ? this.#textLayers.get(parentTextLayer as HTMLDivElement)
          : undefined
        if (endDiv && parentTextLayer && anchor?.parentElement) {
          endDiv.style.width = (parentTextLayer as HTMLElement).style.width
          endDiv.style.height = (parentTextLayer as HTMLElement).style.height
          endDiv.style.userSelect = 'text'
          anchor.parentElement.insertBefore(
            endDiv,
            modifyStart ? anchor : anchor.nextSibling,
          )
        }

        prevRange = range.cloneRange()
      },
      { signal },
    )
  }
}
