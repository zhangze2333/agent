<!--
Chat.vue —— AI 聊天页（v0.2：真流式 + 过程可视化 + 多轮对话）

【v0.1 → v0.2 的三个升级】
1. 真流式：不再用定时器假装打字机。后端 (SSE) 每生成一段就推一段，
   这里用原生 fetch 读响应流（axios 拿不到逐段到达的数据，所以弃用它），
   收到 delta 事件就把文字追加到气泡里——这就是 ChatGPT 那种效果的本质
2. 过程可视化：后端每个阶段都发 status 事件（思考中/调用工具/执行完成），
   显示在底部的状态行里，用户随时知道智能体在干嘛
3. 多轮对话：每次请求把最近的对话历史一起发给后端，
   智能体才有"记忆"——能理解"不用""明天"这种依赖上一句的简短回答
-->
<script setup>
import { nextTick, reactive, ref } from 'vue'
import ChatMessage from '../components/ChatMessage.vue'

const messages = ref([])      // 对话记录：[{role, content, actions}]
const input = ref('')
const sending = ref(false)    // true 时禁用输入，防连发
const steps = ref([])         // 智能体执行步骤清单：[{text, done}]，逐条堆叠显示
const listRef = ref(null)     // 消息列表的 DOM，用来自动滚动

async function scrollToBottom() {
  await nextTick() // 等 Vue 把新消息渲染到页面上再滚动
  listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
}

// 把后端的 status 事件落到"步骤清单"里。
// 设计要点：已完成的步骤保留在列表上（打勾），而不是被下一条状态覆盖——
// 否则"调用工具"和"执行完成"间隔只有几毫秒，人眼根本看不到
function onStatus(p) {
  if (p.step === 'thinking') {
    const last = steps.value[steps.value.length - 1]
    const hasTool = steps.value.some((s) => s.tool)
    // 调用工具后的"思考"其实是在组织回复，文案区分一下
    if (!last || last.done) {
      steps.value.push({ text: hasTool ? '🤔 正在组织回复…' : '🤔 正在思考…', done: false })
    }
  } else if (p.step === 'tool') {
    steps.value.forEach((s) => (s.done = true)) // 之前的步骤都完成了
    const names = {
      add_todo: '➕ 创建待办',
      list_todos: '🔍 查询待办',
      complete_todo: '✅ 完成待办',
      delete_todo: '🗑️ 删除待办',
    }
    const argsText = Object.entries(p.args || {})
      .map(([k, v]) => `${k}=${v}`)
      .join(', ')
    steps.value.push({ text: `${names[p.name] || p.name}（${argsText}）`, done: false, tool: true })
  } else if (p.step === 'tool_result') {
    steps.value.forEach((s) => (s.done = true))
  }
}

// 解析一个 SSE 事件块。块的结构是两行文本：
//   event: delta
//   data: {"text": "部分文字"}
function handleSseBlock(block, aiMsg) {
  let event = 'message'
  const dataLines = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return
  const payload = JSON.parse(dataLines.join('\n'))

  if (event === 'status') {
    onStatus(payload)
    scrollToBottom()
  } else if (event === 'delta') {
    steps.value.forEach((s) => (s.done = true)) // 开始出字了，前置步骤都算完成
    aiMsg.content += payload.text // 真流式的核心：边收边显示
    scrollToBottom()
  } else if (event === 'done') {
    aiMsg.content = payload.reply || aiMsg.content
    aiMsg.actions = payload.actions || []
  } else if (event === 'error') {
    aiMsg.content = `⚠️ ${payload.detail}`
  }
}

