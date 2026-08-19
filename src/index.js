export default {
  async fetch(request, env) {
    const header = request.headers.get("Authorization");

    if (!header || !header.startsWith("Basic ")) {
      return unauthorized();
    }

    let user, pass;
    try {
      [user, pass] = atob(header.slice(6)).split(":");
    } catch {
      return unauthorized();
    }

    if (!safeEqual(pass, env.DASH_PASSWORD)) {
      return unauthorized();
    }

    return env.ASSETS.fetch(request);
  },
};

function unauthorized() {
  return new Response("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Tax dashboard", charset="UTF-8"',
      "Cache-Control": "no-store",
    },
  });
}

// Length-independent comparison, so response timing doesn't leak the password.
function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  const enc = new TextEncoder();
  const x = enc.encode(a);
  const y = enc.encode(b);
  if (x.length !== y.length) return false;
  return crypto.subtle.timingSafeEqual
    ? crypto.subtle.timingSafeEqual(x, y)
    : x.every((v, i) => v === y[i]);
}
