<!--
ChatMessage.vue —— 单条聊天消息气泡（子组件）

v0.3 新增：深度思考块（ZCode/Claude 同款交互）
  - 灰色小字展示模型的推理过程（reasoning）
  - 思考进行中（正文还没出现）：默认展开，实时滚动
  - 正文开始出现：自动收起成一行「💭 已深度思考」，点击可再展开
  - 用 watch 监听 msg.content 的变化来触发自动收起
-->
<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  msg: { type: Object, required: true },
})

// 展开状态的初始值：如果组件创建时还没有正文，说明正在思考，默认展开
const expanded = ref(!props.msg.content)

// 正文一旦开始流式出现，自动收起思考块
watch(
  () => props.msg.content,
  (v) => {
    if (v) expanded.value = false
  }
)

// 把工具调用记录翻译成人话
function describeAction(action) {
  const names = {
    add_todo: '➕ 创建待办',
    list_todos: '🔍 查询待办',
    complete_todo: '✅ 完成待办',
    delete_todo: '🗑️ 删除待办',
  }
  const label = names[action.tool] || action.tool
  const argsText = Object.entries(action.args || {})
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
  return argsText ? `${label}（${argsText}）` : label
}
</script>

<template>
  <div
    class="msg-row"
    :class="msg.role"
  >
    <div class="avatar">
      {{ msg.role === 'user' ? '🧑' : '🤖' }}
    </div>
    <div class="bubble">
      <!-- 深度思考块：模型的推理草稿，灰色弱化展示 -->
      <div
        v-if="msg.reasoning"
        class="reasoning"
      >
        <div
          class="reasoning-head"
          @click="expanded = !expanded"
        >
          <span class="arrow">{{ expanded ? '▾' : '▸' }}</span>
          <span>{{ msg.content ? '💭 已深度思考（点击展开）' : '💭 深度思考中…' }}</span>
        </div>
        <div
          v-show="expanded"
          class="reasoning-body"
        >
          {{ msg.reasoning }}
        </div>
      </div>

      <!-- AI 的回复：如果执行过工具，先显示动作记录 -->
      <div
        v-if="msg.actions && msg.actions.length"
        class="actions"
      >
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
      <div class="content">
        {{ msg.content }}
      </div>
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

/* ───── 深度思考块 ───── */
.reasoning {
  margin-bottom: 8px;
  border-left: 3px solid #dcdfe6;
  background: #f5f7fa;
  border-radius: 6px;
  overflow: hidden;
}

.reasoning-head {
  padding: 5px 10px;
  font-size: 12px;
  color: #909399;
  cursor: pointer;
  user-select: none; /* 标题文字不可选中，点起来更像按钮 */
}

.reasoning-head:hover {
  color: #606266;
}

.arrow {
  display: inline-block;
  width: 14px;
}

.reasoning-body {
  padding: 4px 12px 10px;
  font-size: 12px;
  line-height: 1.7;
  color: #a8abb2;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px; /* 思考内容可能很长，限制高度内部滚动 */
  overflow-y: auto;
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
