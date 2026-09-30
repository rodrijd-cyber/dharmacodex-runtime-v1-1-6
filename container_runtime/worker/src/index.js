import { Container, ContainerProxy, getContainer } from "@cloudflare/containers";

export { ContainerProxy };

const VERSION_PREFIX = "/v1.1.6/";
const ALLOWED_ASSETS = new Set([
  "v1.1.6/manifest.sha256.json",
  "v1.1.6/databases/Astro_Readings_V2.0.db",
  "v1.1.6/databases/DM_DB_v2.0.db",
  "v1.1.6/databases/HD_DB_v2.0.db",
  "v1.1.6/databases/NUM_DB_v2.0.db",
  "v1.1.6/geometry/BodyGraph.svg",
  "v1.1.6/geometry/DM.svg",
  "v1.1.6/ephe/sepl_18.se1",
  "v1.1.6/ephe/seas_18.se1",
  "v1.1.6/ephe/semoon_18.se1"
]);

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  });
}

async function assetBridge(request, env) {
  const url = new URL(request.url);
  if (request.method !== "GET" || !url.pathname.startsWith(VERSION_PREFIX)) {
    return json({ error: "ASSET_NOT_ALLOWED" }, 404);
  }
  const key = url.pathname.slice(1);
  if (!ALLOWED_ASSETS.has(key)) return json({ error: "ASSET_NOT_ALLOWED" }, 404);
  const object = await env.RUNTIME_BUCKET.get(key);
  if (!object) return json({ error: "ASSET_MISSING" }, 404);
  return new Response(object.body, {
    headers: {
      "content-type": key.endsWith(".json") ? "application/json" : "application/octet-stream",
      "cache-control": "no-store",
      "x-dcx-r2-key": key
    }
  });
}

export class DharmaCodexRuntimeContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "20m";
  enableInternet = false;
  allowedHosts = ["runtime-assets"];
}

DharmaCodexRuntimeContainer.outboundByHost = {
  "runtime-assets": assetBridge
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/internal/api/reading") {
      const container = getContainer(env.DCX_RUNTIME_CONTAINER, "runtime-v1-1-6");
      const headers = new Headers(request.headers);
      headers.delete("cookie");
      headers.delete("authorization");
      headers.delete("cf-access-jwt-assertion");
      return container.fetch(new Request("http://container/internal/reading", {
        method: "POST",
        headers,
        body: request.body
      }));
    }
    if (request.method === "GET" && url.pathname === "/internal/runtime/health") {
      const container = getContainer(env.DCX_RUNTIME_CONTAINER, "runtime-v1-1-6");
      return container.fetch(new Request("http://container/health"));
    }
    return json({ error: "NOT_FOUND" }, 404);
  }
};
