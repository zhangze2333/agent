/**
 * stores/auth.js —— 登录态管理（token + 用户名）
 *
 * 【知识点：为什么不用 Pinia 也要抽这个文件？】
 * 登录态被三个地方使用：axios 拦截器（带 token）、路由守卫（判断登录）、
 * 导航栏（显示用户名/退出）。抽成一个共享的 reactive 对象，
 * 改一处全应用生效。（等页面间共享的数据多了，再升级到 Pinia，思路一样）
 *
 * token 存 localStorage：刷新页面/关浏览器还在（持久登录）。
 * 代价是 XSS 攻击能偷 token——企业级更严谨的做法是 HttpOnly Cookie，
 * 学习阶段 localStorage 足够，注释里先记住这个权衡。
 */
import { reactive } from 'vue'

const TOKEN_KEY = 'agent_token'
const USERNAME_KEY = 'agent_username'

export const auth = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  username: localStorage.getItem(USERNAME_KEY) || '',
})

export function setAuth(token, username) {
  auth.token = token
  auth.username = username
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USERNAME_KEY, username)
}

export function clearAuth() {
  auth.token = ''
  auth.username = ''
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USERNAME_KEY)
}
