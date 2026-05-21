import { defineStore } from 'pinia'
import { deleteDocument, getDocument, listDocuments, uploadDocument } from '../api/client'

export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    items: [],
    filters: {
      keyword: '',
      status: ''
    },
    detail: null,
    loading: false,
    pollingTimer: null
  }),
  actions: {
    async fetchList() {
      this.loading = true
      try {
        this.items = await listDocuments(this.filters)
      } finally {
        this.loading = false
      }
    },
    async upload(file, meta) {
      await uploadDocument(file, meta)
      await this.fetchList()
      this.startPolling()
    },
    async openDetail(id) {
      this.detail = await getDocument(id)
    },
    async remove(id) {
      await deleteDocument(id)
      await this.fetchList()
    },
    startPolling() {
      this.stopPolling()
      this.pollingTimer = window.setInterval(async () => {
        await this.fetchList()
        if (!this.items.some((item) => ['uploaded', 'converting', 'chunking', 'embedding'].includes(item.status))) {
          this.stopPolling()
        }
      }, 1600)
    },
    stopPolling() {
      if (this.pollingTimer) window.clearInterval(this.pollingTimer)
      this.pollingTimer = null
    }
  }
})
