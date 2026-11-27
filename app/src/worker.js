import { AUTO_BY, SWEEP_DAYS, planSweep, deliveryState } from "./plan.js";
// VivaMemoirStudio order + mockup approval app — Cloudflare Worker.
//
// What this does:
//   * Serves the phone app (public/index.html).
//   * Lets Derek log in with one password (signed cookie, stays logged in ~4 months).
//   * Receives order data + images pushed by the bots (bot token).
//   * Records Derek's Approve / Adjust taps and wakes the right bot via its
//     Grok Bot routine webhook.
//   * Lets bots confirm a decision and report progress back.
//
// It never messages buyers and never touches Printify. It only records and relays.

const STAGES = ["problem", "needs_ok", "artist", "waiting_buyer", "ordering", "printing", "shipped", "delivered"];
const STATUS_TO_STAGE = {
  "Problem": "problem",
  "Waiting for Derek": "needs_ok",
  "Needs mockup": "artist",
  "Waiting on buyer": "waiting_buyer",
  "Approved - ordering": "ordering",
  "In production": "printing",
  "Shipped": "shipped",
  "Delivered": "delivered",
};
const SESSION_COOKIE = "viva_s";
const SESSION_DAYS = 120;
const IMAGE_KEY_RE = /^[a-f0-9]{64}\.(jpg|png|webp)$/;
const IMAGE_TYPES = { jpg: "image/jpeg", png: "image/png", webp: "image/webp" };
const MAX_LOGIN_FAILS = 8;          // per IP per 15 minutes
const WEBHOOK_TIMEOUT_MS = 10000;
const MAX_MESSAGES = 30;
const MAX_MESSAGE_TEXT = 4000;


export default {
  async fetch(request, env, ctx) {
    try {
      return await route(request, env, ctx);
    } catch (err) {
      console.error(err && err.stack || err);
      return json({ error: "Something went wrong on the server." }, 500);
    }
  },
  // Cron trigger (wrangler.jsonc "triggers.crons"). Re-sends anything a bot hasn't picked up or finished.
  async scheduled(event, env, ctx) {
    ctx.waitUntil(sweep(env).then((r) => console.log("sweep", JSON.stringify(r)))
      .catch((err) => console.error("sweep failed", err && err.stack || err)));
  },
};

async function route(request, env, ctx) {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;

  // ---------- bot endpoints (bearer token) ----------
  if (path.startsWith("/api/bot/")) {
    if (!(await botAuthorized(request, env))) return json({ error: "Bad or missing bot token." }, 401);
    if (path === "/api/bot/push" && method === "POST") return botPush(request, env);
    if (path === "/api/bot/images/missing" && method === "POST") return botImagesMissing(request, env);
    let m;
    if ((m = path.match(/^\/api\/bot\/images\/([^/]+)$/)) && method === "PUT") return botImagePut(request, env, m[1]);
    if (path === "/api/bot/decisions" && method === "GET") return botListDecisions(url, env);
    if ((m = path.match(/^\/api\/bot\/decisions\/([\w-]+)$/)) && method === "GET") return botGetDecision(env, m[1]);
    if ((m = path.match(/^\/api\/bot\/decisions\/([\w-]+)\/ack$/)) && method === "POST") return botAck(request, env, m[1]);
    return json({ error: "Not found." }, 404);
  }

  // ---------- login ----------
  if (path === "/api/login" && method === "POST") return login(request, env);
  if (path === "/api/logout" && method === "POST") {
    return json({ ok: true }, 200, { "Set-Cookie": `${SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax` });
  }

  // ---------- Derek's endpoints (session cookie) ----------
  if (path.startsWith("/api/") || path.startsWith("/img/")) {
    if (!(await sessionValid(request, env))) return json({ error: "Please log in." }, 401);
    if (method !== "GET" && request.headers.get("x-viva") !== "1") return json({ error: "Bad request." }, 400);

    if (path === "/api/me" && method === "GET") return json({ ok: true });
    if (path === "/api/state" && method === "GET") return getState(env);
    if (path === "/api/decisions" && method === "POST") return createDecision(request, env, url);
    let m;
    if ((m = path.match(/^\/api\/decisions\/([\w-]+)\/retry$/)) && method === "POST") return retryDecision(env, m[1], url);
    if ((m = path.match(/^\/img\/([^/]+)$/)) && method === "GET") return serveImage(env, m[1]);
    return json({ error: "Not found." }, 404);
  }

  // ---------- the app itself (static files, contain no order data) ----------
  return env.ASSETS.fetch(request);
}

