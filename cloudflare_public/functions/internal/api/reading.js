const response = (body, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

export async function onRequestPost(context) {
  try {
    const accessAssertion = context.request.headers.get("cf-access-jwt-assertion");
    if (!accessAssertion && context.env.DCX_ALLOW_LOCAL_UNAUTHENTICATED !== "true") {
      return response({ error: "PRIVATE_ACCESS_REQUIRED" }, 401);
    }
    if (!context.env.RUNTIME_SERVICE) return response({ error: "RUNTIME_SERVICE_UNAVAILABLE" }, 503);
    const body = await context.request.text();
    const upstream = await context.env.RUNTIME_SERVICE.fetch("https://runtime.internal/internal/api/reading", {
      method: "POST",
      headers: { "content-type": "application/json", "x-dcx-gateway": "pages-function" },
      body,
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") || "application/json", "cache-control": "no-store" },
    });
  } catch (error) {
    return response({ error: "RUNTIME_READING_UNAVAILABLE" }, 503);
  }
}

export async function onRequest(context) {
  if (context.request.method !== "POST") return response({ error: "METHOD_NOT_ALLOWED" }, 405);
  return onRequestPost(context);
}
