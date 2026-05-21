<template>
  <div class="page chat-page">
    <section class="session-pane">
      <div class="pane-header">
        <span>会话</span>
        <el-button type="primary" size="small" :icon="Plus" @click="chatStore.newSession">新建</el-button>
      </div>
      <div class="session-list">
        <div
          v-for="session in chatStore.sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === chatStore.activeSessionId }"
          @click="chatStore.selectSession(session.id)"
        >
          <template v-if="renamingId === session.id">
            <input
              ref="renameInput"
              v-model="renameTitle"
              class="rename-input"
              @keydown.enter.prevent="confirmRename(session.id)"
              @keydown.escape.prevent="cancelRename"
              @blur="confirmRename(session.id)"
            />
          </template>
          <template v-else>
            <span class="session-title">{{ session.title }}</span>
            <small>{{ formatTime(session.updated_at) }}</small>
          </template>
          <div class="session-actions" @click.stop>
            <el-icon class="action-btn" @click="startRename(session)"><Edit /></el-icon>
            <el-icon class="action-btn" @click="handleDelete(session)"><Delete /></el-icon>
          </div>
        </div>
      </div>
    </section>

    <section class="chat-workspace">
      <div class="chat-status">
        <div>
          <strong>{{ chatStore.activeSession?.title || '对话问答' }}</strong>
          <span class="muted">{{ chatStore.retrievalStatus || '等待提问' }}</span>
        </div>
        <el-switch v-model="settings.form.rerank" active-text="专家模式" @change="persistSettings" />
      </div>

      <div ref="messageScroller" class="message-list">
        <el-empty v-if="!chatStore.messages.length" description="输入问题后开始检索宠物检疫政策知识库" />
        <article v-for="message in chatStore.messages" :key="message.id" class="message" :class="message.role">
          <div class="message-avatar" :class="message.role">
            <svg v-if="message.role === 'user'" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path d="M823.04 970.24a44.992 44.992 0 0 1-45.824-45.824v-131.328c0-102.4-44.288-145.152-145.088-145.152H364.8c-102.4 0-145.152 44.288-145.152 145.152v131.328c0 25.984-19.84 45.824-45.824 45.824A44.992 44.992 0 0 1 128 924.48v-131.328c0-152.768 84.032-236.8 236.8-236.8h267.328c152.704 0 236.8 84.032 236.8 236.8v131.328c0 24.448-19.904 45.824-45.888 45.824zM497.664 518.08a232.064 232.064 0 0 1-232.192-232.192A232.064 232.064 0 0 1 497.664 53.76a232.064 232.064 0 0 1 232.192 232.192 232.064 232.064 0 0 1-232.192 232.192z m0-372.672A140.16 140.16 0 0 0 357.12 285.888a140.16 140.16 0 0 0 140.544 140.544 140.16 140.16 0 0 0 140.544-140.544 140.16 140.16 0 0 0-140.544-140.48z" fill="currentColor"/></svg>
            <svg v-else viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path d="M717.12 274H762c82.842 0 150 67.158 150 150v200c0 82.842-67.158 150-150 150H262c-82.842 0-150-67.158-150-150V424c0-82.842 67.158-150 150-150h44.88l-18.268-109.602c-4.086-24.514 12.476-47.7 36.99-51.786 24.514-4.086 47.7 12.476 51.786 36.99l20 120c0.246 1.472 0.416 2.94 0.516 4.398h228.192c0.1-1.46 0.27-2.926 0.516-4.398l20-120c4.086-24.514 27.272-41.076 51.786-36.99 24.514 4.086 41.076 27.272 36.99 51.786L717.12 274zM308 484v40c0 24.852 20.148 45 45 45S398 548.852 398 524v-40c0-24.852-20.148-45-45-45S308 459.148 308 484z m318 0v40c0 24.852 20.148 45 45 45S716 548.852 716 524v-40c0-24.852-20.148-45-45-45S626 459.148 626 484zM312 912c-24.852 0-45-20.148-45-45S287.148 822 312 822h400c24.852 0 45 20.148 45 45S736.852 912 712 912H312z" fill="currentColor"/></svg>
          </div>
          <div v-if="message.role === 'assistant'" class="message-content markdown-body" v-html="renderMarkdown(message.content || '正在生成回答...')" />
          <div v-else class="message-content">{{ message.content }}</div>
        </article>
      </div>

      <footer class="chat-input">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="请输入宠物入境、出境、疫苗、隔离、口岸等检疫政策问题"
          @keydown.enter.exact.prevent="send"
        />
        <div class="input-actions">
          <span class="muted">Enter 发送，Shift+Enter 换行</span>
          <el-button type="primary" :icon="Promotion" :loading="chatStore.loading" @click="send">发送</el-button>
        </div>
      </footer>
    </section>

    <aside class="source-pane">
      <div class="pane-header">
        <span>参考资料</span>
        <el-tag size="small" type="info">{{ chatStore.sources.length }}</el-tag>
      </div>
      <div class="source-list">
        <el-empty v-if="!chatStore.sources.length" description="回答产生后显示引用来源" />
        <div v-for="source in chatStore.sources" :key="source.chunk_id" class="source-item" @click="previewSource = source">
          <div class="source-title">{{ source.doc_name }}</div>
          <div class="source-text">{{ source.text }}</div>
        </div>
      </div>

      <el-dialog v-model="sourceDialogVisible" :title="previewSource?.doc_name" width="640px" append-to-body>
        <div class="source-dialog-body">{{ previewSource?.text }}</div>
      </el-dialog>
    </aside>
  </div>
</template>

<script setup>
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Plus, Promotion, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '../stores/chat'
import { useSettingsStore } from '../stores/settings'

