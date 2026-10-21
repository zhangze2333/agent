<!--
ChatMessage.vue —— 单条聊天消息气泡（子组件）

【知识点：v-if / v-else 条件渲染】
用户的消息靠右、AI 的消息靠左，气泡样式也不同，
用 v-if / v-else 按 msg.role 切换两套模板。

【知识点：agent 执行动作的展示】
后端返回的 actions 数组记录了 AI 实际调用了哪些工具、传了什么参数。
把它显示出来，你就能"透视"智能体的大脑 —— 学习 Agent 原理时特别直观。
-->
<script setup>
defineProps({
  msg: { type: Object, required: true },
})

// 把工具调用记录翻译成人话
function describeAction(action) {
  const names = {
    add_todo: '➕ 创建待办',
    list_todos: '🔍 查询待办',
    complete_todo: '✅ 完成待办',
    delete_todo: '🗑️ 删除待办',
  }
  const label = names[action.tool] || action.tool
  // JSON.stringify 的第三个参数无意义，这里只是去掉引号让显示更干净
  const argsText = Object.entries(action.args || {})
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
  return argsText ? `${label}（${argsText}）` : label
}
</script>

<template>
  <div class="msg-row" :class="msg.role">
    <div class="avatar">{{ msg.role === 'user' ? '🧑' : '🤖' }}</div>
    <div class="bubble">
      <!-- AI 的回复：如果执行过工具，先显示动作记录 -->
      <div v-if="msg.actions && msg.actions.length" class="actions">
        <el-tag
          v-for="(action, i) in msg.actions"
          :key="i"
          size="small"
          type="success"
          effect="plain"
          class="action-tag"
        >
          {{ describeAction(action) }}
        </el-tag>
      </div>
      <div class="content">{{ msg.content }}</div>
    </div>
  </div>
</template>

<style scoped>
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.msg-row.user {
  flex-direction: row-reverse; /* 用户消息：头像在右 */
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #ebeef5;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-all;
  white-space: pre-wrap; /* 保留 AI 回复里的换行 */
}

.msg-row.user .bubble {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.action-tag {
  font-size: 12px;
}
</style>