// =====================================================================
// Auth helpers
// =====================================================================

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(text)));
  return new Uint8Array(buf);
}

async function safeEqual(a, b) {
  // Compare two secrets without leaking timing. Hash first so lengths match.
  const [ha, hb] = await Promise.all([sha256(a), sha256(b)]);
  if (crypto.subtle.timingSafeEqual) return crypto.subtle.timingSafeEqual(ha, hb);
  let diff = 0;
  for (let i = 0; i < ha.length; i++) diff |= ha[i] ^ hb[i];
  return diff === 0;
}

async function hmac(secret, text) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(text));
  return b64url(new Uint8Array(sig));
}

function b64url(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function getCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  for (const part of header.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return v.join("=");
  }
  return null;
}

async function sessionValid(request, env) {
  if (!env.SESSION_SECRET) return false;
  const c = getCookie(request, SESSION_COOKIE);
  if (!c) return false;
  const [exp, sig] = c.split(".");
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  return safeEqual(sig, await hmac(env.SESSION_SECRET, "s|" + exp));
}

async function botAuthorized(request, env) {
  if (!env.BOT_TOKEN) return false;
  const h = request.headers.get("Authorization") || "";
  if (!h.startsWith("Bearer ")) return false;
  return safeEqual(h.slice(7).trim(), env.BOT_TOKEN);
}

async function login(request, env) {
  if (!env.APP_PASSWORD || !env.SESSION_SECRET) {
    return json({ error: "The app password isn't set up yet (see README step 5)." }, 500);
  }
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const since = Date.now() - 15 * 60 * 1000;
  const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM login_fails WHERE ip = ? AND at > ?").bind(ip, since).first();
  if (row && row.n >= MAX_LOGIN_FAILS) return json({ error: "Too many tries. Wait 15 minutes." }, 429);

  const body = await readJson(request, 10_000);
  const password = body && typeof body.password === "string" ? body.password : "";
  if (!(await safeEqual(password, env.APP_PASSWORD))) {
    await env.DB.batch([
      env.DB.prepare("INSERT INTO login_fails (ip, at) VALUES (?, ?)").bind(ip, Date.now()),
      env.DB.prepare("DELETE FROM login_fails WHERE at < ?").bind(Date.now() - 24 * 3600 * 1000),
    ]);
    return json({ error: "Wrong password." }, 401);
  }
  await env.DB.prepare("DELETE FROM login_fails WHERE ip = ?").bind(ip).run();
  const exp = Date.now() + SESSION_DAYS * 24 * 3600 * 1000;
  const cookie = `${exp}.${await hmac(env.SESSION_SECRET, "s|" + exp)}`;
  return json({ ok: true }, 200, {
    "Set-Cookie": `${SESSION_COOKIE}=${cookie}; Path=/; Max-Age=${SESSION_DAYS * 24 * 3600}; HttpOnly; Secure; SameSite=Lax`,
  });
}

// =====================================================================
// Derek's side
// =====================================================================

async function getState(env) {
  const orders = await env.DB.prepare("SELECT order_id, stage, stage_since, data, pushed_at FROM orders").all();
  const decisions = await env.DB.prepare(
    `SELECT id, order_id, review_key, kind, action, option, version, adjust_text, artist_bot, target_bot,
            decided_by, decided_at, webhook_status, webhook_error, webhook_attempts, status,
            last_note, last_note_by, last_note_at,
            (SELECT COUNT(*) FROM decision_notes n WHERE n.decision_id = decisions.id AND n.by_bot = '${AUTO_BY}') AS auto_wakes,
            (SELECT MAX(n.at) FROM decision_notes n WHERE n.decision_id = decisions.id AND n.by_bot = '${AUTO_BY}') AS last_auto_at,
            (SELECT COUNT(*) FROM decision_notes n WHERE n.decision_id = decisions.id AND n.by_bot = '${AUTO_BY}'
               AND n.note LIKE 'STUCK%' AND (decisions.last_note_at IS NULL OR n.at > decisions.last_note_at)) AS stuck_marks
       FROM decisions ORDER BY decided_at DESC LIMIT 300`).all();
  const nowMs = Date.now();
  for (const d of decisions.results || []) d.delivery_state = deliveryState(d, nowMs);
  const out = (orders.results || []).map((r) => {
    const d = safeParse(r.data) || {};
    d.order_id = r.order_id;
    d.stage = r.stage;
    d.stage_since = r.stage_since;
    d.pushed_at = r.pushed_at;
    return d;
  });
  // Extra info for the "can I trust this?" line. Older app versions ignore it.
  let lastPush = null;
  try {
    await ensureMeta(env);
    const m = await env.DB.prepare("SELECT v FROM meta WHERE k = 'last_push'").first();
    lastPush = m ? safeParse(m.v) : null;
  } catch (err) { console.error("meta read", err); }
  const hooks = safeParse(env.BOT_WEBHOOKS || "") || {};
  const health = {
    last_push: lastPush,
    bots_connected: Object.keys(hooks).filter((k) => hooks[k] && hooks[k].url),
  };
  return json({ orders: out, decisions: decisions.results || [], now: new Date().toISOString(), health });
}

