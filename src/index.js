const SESSION_HOURS = 12;
const COOKIE = "dash_session";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (!env.DASH_PASSWORD) {
      return new Response("DASH_PASSWORD secret is not set.", { status: 500 });
    }

    if (url.pathname === "/logout") {
      return new Response(null, {
        status: 302,
        headers: {
          Location: "/login",
          "Set-Cookie": `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`,
        },
      });
    }

    if (url.pathname === "/login") {
      if (request.method === "POST") {
        const form = await request.formData();
        const supplied = String(form.get("password") || "");

        if (!timingSafeEqual(supplied, env.DASH_PASSWORD)) {
          return html(loginPage("That password does not match."), 401);
        }

        const token = await mintToken(env.DASH_PASSWORD);
        return new Response(null, {
          status: 302,
          headers: {
            Location: "/",
            "Set-Cookie":
              `${COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; ` +
              `Max-Age=${SESSION_HOURS * 3600}`,
          },
        });
      }
      return html(loginPage(), 200);
    }

    const cookie = readCookie(request.headers.get("Cookie"), COOKIE);
    if (!(await verifyToken(cookie, env.DASH_PASSWORD))) {
      return html(loginPage(), 401);
    }

    return env.ASSETS.fetch(request);
  },
};

/* ---------- session token ---------- */
// Cookie holds an expiry plus an HMAC of it, so it cannot be forged
// without the password, and it expires on its own.

async function key(secret) {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
}

async function sign(value, secret) {
  const sig = await crypto.subtle.sign("HMAC", await key(secret), new TextEncoder().encode(value));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function mintToken(secret) {
  const expires = String(Date.now() + SESSION_HOURS * 3600 * 1000);
  return `${expires}.${await sign(expires, secret)}`;
}

async function verifyToken(token, secret) {
  if (!token || !token.includes(".")) return false;
  const [expires, sig] = token.split(".");
  if (!/^\d+$/.test(expires) || Number(expires) < Date.now()) return false;
  return timingSafeEqual(sig, await sign(expires, secret));
}

function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function readCookie(header, name) {
  if (!header) return null;
  for (const part of header.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return v.join("=");
  }
  return null;
}

/* ---------- login page ---------- */

function html(body, status) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

function loginPage(error) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in — tax dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Zilla+Slab:wght@600;700&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0e1a24;--panel:#132430;--line:#22394a;--ink:#e9e2d4;--muted:#7b93a3;--amber:#e6a33c;--rust:#e0765a}
  *{box-sizing:border-box}
  body{
    margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:var(--bg);color:var(--ink);
    font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:14px;padding:24px;
  }
  .card{width:100%;max-width:380px}
  .eyebrow{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
  h1{font-family:"Zilla Slab",Georgia,serif;font-weight:700;font-size:34px;line-height:1.05;margin:0 0 26px}
  .rule{height:1px;background:var(--line);margin-bottom:26px}
  label{display:block;font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:9px}
  input{
    width:100%;background:var(--panel);border:1px solid var(--line);color:var(--ink);
    font-family:inherit;font-size:15px;padding:12px 14px;
  }
  input:focus{outline:none;border-color:var(--amber)}
  button{
    width:100%;margin-top:16px;background:var(--amber);border:0;color:#0e1a24;
    font-family:inherit;font-size:13px;font-weight:600;letter-spacing:.1em;
    text-transform:uppercase;padding:13px;cursor:pointer;
  }
  button:hover{background:var(--ink)}
  button:focus-visible,input:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
  .err{color:var(--rust);font-size:12px;margin:14px 0 0}
  .foot{font-size:11px;color:var(--muted);margin:26px 0 0;line-height:1.6}
</style>
</head>
<body>
  <div class="card">
    <p class="eyebrow">Internal reporting</p>
    <h1>Tax work items</h1>
    <div class="rule"></div>
    <form method="POST" action="/login">
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" autofocus required>
      <button type="submit">Sign in</button>
      ${error ? `<p class="err">${error}</p>` : ""}
    </form>
    <p class="foot">Client data. Do not share this link or password outside the practice.</p>
  </div>
</body>
</html>`;
}
