import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserProfile } from '@/types'

const STORAGE_KEY = 'readmei_user_profile'

export const useUserStore = defineStore('user', () => {
  const profile = ref<UserProfile>(loadProfile())

  const hasProfile = computed(
    () => profile.value.researchDirection.trim().length > 0,
  )

  function loadProfile(): UserProfile {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) return JSON.parse(raw) as UserProfile
    } catch {
      // ignore
    }
    return { researchDirection: '', keywords: [] }
  }

  function saveProfile(p: UserProfile) {
    profile.value = p
    localStorage.setItem(STORAGE_KEY, JSON.stringify(p))
  }

  function updateResearchDirection(direction: string) {
    saveProfile({ ...profile.value, researchDirection: direction })
  }

  function updateKeywords(keywords: string[]) {
    saveProfile({ ...profile.value, keywords })
  }

  return {
    profile,
    hasProfile,
    saveProfile,
    updateResearchDirection,
    updateKeywords,
  }
})
