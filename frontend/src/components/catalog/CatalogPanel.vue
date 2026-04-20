<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  FolderOutlined,
  FolderOpenOutlined,
  FileTextOutlined,
  PlusOutlined,
  CloudUploadOutlined,
  MenuFoldOutlined,
  DeleteOutlined,
} from '@ant-design/icons-vue'
import { usePaperStore } from '@/stores'
import * as api from '@/api'
import axios from 'axios'

const LAST_PAPER_KEY = 'readmei_last_paper_id'

export interface PaperFolder {
  id: string
  name: string
  expanded: boolean
  papers: { id: string; title: string; fileName: string }[]
}

const emit = defineEmits<{
  selectPaper: [paperId: string]
  collapse: []
}>()

const paperStore = usePaperStore()

const folders = ref<PaperFolder[]>([
  {
    id: 'default',
    name: '我的论文',
    expanded: true,
    papers: [],
  },
])

const selectedPaperId = ref<string | null>(null)
const editingFolderId = ref<string | null>(null)
const newFolderName = ref('')
const dragging = ref(false)
const uploading = ref(false)
const catalogLoading = ref(true)

const totalPapers = computed(() =>
  folders.value.reduce((sum, f) => sum + f.papers.length, 0),
)

function getFirstExpandedFolder(): PaperFolder {
  return folders.value.find((f) => f.expanded) ?? folders.value[0]
}

function toggleFolder(folder: PaperFolder) {
  folder.expanded = !folder.expanded
}

function selectPaper(paperId: string) {
  selectedPaperId.value = paperId
  localStorage.setItem(LAST_PAPER_KEY, paperId)
  emit('selectPaper', paperId)
}

function addFolder() {
  const id = crypto.randomUUID()
  folders.value.push({
    id,
    name: '新文件夹',
    expanded: true,
    papers: [],
  })
  editingFolderId.value = id
  newFolderName.value = '新文件夹'
}

function confirmRename(folder: PaperFolder) {
  if (newFolderName.value.trim()) {
    folder.name = newFolderName.value.trim()
  }
  editingFolderId.value = null
}

function briefToCatalogItem(p: { id: string; title: string }, fileNameHint?: string) {
  const title = p.title || fileNameHint?.replace(/\.pdf$/i, '') || '未命名'
  const fileName =
    fileNameHint ?? (title.toLowerCase().endsWith('.pdf') ? title : `${title}.pdf`)
  return { id: p.id, title, fileName }
}

async function refreshCatalogFromServer() {
  catalogLoading.value = true
  try {
    const list = await api.listPapers()
    const folder = folders.value.find((f) => f.id === 'default') ?? getFirstExpandedFolder()
    folder.papers = list.map((p) => briefToCatalogItem(p))

    const lastId = localStorage.getItem(LAST_PAPER_KEY)
    const ids = new Set(list.map((p) => p.id))
    const pick =
      lastId && ids.has(lastId)
        ? lastId
        : list[0]?.id
    if (pick) {
      selectedPaperId.value = pick
      localStorage.setItem(LAST_PAPER_KEY, pick)
      emit('selectPaper', pick)
    } else {
      selectedPaperId.value = null
      localStorage.removeItem(LAST_PAPER_KEY)
      paperStore.$reset()
    }
  } catch {
    // 列表失败时保留空目录，避免阻塞界面
  } finally {
    catalogLoading.value = false
  }
}

onMounted(() => {
  void refreshCatalogFromServer()
})

