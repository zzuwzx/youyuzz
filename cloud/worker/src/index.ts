import { Hono } from "hono";
import { cors } from "hono/cors";
import { authRoutes } from "./routes/auth";
import { adminRoutes } from "./routes/admin";
import { versionRoutes } from "./routes/version";

type Bindings = {
  DB: D1Database;
  ADMIN_TOKEN: string;
  APP_VERSION: string;
  APP_DOWNLOAD_URL: string;
};

const app = new Hono<{ Bindings: Bindings }>();

app.use("*", cors());

app.route("/api/auth", authRoutes);
app.route("/api/admin", adminRoutes);
app.route("/api/version", versionRoutes);

app.get("/api/health", (c) => c.json({ status: "ok" }));

export default app;
