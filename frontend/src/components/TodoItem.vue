<!--
TodoItem.vue —— 单条待办（子组件）

【知识点：组件之间怎么传数据？—— props 向下、emit 向上】
  父组件(TodoList) --props--> 子组件(TodoItem)：传数据
  子组件 --emit 事件--> 父组件：报告"我被点了"，由父组件决定怎么改数据
  永远不要在子组件里直接改 props 的值，这叫"单向数据流"，数据流向清晰不混乱
-->
<script setup>
import { computed } from 'vue'

// defineProps：声明本组件接收哪些数据
const props = defineProps({
  todo: { type: Object, required: true },
})

// defineEmits：声明本组件会发出哪些事件
const emit = defineEmits(['toggle', 'delete'])

const priorityMap = {
  high: { label: '高', type: 'danger' },
  medium: { label: '中', type: 'warning' },
  low: { label: '低', type: 'info' },
}

const priorityInfo = computed(() => priorityMap[props.todo.priority] || priorityMap.medium)
</script>

<template>
  <div class="todo-item" :class="{ done: todo.completed }">
    <!-- .stop 阻止事件冒泡；勾选框切换完成状态 -->
    <el-checkbox
      :model-value="todo.completed"
      @change="emit('toggle', todo)"
    />
    <span class="title">{{ todo.title }}</span>
    <el-tag v-if="todo.due_date" size="small" type="info" effect="plain">
      📅 {{ todo.due_date }}
    </el-tag>
    <el-tag size="small" :type="priorityInfo.type">{{ priorityInfo.label }}优先</el-tag>
    <el-button
      type="danger"
      text
      size="small"
      @click="emit('delete', todo)"
    >
      删除
    </el-button>
  </div>
</template>

<style scoped>
.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  transition: box-shadow 0.2s;
}

.todo-item:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.title {
  flex: 1;
  font-size: 15px;
  word-break: break-all;
}

/* 已完成的：划线+变灰 */
.todo-item.done .title {
  text-decoration: line-through;
  color: #c0c4cc;
}
</style>
