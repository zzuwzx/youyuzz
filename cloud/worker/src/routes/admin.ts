import { Hono } from "hono";

type Bindings = { DB: D1Database; ADMIN_TOKEN: string };
export const adminRoutes = new Hono<{ Bindings: Bindings }>();

// Admin auth middleware
adminRoutes.use("*", async (c, next) => {
  const token = c.req.header("Authorization")?.replace("Bearer ", "");
  if (!token || token !== c.env.ADMIN_TOKEN) {
    return c.json({ error: "Unauthorized" }, 401);
  }
  await next();
});

// POST /api/admin/codes/generate - batch generate codes
adminRoutes.post("/codes/generate", async (c) => {
  const { count, valid_days, max_devices, batch_id } = await c.req.json<{
    count: number; valid_days?: number; max_devices?: number; batch_id?: string;
  }>();

  if (!count || count < 1 || count > 1000) {
    return c.json({ error: "count must be 1-1000" }, 400);
  }

  const db = c.env.DB;
  const codes: string[] = [];
  const batch = batch_id || `batch-${Date.now()}`;

  for (let i = 0; i < count; i++) {
    const code = generateCode();
    await db
      .prepare(
        "INSERT INTO activation_codes (code, batch_id, valid_days, max_devices) VALUES (?, ?, ?, ?)"
      )
      .bind(code, batch, valid_days || 365, max_devices || 2)
      .run();
    codes.push(code);
  }

  await db
    .prepare("INSERT INTO audit_log (action, detail) VALUES (?, ?)")
    .bind("generate_codes", `batch=${batch} count=${count}`)
    .run();

  return c.json({ batch_id: batch, codes });
});

// GET /api/admin/users - list activated users
adminRoutes.get("/users", async (c) => {
  const db = c.env.DB;
  const { results } = await db
    .prepare(
      `SELECT l.license_key, l.device_id, l.device_type, l.activated_at,
              l.expires_at, l.last_heartbeat, l.is_revoked,
              ac.code as activation_code
       FROM licenses l
       JOIN activation_codes ac ON l.code_id = ac.id
       ORDER BY l.activated_at DESC LIMIT 100`
    )
    .all();
  return c.json({ users: results });
});

// PUT /api/admin/users/:id - update user status
adminRoutes.put("/users/:id", async (c) => {
  const id = c.req.param("id");
  const { is_revoked } = await c.req.json<{ is_revoked: number }>();

  const db = c.env.DB;
  await db
    .prepare("UPDATE licenses SET is_revoked = ? WHERE id = ?")
    .bind(is_revoked, id)
    .run();

  return c.json({ ok: true });
});

// GET /api/admin/stats - overview stats
adminRoutes.get("/stats", async (c) => {
  const db = c.env.DB;
  const total = await db.prepare("SELECT COUNT(*) as cnt FROM licenses").first();
  const active = await db
    .prepare("SELECT COUNT(*) as cnt FROM licenses WHERE is_revoked = 0 AND expires_at > datetime('now')")
    .first();
  const codesUsed = await db
    .prepare("SELECT COUNT(*) as cnt FROM activation_codes WHERE is_used = 1")
    .first();
  const codesUnused = await db
    .prepare("SELECT COUNT(*) as cnt FROM activation_codes WHERE is_used = 0")
    .first();

  return c.json({
    total_licenses: total?.cnt || 0,
    active_licenses: active?.cnt || 0,
    codes_used: codesUsed?.cnt || 0,
    codes_unused: codesUnused?.cnt || 0,
  });
});

function generateCode(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const seg = (len: number) =>
    Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  return `${seg(4)}-${seg(4)}-${seg(4)}`;
}
