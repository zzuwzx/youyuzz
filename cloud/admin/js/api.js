// api.js — API 调用封装
const BASE_URL = "https://youyuzz-auth.zxxxwang-82a.workers.dev";
// 本地开发时也可改为 "" 使用相对路径（同域部署后）

async function apiFetch(path, options = {}) {
  const token = sessionStorage.getItem("admin_token");
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    sessionStorage.removeItem("admin_token");
    window.location.hash = "#/login";
    throw new Error("认证失败，请重新登录");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `请求失败 (${res.status})`);
  return data;
}

const API = {
  // admin
  generateCodes(body) { return apiFetch("/api/admin/codes/generate", { method: "POST", body: JSON.stringify(body) }); },
  getUsers()          { return apiFetch("/api/admin/users"); },
  updateUser(id, body){ return apiFetch(`/api/admin/users/${id}`, { method: "PUT", body: JSON.stringify(body) }); },
  getStats()          { return apiFetch("/api/admin/stats"); },
};
