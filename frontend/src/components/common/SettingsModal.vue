<script setup lang="ts">
import { ref, watch } from 'vue'
import { useUserStore } from '@/stores'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const userStore = useUserStore()
const direction = ref(userStore.profile.researchDirection)
const keywordsText = ref(userStore.profile.keywords.join(', '))

watch(
  () => props.open,
  (val) => {
    if (val) {
      direction.value = userStore.profile.researchDirection
      keywordsText.value = userStore.profile.keywords.join(', ')
    }
  },
)

function save() {
  const keywords = keywordsText.value
    .split(/[,，]/)
    .map((k: string) => k.trim())
    .filter(Boolean)
  userStore.saveProfile({
    researchDirection: direction.value.trim(),
    keywords,
  })
  emit('update:open', false)
}

function cancel() {
  emit('update:open', false)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="cancel"
      >
        <div
          class="bg-panel rounded-xl shadow-dropdown w-full max-w-lg mx-4 p-6"
        >
          <h3 class="text-lg font-semibold text-text-primary mb-5">
            个人设置
          </h3>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-text-secondary mb-1.5">
                研究方向
              </label>
              <input
                v-model="direction"
                type="text"
                placeholder="例如：计算机视觉、自然语言处理、生物信息学"
                class="w-full h-10 px-3 rounded-lg border border-border bg-surface
                       text-sm text-text-primary placeholder:text-text-muted
                       focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-text-secondary mb-1.5">
                关键词（逗号分隔）
              </label>
              <input
                v-model="keywordsText"
                type="text"
                placeholder="例如：目标检测, Transformer, 数据增强"
                class="w-full h-10 px-3 rounded-lg border border-border bg-surface
                       text-sm text-text-primary placeholder:text-text-muted
                       focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
              />
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button
              class="px-4 h-9 rounded-lg text-sm text-text-secondary border border-border
                     hover:bg-surface-alt transition-colors"
              @click="cancel"
            >
              取消
            </button>
            <button
              class="px-4 h-9 rounded-lg text-sm text-white bg-primary
                     hover:bg-primary-light transition-colors"
              @click="save"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
