<template>
  <div class="page chat-page">
    <section class="session-pane">
      <div class="pane-header">
        <span>会话</span>
        <el-button type="primary" size="small" :icon="Plus" @click="chatStore.newSession">新建</el-button>
      </div>
      <div class="session-list">
        <button
          v-for="session in chatStore.sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === chatStore.activeSessionId }"
          @click="chatStore.selectSession(session.id)"
        >
          <span>{{ session.title }}</span>
          <small>{{ formatTime(session.updated_at) }}</small>
        </button>
      </div>
    </section>

    <section class="chat-workspace">
      <div class="chat-status">
        <div>
          <strong>{{ chatStore.activeSession?.title || '对话问答' }}</strong>
          <span class="muted">{{ chatStore.retrievalStatus || '等待提问' }}</span>
        </div>
        <el-switch v-model="settings.form.rerank" active-text="rerank" @change="persistSettings" />
      </div>

      <div ref="messageScroller" class="message-list">
        <el-empty v-if="!chatStore.messages.length" description="输入问题后开始检索宠物检疫政策知识库" />
        <article v-for="message in chatStore.messages" :key="message.id" class="message" :class="message.role">
          <div class="message-role">{{ message.role === 'user' ? '用户' : '助手' }}</div>
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
        <span>本轮引用</span>
        <el-tag size="small">{{ chatStore.sources.length }}</el-tag>
      </div>
      <div class="source-list">
        <el-empty v-if="!chatStore.sources.length" description="回答产生后显示引用来源" />
        <div v-for="source in chatStore.sources" :key="source.chunk_id" class="source-item">
          <div class="source-title">{{ source.doc_name }}</div>
          <div class="source-meta">
            {{ source.section_title || '未分章节' }} · chunk {{ source.chunk_index }}
          </div>
          <p>{{ source.text }}</p>
          <el-tag v-if="source.score" size="small" type="info">score {{ source.score }}</el-tag>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { nextTick, onMounted, ref, watch } from 'vue'
import { Plus, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
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
  grid-template-columns: 260px minmax(0, 1fr) 320px;
  min-height: 0;
  background: var(--content-bg);
}

.session-pane,
.source-pane {
  min-width: 0;
  min-height: 0;
  background: #fff;
  border-right: 1px solid var(--panel-border);
  overflow: hidden;
}

.source-pane {
  border-right: 0;
  border-left: 1px solid var(--panel-border);
}

.pane-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  font-size: 15px;
  font-weight: 700;
  border-bottom: 1px solid var(--panel-border);
}

.session-list,
.source-list {
  height: calc(100vh - var(--header-height) - 48px);
  overflow: auto;
}

.session-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  text-align: left;
  color: var(--text-main);
  background: transparent;
  border: 0;
  border-left: 3px solid transparent;
  cursor: pointer;
}

.session-item:hover,
.session-item.active {
  background: #f0f6ff;
  border-left-color: var(--accent);
}

.session-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
}

.session-item small {
  color: var(--text-secondary);
}

.chat-workspace {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: 48px minmax(0, 1fr) 128px;
  height: 100%;
}

.chat-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--panel-border);
  background: #fff;
}

.chat-status > div {
  display: flex;
  align-items: center;
  gap: 12px;
}

.message-list {
  min-height: 0;
  overflow: auto;
  padding: 16px 18px;
}

.message {
  max-width: 880px;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.message.user {
  margin-left: auto;
}

.message-role {
  width: 44px;
  height: 28px;
  line-height: 28px;
  text-align: center;
  color: #fff;
  background: #607d9f;
  border-radius: 4px;
  font-size: 13px;
}

.message.user .message-role {
  background: var(--accent);
}

.message-content {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  background: #fff;
  font-size: 14px;
}

.message.user .message-content {
  color: #fff;
  border-color: var(--accent);
  background: var(--accent);
}

.chat-input {
  padding: 12px 16px;
  border-top: 1px solid var(--panel-border);
  background: #fff;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.source-item {
  padding: 12px;
  border-bottom: 1px solid var(--panel-border);
}

.source-title {
  font-weight: 700;
  line-height: 1.4;
}

.source-meta {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 13px;
}

.source-item p {
  max-height: 72px;
  overflow: hidden;
  margin: 8px 0;
  color: var(--text-main);
  font-size: 13px;
  line-height: 1.6;
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
    border-bottom: 1px solid var(--panel-border);
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
    grid-template-columns: 40px minmax(0, 1fr);
  }

  .message-list {
    padding: 12px;
  }
}
</style>
