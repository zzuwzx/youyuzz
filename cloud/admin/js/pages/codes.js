// codes.js — 兑换码管理
function renderCodes(container) {
  container.innerHTML = `
    <h2>兑换码管理</h2>
    <form id="gen-form" class="card">
      <div class="form-row">
        <label>数量 <input type="number" id="c-count" value="10" min="1" max="1000" required></label>
        <label>有效期(天) <input type="number" id="c-days" value="30" min="1" required></label>
        <label>设备限制 <input type="number" id="c-devices" value="1" min="1" max="10"></label>
        <label>批次ID <input type="text" id="c-batch" placeholder="可选"></label>
      </div>
      <button type="submit">生成兑换码</button>
    </form>
    <div id="codes-result" class="card" style="display:none">
      <div class="toolbar">
        <span id="codes-count"></span>
        <button id="copy-all-btn">复制全部</button>
        <button id="export-csv-btn">导出 CSV</button>
      </div>
      <div class="table-wrap"><table id="codes-table"><thead><tr>
        <th>#</th><th>兑换码</th><th>批次</th><th>操作</th>
      </tr></thead><tbody></tbody></table></div>
    </div>
  `;

  let generated = [];
  let lastBatch = "";

  document.getElementById("gen-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      count: +document.getElementById("c-count").value,
      expiry_days: +document.getElementById("c-days").value,
      device_limit: +document.getElementById("c-devices").value,
    };
    lastBatch = document.getElementById("c-batch").value.trim();
    if (lastBatch) body.batch_id = lastBatch;
    try {
      const res = await API.generateCodes(body);
      generated = res.codes || res;
      showCodes(generated);
    } catch (err) { alert(err.message); }
  });

  function showCodes(codes) {
    const box = document.getElementById("codes-result");
    box.style.display = "";
    document.getElementById("codes-count").textContent = `共 ${codes.length} 个`;
    const tbody = document.querySelector("#codes-table tbody");
    tbody.innerHTML = codes.map((c, i) => {
      const code = typeof c === "string" ? c : c.code;
      return `<tr><td>${i+1}</td><td class="mono">${code}</td><td>${lastBatch||"-"}</td>
        <td><button class="btn-sm copy-one" data-code="${code}">复制</button></td></tr>`;
    }).join("");

    tbody.querySelectorAll(".copy-one").forEach(btn => {
      btn.onclick = () => { navigator.clipboard.writeText(btn.dataset.code); btn.textContent="✓"; };
    });
  }

  document.getElementById("copy-all-btn").addEventListener("click", () => {
    const all = generated.map(c => typeof c === "string" ? c : c.code).join("\n");
    navigator.clipboard.writeText(all);
  });

  document.getElementById("export-csv-btn").addEventListener("click", () => {
    const rows = [["兑换码","批次"]];
    generated.forEach(c => { rows.push([typeof c==="string"?c:c.code, lastBatch||""]); });
    const csv = rows.map(r => r.join(",")).join("\n");
    const blob = new Blob(["\uFEFF"+csv], {type:"text/csv;charset=utf-8"});
    const a = document.createElement("a"); a.href=URL.createObjectURL(blob);
    a.download=`codes_${Date.now()}.csv`; a.click();
  });
}
