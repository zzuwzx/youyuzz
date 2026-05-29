// auth.js — 登录状态管理
const Auth = {
  isLoggedIn() { return !!sessionStorage.getItem("admin_token"); },
  setToken(t)  { sessionStorage.setItem("admin_token", t); },
  clear()      { sessionStorage.removeItem("admin_token"); },
};
