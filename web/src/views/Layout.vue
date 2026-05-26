<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">
        <span class="brand-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M8.2 7.6h7.6M8.2 16.4h7.6M7.8 8.2l8.4 7.6M16.2 8.2l-8.4 7.6" stroke-width="1.8" stroke-linecap="round" />
            <circle cx="7" cy="7" r="2.4" fill="currentColor" stroke="none" />
            <circle cx="17" cy="7" r="2.4" fill="currentColor" stroke="none" />
            <circle cx="7" cy="17" r="2.4" fill="currentColor" stroke="none" />
            <circle cx="17" cy="17" r="2.4" fill="currentColor" stroke="none" />
          </svg>
        </span>
        <div class="brand-name">CodexPool</div>
      </div>
      <el-menu :default-active="route.path" router class="nav-menu">
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/api-keys">
          <el-icon><Key /></el-icon>
          <span>API 密钥</span>
        </el-menu-item>
        <el-menu-item index="/upstreams">
          <el-icon><Connection /></el-icon>
          <span>上游账号</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer">
        <button type="button" class="footer-action">
          <el-icon><Fold /></el-icon>
          <span>收起</span>
        </button>
      </div>
    </el-aside>
    <el-container class="main-wrap">
      <el-header class="header">
        <div class="title-block">
          <h1 class="page-heading">{{ title }}</h1>
          <p class="page-subtitle">{{ subtitle }}</p>
        </div>
        <div class="header-actions">
          <button type="button" class="user-pill" @click="openProfile">
            <span class="user-badge" :class="{ 'has-image': avatarSrc }">
              <img v-if="avatarSrc" :src="avatarSrc" alt="" class="user-avatar" />
              <span v-else>{{ userInitial }}</span>
            </span>
            <span>
              <strong>{{ displayName }}</strong>
            </span>
          </button>
          <button type="button" class="logout-btn" @click="logout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>

    <el-dialog v-model="showProfile" title="个人信息" width="560px" align-center>
      <el-form label-position="top" @submit.prevent="saveProfile">
        <div class="profile-head">
          <div class="avatar-editor">
            <div class="avatar-preview" :class="{ empty: !avatarPreview && !avatarSrc }">
              <img v-if="avatarPreview || avatarSrc" :src="avatarPreview || avatarSrc" alt="" />
              <span v-else>{{ userInitial }}</span>
            </div>
            <div class="avatar-actions">
              <el-upload
                :show-file-list="false"
                accept="image/jpeg,image/png,image/gif,image/webp"
                :auto-upload="false"
                :on-change="onAvatarPick"
              >
                <el-button size="small" :loading="avatarUploading">上传头像</el-button>
              </el-upload>
              <el-button
                v-if="currentUser?.has_avatar || avatarPreview"
                size="small"
                link
                type="danger"
                :loading="avatarUploading"
                @click="removeAvatarFile"
              >
                移除头像
              </el-button>
              <p class="avatar-hint">支持 JPG / PNG / GIF / WebP，最大 2MB</p>
            </div>
          </div>
          <div class="profile-meta">
            <div class="meta-row"><span>用户 ID</span><strong>{{ currentUser?.id || "-" }}</strong></div>
            <div class="meta-row"><span>注册时间</span><strong>{{ formatDate(currentUser?.created_at) }}</strong></div>
          </div>
        </div>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名" required>
              <el-input v-model="profileForm.username" maxlength="64" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="显示名称">
              <el-input v-model="profileForm.displayName" maxlength="64" placeholder="在界面中展示的名称" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="profileForm.email" maxlength="128" placeholder="name@example.com" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model="profileForm.phone" maxlength="32" placeholder="可选" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="个人简介">
          <el-input
            v-model="profileForm.bio"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="简单介绍一下自己"
          />
        </el-form-item>

        <el-divider content-position="left">修改密码（可选）</el-divider>
        <el-form-item label="当前密码">
          <el-input
            v-model="profileForm.currentPassword"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="仅修改密码时填写"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="profileForm.newPassword"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="至少 6 位"
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="profileForm.confirmPassword"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="再次输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProfile = false">取消</el-button>
        <el-button type="primary" :loading="profileSaving" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Connection,
  Fold,
  Key,
  Odometer,
  SwitchButton,
} from "@element-plus/icons-vue";
import { deleteAvatar, fetchAvatarBlob, me, updateMe, uploadAvatar } from "../api";
import { ElMessage } from "element-plus";

