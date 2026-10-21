/**
 * router/index.js —— 路由配置（页面导航）
 *
 * 【知识点：SPA 单页应用】
 * 整个网站其实只有一个 HTML，"换页"是 Vue Router 在切换显示不同的组件，
 * 不需要向服务器重新请求页面，所以快、丝滑。
 *
 * 路由表 = "URL 地址 -> 显示哪个组件"的映射：
 *   /       -> TodoList.vue（待办列表）
 *   /chat   -> Chat.vue（AI 聊天）
 */
import { createRouter, createWebHistory } from 'vue-router'
import TodoList from '../views/TodoList.vue'
import Chat from '../views/Chat.vue'

const router = createRouter({
  history: createWebHistory(), // 用浏览器真实的 URL（/chat），而不是 #/chat
  routes: [
    { path: '/', name: 'todos', component: TodoList },
    { path: '/chat', name: 'chat', component: Chat },
  ],
})

export default router
