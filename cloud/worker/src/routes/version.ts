import { Hono } from "hono";

type Bindings = { APP_VERSION: string; APP_DOWNLOAD_URL: string };
export const versionRoutes = new Hono<{ Bindings: Bindings }>();

// GET /api/version/latest
versionRoutes.get("/latest", (c) => {
  return c.json({
    version: c.env.APP_VERSION,
    download_url: c.env.APP_DOWNLOAD_URL,
  });
});
