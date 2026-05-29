import { Hono } from "hono";

type Bindings = { DB: D1Database };
export const authRoutes = new Hono<{ Bindings: Bindings }>();

// POST /api/auth/activate - activate redemption code
authRoutes.post("/activate", async (c) => {
  const { code, device_id } = await c.req.json<{ code: string; device_id: string }>();
  if (!code || !device_id) return c.json({ error: "code and device_id required" }, 400);

  const db = c.env.DB;
  const row = await db
    .prepare("SELECT * FROM activation_codes WHERE code = ? AND is_used = 0")
    .bind(code)
    .first();

  if (!row) return c.json({ error: "Invalid or already used code" }, 400);

  const expires = new Date();
  expires.setDate(expires.getDate() + (row.valid_days as number));
  const licenseKey = crypto.randomUUID();

  await db
    .prepare(
      "INSERT INTO licenses (license_key, code_id, device_id, expires_at) VALUES (?, ?, ?, ?)"
    )
    .bind(licenseKey, row.id, device_id, expires.toISOString())
    .run();

  await db
    .prepare("UPDATE activation_codes SET is_used = 1, used_at = datetime('now') WHERE id = ?")
    .bind(row.id)
    .run();

  await db
    .prepare("INSERT INTO audit_log (action, detail, ip) VALUES (?, ?, ?)")
    .bind("activate", `code=${code} device=${device_id}`, c.req.header("CF-Connecting-IP"))
    .run();

  return c.json({ license_key: licenseKey, expires_at: expires.toISOString() });
});

// POST /api/auth/verify - verify license validity
authRoutes.post("/verify", async (c) => {
  const { license_key, device_id } = await c.req.json<{ license_key: string; device_id: string }>();
  if (!license_key || !device_id) return c.json({ error: "license_key and device_id required" }, 400);

  const db = c.env.DB;
  const license = await db
    .prepare(
      "SELECT * FROM licenses WHERE license_key = ? AND device_id = ? AND is_revoked = 0"
    )
    .bind(license_key, device_id)
    .first();

  if (!license) return c.json({ valid: false, reason: "not found or revoked" });

  const expires = new Date(license.expires_at as string);
  if (expires < new Date()) return c.json({ valid: false, reason: "expired" });

  return c.json({
    valid: true,
    expires_at: license.expires_at,
    device_type: license.device_type,
  });
});

// POST /api/auth/heartbeat - update last heartbeat
authRoutes.post("/heartbeat", async (c) => {
  const { license_key, device_id } = await c.req.json<{ license_key: string; device_id: string }>();
  if (!license_key || !device_id) return c.json({ error: "missing fields" }, 400);

  const db = c.env.DB;
  await db
    .prepare(
      "UPDATE licenses SET last_heartbeat = datetime('now') WHERE license_key = ? AND device_id = ?"
    )
    .bind(license_key, device_id)
    .run();

  return c.json({ ok: true });
});

// GET /api/auth/status - query license status
authRoutes.get("/status", async (c) => {
  const key = c.req.query("license_key");
  if (!key) return c.json({ error: "license_key required" }, 400);

  const db = c.env.DB;
  const license = await db
    .prepare("SELECT * FROM licenses WHERE license_key = ?")
    .bind(key)
    .first();

  if (!license) return c.json({ found: false });

  return c.json({
    found: true,
    device_id: license.device_id,
    device_type: license.device_type,
    expires_at: license.expires_at,
    is_revoked: license.is_revoked === 1,
    last_heartbeat: license.last_heartbeat,
  });
});
