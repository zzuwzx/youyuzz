// router.js — hash 路由
const Router = {
  routes: {},
  register(hash, renderFn) { this.routes[hash] = renderFn; },
  start() {
    window.addEventListener("hashchange", () => this.resolve());
    this.resolve();
  },
  resolve() {
    const hash = location.hash || "#/login";
    if (!Auth.isLoggedIn() && hash !== "#/login") {
      location.hash = "#/login";
      return;
    }
    const render = this.routes[hash];
    const app = document.getElementById("app");
    if (render) { render(app); } else { app.innerHTML = "<p>页面不存在</p>"; }
    // 高亮导航
    document.querySelectorAll(".nav-link").forEach(a => {
      a.classList.toggle("active", a.getAttribute("href") === hash);
    });
  },
};