const route = useRoute();
const router = useRouter();
const currentUser = ref(null);
const showProfile = ref(false);
const profileSaving = ref(false);
const avatarUploading = ref(false);
const avatarSrc = ref("");
const avatarPreview = ref("");
const avatarObjectUrl = ref("");
const profileForm = ref({
  username: "",
  displayName: "",
  email: "",
  phone: "",
  bio: "",
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});
const title = computed(() => {
  if (route.path === "/api-keys") return "API 密钥";
  if (route.path === "/upstreams") return "上游账号";
  return "仪表盘";
});
const subtitle = computed(() => {
  if (route.path === "/api-keys") return "管理您的 API 密钥。";
  if (route.path === "/upstreams") return "配置代理转发的上游账号。";
  return "欢迎回来！这是您账户的概览。";
});
function usernameInitials(name) {
  const text = (name || "U").trim();
  if (!text) return "U";
  return text.slice(0, 2).toUpperCase();
}

const userInitial = computed(() =>
  usernameInitials(profileForm.value.username || currentUser.value?.username)
);
const displayName = computed(() => currentUser.value?.username || "未登录");

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function revokeAvatarUrl() {
  if (avatarObjectUrl.value) {
    URL.revokeObjectURL(avatarObjectUrl.value);
    avatarObjectUrl.value = "";
  }
  if (avatarPreview.value) {
    URL.revokeObjectURL(avatarPreview.value);
    avatarPreview.value = "";
  }
  avatarSrc.value = "";
}

async function loadAvatar() {
  revokeAvatarUrl();
  if (!currentUser.value?.has_avatar) return;
  try {
    const { data } = await fetchAvatarBlob();
    avatarObjectUrl.value = URL.createObjectURL(data);
    avatarSrc.value = avatarObjectUrl.value;
  } catch {
    revokeAvatarUrl();
  }
}

function resetProfileForm() {
  if (avatarPreview.value) {
    URL.revokeObjectURL(avatarPreview.value);
  }
  profileForm.value = {
    username: currentUser.value?.username || "",
    displayName: currentUser.value?.display_name || "",
    email: currentUser.value?.email || "",
    phone: currentUser.value?.phone || "",
    bio: currentUser.value?.bio || "",
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  };
  avatarPreview.value = "";
}

function openProfile() {
  if (!currentUser.value) return;
  resetProfileForm();
  showProfile.value = true;
}

async function loadUser() {
  try {
    const { data } = await me();
    currentUser.value = data;
    await loadAvatar();
  } catch {
    currentUser.value = null;
    revokeAvatarUrl();
  }
}

async function onAvatarPick(uploadFile) {
  const file = uploadFile?.raw;
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning("头像不能超过 2MB");
    return;
  }
  avatarPreview.value = URL.createObjectURL(file);
  avatarUploading.value = true;
  try {
    const { data } = await uploadAvatar(file);
    currentUser.value = data;
    avatarPreview.value = "";
    await loadAvatar();
    ElMessage.success("头像已更新");
  } catch (err) {
    avatarPreview.value = "";
    ElMessage.error(err.response?.data?.detail || "头像上传失败");
  } finally {
    avatarUploading.value = false;
  }
}

async function removeAvatarFile() {
  avatarUploading.value = true;
  try {
    const { data } = await deleteAvatar();
    currentUser.value = data;
    avatarPreview.value = "";
    revokeAvatarUrl();
    ElMessage.success("头像已移除");
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || "移除头像失败");
  } finally {
    avatarUploading.value = false;
  }
}

async function saveProfile() {
  const username = profileForm.value.username.trim();
  if (!username) {
    ElMessage.warning("用户名不能为空");
    return;
  }

  const { newPassword, confirmPassword, currentPassword } = profileForm.value;
  if (newPassword || confirmPassword || currentPassword) {
    if (!currentPassword) {
      ElMessage.warning("修改密码需要填写当前密码");
      return;
    }
    if (!newPassword) {
      ElMessage.warning("请填写新密码");
      return;
    }
    if (newPassword.length < 6) {
      ElMessage.warning("新密码至少 6 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      ElMessage.warning("两次输入的新密码不一致");
      return;
    }
  }

  profileSaving.value = true;
  try {
    const payload = {
      username,
      display_name: profileForm.value.displayName.trim() || null,
      email: profileForm.value.email.trim() || null,
      phone: profileForm.value.phone.trim() || null,
      bio: profileForm.value.bio.trim() || null,
    };
    if (newPassword) {
      payload.current_password = currentPassword;
      payload.new_password = newPassword;
    }
    const { data } = await updateMe(payload);
    currentUser.value = data;
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
    }
    showProfile.value = false;
    ElMessage.success("个人信息已更新");
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || "保存失败");
  } finally {
    profileSaving.value = false;
  }
}

function logout() {
  localStorage.removeItem("token");
  router.push("/login");
}

onMounted(loadUser);
onUnmounted(revokeAvatarUrl);
</script>

<style scoped>
.layout {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  background: var(--cp-bg);
}