let META_READY = false;
async function ensureMeta(env) {
  if (META_READY) return;
  await env.DB.prepare("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL, at TEXT NOT NULL)").run();
  META_READY = true;
}

function reviewKey(order) {
  const r = order.review;
  if (!r || !r.kind) return null;
  return `${order.order_id}|${r.kind}|${r.version || ""}`;
}

async function createDecision(request, env, url) {
  const body = await readJson(request, 20_000);
  if (!body) return json({ error: "Bad request." }, 400);
  const { order_id, review_key, action } = body;
  if (action !== "approve" && action !== "adjust") return json({ error: "Unknown action." }, 400);

  const row = await env.DB.prepare("SELECT data FROM orders WHERE order_id = ?").bind(String(order_id || "")).first();
  if (!row) return json({ error: "That order isn't in the app anymore. Pull down to refresh." }, 404);
  const order = safeParse(row.data) || {};
  order.order_id = String(order_id);
  const review = order.review;
  const key = reviewKey(order);
  if (!key) return json({ error: "This order has nothing waiting for your OK." }, 409);
  if (key !== review_key) return json({ error: "The bot posted a newer mockup. Refresh to see it." }, 409);

  const options = Array.isArray(review.options) ? review.options : [];
  let option = null;
  let adjustText = null;
  let approvedFiles = [];
  let approvedOptions = [];
  if (action === "approve") {
    if (options.length === 0) return json({ error: "There's no mockup image to approve yet." }, 409);
    const requested = body.option;
    if (options.length === 1 && requested !== "all") {
      option = options[0].label || null;
      approvedOptions = options.slice(0, 1);
    } else if (requested === "all") {
      option = "all";
      approvedOptions = options;
    } else if (typeof requested === "string" && options.some((o) => o.label === requested)) {
      option = requested;
      approvedOptions = options.filter((o) => o.label === requested);
    } else {
      return json({ error: "Approve all, or pick one option." }, 400);
    }
    approvedFiles = approvedOptions.map((o) => o.source_path).filter(Boolean);
    approvedOptions = approvedOptions.map((o) => ({ label: o.label || null, source_path: o.source_path || null }));
  } else {
    adjustText = typeof body.adjust_text === "string" ? body.adjust_text.trim() : "";
    if (!adjustText) return json({ error: "Type what to change first." }, 400);
    if (adjustText.length > 2000) return json({ error: "That note is too long (2000 characters max)." }, 400);
    if (typeof body.option === "string" && options.some((o) => o.label === body.option)) option = body.option;
  }

  const kind = review.kind;
  const artist = review.artist_bot || order.artist_bot || "Designer";
  // Approvals go to Messanger (sends proof / places order). Art changes go back to the
  // original artist. Changes to a Printify mockup go to Messanger, who made it.
  const target = action === "approve" || kind === "printify_mockup" ? "Messanger" : artist;

  const id = crypto.randomUUID();
  const now = new Date();
  const payload = buildPayload({
    id, order, kind, action, option, version: review.version || null, adjustText, artist, target,
    approvedFiles, approvedOptions, now, origin: url.origin,
  });

  try {
    await env.DB.prepare(
      `INSERT INTO decisions (id, order_id, review_key, kind, action, option, version, adjust_text, artist_bot,
         target_bot, payload, decided_by, decided_at, webhook_status, webhook_attempts, status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Derek', ?, 'sending', 0, 'pending')`)
      .bind(id, order.order_id, key, kind, action, option, review.version || null, adjustText, artist, target,
        JSON.stringify(payload), now.toISOString())
      .run();
  } catch (err) {
    if (String(err).includes("UNIQUE")) {
      const existing = await publicDecision(env, null, key);
      return json({ error: "You already decided on this one.", decision: existing }, 409);
    }
    throw err;
  }

  await deliver(env, id, target, { ...payload, wake_reason: "new", ...(await pendingInfo(env, target)) });
  return json({ ok: true, decision: await publicDecision(env, id) });
}

