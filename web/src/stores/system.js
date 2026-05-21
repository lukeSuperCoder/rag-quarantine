import { defineStore } from 'pinia'
import { apiMode, getHealth } from '../api/client'

export const useSystemStore = defineStore('system', {
  state: () => ({
    healthStatus: 'checking',
    health: null
  }),
  actions: {
    async checkHealth() {
      this.healthStatus = 'checking'
      try {
        this.health = await getHealth()
        this.healthStatus = apiMode() === 'mock' ? 'mock' : 'ok'
      } catch (error) {
        this.healthStatus = 'down'
      }
    }
  }
})
