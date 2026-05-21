<template>
  <div class="page-padded document-page">
    <section class="toolbar">
      <el-input v-model="store.filters.keyword" clearable placeholder="按文件名或文档名搜索" :prefix-icon="Search" @change="store.fetchList" />
      <el-select v-model="store.filters.status" clearable placeholder="处理状态" @change="store.fetchList">
        <el-option v-for="status in statusOptions" :key="status.value" :label="status.label" :value="status.value" />
      </el-select>
      <el-button :icon="Refresh" @click="store.fetchList">刷新</el-button>
      <el-upload :show-file-list="false" :auto-upload="false" :on-change="handleUploadChange" accept=".doc,.docx,.xls">
        <el-button type="primary" :icon="UploadFilled">上传文档</el-button>
      </el-upload>
    </section>

    <section class="panel table-panel">
      <el-table v-loading="store.loading" :data="store.items" height="100%">
        <el-table-column prop="doc_name" label="文档名" min-width="240" show-overflow-tooltip />
        <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="doc_type" label="类型" width="160" />
        <el-table-column prop="country" label="国家/地区" width="120" />
        <el-table-column prop="chunk_count" label="Chunks" width="90" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">详情</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-drawer v-model="detailVisible" title="文档处理详情" size="420px">
      <template v-if="store.detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="文档名">{{ store.detail.doc_name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ store.detail.doc_type }}</el-descriptions-item>
          <el-descriptions-item label="国家/地区">{{ store.detail.country }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(store.detail.status)">{{ statusLabel(store.detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="分块数">{{ store.detail.chunk_count }}</el-descriptions-item>
          <el-descriptions-item label="错误信息">{{ store.detail.error_message || '无' }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-preview">
          <div class="panel-title">转换文本预览</div>
          <p>{{ store.detail.txt_preview || '暂无预览' }}</p>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import { useDocumentsStore } from '../stores/documents'

const store = useDocumentsStore()
const detailVisible = ref(false)

const statusOptions = [
  { label: '已上传', value: 'uploaded' },
  { label: '转换中', value: 'converting' },
  { label: '分块中', value: 'chunking' },
  { label: '入库中', value: 'embedding' },
  { label: '已就绪', value: 'ready' },
  { label: '失败', value: 'failed' }
]

async function handleUploadChange(uploadFile) {
  const file = uploadFile.raw
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['doc', 'docx', 'xls'].includes(ext)) {
    ElMessage.error('仅支持 .doc、.docx、.xls 文件')
    return
  }
  await store.upload(file, { country: '待识别' })
  ElMessage.success('上传已提交，正在轮询处理状态')
}

async function openDetail(id) {
  await store.openDetail(id)
  detailVisible.value = true
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除「${row.doc_name}」及其向量数据？`, '删除确认', { type: 'warning' })
  await store.remove(row.id)
  ElMessage.success('已删除文档')
}

function statusLabel(value) {
  return statusOptions.find((item) => item.value === value)?.label || value
}

function statusType(value) {
  if (value === 'ready') return 'success'
  if (value === 'failed') return 'danger'
  if (['converting', 'chunking', 'embedding'].includes(value)) return 'warning'
  return 'info'
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : ''
}

onMounted(store.fetchList)
onBeforeUnmount(store.stopPolling)
</script>

<style scoped>
.document-page {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
}

.toolbar .el-input {
  max-width: 320px;
}

.toolbar .el-select {
  width: 160px;
}

.table-panel {
  min-height: 0;
  overflow: hidden;
  border-radius: var(--radius-md);
}

.table-panel :deep(.el-table__row) {
  transition: background var(--transition-fast);
}

.detail-preview {
  margin-top: 20px;
}

.detail-preview p {
  padding: 14px 18px;
  color: var(--text-secondary);
  line-height: 1.75;
  background: var(--primary-lightest);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
}
</style>
