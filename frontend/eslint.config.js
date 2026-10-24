/**
 * ESLint 9 扁平配置：JS/Vue 代码检查
 * 用法：npm run lint（检查并自动修复）
 */
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      // 声明浏览器环境：window/fetch/localStorage 等全局对象才不会被误报为未定义
      globals: { ...globals.browser },
    },
    rules: {
      // 组件文件名单词约束（Chat.vue 只有一个词）对这个小项目没意义，关闭
      'vue/multi-word-component-names': 'off',
    },
  },
]
