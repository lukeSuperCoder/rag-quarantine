<template>
  <div class="page-padded knowledge-page">
    <section class="toolbar">
      <el-input v-model="store.filters.keyword" placeholder="输入关键词，如：隔离、狂犬病、口岸" :prefix-icon="Search" clearable @keyup.enter="store.search" />
      <el-input v-model="store.filters.country" placeholder="国家/地区" clearable />
      <el-select v-model="store.filters.doc_type" clearable placeholder="文档类型">
        <el-option label="入境法规" value="entry_regulation" />
        <el-option label="出境要求" value="country_export_req" />
        <el-option label="口岸名单" value="port_list" />
        <el-option label="实验室名单" value="lab_list" />
      </el-select>
      <el-button type="primary" :icon="Search" :loading="store.loading" @click="store.search">搜索</el-button>
    </section>

    <section class="knowledge-content">
      <div class="panel result-panel">
        <div class="panel-header">
          <span class="panel-title">知识片段</span>
          <el-tag size="small">{{ store.items.length }}</el-tag>
        </div>
        <div class="result-list">
          <el-empty v-if="!store.items.length" description="暂无匹配片段" />
          <button v-for="item in store.items" :key="item.chunk_id" class="chunk-row" @click="openChunk(item.chunk_id)">
            <div class="chunk-title">{{ item.doc_name }}</div>
            <div class="chunk-meta">{{ item.country || '未标注' }} · {{ item.section_title || '未分章节' }} · chunk {{ item.chunk_index }}</div>
            <p>{{ item.text }}</p>
          </button>
        </div>
      </div>

      <el-drawer v-model="drawerVisible" title="片段详情" size="480px">
        <template v-if="store.detail">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="来源文档">{{ store.detail.doc_name }}</el-descriptions-item>
            <el-descriptions-item label="章节">{{ store.detail.section_title || '未分章节' }}</el-descriptions-item>
            <el-descriptions-item label="Chunk">{{ store.detail.chunk_index }}</el-descriptions-item>
          </el-descriptions>
          <el-input v-model="editingText" class="chunk-editor" type="textarea" :rows="10" resize="none" />
          <div class="drawer-actions">
            <el-button @click="drawerVisible = false">取消</el-button>
            <el-button type="primary" @click="saveChunk">保存并重新 embedding</el-button>
          </div>
        </template>
      </el-drawer>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useKnowledgeStore } from '../stores/knowledge'

const store = useKnowledgeStore()
const drawerVisible = ref(false)
const editingText = ref('')

async function openChunk(chunkId) {
  await store.openChunk(chunkId)
  editingText.value = store.detail?.text || ''
  drawerVisible.value = true
}

async function saveChunk() {
  await store.saveChunk(editingText.value)
  ElMessage.success('片段已保存，后端应重新生成 embedding')
  drawerVisible.value = false
}

onMounted(store.search)
</script>

<style scoped>
.knowledge-page {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
}

.toolbar .el-input:first-child {
  max-width: 360px;
}

.toolbar .el-input:not(:first-child),
.toolbar .el-select {
  width: 160px;
}

.knowledge-content,
.result-panel {
  min-height: 0;
}

.result-panel {
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.result-list {
  overflow: auto;
}

.chunk-row {
  width: 100%;
  padding: 16px 18px;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all var(--transition-base);
}

.chunk-row:hover {
  background: rgba(13, 148, 136, 0.04);
}

.chunk-title {
  font-weight: 700;
  color: var(--text-primary);
}

.chunk-meta {
  margin-top: 5px;
  color: var(--text-tertiary);
  font-size: 12px;
  letter-spacing: 0.3px;
}

.chunk-row p {
  margin: 10px 0 0;
  color: var(--text-secondary);
  line-height: 1.7;
  font-size: 13px;
}

.chunk-editor {
  margin-top: 20px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
</style>
