<!--
Login.vue —— 登录/注册页（二合一：mode 切换）

【知识点：el-form 表单校验】
rules 定义每个字段的校验规则（必填/长度/自定义正则），
el-form-item 的 prop 对应字段名，validate() 触发整体校验——
企业前端的标准表单写法，比手写 if 校验规范得多。
-->
<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authLogin, authRegister } from '../api'
import { setAuth } from '../stores/auth'

const router = useRouter()
const mode = ref('login') // 'login' | 'register'，两套界面共用一个表单
const loading = ref(false)

const form = reactive({ username: '', password: '' })

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名 3-30 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

const formRef = ref(null)

async function handleSubmit() {
  // validate 返回是否通过；不通过时 ElForm 自己会标红提示
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const fn = mode.value === 'login' ? authLogin : authRegister
    const res = await fn({ username: form.username, password: form.password })
    setAuth(res.data.token, res.data.username) // 注册接口也直接返回 token（注册即登录）
    ElMessage.success(mode.value === 'login' ? '欢迎回来' : '注册成功')
    router.push('/')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败，请重试')
  } finally {
    loading.value = false
  }
}

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  formRef.value?.clearValidate() // 切换时清掉上一模式的红字提示
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <h2 class="title">🤖 AI 待办助手</h2>
      <p class="subtitle">{{ mode === 'login' ? '登录你的账号' : '创建一个新账号' }}</p>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <!-- show-password：自带小眼睛切换明文/密文 -->
          <el-input v-model="form.password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-button type="primary" class="submit" :loading="loading" @click="handleSubmit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <div class="switch">
        <span>{{ mode === 'login' ? '还没有账号？' : '已有账号？' }}</span>
        <el-link type="primary" @click="switchMode">
          {{ mode === 'login' ? '去注册' : '去登录' }}
        </el-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.login-card {
  width: 380px;
  padding: 12px 8px;
}

.title {
  text-align: center;
  color: #409eff;
  margin: 8px 0 4px;
}

.subtitle {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin-bottom: 24px;
}

.submit {
  width: 100%;
}

.switch {
  margin-top: 14px;
  text-align: center;
  font-size: 13px;
  color: #909399;
}
</style>
