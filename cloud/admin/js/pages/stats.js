// stats.js — 统计概览
async function renderStats(container) {
  container.innerHTML = `<h2>统计概览</h2><div id="stats-cards" class="stats-grid"><p>加载中…</p></div>`;
  try {
    const s = await API.getStats();
    const cards = [
      { label: "总授权数",   value: s.total_licenses ?? s.active_licenses ?? 0, icon: "🔑" },
      { label: "活跃授权",   value: s.active_licenses ?? 0, icon: "✅" },
      { label: "已用兑换码", value: s.codes_used ?? 0, icon: "🎫" },
      { label: "未用兑换码", value: s.codes_unused ?? 0, icon: "🎟️" },
    ];
    document.getElementById("stats-cards").innerHTML = cards.map(c =>
      `<div class="stat-card"><div class="stat-icon">${c.icon}</div><div class="stat-value">${c.value}</div><div class="stat-label">${c.label}</div></div>`
    ).join("");
  } catch (err) { container.innerHTML = `<p class="error-msg">${err.message}</p>`; }
}