.aside {
  display: flex;
  flex-direction: column;
  margin: 0;
  height: 100vh;
  position: sticky;
  top: 0;
  overflow: hidden;
  background: var(--cp-sidebar);
  border-right: 1px solid var(--cp-glass-edge);
  box-shadow: none;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 68px;
  padding: 0 16px;
  border-bottom: 1px solid var(--cp-glass-edge);
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #dfe5ee;
  color: #0ea5e9;
  box-shadow: 0 2px 8px rgba(17, 24, 39, 0.08);
  flex-shrink: 0;
}

.brand-icon svg {
  width: 21px;
  height: 21px;
}

.brand-name {
  font-weight: 800;
  font-size: 18px;
  color: var(--cp-text);
}

.nav-menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  padding: 12px 10px;
}

.nav-menu :deep(.el-menu-item) {
  height: 42px;
  line-height: 42px;
  margin-bottom: 6px;
  border-radius: 8px;
  color: var(--cp-text-muted);
  font-size: 14px;
  font-weight: 700;
  transition: background var(--cp-transition), color var(--cp-transition);
  cursor: pointer;
}

.nav-menu :deep(.el-menu-item:hover) {
  background: #eefbff;
  color: var(--cp-primary-hover);
}

.nav-menu :deep(.el-menu-item.is-active) {
  background: #eafbff;
  color: #0ea5e9;
  font-weight: 800;
  position: relative;
}

.nav-menu :deep(.el-menu-item.is-active::before) {
  content: none;
}

.nav-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 10px;
}

.aside-footer {
  border-top: 1px solid var(--cp-glass-edge);
  padding: 12px 12px 14px;
}

.footer-action {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--cp-text-muted);
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: background var(--cp-transition), color var(--cp-transition);
}

.footer-action:hover {
  background: #f0f9ff;
  color: var(--cp-primary-hover);
}

.footer-action .el-icon {
  font-size: 18px;
}

.main-wrap {
  flex: 1;
  min-width: 0;
  flex-direction: column;
  background: transparent;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: auto !important;
  min-height: 68px;
  padding: 0 24px !important;
  margin-bottom: 0;
  background: #ffffff;
  border-bottom: 1px solid var(--cp-glass-edge);
  gap: 18px;
}

.page-heading {
  margin: 0;
  font-size: 20px;
}

.page-subtitle {
  margin: 4px 0 0;
  color: var(--cp-text-subtle);
  font-size: 13px;
}

.title-block {
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding: 0 4px;
  border: 0;
  box-shadow: none;
  background: transparent;
  color: var(--cp-text-muted);
  white-space: nowrap;
  font-family: inherit;
  cursor: pointer;
  border-radius: 8px;
  transition: background var(--cp-transition);
}

.user-pill:hover {
  background: #f0f9ff;
}

.user-pill strong {
  display: block;
  color: var(--cp-text);
  font-size: 14px;
  line-height: 1.2;
}

.user-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #0ea5e9;
  color: #ffffff;
  font-weight: 800;
  font-size: 12px;
  letter-spacing: -0.02em;
  overflow: hidden;
  flex-shrink: 0;
}

.user-badge.has-image {
  background: #e2e8f0;
}

.user-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-head {
  display: flex;
  gap: 20px;
  margin-bottom: 8px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--cp-glass-edge);
}

.avatar-editor {
  display: flex;
  gap: 14px;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.avatar-preview {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  background: #0ea5e9;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-preview.empty {
  background: #e2e8f0;
  color: #64748b;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.avatar-hint {
  margin: 0;
  font-size: 12px;
  color: var(--cp-text-subtle);
}

.profile-meta {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  min-width: 180px;
}

.meta-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}

.meta-row span {
  color: var(--cp-text-subtle);
}

.meta-row strong {
  color: var(--cp-text);
  font-weight: 700;
}

.logout-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  font-family: inherit;
  font-size: 16px;
  border: 1px solid var(--cp-glass-edge);
  border-radius: 8px;
  background: #ffffff;
  color: var(--cp-text-muted);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--cp-transition), color var(--cp-transition), border-color var(--cp-transition);
}

.logout-btn:hover {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

.main-content {
  padding: 24px !important;
  overflow: auto;
}

@media (max-width: 768px) {
  .layout {
    flex-direction: column;
    padding: 0;
  }

  .aside {
    width: 100% !important;
    height: auto;
    position: static;
  }

  .nav-menu :deep(.el-menu-item) {
    display: inline-flex;
    width: auto;
    margin-right: 4px;
  }

  .nav-menu {
    display: flex;
    flex-wrap: wrap;
    padding: 8px;
  }

  .header {
    flex-wrap: wrap;
    gap: 12px;
    padding: 16px !important;
  }

  .page-heading {
    font-size: 18px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .main-content {
    padding: 16px !important;
  }
}
</style>
