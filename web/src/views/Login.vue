<template>
  <div class="login-page">
    <div class="login-card glass-strong">
      <div class="login-brand">
        <span class="login-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </span>
        <div>
          <h1>Codex Pool</h1>
          <p class="sub">{{ isRegister ? "创建新账号" : "账号池管理控制台" }}</p>
        </div>
      </div>
      <el-form label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input
            v-model="username"
            placeholder="请输入用户名"
            size="large"
            maxlength="64"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            show-password
            :placeholder="isRegister ? '至少 6 位密码' : '请输入密码'"
            size="large"
          />
        </el-form-item>
        <el-form-item v-if="isRegister" label="确认密码">
          <el-input
            v-model="confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入密码"
            size="large"
          />
        </el-form-item>
        <el-button
          type="primary"
          native-type="submit"
          :loading="loading"
          size="large"
          class="submit-btn"
        >
          {{ isRegister ? "注册" : "登录" }}
        </el-button>
      </el-form>
      <p class="mode-switch">
        <template v-if="isRegister">
          已有账号？
          <button type="button" class="link-btn" @click="switchMode(false)">去登录</button>
        </template>
        <template v-else>
          还没有账号？
          <button type="button" class="link-btn" @click="switchMode(true)">创建账号</button>
        </template>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { login, register } from "../api";

const router = useRouter();
const isRegister = ref(false);
const username = ref("");
const password = ref("");
const confirmPassword = ref("");
const loading = ref(false);

function switchMode(registerMode) {
  isRegister.value = registerMode;
  password.value = "";
  confirmPassword.value = "";
}

async function onSubmit() {
  const name = username.value.trim();
  if (!name) {
    ElMessage.warning("请输入用户名");
    return;
  }
  if (!password.value) {
    ElMessage.warning("请输入密码");
    return;
  }
  if (isRegister.value) {
    if (password.value.length < 6) {
      ElMessage.warning("密码至少 6 位");
      return;
    }
    if (password.value !== confirmPassword.value) {
      ElMessage.warning("两次输入的密码不一致");
      return;
    }
  }

  loading.value = true;
  try {
    const request = isRegister.value
      ? register(name, password.value)
      : login(name, password.value);
    const { data } = await request;
    localStorage.setItem("token", data.access_token);
    ElMessage.success(isRegister.value ? "注册成功" : "登录成功");
    router.push("/");
  } catch (err) {
    const detail = err?.response?.data?.detail;
    if (detail === "username already exists") {
      ElMessage.error("用户名已存在");
    } else if (detail === "invalid username or password") {
      ElMessage.error("用户名或密码错误");
    } else {
      ElMessage.error(isRegister.value ? "注册失败" : "登录失败");
    }
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  z-index: 2;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: 36px 32px 32px;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 28px;
}

.login-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--cp-primary) 0%, var(--cp-primary-light) 100%);
  color: #fff;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3);
  flex-shrink: 0;
}

.login-icon svg {
  width: 26px;
  height: 26px;
}

.login-brand h1 {
  margin: 0;
  font-family: "Fira Code", monospace;
  font-size: 22px;
  font-weight: 600;
  color: var(--cp-text);
}

.sub {
  color: var(--cp-text-muted);
  margin: 4px 0 0;
  font-size: 14px;
}

.login-card :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--cp-text-muted);
  padding-bottom: 6px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.mode-switch {
  margin: 20px 0 0;
  text-align: center;
  font-size: 14px;
  color: var(--cp-text-muted);
}

.link-btn {
  border: 0;
  padding: 0;
  margin: 0;
  background: none;
  color: var(--cp-primary);
  font-size: inherit;
  font-weight: 600;
  cursor: pointer;
}

.link-btn:hover {
  text-decoration: underline;
}
</style>