// Every wake tells the bot how many decisions it has open, so it handles ALL of them in one run
// (5 approves in a row may arrive as 5 wakes, 1 coalesced wake, or wakes while the bot is busy).
async function pendingInfo(env, bot) {
  try {
    const r = await env.DB.prepare("SELECT id FROM decisions WHERE status = 'pending' AND target_bot = ? ORDER BY decided_at ASC LIMIT 50")
      .bind(bot).all();
    const ids = (r.results || []).map((x) => x.id);
    return {
      pending_for_you: ids.length,
      pending_ids: ids,
      handle_all: `You have ${ids.length} open decision${ids.length === 1 ? "" : "s"}. Run: python3 /workspace/orders/push_to_app.py pending --bot "${bot}" and handle EVERY one, not only this one. Ack each one "started" right away, then --done when finished.`,
    };
  } catch (err) {
    console.error("pendingInfo", err);
    return {};
  }
}

async function autoNote(env, id, note) {
  await env.DB.prepare("INSERT INTO decision_notes (decision_id, at, by_bot, note, done) VALUES (?, ?, ?, ?, 0)")
    .bind(id, new Date().toISOString(), AUTO_BY, String(note).slice(0, 500)).run();
}

async function retryDecision(env, id, url) {
  const row = await env.DB.prepare(
    "SELECT target_bot, payload, webhook_status, status, last_note_at, decided_at FROM decisions WHERE id = ?").bind(id).first();
  if (!row) return json({ error: "Not found." }, 404);
  // ?force=1 re-wakes the bot for a decision that was delivered but never picked up (no ack after 30 min).
  // Same decision id, so a bot that already started will see it in "pending" and must not redo the work.
  const force = url && url.searchParams.get("force") === "1";
  const unpicked = row.status === "pending" && !row.last_note_at && Date.now() - Date.parse(row.decided_at) > 30 * 60 * 1000;
  const staleOpen = row.status === "pending" && row.last_note_at && Date.now() - Date.parse(row.last_note_at) > 60 * 60 * 1000;
  if (row.webhook_status === "delivered" && !(force && (unpicked || staleOpen))) return json({ ok: true, decision: await publicDecision(env, id) });
  const payload = safeParse(row.payload) || {};
  const extra = row.webhook_status === "delivered"
    ? { wake_reason: "derek_resend", reminder: "Derek tapped Resend. If you already did this decision, just ack it with --done and where it stands. Never send a proof twice or place a second order." }
    : { wake_reason: "derek_retry" };
  await deliver(env, id, row.target_bot, { ...payload, ...extra, ...(await pendingInfo(env, row.target_bot)) });
  await autoNote(env, id, `Derek tapped ${row.webhook_status === "delivered" ? "Resend" : "Retry"}; woke ${row.target_bot} again.`);
  return json({ ok: true, decision: await publicDecision(env, id) });
}

function buildPayload({ id, order, kind, action, option, version, adjustText, artist, target, approvedFiles, approvedOptions, now, origin }) {
  const who = `order ${order.order_id} (${order.buyer_first_name || "buyer"})`;
  const files = Array.isArray(approvedFiles) ? approvedFiles : [];
  const optsList = Array.isArray(approvedOptions) ? approvedOptions : [];
  const labels = optsList.map((o) => o && o.label).filter(Boolean);
  const opt = option === "all"
    ? `ALL ${files.length || labels.length || "listed"} option${(files.length || labels.length) === 1 ? "" : "s"} of `
    : (option ? `option ${option} of ` : "");
  let task;
  if (action === "approve" && kind === "art_proof") {
    const all = option === "all" || files.length > 1;
    const send = all
      ? `send EVERY file in approved_files to the buyer on Etsy as proofs (all of them, not just one)`
      : `send the approved proof file to the buyer on Etsy`;
    const after = all && files.length > 1
      ? ` Because more than one option was sent, wait for the buyer to pick a final before placing a Printify order.`
      : "";
    const named = labels.length ? ` (${labels.join(", ")})` : "";
    task = `Derek approved ${opt}${version || "the mockup"} for ${who}${named}. Confirm this decision first (GET confirm_url with your bot token), then ${send}.${after} Then POST to ack_url with done=true.`;
  } else if (action === "approve") {
    task = `Derek approved the Printify mockup for ${who}. Confirm this decision first (GET confirm_url with your bot token), then place and pay the Printify order. Then POST to ack_url with done=true.`;
  } else if (kind === "printify_mockup") {
    task = `Derek wants changes to the Printify mockup for ${who} before ordering. Confirm this decision first (GET confirm_url with your bot token). His exact words: "${adjustText}". Fix the Printify product, then push the new mockup to the app with a new review.version so he can OK it. Do NOT place the order. POST to ack_url when work starts, and with done=true when the new mockup is pushed.`;
  } else {
    task = `Derek wants changes to ${version || "the mockup"} for ${who}. Confirm this decision first (GET confirm_url with your bot token). Pass his exact words to ${target}: "${adjustText}". The artist makes the next version and pushes it to the app. POST to ack_url when work starts, and with done=true when the new version is pushed.`;
  }
  return {
    type: "derek_decision",
    task,
    decision_id: id,
    order_id: order.order_id,
    buyer_first_name: order.buyer_first_name || null,
    product: order.product || null,
    kind,
    action,
    option,
    version,
    adjust_text: adjustText,
    approved_files: files,
    approved_options: optsList,
    artist_bot: artist,
    target_bot: target,
    decided_by: "Derek",
    decided_at: now.toISOString(),
    decided_at_pt: formatPT(now),
    confirm_url: `${origin}/api/bot/decisions/${id}`,
    ack_url: `${origin}/api/bot/decisions/${id}/ack`,
  };
}

