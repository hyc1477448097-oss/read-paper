<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col bg-surface">
    <AppHeader />
    <RouterView v-slot="{ Component }">
      <Transition name="fade" mode="out-in">
        <component :is="Component" class="flex-1" />
      </Transition>
    </RouterView>
  </div>
</template>
