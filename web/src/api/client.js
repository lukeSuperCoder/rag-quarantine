import axios from 'axios'
import { ElMessage } from 'element-plus'
import { createMockDocument, createMockSession, mockDocuments, mockMessages, mockSessions, mockSources } from './mockData'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 5000
})

let useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const sessionState = [...mockSessions]
const messageState = structuredClone(mockMessages)
const documentState = [...mockDocuments]

function unwrap(response) {
  const payload = response.data
  if (payload?.code !== 0) {
    throw new Error(payload?.message || '接口返回失败')
  }
  return payload.data
}

async function requestWithMock(realRequest, mockRequest) {
  if (useMock) return mockRequest()
  try {
    return await realRequest()
  } catch (error) {
    ElMessage.warning('后端暂不可用，已切换 Mock 联调数据')
    useMock = true
    return mockRequest()
  }
}

export const apiMode = () => (useMock ? 'mock' : 'real')

export async function getHealth() {
  return requestWithMock(
    async () => unwrap(await api.get('/api/health')),
    async () => ({
      service: 'mock',
      sqlite: 'mock',
      milvus: 'mock',
      zhipu_api_key: 'mock'
    })
  )
}

export async function listSessions() {
  return requestWithMock(
    async () => unwrap(await api.get('/api/chat/sessions')).items,
    async () => structuredClone(sessionState)
  )
}

export async function createSession(title) {
  return requestWithMock(
    async () => unwrap(await api.post('/api/chat/sessions', { title })),
    async () => {
      const session = createMockSession(title)
      sessionState.unshift(session)
      messageState[session.id] = []
      return session
    }
  )
}

export async function listMessages(sessionId) {
  return requestWithMock(
    async () => unwrap(await api.get(`/api/chat/sessions/${sessionId}/messages`)).items,
    async () => structuredClone(messageState[sessionId] || [])
  )
}

export async function sendChatStream(payload, handlers) {
  if (useMock) {
    return mockChatStream(payload, handlers)
  }

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!response.ok || !response.body) throw new Error('流式接口不可用')
    await readSseStream(response.body, handlers)
  } catch (error) {
    ElMessage.warning('流式接口暂不可用，已使用 Mock SSE 事件联调')
    useMock = true
    await mockChatStream(payload, handlers)
  }
}

async function readSseStream(body, handlers) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const block of events) dispatchSseBlock(block, handlers)
  }
}

function dispatchSseBlock(block, handlers) {
  const lines = block.split('\n')
  const event = lines.find((line) => line.startsWith('event:'))?.replace('event:', '').trim()
  const dataLine = lines.find((line) => line.startsWith('data:'))?.replace('data:', '').trim()
  if (!event || !dataLine) return
  handlers[event]?.(JSON.parse(dataLine))
}

async function mockChatStream(payload, handlers) {
  const sourceItems = mockSources.slice(0, payload.top_k || 5)
  handlers.retrieve_start?.({ query: payload.question, top_k: payload.top_k, rerank: payload.rerank })
  await wait(240)
  handlers.retrieve_done?.({ count: sourceItems.length })
  await wait(260)
  handlers.sources?.({ items: sourceItems })

  const answer = [
    '根据当前知识库，宠物入境中国是否需要隔离，主要看三个条件：',
    '\n\n1. 来源国家或地区是否属于指定范围；',
    '\n2. 是否提供有效的狂犬病疫苗接种和抗体检测材料；',
    '\n3. 入境口岸是否具备相应检疫条件。',
    '\n\n如果材料不完整、检测报告不被采信，或不满足免隔离条件，通常需要进入指定隔离场接受隔离检疫。建议出行前按目的地海关口岸要求核对材料。'
  ]

  for (const delta of answer) {
    handlers.delta?.({ content: delta })
    await wait(180)
  }

  const assistant = {
    id: `msg_${Date.now()}`,
    session_id: payload.session_id,
    role: 'assistant',
    content: answer.join(''),
    sources: sourceItems,
    created_at: new Date().toISOString()
  }
  messageState[payload.session_id] = messageState[payload.session_id] || []
  messageState[payload.session_id].push({
    id: `msg_user_${Date.now()}`,
    session_id: payload.session_id,
    role: 'user',
    content: payload.question,
    sources: [],
    created_at: new Date().toISOString()
  })
  messageState[payload.session_id].push(assistant)
  handlers.done?.({ message_id: assistant.id, session_id: payload.session_id })
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function listDocuments(params = {}) {
  return requestWithMock(
    async () => unwrap(await api.get('/api/documents', { params })).items,
    async () => structuredClone(documentState.filter((doc) => {
      const keywordOk = !params.keyword || `${doc.filename}${doc.doc_name}`.includes(params.keyword)
      const statusOk = !params.status || doc.status === params.status
      return keywordOk && statusOk
    }))
  )
}

export async function uploadDocument(file, meta = {}) {
  return requestWithMock(
    async () => {
      const form = new FormData()
      form.append('file', file)
      if (meta.doc_type) form.append('doc_type', meta.doc_type)
      if (meta.country) form.append('country', meta.country)
      return unwrap(await api.post('/api/documents/upload', form))
    },
    async () => {
      const doc = createMockDocument(file, meta)
      documentState.unshift(doc)
      setTimeout(() => {
        doc.status = 'ready'
        doc.chunk_count = 6
        doc.updated_at = new Date().toISOString()
      }, 1800)
      return { document_id: doc.id, filename: doc.filename, status: doc.status }
    }
  )
}

export async function getDocument(documentId) {
  return requestWithMock(
    async () => unwrap(await api.get(`/api/documents/${documentId}`)),
    async () => {
      const doc = documentState.find((item) => item.id === documentId)
      return {
        ...doc,
        txt_preview: '文档转换后的文本预览会显示在这里，用于联调详情抽屉和处理状态展示。'
      }
    }
  )
}

export async function deleteDocument(documentId) {
  return requestWithMock(
    async () => unwrap(await api.delete(`/api/documents/${documentId}`)),
    async () => {
      const index = documentState.findIndex((item) => item.id === documentId)
      if (index >= 0) documentState.splice(index, 1)
      return { document_id: documentId, deleted: true }
    }
  )
}

export async function searchKnowledge(params) {
  return requestWithMock(
    async () => unwrap(await api.get('/api/knowledge/search', { params })).items,
    async () => mockSources
      .filter((item) => {
        const keywordOk = !params.keyword || item.text.includes(params.keyword) || item.doc_name.includes(params.keyword)
        const typeOk = !params.doc_type || item.doc_type === params.doc_type
        const countryOk = !params.country || item.country.includes(params.country)
        return keywordOk && typeOk && countryOk
      })
      .slice(0, params.limit || 20)
  )
}

export async function getChunk(chunkId) {
  return requestWithMock(
    async () => unwrap(await api.get(`/api/knowledge/chunks/${chunkId}`)),
    async () => mockSources.find((item) => item.chunk_id === chunkId)
  )
}

export async function updateChunk(chunkId, text) {
  return requestWithMock(
    async () => unwrap(await api.put(`/api/knowledge/chunks/${chunkId}`, { text })),
    async () => {
      const item = mockSources.find((chunk) => chunk.chunk_id === chunkId)
      if (item) item.text = text
      return { chunk_id: chunkId, updated: true, reembedded: true }
    }
  )
}