function webhookFor(env, bot) {
  const all = safeParse(env.BOT_WEBHOOKS || "") || {};
  return all[bot] || all.default || null;
}

async function deliver(env, id, target, payload) {
  const hook = webhookFor(env, target);
  let status, error = null;
  if (!hook || !hook.url) {
    status = "not_configured";
    error = `No webhook set for ${target}. The bot will see it on its next check.`;
  } else {
    ({ status, error } = await postWebhook(hook, payload));
  }
  await env.DB.prepare(
    "UPDATE decisions SET webhook_status = ?, webhook_error = ?, webhook_attempts = webhook_attempts + 1 WHERE id = ?")
    .bind(status, error, id).run();
}

async function publicDecision(env, id, reviewKeyValue) {
  const sql = `SELECT id, order_id, review_key, kind, action, option, version, adjust_text, artist_bot, target_bot,
      decided_by, decided_at, webhook_status, webhook_error, webhook_attempts, status, last_note, last_note_by, last_note_at
      FROM decisions WHERE ${id ? "id" : "review_key"} = ?`;
  return env.DB.prepare(sql).bind(id || reviewKeyValue).first();
}

async function serveImage(env, key) {
  if (!IMAGE_KEY_RE.test(key)) return new Response("Not found", { status: 404 });
  const obj = await env.IMAGES.get(key, { type: "stream" });
  if (!obj) return new Response("Not found", { status: 404 });
  const ext = key.split(".").pop();
  return new Response(obj, {
    headers: {
      "Content-Type": IMAGE_TYPES[ext],
      // Private: only this logged-in browser may cache it. Names are content hashes, so they never change.
      "Cache-Control": "private, max-age=31536000, immutable",
    },
  });
}

// =====================================================================
// Bot side
// =====================================================================

