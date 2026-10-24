<!--
App.vue —— 根组件：整个应用的"外壳"

【知识点：.vue 单文件组件（SFC）的三段结构】
  <template>  模板：HTML 结构，负责"长什么样"
  <script>    逻辑：数据、函数，负责"怎么动"
  <style>     样式：CSS，负责"怎么美"

【知识点：<router-view>】
  路由的"出口"：URL 匹配到哪个组件，哪个组件就渲染在这个标签的位置。
  <router-link> 会渲染成 <a>，但点击时不刷新页面，由路由切换组件。
-->
<script setup>
import { auth, clearAuth } from './stores/auth'

function handleLogout() {
  clearAuth()
  window.location.href = '/login' // 整页跳转，顺带清空所有页面状态
}
</script>

<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="logo">
        🤖 AI 待办助手
      </div>
      <nav class="nav">
        <router-link
          to="/"
          class="nav-link"
        >
          📋 待办列表
        </router-link>
        <router-link
          to="/chat"
          class="nav-link"
        >
          💬 AI 助手
        </router-link>
        <template v-if="auth.token">
          <span class="user-chip">👤 {{ auth.username }}</span>
          <el-button
            text
            size="small"
            @click="handleLogout"
          >
            退出
          </el-button>
        </template>
      </nav>
    </el-header>

    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
/* scoped：样式只作用于本组件，不会污染其他组件 */
.layout {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 10;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
}

.nav {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 6px 16px;
  border-radius: 6px;
  color: #606266;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

/* 当前页面对应的导航项会自动获得这个 class（router-link 的能力） */
.nav-link.router-link-active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}

.user-chip {
  color: #606266;
  font-size: 13px;
  padding: 0 4px;
}

.main {
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}
</style>