async function importFile(file: File) {
  if (file.type !== 'application/pdf') return
  uploading.value = true
  try {
    await paperStore.uploadPaper(file)
    if (paperStore.currentPaper) {
      const folder = getFirstExpandedFolder()
      const item = briefToCatalogItem(paperStore.currentPaper, file.name)
      const idx = folder.papers.findIndex((x) => x.id === item.id)
      if (idx >= 0) folder.papers[idx] = item
      else folder.papers.unshift(item)
      selectedPaperId.value = paperStore.currentPaper.id
      localStorage.setItem(LAST_PAPER_KEY, paperStore.currentPaper.id)
      emit('selectPaper', paperStore.currentPaper.id)
    }
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      const detail = err.response.data?.detail as
        | { message?: string; existing_paper_id?: string; title?: string }
        | string
        | undefined
      const existingId =
        typeof detail === 'object' ? detail?.existing_paper_id : undefined
      const title =
        (typeof detail === 'object' ? detail?.title : undefined) ||
        file.name.replace(/\.pdf$/i, '')
      window.alert(`已存在同名论文「${title}」，不再重复导入。`)
      if (existingId) {
        let found = false
        for (const f of folders.value) {
          if (f.papers.some((p) => p.id === existingId)) {
            found = true
            break
          }
        }
        if (!found) {
          await refreshCatalogFromServer()
        }
        selectedPaperId.value = existingId
        localStorage.setItem(LAST_PAPER_KEY, existingId)
        emit('selectPaper', existingId)
      }
      return
    }
    throw err
  } finally {
    uploading.value = false
  }
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  dragging.value = true
}

function handleDragLeave() {
  dragging.value = false
}

async function handleDrop(e: DragEvent) {
  e.preventDefault()
  dragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) await importFile(file)
}

function handleClickUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.pdf'
  input.onchange = () => {
    const file = input.files?.[0]
    if (file) importFile(file)
  }
  input.click()
}

function collectAllPaperIds(): string[] {
  const ids: string[] = []
  for (const f of folders.value) {
    for (const p of f.papers) ids.push(p.id)
  }
  return ids
}

async function confirmDeletePaper(paper: { id: string; title: string; fileName: string }) {
  const label = paper.title || paper.fileName
  const ok = window.confirm(
    `确定删除「${label}」？将同时删除本地 PDF、数据库记录与向量索引，且不可恢复。`,
  )
  if (!ok) return
  try {
    await api.deletePaper(paper.id)
  } catch (err) {
    // 404 视为后端已不存在，其余错误继续抛出
    if (!(axios.isAxiosError(err) && err.response?.status === 404)) {
      throw err
    }
  }
  const wasSelected = selectedPaperId.value === paper.id
  for (const folder of folders.value) {
    folder.papers = folder.papers.filter((p) => p.id !== paper.id)
  }
  if (paperStore.currentPaper?.id === paper.id) {
    paperStore.$reset()
  }
  const remaining = collectAllPaperIds()
  if (remaining.length === 0) {
    selectedPaperId.value = null
    localStorage.removeItem(LAST_PAPER_KEY)
    return
  }
  if (wasSelected) {
    const nextId = remaining[0]
    selectedPaperId.value = nextId
    localStorage.setItem(LAST_PAPER_KEY, nextId)
    emit('selectPaper', nextId)
  }
}
</script>