async function botPush(request, env) {
  const body = await readJson(request, 5_000_000);
  if (!body || !Array.isArray(body.orders)) return json({ error: "Send JSON like {\"orders\": [...]}." }, 400);
  if (body.orders.length > 1000) return json({ error: "Too many orders in one push." }, 400);
  // Safety: an empty push would wipe the whole board (e.g. a broken or half-written tracker file).
  if (body.orders.length === 0 && body.allow_empty !== true) {
    return json({ error: "Refusing an empty push (it would erase every order). Check ORDER_TRACKER.csv. Send allow_empty: true only if the board really should be empty." }, 400);
  }

  const nowIso = new Date().toISOString();
  const existing = await env.DB.prepare("SELECT order_id, stage, stage_since FROM orders").all();
  const prev = new Map((existing.results || []).map((r) => [r.order_id, r]));

  const seen = new Set();
  const stmts = [];
  const changes = [];
  const problems = [];
  for (const raw of body.orders) {
    if (!raw || typeof raw !== "object") continue;
    const id = String(raw.order_id || "").trim();
    if (!id || id.length > 60) { problems.push("An order is missing order_id."); continue; }
    if (seen.has(id)) { problems.push(`Order ${id} appears twice; kept the first.`); continue; }
    seen.add(id);
    let stage = STAGES.includes(raw.stage) ? raw.stage : STATUS_TO_STAGE[raw.status];
    if (!stage) { problems.push(`Order ${id} has unknown status "${raw.status}"; shown as Something's wrong.`); stage = "problem"; }
    const old = prev.get(id);
    let since = old && old.stage === stage ? old.stage_since : nowIso;
    if (!old && typeof raw.stage_since === "string" && !isNaN(Date.parse(raw.stage_since))) since = raw.stage_since;
    if (old && old.stage !== stage) changes.push({ order_id: id, from: old.stage, to: stage });
    const data = { ...raw, order_id: id, stage };
    delete data.stage_since;
    data.messages = sanitizeMessages(raw.messages);
    stmts.push(env.DB.prepare(
      `INSERT INTO orders (order_id, stage, stage_since, data, pushed_at) VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(order_id) DO UPDATE SET stage = excluded.stage, stage_since = excluded.stage_since,
         data = excluded.data, pushed_at = excluded.pushed_at`)
      .bind(id, stage, since, JSON.stringify(data), nowIso));
  }
  // Orders no longer in the tracker are removed from the board (their decisions are kept).
  stmts.push(env.DB.prepare("DELETE FROM orders WHERE order_id NOT IN (SELECT value FROM json_each(?))")
    .bind(JSON.stringify([...seen])));
  // Remember when the last push happened and what looked off, so Derek can see if the board is fresh.
  const clientWarnings = Array.isArray(body.warnings)
    ? body.warnings.filter((w) => typeof w === "string").slice(0, 50).map((w) => w.slice(0, 300)) : [];
  const by = typeof body.pushed_by === "string" ? body.pushed_by.trim().slice(0, 40) : null;
  let metaOk = true;
  try { await ensureMeta(env); } catch (err) { metaOk = false; console.error("meta create", err); }
  if (metaOk) {
    stmts.push(env.DB.prepare(
      "INSERT INTO meta (k, v, at) VALUES ('last_push', ?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v, at = excluded.at")
      .bind(JSON.stringify({ at: nowIso, orders: seen.size, by, warnings: [...problems, ...clientWarnings] }), nowIso));
  }
  await env.DB.batch(stmts);
  return json({ ok: true, orders: seen.size, stage_changes: changes, warnings: problems });
}

async function botImagesMissing(request, env) {
  const body = await readJson(request, 500_000);
  const keys = body && Array.isArray(body.keys) ? body.keys.filter((k) => IMAGE_KEY_RE.test(k)) : [];
  if (!keys.length) return json({ missing: [] });
  const res = await env.DB.prepare("SELECT key FROM images WHERE key IN (SELECT value FROM json_each(?))")
    .bind(JSON.stringify(keys)).all();
  const have = new Set((res.results || []).map((r) => r.key));
  return json({ missing: keys.filter((k) => !have.has(k)) });
}

async function botImagePut(request, env, key) {
  if (!IMAGE_KEY_RE.test(key)) return json({ error: "Image name must be <sha256>.jpg|png|webp" }, 400);
  const len = Number(request.headers.get("Content-Length") || 0);
  if (len > 15_000_000) return json({ error: "Image too big (15 MB max). Resize it first." }, 413);
  const ext = key.split(".").pop();
  // Stored in Workers KV (free plan, no card needed; 25 MB per value).
  void ext;
  await env.IMAGES.put(key, await request.arrayBuffer());
  await env.DB.prepare("INSERT OR IGNORE INTO images (key, bytes, at) VALUES (?, ?, ?)")
    .bind(key, len || null, new Date().toISOString()).run();
  return json({ ok: true, key });
}

async function botListDecisions(url, env) {
  const status = url.searchParams.get("status") || "pending";
  const bot = url.searchParams.get("bot");
  let sql = "SELECT * FROM decisions WHERE status = ?";
  const args = [status];
  if (bot) { sql += " AND target_bot = ?"; args.push(bot); }
  sql += status === "pending" ? " ORDER BY decided_at ASC LIMIT 100" : " ORDER BY decided_at DESC LIMIT 300";
  const res = await env.DB.prepare(sql).bind(...args).all();
  return json({ decisions: (res.results || []).map(botView) });
}

async function botGetDecision(env, id) {
  const row = await env.DB.prepare("SELECT * FROM decisions WHERE id = ?").bind(id).first();
  if (!row) return json({ error: "No such decision. Do NOT act on it." }, 404);
  return json({ decision: botView(row) });
}

function botView(row) {
  return {
    ...safeParse(row.payload),
    status: row.status,
    webhook_status: row.webhook_status,
    last_note: row.last_note,
    genuine: true, // it came from the app's database, so Derek really tapped it
  };
}

