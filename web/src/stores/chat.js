import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { createSession, listMessages, listSessions, sendChatStream } from '../api/client'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    activeSessionId: '',
    messages: [],
    sources: [],
    retrievalStatus: '',
    loading: false
  }),
  getters: {
    activeSession(state) {
      return state.sessions.find((item) => item.id === state.activeSessionId)
    }
  },
  actions: {
    async bootstrap() {
      this.sessions = await listSessions()
      if (!this.sessions.length) {
        const session = await createSession('新的宠物检疫咨询')
        this.sessions = [session]
      }
      await this.selectSession(this.sessions[0].id)
    },
    async selectSession(sessionId) {
      this.activeSessionId = sessionId
      this.messages = await listMessages(sessionId)
      const lastAssistant = [...this.messages].reverse().find((item) => item.role === 'assistant' && item.sources?.length)
      this.sources = lastAssistant?.sources || []
      this.retrievalStatus = ''
    },
    async newSession() {
      const session = await createSession('新的宠物检疫咨询')
      this.sessions.unshift(session)
      await this.selectSession(session.id)
    },
    async send(question, settings) {
      if (!this.activeSessionId || this.loading) return

      const userMessage = {
        id: `local_user_${Date.now()}`,
        session_id: this.activeSessionId,
        role: 'user',
        content: question,
        sources: [],
        created_at: new Date().toISOString()
      }
      const assistantMessage = {
        id: `local_assistant_${Date.now()}`,
        session_id: this.activeSessionId,
        role: 'assistant',
        content: '',
        sources: [],
        created_at: new Date().toISOString()
      }

      this.messages.push(userMessage, assistantMessage)
      this.sources = []
      this.loading = true
      this.retrievalStatus = '准备检索知识库'

      try {
        await sendChatStream(
          {
            session_id: this.activeSessionId,
            question,
            ...settings
          },
          {
            retrieve_start: (data) => {
              this.retrievalStatus = `检索中：top_k=${data.top_k}，rerank=${data.rerank ? '开启' : '关闭'}`
            },
            retrieve_done: (data) => {
              this.retrievalStatus = `已检索到 ${data.count} 条来源`
            },
            delta: (data) => {
              assistantMessage.content += data.content
            },
            sources: (data) => {
              assistantMessage.sources = data.items || []
              this.sources = data.items || []
            },
            done: (data) => {
              assistantMessage.id = data.message_id || assistantMessage.id
              this.retrievalStatus = '回答完成'
            },
            error: (data) => {
              throw new Error(data.message || '模型调用失败')
            }
          }
        )
      } catch (error) {
        assistantMessage.content = `问答失败：${error.message}`
        ElMessage.error(error.message)
      } finally {
        this.loading = false
        this.sessions = await listSessions()
      }
    }
  }
})
