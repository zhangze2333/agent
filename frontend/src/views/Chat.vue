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
import { auth } from '../stores/auth'

const messages = ref([])      // 对话记录：[{role, content, actions}]
const input = ref('')
const sending = ref(false)    // true 时禁用输入，防连发
const steps = ref([])         // 执行过程清单：[{text, state}]，像 todo 列表一样逐条打勾
const listRef = ref(null)     // 消息列表的 DOM，用来自动滚动

async function scrollToBottom() {
  await nextTick() // 等 Vue 把新消息渲染到页面上再滚动
  listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
}

// 把清单里所有步骤标记为完成（打绿勾）
function finishAllSteps() {
  steps.value.forEach((s) => (s.state = 'done'))
}

const TOOL_NAMES = {
  add_todo: '创建待办',
  list_todos: '查询待办',
  complete_todo: '完成待办',
  delete_todo: '删除待办',
}

// 把后端的 status 事件落到"执行清单"里。
// 每个步骤有 state：active=进行中（转圈） done=已完成（绿勾）。
// 已完成的步骤永远保留在清单上——这是给用户的"施工记录"
function onStatus(p) {
  if (p.step === 'thinking') {
    // 发送瞬间本地已预置"分析问题"步骤，这里去重：同样的步骤正在做就不重复加
    const last = steps.value[steps.value.length - 1]
    const organized = steps.value.some((s) => s.tool) // 调过工具后的思考 = 在组织回复
    const want = organized ? '组织最终回复' : '分析问题'
    if (last && last.state === 'active' && last.text === want) return
    finishAllSteps()
    steps.value.push({ text: want, state: 'active' })
  } else if (p.step === 'tool') {
    finishAllSteps()
    const name = TOOL_NAMES[p.name] || p.name
    const argsText = Object.entries(p.args || {})
      .map(([k, v]) => `${k}=${v}`)
      .join('，')
    steps.value.push({ text: `${name}：${argsText}`, state: 'active', tool: true })
  } else if (p.step === 'tool_result') {
    finishAllSteps() // 工具执行完成 → 该步骤立刻打上绿勾（并永久保留）
  }
}

// 解析一个 SSE 事件块。块的结构是两行文本：
//   event: delta
//   data: {"text": "部分文字"}
function handleSseBlock(block, aiMsg, ensureBubble) {
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
  } else if (event === 'reasoning') {
    ensureBubble() // 收到第一段思考/正文时才创建气泡，避免长时间的空白框
    aiMsg.reasoning += payload.text // 模型的深度思考过程，思考块里实时展示
    scrollToBottom()
  } else if (event === 'delta') {
    ensureBubble()
    finishAllSteps() // 开始出字了，前置步骤都算完成
    aiMsg.content += payload.text // 真流式的核心：边收边显示
    scrollToBottom()
  } else if (event === 'done') {
    ensureBubble()
    aiMsg.content = payload.reply || aiMsg.content
    aiMsg.actions = payload.actions || []
  } else if (event === 'error') {
    ensureBubble()
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
  // 发送瞬间就本地预置第一步（不等网络事件），清单从第 0 秒就可见
  steps.value = [{ text: '分析问题', state: 'active' }]
  scrollToBottom()

  // AI 气泡此时【不】创建：空白的回答框很难看。
  // 等收到第一段思考/正文时（ensureBubble）才出现，期间由执行清单代表它
  // （必须用 reactive() 包裹，否则修改 content 界面不更新——Vue3 响应式陷阱，v0.1 踩过）
  const aiMsg = reactive({ role: 'assistant', content: '', reasoning: '', actions: [] })
  let aiPushed = false
  const ensureBubble = () => {
    if (!aiPushed) {
      messages.value.push(aiMsg)
      aiPushed = true
    }
  }

  try {
    // 原生 fetch 发起流式请求；AbortSignal.timeout 限制总时长 120 秒
    // 注意：fetch 不会走 axios 拦截器，登录头要自己带；401 时后端返回普通 JSON
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify({ message: text, history }),
      signal: AbortSignal.timeout(120000),
    })
    if (resp.status === 401) {
      window.location.href = '/login' // 登录过期，踢回登录页
      return
    }
    if (!resp.ok) {
      // 非 200 时后端返回的是普通 JSON 错误体
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `请求失败（HTTP ${resp.status}）`)
    }

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
        if (block.trim()) handleSseBlock(block, aiMsg, ensureBubble)
      }
    }
  } catch (err) {
    ensureBubble()
    aiMsg.content = `⚠️ ${err.name === 'TimeoutError' ? '请求超时了，请重试' : err.message || '网络错误，请检查后端是否启动'}`
  } finally {
    sending.value = false
    steps.value = [] // 全部执行完成，清单完成使命（完整回复+绿标签已经接班）
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

      <!-- 智能体执行过程：todo 列表式清单，进行中转圈、完成打绿勾，完成后保留 -->
      <div v-if="steps.length" class="steps-card">
        <div class="steps-title">🤖 执行过程</div>
        <div
          v-for="(s, i) in steps"
          :key="i"
          class="step-row"
          :class="{ active: s.state === 'active', done: s.state === 'done' }"
        >
          <span v-if="s.state === 'done'" class="check-badge">✓</span>
          <span v-else class="spinner"></span>
          <span class="step-text">{{ s.text }}</span>
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

/* ───── 执行过程清单卡片 ───── */
.steps-card {
  margin: 4px 0 8px 46px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 10px 14px;
  max-width: 75%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.steps-title {
  font-size: 12px;
  color: #909399;
  font-weight: 600;
  margin-bottom: 6px;
}

.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
}

.step-row + .step-row {
  margin-top: 2px;
}

/* 进行中的步骤：浅蓝底高亮 */
.step-row.active {
  background: #ecf5ff;
  color: #303133;
  font-weight: 500;
}

.step-row.done {
  color: #909399;
}

/* 已完成的绿勾：绿色圆形徽章，醒目 */
.check-badge {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #67c23a;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 进行中的转圈动画 */
.spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid #dcdfe6;
  border-top-color: #409eff;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.input-bar {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  border-top: 1px solid #ebeef5;
  background: #f5f7fa;
}
</style>
