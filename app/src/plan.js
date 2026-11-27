// Pure decision logic for the Viva Orders delivery guarantee. No I/O, so it can be unit-tested
// with plain Node (see test/plan.test.mjs).

// ---- Delivery guarantee (cron sweep) ----
// Every few minutes the Worker's cron looks at every decision that isn't done and makes sure a bot
// actually has it. No LLM polling: a bot is only woken when something is overdue.
export const AUTO_BY = "Viva app";                    // decision_notes.by_bot for the app's own retry log
export const FAILED_RETRY_MIN = [2, 5, 15, 30, 60, 120, 240, 480]; // webhook never got through: retry backoff
export const NO_ACK_REWAKE_MIN = [20, 60, 180];       // delivered but no "started" ack: re-wake at these ages
export const OPEN_NUDGE_HOURS = { approve: 2, adjust: 4 }; // started but not done after this long: nudge
export const MAX_OPEN_NUDGES = 2;
export const SENDING_STUCK_MIN = 2;                   // 'sending' that long means the tap's request died midway
export const SWEEP_DAYS = 14;                         // only look at decisions this recent

// What Derek's card should say. sent = delivered, not picked up yet; working = a bot acked;
// stuck = the app gave up re-waking and wants a human; failed = never got through yet.
export function deliveryState(d, nowMs) {
  if (d.status === "done") return "done";
  if (Number(d.stuck_marks) > 0) return "stuck";
  if (d.webhook_status === "failed" || d.webhook_status === "not_configured") return "failed";
  if (d.webhook_status === "sending") return nowMs - Date.parse(d.decided_at) > SENDING_STUCK_MIN * 60000 ? "failed" : "sending";
  if (d.last_note_at) return "working";
  return "sent";
}

// Pure function (unit-tested in test/plan.test.mjs): what should the sweep do with this decision?
// row: decision row + auto_wakes (count of app notes), last_auto_at, stuck_marks, auto_since_ack.
export function planSweep(row, nowMs) {
  if (row.status !== "pending") return { act: "none" };
  if (Number(row.stuck_marks) > 0) return { act: "none", why: "already marked stuck" };
  const age = (t) => (nowMs - Date.parse(t)) / 60000; // minutes
  const sinceDecided = age(row.decided_at);
  const autos = Number(row.auto_wakes) || 0;
  const lastTry = row.last_auto_at && Date.parse(row.last_auto_at) > Date.parse(row.decided_at) ? row.last_auto_at : row.decided_at;

  const notThrough = row.webhook_status === "failed" || row.webhook_status === "not_configured" ||
    (row.webhook_status === "sending" && sinceDecided > SENDING_STUCK_MIN);
  if (notThrough) {
    const n = Number(row.webhook_attempts) || 0;
    if (n > FAILED_RETRY_MIN.length) return { act: "stuck", why: `webhook failed ${n} times (${row.webhook_error || row.webhook_status})` };
    const wait = FAILED_RETRY_MIN[Math.max(0, Math.min(n - 1, FAILED_RETRY_MIN.length - 1))];
    if (age(lastTry) >= wait) return { act: "wake", reason: "retry_failed", why: `delivery ${row.webhook_status}; try ${n + 1}` };
    return { act: "none", why: "waiting to retry" };
  }
  if (row.webhook_status !== "delivered") return { act: "none", why: "sending" };

  if (!row.last_note_at) {
    // Delivered, but no bot has said "started".
    if (autos >= NO_ACK_REWAKE_MIN.length) {
      return sinceDecided >= NO_ACK_REWAKE_MIN[NO_ACK_REWAKE_MIN.length - 1] + 60
        ? { act: "stuck", why: `no bot picked it up after ${autos + 1} wakes` } : { act: "none", why: "last re-wake pending" };
    }
    if (sinceDecided >= NO_ACK_REWAKE_MIN[autos]) return { act: "wake", reason: "no_ack_rewake", why: `no ack after ${Math.round(sinceDecided)} min` };
    return { act: "none", why: "waiting for first ack" };
  }

  // A bot acked "started" but never "done" (the Person22 case: started, then sat for a day).
  const hours = OPEN_NUDGE_HOURS[row.action] || 4;
  const openMin = age(row.last_note_at);
  const nudges = Number(row.auto_since_ack) || 0;
  if (openMin < hours * 60) return { act: "none", why: "bot working" };
  if (row.last_auto_at && age(row.last_auto_at) < hours * 60) return { act: "none", why: "nudged recently" };
  if (nudges >= MAX_OPEN_NUDGES) return { act: "stuck", why: `started ${Math.round(openMin / 60)} h ago but never marked done` };
  return { act: "wake", reason: "still_open_nudge", why: `started ${Math.round(openMin / 60)} h ago, not done` };
}

