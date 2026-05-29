// login.js — 登录页
function renderLogin(container) {
  container.innerHTML = `
    <div class="login-wrapper">
      <div class="login-card">
        <h1>🦑 鱿郁仔仔</h1>
        <p class="subtitle">管理后台</p>
        <form id="login-form">
          <input type="password" id="token-input" placeholder="输入 Admin Token" autocomplete="off" />
          <button type="submit">登录</button>
        </form>
        <p id="login-error" class="error-msg"></p>
      </div>
    </div>
  `;
  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const token = document.getElementById("token-input").value.trim();
    if (!token) return;
    Auth.setToken(token);
    try {
      await API.getStats();
      location.hash = "#/stats";
    } catch (err) {
      Auth.clear();
      document.getElementById("login-error").textContent = err.message;
    }
  });
}