const md = new MarkdownIt({
  breaks: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return `<pre><code class="hljs">${hljs.highlight(str, { language: lang }).value}</code></pre>`
    }
    return `<pre><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
  }
})

const chatStore = useChatStore()
const settings = useSettingsStore()
const question = ref('')
const messageScroller = ref(null)
const previewSource = ref(null)
const sourceDialogVisible = computed({
  get: () => !!previewSource.value,
  set: (v) => { if (!v) previewSource.value = null }
})

const renamingId = ref('')
const renameTitle = ref('')

function startRename(session) {
  renamingId.value = session.id
  renameTitle.value = session.title
}

async function confirmRename(sessionId) {
  const title = renameTitle.value.trim()
  if (!title || !renamingId.value) return cancelRename()
  renamingId.value = ''
  await chatStore.rename(sessionId, title)
}

function cancelRename() {
  renamingId.value = ''
  renameTitle.value = ''
}

async function handleDelete(session) {
  try {
    await ElMessageBox.confirm(`确定删除「${session.title}」？`, '删除会话', { type: 'warning' })
    await chatStore.remove(session.id)
  } catch { /* cancelled */ }
}

const renderMarkdown = (content) => md.render(content)

async function send() {
  const content = question.value.trim()
  if (!content) {
    ElMessage.warning('请输入问题')
    return
  }
  question.value = ''
  await chatStore.send(content, settings.form)
}

function persistSettings() {
  settings.update({ rerank: settings.form.rerank })
}

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

watch(
  () => chatStore.messages.map((item) => item.content).join('|'),
  async () => {
    await nextTick()
    if (messageScroller.value) messageScroller.value.scrollTop = messageScroller.value.scrollHeight
  }
)

onMounted(() => chatStore.bootstrap())
</script>

<style scoped>
.chat-page {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 340px;
  min-height: 0;
  background: transparent;
}

.session-pane,
.source-pane {
  min-width: 0;
  min-height: 0;
  background: var(--glass-bg-strong);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  overflow: hidden;
}

.session-pane {
  border-right: 1px solid var(--border-light);
}

.source-pane {
  border-right: 0;
  border-left: 1px solid var(--border-light);
}

.pane-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  font-family: "Noto Serif SC", "Source Han Serif SC", Georgia, serif;
  font-size: 15px;
  font-weight: 600;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
}

.session-list,
.source-list {
  height: calc(100vh - var(--header-height) - 56px);
  overflow: auto;
}

.session-item {
  width: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 13px 18px;
  text-align: left;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  border-left: 3px solid transparent;
  cursor: pointer;
  transition: all var(--transition-base);
}

.session-item:hover {
  background: rgba(13, 148, 136, 0.04);
}

.session-item.active {
  background: rgba(13, 148, 136, 0.08);
  border-left-color: var(--primary);
}

.session-item:hover .session-actions {
  opacity: 1;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  padding-right: 52px;
}

.session-item small {
  color: var(--text-tertiary);
  font-size: 12px;
}

.session-actions {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.action-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xs);
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 14px;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: rgba(13, 148, 136, 0.1);
  color: var(--primary);
}

.rename-input {
  width: 100%;
  font-size: 14px;
  font-weight: 600;
  padding: 4px 8px;
  border: 1.5px solid var(--primary);
  border-radius: var(--radius-xs);
  outline: none;
  background: var(--bg-overlay);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.08);
}

.chat-workspace {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: 56px minmax(0, 1fr) 140px;
  height: 100%;
}

.chat-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--glass-bg-strong);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}

.chat-status > div {
  display: flex;
  align-items: center;
  gap: 14px;
}

.chat-status strong {
  font-family: "Noto Serif SC", "Source Han Serif SC", Georgia, serif;
  font-size: 15px;
}

.message-list {
  min-height: 0;
  overflow: auto;
  padding: 24px 20px;
}

.message {
  max-width: 860px;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 12px;
  margin-bottom: 18px;
  animation: fadeInUp 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.message.user {
  margin-left: auto;
}

.message-avatar {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--dark-700);
  border-radius: 50%;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.message-avatar svg {
  width: 20px;
  height: 20px;
}

.message.user .message-avatar {
  background: var(--primary);
}

.message-content {
  min-width: 0;
  padding: 14px 18px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-overlay);
  font-size: 14px;
  line-height: 1.7;
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--transition-fast);
}

.message.user .message-content {
  color: #fff;
  border-color: var(--primary);
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  box-shadow: 0 3px 14px rgba(13, 148, 136, 0.2);
}

.chat-input {
  padding: 14px 20px;
  border-top: 1px solid var(--border-subtle);
  background: var(--glass-bg-strong);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.source-item {
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all var(--transition-base);
}

.source-item:hover {
  background: rgba(13, 148, 136, 0.04);
}

.source-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-text {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.source-dialog-body {
  max-height: 60vh;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.85;
  white-space: pre-wrap;
  color: var(--text-primary);
  padding: 8px 0;
}

@media (max-width: 1100px) {
  .chat-page {
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .source-pane {
    display: none;
  }
}

@media (max-width: 768px) {
  .chat-page {
    grid-template-columns: 1fr;
    grid-template-rows: 156px minmax(0, 1fr);
  }

  .session-pane {
    border-right: 0;
    border-bottom: 1px solid var(--border-light);
  }

  .session-list {
    height: 108px;
  }

  .session-item {
    min-height: 54px;
  }

  .chat-workspace {
    grid-template-rows: 48px minmax(0, 1fr) 128px;
    min-height: 0;
  }

  .message {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .message-list {
    padding: 14px;
  }
}
</style>
