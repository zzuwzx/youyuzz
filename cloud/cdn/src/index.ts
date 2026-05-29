// 鱿郁仔仔 — Cloudflare CDN Worker
// 用途：加速 GitHub Releases 分发，提供全球 CDN 加速
// 功能：
//   - 代理 GitHub Releases 下载
//   - 全球边缘节点加速
//   - 自动缓存静态资源
//   - CORS 支持

interface Env {
  GITHUB_RELEASES_URL: string;
  CACHE_TTL: string;
  ALLOWED_ORIGINS: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // CORS 头
    const corsHeaders = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGINS || "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    
    // 处理 OPTIONS 预检请求
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }
    
    // 路由处理
    const path = url.pathname;
    
    // GET / - 首页
    if (path === "/") {
      return new Response(
        JSON.stringify({
          service: "鱿郁仔仔 CDN",
          version: "1.0.0",
          endpoints: {
            latest: "/latest",
            download: "/download/{version}/{filename}",
            health: "/health",
          },
        }),
        {
          headers: {
            "Content-Type": "application/json",
            ...corsHeaders,
          },
        }
      );
    }
    
    // GET /health - 健康检查
    if (path === "/health") {
      return new Response(
        JSON.stringify({ status: "ok", timestamp: new Date().toISOString() }),
        {
          headers: {
            "Content-Type": "application/json",
            ...corsHeaders,
          },
        }
      );
    }
    
    // GET /latest - 获取最新版本信息
    if (path === "/latest") {
      try {
        const releasesUrl = `${env.GITHUB_RELEASES_URL}/latest`;
        const response = await fetch(releasesUrl, {
          headers: {
            Accept: "application/vnd.github.v3+json",
            "User-Agent": "youyuzz-cdn/1.0",
          },
        });
        
        if (!response.ok) {
          return new Response(
            JSON.stringify({ error: "Failed to fetch latest release" }),
            {
              status: response.status,
              headers: {
                "Content-Type": "application/json",
                ...corsHeaders,
              },
            }
          );
        }
        
        const data = await response.json();
        
        // 提取需要的信息
        const release = {
          version: data.tag_name?.replace("v", "") || "unknown",
          name: data.name,
          body: data.body,
          published_at: data.published_at,
          html_url: data.html_url,
          assets: data.assets?.map((asset: any) => ({
            name: asset.name,
            size: asset.size,
            download_url: `/download/${data.tag_name?.replace("v", "")}/${asset.name}`,
            content_type: asset.content_type,
          })) || [],
        };
        
        return new Response(JSON.stringify(release, null, 2), {
          headers: {
            "Content-Type": "application/json",
            "Cache-Control": `public, max-age=${env.CACHE_TTL || 3600}`,
            ...corsHeaders,
          },
        });
      } catch (error) {
        return new Response(
          JSON.stringify({ error: "Internal server error" }),
          {
            status: 500,
            headers: {
              "Content-Type": "application/json",
              ...corsHeaders,
            },
          }
        );
      }
    }
    
    // GET /download/{version}/{filename} - 下载文件
    if (path.startsWith("/download/")) {
      const parts = path.split("/");
      if (parts.length < 4) {
        return new Response(
          JSON.stringify({ error: "Invalid download path" }),
          {
            status: 400,
            headers: {
              "Content-Type": "application/json",
              ...corsHeaders,
            },
          }
        );
      }
      
      const version = parts[2];
      const filename = parts.slice(3).join("/");
      const githubUrl = `${env.GITHUB_RELEASES_URL}/download/v${version}/${filename}`;
      
      try {
        // 代理下载请求
        const response = await fetch(githubUrl, {
          headers: {
            "User-Agent": "youyuzz-cdn/1.0",
          },
          redirect: "follow",
        });
        
        if (!response.ok) {
          return new Response(
            JSON.stringify({ error: "File not found" }),
            {
              status: response.status,
              headers: {
                "Content-Type": "application/json",
                ...corsHeaders,
              },
            }
          );
        }
        
        // 返回文件流
        return new Response(response.body, {
          headers: {
            "Content-Type": response.headers.get("Content-Type") || "application/octet-stream",
            "Content-Disposition": `attachment; filename="${filename}"`,
            "Cache-Control": `public, max-age=86400`, // 24小时缓存
            ...corsHeaders,
          },
        });
      } catch (error) {
        return new Response(
          JSON.stringify({ error: "Download failed" }),
          {
            status: 500,
            headers: {
              "Content-Type": "application/json",
              ...corsHeaders,
            },
          }
        );
      }
    }
    
    // 404
    return new Response(
      JSON.stringify({ error: "Not found" }),
      {
        status: 404,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders,
        },
      }
    );
  },
};