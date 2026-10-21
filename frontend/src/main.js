/**
 * main.js —— 前端应用的入口
 *
 * 【知识点：一个 Vue 应用的启动过程】
 * 1. import App：根组件（App.vue）
 * 2. createApp(App)：创建应用实例
 * 3. .use(router)：安装路由，让页面之间能跳转
 * 4. .use(ElementPlus)：安装 UI 组件库，全局可用 el-xxx 组件
 * 5. .mount('#app')：把应用渲染到 index.html 里的 <div id="app"> 中
 */
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'

createApp(App).use(router).use(ElementPlus, { locale: zhCn }).mount('#app')
