/**
 * api/index.js —— 后端接口调用层（基于 axios）
 *
 * 【v1.0 企业级新增：拦截器】
 * 拦截器 = axios 的"中间件"，每个请求/响应都先过一遍：
 * - 请求拦截器：自动带上 Authorization 头（组件再也不用自己管 token）
 * - 响应拦截器：收到 401（未登录/过期）统一踢回登录页
 *   —— "登录过期跳登录页"这个逻辑写一次，全应用生效
 */
import axios from 'axios'
import { auth, clearAuth } from '../stores/auth'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // AI 回复可能要几秒到几十秒，超时设长一点
})

// 请求拦截器：每个请求自动附带登录令牌
api.interceptors.request.use((config) => {
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// 响应拦截器：401 = 未登录或登录过期，清空登录态回登录页
api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err.response?.status === 401) {
      clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ───── 用户认证接口 ─────
export function authRegister(data) {
  return api.post('/auth/register', data) // data: {username, password}
}

export function authLogin(data) {
  return api.post('/auth/login', data)
}

export function authMe() {
  return api.get('/auth/me')
}

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
