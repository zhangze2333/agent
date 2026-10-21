<!--
Chat.vue —— AI 聊天页（本项目最好玩的部分）

【知识点：智能体在前端眼里的样子】
前端其实很简单：把用户输入 POST 到 /api/chat，拿回 {reply, actions}。
复杂的大脑（工具调用循环）全在后端。这正是"前后端分离"的好处——
前端不需要懂 AI，后端不需要懂页面。

【知识点：打字机效果】
后端是一次性返回完整回复的（没有流式），但我们可以在前端用 setInterval
每隔 30ms 多显示几个字，制造"AI 在打字"的效果。真正的流式传输（SSE）
是这个项目的进阶练习方向，见 README。
-->
<script setup>
import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ChatMessage from '../components/ChatMessage.vue'
import { sendChat } from '../api'

// 对话记录：[{role: 'user'|'assistant', content: '...', actions: [...]}]
const messages = ref([])
const input = ref('')
const sending = ref(false) // true 时禁用输入框，防止连发
const listRef = ref(null)  // 绑定消息列表 DOM，用于自动滚动

// 每次新消息出现时滚动到底部。nextTick：等 Vue 把 DOM 更新完再操作 DOM
async function scrollToBottom() {
  await nextTick()
  listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
}

// 打字机效果：把 fullText 慢慢"打"进某条消息的 content 里
function typeOut(msg, fullText) {
  return new Promise((resolve) => {
    let i = 0
    const timer = setInterval(() => {
      i += 2 // 每次多显示 2 个字符
      msg.content = fullText.slice(0, i)
      listRef.value?.scrollTo({ top: listRef.value.scrollHeight })
      if (i >= fullText.length) {
        clearInterval(timer)
        resolve()
      }
    }, 30)
  })
}

async function handleSend() {
  const text = input.value.trim()
  if (!text || sending.value) return

  // 1. 立刻把用户的话显示在界面上（不用等后端）
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  sending.value = true
  scrollToBottom()

  try {
    // 2. 请求后端智能体（大脑在后端，可能要几秒）
    const res = await sendChat(text)

    // 3. 先创建一条"空"的 AI 消息，再让文字一个个出现
    const aiMsg = { role: 'assistant', content: '', actions: res.data.actions || [] }
    messages.value.push(aiMsg)
    await typeOut(aiMsg, res.data.reply || '（AI 没有返回内容）')
  } catch (err) {
    // axios 请求失败：err.response.data.detail 里是后端给的错误说明
    const detail = err.response?.data?.detail || '网络错误，请检查后端是否启动'
    messages.value.push({ role: 'assistant', content: `⚠️ ${detail}` })
  } finally {
    sending.value = false
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
          <el-button plain size="small" @click="quickAsk('我现在都有哪些事没做完？')">我现在都有哪些事没做完？</el-button>
          <el-button plain size="small" @click="quickAsk('把最早的一条待办删掉')">把最早的一条待办删掉</el-button>
        </div>
      </div>

      <ChatMessage v-for="(msg, i) in messages" :key="i" :msg="msg" />

      <!-- AI 思考中提示 -->
      <div v-if="sending" class="thinking">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        助手思考中，涉及工具调用会稍慢一些…
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

/* 三个点循环放大的"思考中"动画 */
.thinking {
  color: #909399;
  font-size: 13px;
  padding: 8px 0 8px 46px;
}

.dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 4px;
  border-radius: 50%;
  background: #409eff;
  animation: blink 1.2s infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0%, 60%, 100% { opacity: 0.25; }
  30% { opacity: 1; }
}

.input-bar {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  border-top: 1px solid #ebeef5;
  background: #f5f7fa;
}
</style>
