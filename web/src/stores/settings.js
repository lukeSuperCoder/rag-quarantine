import { defineStore } from 'pinia'

const STORAGE_KEY = 'quarantine-rag.settings.v1'

const defaults = {
  top_k: 5,
  rerank: false,
  temperature: 0.7,
  max_history: 20
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    form: loadSettings()
  }),
  actions: {
    update(next) {
      this.form = { ...this.form, ...next }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.form))
    },
    reset() {
      this.form = { ...defaults }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.form))
    }
  }
})

function loadSettings() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
  } catch {
    return { ...defaults }
  }
}