async function handleSend() {
  const text = input.value.trim()
  if (!text || sending.value) return

  // 组装历史对话（只取最近 10 条，控制大小）。
  // 必须在 push 本条消息之前取，否则会把刚说的话重复算进历史
  const history = messages.value
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .slice(-10)
    .map((m) => ({ role: m.role, content: m.content }))

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  sending.value = true
  steps.value = [] // 新一轮对话，步骤清单从零开始
  scrollToBottom()

  // AI 的气泡先以"空壳"出现，内容随后由流式数据填充
  // （必须用 reactive() 包裹，否则修改 content 界面不更新——Vue3 响应式陷阱，v0.1 踩过）
  const aiMsg = reactive({ role: 'assistant', content: '', actions: [] })
  let aiPushed = false

  try {
    // 原生 fetch 发起流式请求；AbortSignal.timeout 限制总时长 120 秒
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history }),
      signal: AbortSignal.timeout(120000),
    })
    if (!resp.ok) {
      // 非 200 时后端返回的是普通 JSON 错误体
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `请求失败（HTTP ${resp.status}）`)
    }

    messages.value.push(aiMsg)
    aiPushed = true

    // 读流：resp.body 是字节流，用 reader 循环读取 + TextDecoder 转文字。
    // 网络传输不保证按事件块切割，所以要攒进 buf 里按空行(\n\n)切分
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, idx)
        buf = buf.slice(idx + 2)
        if (block.trim()) handleSseBlock(block, aiMsg)
      }
    }
  } catch (err) {
    if (!aiPushed) messages.value.push(aiMsg)
    aiMsg.content = `⚠️ ${err.name === 'TimeoutError' ? '请求超时了，请重试' : err.message || '网络错误，请检查后端是否启动'}`
  } finally {
    sending.value = false
    steps.value = [] // 完整回复和动作标签已入列，步骤清单完成使命
    scrollToBottom()
  }
}

// 快捷提问
function quickAsk(text) {
  input.value = text
  handleSend()
}
</script>

<template>
  <div class="chat-page">
    <!-- 消息列表 -->
    <div ref="listRef" class="msg-list">
      <div v-if="messages.length === 0" class="welcome">
        <h2>你好，我是你的待办助手 🤖</h2>
        <p>直接用说话的方式管理待办，比如：</p>
        <div class="examples">
          <el-button plain size="small" @click="quickAsk('帮我记一下：明天上午十点开会')">帮我记一下：明天上午十点开会</el-button>
          <el-button plain size="small" @click="quickAsk('帮我记一下买牛奶')">帮我记一下买牛奶（试试不提时间）</el-button>
          <el-button plain size="small" @click="quickAsk('我现在都有哪些事没做完？')">我现在都有哪些事没做完？</el-button>
        </div>
      </div>

      <ChatMessage v-for="(msg, i) in messages" :key="i" :msg="msg" />

      <!-- 智能体执行过程：逐步堆叠的清单，完成的打勾 -->
      <div v-if="sending && steps.length" class="steps">
        <div v-for="(s, i) in steps" :key="i" class="step" :class="{ done: s.done }">
          <span class="step-mark">{{ s.done ? '✓' : '⏳' }}</span>{{ s.text }}
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="input-bar">
      <el-input
        v-model="input"
        placeholder="和 AI 说点什么…（回车发送）"
        size="large"
        :disabled="sending"
        @keyup.enter="handleSend"
      />
      <el-button type="primary" size="large" :loading="sending" @click="handleSend">
        发送
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px - 48px); /* 视口高度减掉头部和边距 */
}

.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 4px;
}

.welcome {
  text-align: center;
  color: #909399;
  margin-top: 60px;
}

.welcome h2 {
  color: #303133;
  margin-bottom: 8px;
}

.examples {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

/* 步骤清单：每行一个步骤，完成的变灰打勾 */
.steps {
  padding: 4px 0 8px 46px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step {
  color: #606266;
  font-size: 13px;
}

.step.done {
  color: #c0c4cc;
}

.step-mark {
  display: inline-block;
  width: 22px;
}

.input-bar {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  border-top: 1px solid #ebeef5;
  background: #f5f7fa;
}
</style>
