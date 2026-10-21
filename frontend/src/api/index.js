/**
 * api/index.js —— 后端接口调用层（基于 axios）
 *
 * 【知识点：为什么要单独抽一层 api 文件？】
 * 组件里不直接写 axios.get('http://127.0.0.1:8000/api/todos') 这种代码，
 * 而是统一在这里封装。好处：
 * 1. 后端地址改动时只改这一个文件
 * 2. 组件只管"调 fetchTodos()"，不用关心请求细节（关注点分离）
 *
 * 注意 baseURL 是 '/api'，配合 vite.config.js 的 proxy 转发到后端 8000 端口
 */
import axios from 'axios'

// 创建一个配置好的 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // AI 回复可能要几秒到几十秒，超时设长一点
})

// ───── 待办相关接口 ─────
export function fetchTodos(params) {
  return api.get('/todos', { params }) // params: {completed: false} 会拼成 ?completed=false
}

export function createTodo(data) {
  return api.post('/todos', data)
}

export function updateTodo(id, data) {
  return api.put(`/todos/${id}`, data)
}

export function deleteTodo(id) {
  return api.delete(`/todos/${id}`)
}

// ───── AI 聊天接口 ─────
export function sendChat(message) {
  return api.post('/chat', { message })
}