async function botAck(request, env, id) {
  const body = await readJson(request, 20_000) || {};
  const row = await env.DB.prepare("SELECT id FROM decisions WHERE id = ?").bind(id).first();
  if (!row) return json({ error: "No such decision." }, 404);
  const note = typeof body.note === "string" ? body.note.trim().slice(0, 500) : "";
  const by = typeof body.by === "string" ? body.by.trim().slice(0, 40) : "bot";
  const done = body.done === true;
  const now = new Date().toISOString();
  const stmts = [
    env.DB.prepare("INSERT INTO decision_notes (decision_id, at, by_bot, note, done) VALUES (?, ?, ?, ?, ?)")
      .bind(id, now, by, note, done ? 1 : 0),
    env.DB.prepare(`UPDATE decisions SET last_note = ?, last_note_by = ?, last_note_at = ?
                    ${done ? ", status = 'done'" : ""} WHERE id = ?`).bind(note || (done ? "Done" : "Working on it"), by, now, id),
  ];
  await env.DB.batch(stmts);
  return json({ ok: true });
}

// =====================================================================
// Delivery guarantee: cron sweep
// =====================================================================

async function sweep(env, nowMs = Date.now()) {
  const since = new Date(nowMs - SWEEP_DAYS * 86400000).toISOString();
  const res = await env.DB.prepare(
    `SELECT d.id, d.order_id, d.kind, d.action, d.version, d.target_bot, d.artist_bot, d.payload, d.decided_at,
            d.webhook_status, d.webhook_error, d.webhook_attempts, d.status, d.last_note, d.last_note_by, d.last_note_at,
            (SELECT COUNT(*) FROM decision_notes n WHERE n.decision_id = d.id AND n.by_bot = ?1) AS auto_wakes,
            (SELECT MAX(n.at) FROM decision_notes n WHERE n.decision_id = d.id AND n.by_bot = ?1) AS last_auto_at,
            (SELECT COUNT(*) FROM decision_notes n WHERE n.decision_id = d.id AND n.by_bot = ?1 AND n.note LIKE 'STUCK%'
               AND (d.last_note_at IS NULL OR n.at > d.last_note_at)) AS stuck_marks,
            (SELECT COUNT(*) FROM decision_notes n WHERE n.decision_id = d.id AND n.by_bot = ?1
               AND d.last_note_at IS NOT NULL AND n.at > d.last_note_at) AS auto_since_ack
       FROM decisions d WHERE d.status = 'pending' AND d.decided_at > ?2 ORDER BY d.decided_at ASC LIMIT 200`)
    .bind(AUTO_BY, since).all();
  const rows = res.results || [];
  // Group wakes per bot: 5 overdue decisions for Messanger = ONE wake listing all 5 (saves usage).
  const wakeByBot = new Map();
  const summary = { checked: rows.length, woke: [], stuck: [] };
  for (const row of rows) {
    const plan = planSweep(row, nowMs);
    if (plan.act === "wake") {
      if (!wakeByBot.has(row.target_bot)) wakeByBot.set(row.target_bot, []);
      wakeByBot.get(row.target_bot).push({ row, plan });
    } else if (plan.act === "stuck") {
      await autoNote(env, row.id, `STUCK: ${plan.why}. Derek: tap Resend or tell Manager.`);
      summary.stuck.push(row.id);
      await escalate(env, row, plan.why);
    }
  }
  for (const [bot, items] of wakeByBot) {
    const first = items[0];
    const payload = {
      type: "derek_decision_reminder",
      wake_reason: items.map((x) => x.plan.reason).join(","),
      task: `REMINDER from the Viva Orders app: ${items.length} of Derek's decisions for you are not finished (${items.map((x) => `${x.row.order_id} ${x.row.action} ${x.row.version || ""}: ${x.plan.why}`).join("; ")}). ` +
        `Follow 'When the Derek's decisions routine wakes you' in /workspace/orders/BOT_INSTRUCTIONS.md. If you already did one, just ack it --done with where it stands; never send a proof twice or place a second order.`,
      decision_id: first.row.id,        // for older routines that read one id
      decision_ids: items.map((x) => x.row.id),
      target_bot: bot,
      ...(await pendingInfo(env, bot)),
    };
    // One HTTP call per bot. Its result is recorded on every decision in the group.
    await deliverGroup(env, items.map((x) => ({ id: x.row.id, count: x.plan.reason === "retry_failed" })), bot, payload);
    for (const x of items) {
      await autoNote(env, x.row.id, `Auto re-wake (${x.plan.reason}): ${x.plan.why}.`);
      summary.woke.push(x.row.id);
    }
  }
  return summary;
}

