<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  SearchOutlined,
  SettingOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { usePaperStore, useUserStore } from '@/stores'
import SettingsModal from './SettingsModal.vue'

const router = useRouter()
const paperStore = usePaperStore()
const userStore = useUserStore()

const searchQuery = ref('')
const showSettings = ref(false)

function goHome() {
  router.push('/')
}
</script>

<template>
  <header
    class="h-[var(--height-header)] bg-panel border-b border-border flex items-center px-5 gap-4 shrink-0 z-40"
  >
    <!-- Left: Logo & Breadcrumb -->
    <div class="flex items-center gap-3 min-w-0">
      <div
        class="flex items-center gap-2 cursor-pointer select-none"
        @click="goHome"
      >
        <div
          class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"
        >
          <span class="text-white font-bold text-sm">R</span>
        </div>
        <span class="font-semibold text-text-primary text-base hidden sm:block">
          ReadMei
        </span>
      </div>

      <template v-if="paperStore.currentPaper">
        <span class="text-text-muted mx-1">/</span>
        <span class="text-sm text-text-primary font-medium truncate max-w-[400px]">
          {{ paperStore.currentPaper.title }}
        </span>
      </template>
    </div>

    <!-- Center: Search -->
    <div class="flex-1 flex justify-center max-w-md mx-auto">
      <div
        class="relative w-full"
      >
        <SearchOutlined
          class="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm"
        />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索论文、笔记..."
          class="w-full h-9 pl-9 pr-4 rounded-lg bg-surface border border-border text-sm
                 text-text-primary placeholder:text-text-muted
                 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30
                 transition-all duration-[var(--transition-fast)]"
        />
      </div>
    </div>

    <!-- Right: User & Settings -->
    <div class="flex items-center gap-2">
      <button
        class="w-9 h-9 rounded-lg flex items-center justify-center text-text-secondary
               hover:bg-surface-alt hover:text-text-primary transition-colors"
        title="设置"
        @click="showSettings = true"
      >
        <SettingOutlined />
      </button>
      <div
        class="w-9 h-9 rounded-full bg-primary-light/20 flex items-center justify-center
               text-primary cursor-pointer"
        :title="userStore.profile.researchDirection || '设置研究方向'"
      >
        <UserOutlined />
      </div>
    </div>

    <SettingsModal v-model:open="showSettings" />
  </header>
</template>
