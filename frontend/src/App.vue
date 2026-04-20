<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
</script>

<template>
  <div class="h-screen flex flex-col overflow-hidden bg-surface">
    <AppHeader />
    <RouterView v-slot="{ Component }">
      <Transition name="fade" mode="out-in">
        <component :is="Component" class="flex-1" />
      </Transition>
    </RouterView>
  </div>
</template>
