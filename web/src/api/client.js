import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 5000
})

function unwrap(response) {
  const payload = response.data
  if (payload?.code !== 0) {
    throw new Error(payload?.message || '接口返回失败')
  }
  return payload.data
}

export async function getHealth() {
  return unwrap(await api.get('/api/health'))
}

export async function listSessions() {
  return unwrap(await api.get('/api/chat/sessions')).items
}

export async function createSession(title) {
  return unwrap(await api.post('/api/chat/sessions', { title }))
}

export async function renameSession(sessionId, title) {
  return unwrap(await api.put(`/api/chat/sessions/${sessionId}`, { title }))
}

export async function deleteSession(sessionId) {
  return unwrap(await api.delete(`/api/chat/sessions/${sessionId}`))
}

export async function listMessages(sessionId) {
  return unwrap(await api.get(`/api/chat/sessions/${sessionId}/messages`)).items
}

export async function sendChatStream(payload, handlers) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  if (!response.ok || !response.body) throw new Error('流式接口不可用')
  await readSseStream(response.body, handlers)
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

export async function listDocuments(params = {}) {
  return unwrap(await api.get('/api/documents', { params })).items
}

export async function uploadDocument(file, meta = {}) {
  const form = new FormData()
  form.append('file', file)
  if (meta.doc_type) form.append('doc_type', meta.doc_type)
  if (meta.country) form.append('country', meta.country)
  return unwrap(await api.post('/api/documents/upload', form))
}

export async function getDocument(documentId) {
  return unwrap(await api.get(`/api/documents/${documentId}`))
}

export async function deleteDocument(documentId) {
  return unwrap(await api.delete(`/api/documents/${documentId}`))
}

export async function searchKnowledge(params) {
  return unwrap(await api.get('/api/knowledge/search', { params })).items
}

export async function getChunk(chunkId) {
  return unwrap(await api.get(`/api/knowledge/chunks/${chunkId}`))
}

export async function updateChunk(chunkId, text) {
  return unwrap(await api.put(`/api/knowledge/chunks/${chunkId}`, { text }))
}
