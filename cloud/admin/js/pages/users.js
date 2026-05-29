// users.js — 用户列表
async function renderUsers(container) {
  container.innerHTML = `<h2>用户列表</h2><div id="users-box" class="card"><p>加载中…</p></div>`;
  try {
    const users = await API.getUsers();
    const box = document.getElementById("users-box");
    if (!users.length) { box.innerHTML = "<p>暂无激活用户</p>"; return; }
    box.innerHTML = `<div class="table-wrap"><table id="users-table"><thead><tr>
      <th>License Key</th><th>设备ID</th><th>设备类型</th><th>激活时间</th><th>到期时间</th><th>状态</th><th>操作</th>
    </tr></thead><tbody>${users.map(u => {
      const active = u.status === "active";
      return `<tr>
        <td class="mono">${u.license_key||""}</td>
        <td class="mono">${u.device_id||""}</td>
        <td>${u.device_type||""}</td>
        <td>${u.activated_at?new Date(u.activated_at).toLocaleDateString():""}</td>
        <td>${u.expires_at?new Date(u.expires_at).toLocaleDateString():""}</td>
        <td><span class="badge ${active?"active":"disabled"}">${active?"活跃":"已禁用"}</span></td>
        <td><button class="btn-sm toggle-btn" data-id="${u.license_key}" data-status="${u.status}">${active?"禁用":"启用"}</button></td>
      </tr>`;
    }).join("")}</tbody></table></div>`;

    box.querySelectorAll(".toggle-btn").forEach(btn => {
      btn.onclick = async () => {
        const newStatus = btn.dataset.status === "active" ? "disabled" : "active";
        try {
          await API.updateUser(btn.dataset.id, { status: newStatus });
          renderUsers(container);
        } catch (err) { alert(err.message); }
      };
    });
  } catch (err) { container.innerHTML = `<p class="error-msg">${err.message}</p>`; }
}
