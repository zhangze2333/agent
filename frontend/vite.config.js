/**
 * vite.config.js —— Vite 构建工具的配置文件
 *
 * 【知识点：Vite 是什么？】
 * 浏览器不能直接认识 .vue 这种单文件组件，Vite 负责把项目"翻译"成浏览器
 * 能跑的标准 JS/CSS。开发时它还提供 dev server（npm run dev）。
 *
 * 【知识点：proxy 代理 —— 前后端联调的关键】
 * 开发时前端跑在 5173 端口，后端跑在 8010 端口。
 * 前端代码里所有请求都写相对路径 /api/xxx，
 * Vite 开发服务器会把 /api 开头的请求自动转发给后端 8010 端口。
 * 好处1：前端代码不用区分开发/生产环境的后端地址
 * 好处2：浏览器看到的是同源请求，不会有跨域问题（双保险，后端也开了 CORS）
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
})
