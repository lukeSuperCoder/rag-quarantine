<template>
  <div class="page-padded settings-page">
    <section class="panel settings-panel">
      <div class="panel-header">
        <span class="panel-title">问答参数</span>
        <el-button size="small" @click="reset">恢复默认</el-button>
      </div>
      <el-form label-width="140px" class="settings-form">
        <el-form-item label="引用片段 top_k">
          <el-input-number v-model="localForm.top_k" :min="1" :max="20" />
          <span class="form-help">每轮检索返回的候选知识片段数量</span>
        </el-form-item>
        <el-form-item label="启用重排序">
          <el-switch v-model="localForm.rerank" />
          <span class="form-help">发送问答请求时传递 rerank 参数</span>
        </el-form-item>
        <el-form-item label="temperature">
          <el-slider v-model="localForm.temperature" :min="0" :max="1.5" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="最大历史轮数">
          <el-input-number v-model="localForm.max_history" :min="1" :max="50" />
          <span class="form-help">后端读取会话历史时的上限</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="save">保存设置</el-button>
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useSettingsStore } from '../stores/settings'

const settings = useSettingsStore()
const localForm = reactive({ ...settings.form })

function save() {
  settings.update(localForm)
  ElMessage.success('设置已保存')
}

function reset() {
  settings.reset()
  Object.assign(localForm, settings.form)
}
</script>

<style scoped>
.settings-page {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 40px;
}

.settings-panel {
  width: min(680px, 100%);
  box-shadow: var(--shadow-md);
}

.settings-form {
  padding: 24px 28px 16px;
}

.form-help {
  margin-left: 14px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.settings-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-primary);
}
</style>