<template>
  <div
    class="flex flex-col h-full bg-panel transition-colors"
    :class="dragging ? 'ring-2 ring-inset ring-primary bg-primary/5' : ''"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <!-- Header -->
    <div class="h-11 flex items-center justify-between px-3 border-b border-border shrink-0">
      <span class="text-xs font-semibold text-text-secondary uppercase tracking-wider">
        文件目录
      </span>
      <div class="flex items-center gap-1">
        <button
          class="w-6 h-6 rounded flex items-center justify-center text-text-muted
                 hover:bg-surface-alt hover:text-text-primary transition-colors"
          title="导入论文"
          @click="handleClickUpload"
        >
          <CloudUploadOutlined class="text-xs" />
        </button>
        <button
          class="w-6 h-6 rounded flex items-center justify-center text-text-muted
                 hover:bg-surface-alt hover:text-text-primary transition-colors"
          title="新建文件夹"
          @click="addFolder"
        >
          <PlusOutlined class="text-xs" />
        </button>
        <button
          class="w-6 h-6 rounded flex items-center justify-center text-text-muted
                 hover:bg-surface-alt hover:text-text-primary transition-colors"
          title="收起目录"
          @click="emit('collapse')"
        >
          <MenuFoldOutlined class="text-xs" />
        </button>
      </div>
    </div>

    <!-- Folder tree -->
    <div class="flex-1 overflow-auto py-1">
      <!-- Drag overlay hint -->
      <div
        v-if="dragging"
        class="flex flex-col items-center justify-center h-full text-primary"
      >
        <CloudUploadOutlined class="text-3xl mb-2" />
        <p class="text-xs font-medium">松开以导入 PDF</p>
      </div>

      <!-- Uploading state -->
      <div
        v-else-if="uploading"
        class="flex items-center justify-center h-full text-text-muted text-xs"
      >
        导入中...
      </div>

      <!-- Initial catalog load from server -->
      <div
        v-else-if="catalogLoading"
        class="flex items-center justify-center h-full text-text-muted text-xs"
      >
        加载目录中...
      </div>

      <!-- Normal folder tree -->
      <template v-else>
        <div v-if="folders.length === 0" class="px-3 py-8 text-center text-text-muted text-xs">
          暂无文件夹
        </div>

        <div v-for="folder in folders" :key="folder.id" class="select-none">
          <!-- Folder row -->
          <div
            class="flex items-center gap-1.5 px-3 py-1.5 cursor-pointer
                   hover:bg-surface-alt transition-colors group"
            @click="toggleFolder(folder)"
          >
            <component
              :is="folder.expanded ? FolderOpenOutlined : FolderOutlined"
              class="text-sm text-warning shrink-0"
            />
            <template v-if="editingFolderId === folder.id">
              <input
                v-model="newFolderName"
                class="flex-1 h-5 px-1 text-xs bg-surface border border-primary rounded
                       focus:outline-none"
                @click.stop
                @keydown.enter="confirmRename(folder)"
                @blur="confirmRename(folder)"
              />
            </template>
            <template v-else>
              <span class="flex-1 text-xs text-text-primary truncate">
                {{ folder.name }}
              </span>
              <span class="text-[10px] text-text-muted tabular-nums">
                {{ folder.papers.length }}
              </span>
            </template>
          </div>

          <!-- Papers in folder -->
          <div v-if="folder.expanded" class="ml-3">
            <div
              v-for="paper in folder.papers"
              :key="paper.id"
              class="group/row flex items-center gap-1 px-3 py-1.5 rounded-md mx-1 transition-colors"
              :class="
                selectedPaperId === paper.id
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:bg-surface-alt hover:text-text-primary'
              "
            >
              <div
                class="flex min-w-0 flex-1 cursor-pointer items-center gap-1.5"
                @click="selectPaper(paper.id)"
              >
                <FileTextOutlined class="text-xs shrink-0" />
                <span class="text-xs truncate">{{ paper.title || paper.fileName }}</span>
              </div>
              <button
                type="button"
                class="shrink-0 rounded p-0.5 text-text-muted opacity-0 transition-opacity
                       hover:bg-danger/10 hover:text-danger group-hover/row:opacity-100"
                title="删除论文"
                @click.stop="confirmDeletePaper(paper)"
              >
                <DeleteOutlined class="text-xs" />
              </button>
            </div>

            <div
              v-if="folder.papers.length === 0"
              class="px-3 py-4 text-center"
            >
              <p class="text-[10px] text-text-muted mb-2">拖拽 PDF 到此处导入</p>
              <button
                class="text-[10px] text-primary hover:text-primary-light transition-colors"
                @click.stop="handleClickUpload"
              >
                或点击选择文件
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Footer info -->
    <div class="px-3 py-2 border-t border-border text-[10px] text-text-muted">
      共 {{ totalPapers }} 篇论文
    </div>
  </div>
</template>