// Stuck = re-waking didn't work. Tell a second bot, if one is configured (vars.ESCALATE_TO_BOT).
// Artist decisions escalate to that bot (normally Messanger, who reassigns art). Approvals already
// target Messanger, so they escalate only if ESCALATE_TO_BOT is someone else.
async function escalate(env, row, why) {
  const to = (env.ESCALATE_TO_BOT || "").trim();
  if (!to || to === row.target_bot) return;
  const hook = webhookFor(env, to);
  if (!hook || !hook.url || (safeParse(env.BOT_WEBHOOKS || "") || {})[to] == null) return;
  const payload = {
    type: "derek_decision_stuck",
    task: `Escalation from the Viva Orders app: Derek's ${row.action} on ${row.order_id} ${row.version || ""} for ${row.target_bot} is stuck (${why}). ` +
      `Check with python3 /workspace/orders/push_to_app.py show ${row.id}. Don't do ${row.target_bot}'s work twice: if ${row.target_bot} is an artist that is busy or not answering, hand the job to a backup artist per BOT_INSTRUCTIONS.md (priority message) and ack the decision with a note. Tell Derek in one line.`,
    decision_id: row.id,
    stuck_bot: row.target_bot,
    escalated_to: to,
  };
  await postWebhook(hook, payload);
  await autoNote(env, row.id, `Escalated to ${to}.`);
}

async function postWebhook(hook, payload) {
  try {
    const headers = { "Content-Type": "application/json" };
    if (hook.key) headers["Authorization"] = `Bearer ${hook.key}`;
    const res = await fetch(hook.url, { method: "POST", headers, body: JSON.stringify(payload), signal: AbortSignal.timeout(WEBHOOK_TIMEOUT_MS) });
    if (res.ok) return { status: "delivered", error: null };
    return { status: "failed", error: `Grok Bot answered HTTP ${res.status}` };
  } catch (err) {
    return { status: "failed", error: err && err.name === "TimeoutError" ? "Grok Bot didn't answer in 10 seconds" : `Couldn't reach Grok Bot (${err && err.message || err})` };
  }
}

async function deliverGroup(env, targets, target, payload) {
  const hook = webhookFor(env, target);
  const r = !hook || !hook.url
    ? { status: "not_configured", error: `No webhook set for ${target}. The bot will see it on its next check.` }
    : await postWebhook(hook, payload);
  // A failed reminder never downgrades a decision that was already delivered once.
  for (const { id, count } of targets) {
    await env.DB.prepare(
      `UPDATE decisions SET webhook_attempts = webhook_attempts + ?,
         webhook_status = CASE WHEN ? = 'delivered' THEN 'delivered' WHEN webhook_status = 'delivered' THEN 'delivered' ELSE ? END,
         webhook_error = CASE WHEN ? = 'delivered' THEN NULL WHEN webhook_status = 'delivered' THEN webhook_error ELSE ? END
       WHERE id = ?`).bind(count ? 1 : 0, r.status, r.status, r.status, r.error, id).run();
  }
  return r;
}

// =====================================================================
// Small utilities
// =====================================================================

function json(obj, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...extraHeaders },
  });
}

async function readJson(request, maxBytes) {
  const len = Number(request.headers.get("Content-Length") || 0);
  if (len > maxBytes) return null;
  const text = await request.text();
  if (text.length > maxBytes) return null;
  return safeParse(text);
}

function safeParse(text) {
  try { return JSON.parse(text); } catch { return null; }
}

function sanitizeMessages(raw) {
  if (!Array.isArray(raw)) return [];
  const out = [];
  for (const m of raw) {
    if (!m || typeof m !== "object") continue;
    const frm = String(m.from || "").toLowerCase() === "shop" ? "shop" : "buyer";
    const item = { from: frm };
    if (typeof m.at === "string" && m.at.trim()) item.at = m.at.trim().slice(0, 80);
    if (typeof m.text === "string" && m.text.trim()) {
      item.text = m.text.replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, "[email removed]")
        .replace(/(?<![\w.])(?:\+?1[\s.-])?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?!\w)/g, "[phone removed]")
        .trim().slice(0, MAX_MESSAGE_TEXT);
      if (!item.text) delete item.text;
    }
    if (typeof m.image === "string" && IMAGE_KEY_RE.test(m.image)) item.image = m.image;
    if (!item.text && !item.image) continue;
    out.push(item);
    if (out.length >= MAX_MESSAGES) break;
  }
  return out;
}

function formatPT(date) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "numeric", minute: "2-digit", hour12: true,
  }).formatToParts(date).map((p) => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute} ${parts.dayPeriod} PT`;
}
