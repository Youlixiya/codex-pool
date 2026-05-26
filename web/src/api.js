import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const login = (username, password) =>
  api.post("/auth/login", { username, password });

export const register = (username, password) =>
  api.post("/auth/register", { username, password });

export const me = () => api.get("/auth/me");
export const updateMe = (data) => api.put("/auth/me", data);
export const uploadAvatar = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/auth/me/avatar", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const deleteAvatar = () => api.delete("/auth/me/avatar");
export const fetchAvatarBlob = () =>
  api.get("/auth/me/avatar", { responseType: "blob" });
export const dashboardStats = () => api.get("/dashboard/stats");
export const modelUsage = () => api.get("/dashboard/models");
export const platformUsage = () => api.get("/dashboard/platforms");
export const usageTrend = (days = 7) => api.get("/dashboard/trend", { params: { days } });
export const listApiKeys = () => api.get("/api-keys");
export const createApiKey = (name) => api.post("/api-keys", { name });
export const updateApiKey = (id, data) => api.patch(`/api-keys/${id}`, data);
export const deleteApiKey = (id) => api.delete(`/api-keys/${id}`);
export const revealApiKey = (id) => api.get(`/api-keys/${id}/secret`);
export const listUpstreams = () => api.get("/upstreams");
export const createUpstream = (data) => api.post("/upstreams", data);
export const updateUpstream = (id, data) => api.patch(`/upstreams/${id}`, data);
export const deleteUpstream = (id) => api.delete(`/upstreams/${id}`);
export const startChatgptOAuth = (data) => api.post("/upstreams/oauth/chatgpt/start", data);
export const getChatgptOAuthStatus = (sessionId) =>
  api.get(`/upstreams/oauth/chatgpt/status/${sessionId}`);
export const getChatgptQuota = (authFile) =>
  api.get("/upstreams/oauth/chatgpt/quota", { params: { auth_file: authFile } });
export const getUpstreamQuota = (id) => api.get(`/upstreams/${id}/quota`);
export const testUpstreamConnection = (id) => api.post(`/upstreams/${id}/test`);
