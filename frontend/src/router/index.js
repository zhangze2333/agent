/**
 * router/index.js —— 路由配置（页面导航）+ 登录守卫
 *
 * 【v1.0 新增：全局前置守卫 beforeEach】
 * 每次路由跳转前都会经过它：没登录就去 /login。
 * 这就是"没登录打不开页面"的实现（后端 401 是第二道防线，两层缺一不可）。
 */
import { createRouter, createWebHistory } from 'vue-router'
import TodoList from '../views/TodoList.vue'
import Chat from '../views/Chat.vue'
import Login from '../views/Login.vue'
import { auth } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(), // 用浏览器真实的 URL（/chat），而不是 #/chat
  routes: [
    { path: '/', name: 'todos', component: TodoList },
    { path: '/chat', name: 'chat', component: Chat },
    { path: '/login', name: 'login', component: Login },
  ],
})

// 全局守卫：未登录只能访问 /login，其余一律跳登录页
router.beforeEach((to) => {
  if (to.path !== '/login' && !auth.token) {
    return '/login'
  }
})

export default router
