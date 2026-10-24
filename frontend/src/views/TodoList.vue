<!--
TodoList.vue —— 待办列表页（视图组件）

【知识点：组合式 API 的几个核心角色】
  ref(初始值)       创建一个"响应式数据"：它变化时，页面自动跟着变。
                    JS 里要用 .value 访问，模板里直接写名字。
  computed(() =>..) 计算属性：由其他数据算出来的值，依赖变了自动重算（带缓存）
  onMounted(...)    生命周期钩子：组件"挂载"到页面后执行，适合发首次数据请求

【这个页面演示的标准套路】
  页面加载 -> 请求列表 -> 用户操作(增/改/删) -> 请求后端 -> 成功后刷新列表
  所有前端和后端交互的页面都是这个模式，学会一个就会了所有。
-->
<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import TodoItem from '../components/TodoItem.vue'
import { createTodo, deleteTodo, fetchTodos, updateTodo } from '../api'

// ───── 响应式状态 ─────
const todos = ref([]) // 待办列表，从后端获取
const loading = ref(false) // 是否正在加载（控制转圈动画）
const filter = ref('all') // 筛选：all / active / done

// 新增表单的三项数据，用 v-model 和输入框双向绑定
const newTitle = ref('')
const newDueDate = ref('')
const newPriority = ref('medium')

// ───── 计算属性：根据 filter 筛选后的列表（模板里渲染的是它）─────
const filteredTodos = computed(() => {
  if (filter.value === 'active') return todos.value.filter((t) => !t.completed)
  if (filter.value === 'done') return todos.value.filter((t) => t.completed)
  return todos.value
})

const activeCount = computed(() => todos.value.filter((t) => !t.completed).length)

// ───── 数据操作函数 ─────
async function loadTodos() {
  loading.value = true
  try {
    // axios 返回的数据在 .data 里（后端返回什么，这里就是什么）
    const res = await fetchTodos()
    todos.value = res.data
  } catch {
    // 不需要 err 变量：这里只提示，不区分错误类型（ES2019 可选 catch 绑定）
    ElMessage.error('加载待办失败，请重新登录试试')
  } finally {
    loading.value = false // 无论成败都关掉 loading
  }
}

async function handleAdd() {
  const title = newTitle.value.trim() // 去掉首尾空格
  if (!title) {
    ElMessage.warning('先写点什么要做的事吧')
    return
  }
  await createTodo({ title, due_date: newDueDate.value || null, priority: newPriority.value })
  newTitle.value = '' // 清空表单
  newDueDate.value = ''
  ElMessage.success('已添加')
  await loadTodos() // 重新拉列表，让新增的显示出来
}

// 点勾选框：把 completed 取反后提交给后端
async function handleToggle(todo) {
  await updateTodo(todo.id, { completed: !todo.completed })
  await loadTodos()
}

// 点删除：弹确认框，防止手滑
async function handleDelete(todo) {
  await ElMessageBox.confirm(`确定删除「${todo.title}」吗？`, '确认', { type: 'warning' })
  await deleteTodo(todo.id)
  ElMessage.success('已删除')
  await loadTodos()
}

// 组件挂载后立刻加载列表
onMounted(loadTodos)
</script>

<template>
  <div class="todo-page">
    <!-- 新增区域 -->
    <el-card
      class="add-card"
      shadow="never"
    >
      <div class="add-row">
        <el-input
          v-model="newTitle"
          placeholder="要做点什么？回车快速添加"
          size="large"
          clearable
          @keyup.enter="handleAdd"
        />
        <el-date-picker
          v-model="newDueDate"
          type="date"
          placeholder="截止日期(可选)"
          value-format="YYYY-MM-DD"
          style="width: 170px"
        />
        <el-select
          v-model="newPriority"
          style="width: 110px"
        >
          <el-option
            label="高优先"
            value="high"
          />
          <el-option
            label="中优先"
            value="medium"
          />
          <el-option
            label="低优先"
            value="low"
          />
        </el-select>
        <el-button
          type="primary"
          size="large"
          @click="handleAdd"
        >
          添加
        </el-button>
      </div>
    </el-card>

    <!-- 筛选栏 -->
    <div class="toolbar">
      <el-radio-group v-model="filter">
        <el-radio-button value="all">
          全部
        </el-radio-button>
        <el-radio-button value="active">
          未完成
        </el-radio-button>
        <el-radio-button value="done">
          已完成
        </el-radio-button>
      </el-radio-group>
      <span class="count">还有 {{ activeCount }} 件事没做完</span>
    </div>

    <!-- 列表区域 -->
    <div
      v-loading="loading"
      class="list"
    >
      <!-- v-for：循环渲染；:key 帮 Vue 高效更新，必须唯一稳定 -->
      <TodoItem
        v-for="todo in filteredTodos"
        :key="todo.id"
        :todo="todo"
        @toggle="handleToggle"
        @delete="handleDelete"
      />
      <el-empty
        v-if="!loading && filteredTodos.length === 0"
        description="没有待办，去添加一条，或者去 AI 助手页说「帮我记一件事」"
      />
    </div>
  </div>
</template>

<style scoped>
.todo-page {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.add-row {
  display: flex;
  gap: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.count {
  color: #909399;
  font-size: 13px;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
}
</style>
