import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import DocumentsView from '../views/DocumentsView.vue'
import KnowledgeView from '../views/KnowledgeView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', name: 'chat', component: ChatView, meta: { title: '对话问答' } },
  { path: '/documents', name: 'documents', component: DocumentsView, meta: { title: '文档管理' } },
  { path: '/knowledge', name: 'knowledge', component: KnowledgeView, meta: { title: '知识库查询' } },
  { path: '/settings', name: 'settings', component: SettingsView, meta: { title: '问答设置' } }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
