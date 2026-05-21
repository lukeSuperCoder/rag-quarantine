<template>
  <div class="shell">
    <header class="app-header">
      <div class="header-title">宠物检疫政策智能问答</div>
      <div class="header-actions">
        <el-tag :type="healthTagType" effect="dark" size="small">{{ healthText }}</el-tag>
        <el-button size="small" :icon="Refresh" @click="refreshHealth">健康检查</el-button>
      </div>
    </header>

    <div class="shell-body">
      <aside class="app-sidebar">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path" class="menu-item">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </aside>

      <main class="app-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ChatDotRound, Collection, Files, Setting, Refresh } from '@element-plus/icons-vue'
import { useSystemStore } from './stores/system'

const systemStore = useSystemStore()

const navItems = [
  { path: '/chat', label: '对话问答', icon: ChatDotRound },
  { path: '/documents', label: '文档管理', icon: Files },
  { path: '/knowledge', label: '知识库查询', icon: Collection },
  { path: '/settings', label: '问答设置', icon: Setting }
]

const healthText = computed(() => {
  if (systemStore.healthStatus === 'ok') return '后端可用'
  if (systemStore.healthStatus === 'checking') return '检查中'
  return '未连接'
})

const healthTagType = computed(() => {
  if (systemStore.healthStatus === 'ok') return 'success'
  if (systemStore.healthStatus === 'checking') return 'info'
  return 'danger'
})

const refreshHealth = () => systemStore.checkHealth()

onMounted(refreshHealth)
</script>
