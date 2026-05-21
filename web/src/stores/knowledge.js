import { defineStore } from 'pinia'
import { getChunk, searchKnowledge, updateChunk } from '../api/client'

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    filters: {
      keyword: '隔离',
      doc_type: '',
      country: '',
      limit: 20
    },
    items: [],
    detail: null,
    loading: false
  }),
  actions: {
    async search() {
      this.loading = true
      try {
        this.items = await searchKnowledge(this.filters)
      } finally {
        this.loading = false
      }
    },
    async openChunk(chunkId) {
      this.detail = await getChunk(chunkId)
    },
    async saveChunk(text) {
      await updateChunk(this.detail.chunk_id, text)
      this.detail.text = text
      await this.search()
    }
  }
})
