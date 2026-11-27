// node --test test/plan.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { planSweep, deliveryState } from "../src/plan.js";

const T0 = Date.parse("2026-11-27T00:00:00Z");
const min = (m) => T0 + m * 60000;
const iso = (m) => new Date(min(m)).toISOString();
const base = (o = {}) => ({ status: "pending", action: "approve", decided_at: iso(0), webhook_status: "delivered",
  webhook_attempts: 1, last_note_at: null, auto_wakes: 0, last_auto_at: null, stuck_marks: 0, auto_since_ack: 0, ...o });

test("done decisions are left alone", () => {
  assert.equal(planSweep(base({ status: "done" }), min(999)).act, "none");
});
test("delivered, acked quickly: nothing to do", () => {
  assert.equal(planSweep(base({ last_note_at: iso(3) }), min(30)).act, "none");
});
test("no ack: re-wake at 20, 60, 180 min, then stuck at 240", () => {
  assert.equal(planSweep(base(), min(19)).act, "none");
  assert.equal(planSweep(base(), min(20)).reason, "no_ack_rewake");
  assert.equal(planSweep(base({ auto_wakes: 1, last_auto_at: iso(20) }), min(59)).act, "none");
  assert.equal(planSweep(base({ auto_wakes: 1, last_auto_at: iso(20) }), min(60)).act, "wake");
  assert.equal(planSweep(base({ auto_wakes: 2, last_auto_at: iso(60) }), min(180)).act, "wake");
  assert.equal(planSweep(base({ auto_wakes: 3, last_auto_at: iso(180) }), min(200)).act, "none");
  assert.equal(planSweep(base({ auto_wakes: 3, last_auto_at: iso(180) }), min(240)).act, "stuck");
});
test("failed webhook: backoff retries, stuck after 9 attempts", () => {
  const f = (o) => base({ webhook_status: "failed", webhook_error: "HTTP 429", ...o });
  assert.equal(planSweep(f({ webhook_attempts: 1 }), min(1)).act, "none");
  assert.equal(planSweep(f({ webhook_attempts: 1 }), min(2)).reason, "retry_failed");
  assert.equal(planSweep(f({ webhook_attempts: 2, auto_wakes: 1, last_auto_at: iso(2) }), min(6)).act, "none");
  assert.equal(planSweep(f({ webhook_attempts: 2, auto_wakes: 1, last_auto_at: iso(2) }), min(7)).act, "wake");
  assert.equal(planSweep(f({ webhook_attempts: 9 }), min(2000)).act, "stuck");
});
test("tap request died while 'sending'", () => {
  assert.equal(planSweep(base({ webhook_status: "sending", webhook_attempts: 0 }), min(1)).act, "none");
  assert.equal(planSweep(base({ webhook_status: "sending", webhook_attempts: 0 }), min(3)).reason, "retry_failed");
});
test("Person22 case: adjust started, never done -> nudge at 4h, 8h, stuck at 12h", () => {
  const a = (o) => base({ action: "adjust", last_note_at: iso(1), ...o });
  assert.equal(planSweep(a(), min(200)).act, "none");
  assert.equal(planSweep(a(), min(241)).reason, "still_open_nudge");
  assert.equal(planSweep(a({ auto_wakes: 1, auto_since_ack: 1, last_auto_at: iso(241) }), min(400)).act, "none");
  assert.equal(planSweep(a({ auto_wakes: 1, auto_since_ack: 1, last_auto_at: iso(241) }), min(481)).act, "wake");
  assert.equal(planSweep(a({ auto_wakes: 2, auto_since_ack: 2, last_auto_at: iso(481) }), min(721)).act, "stuck");
});
test("a fresh bot ack resets the nudge clock", () => {
  const a = base({ action: "adjust", last_note_at: iso(500), auto_wakes: 2, auto_since_ack: 0, last_auto_at: iso(481) });
  assert.equal(planSweep(a, min(600)).act, "none");
});
test("already marked stuck: no more wakes", () => {
  assert.equal(planSweep(base({ stuck_marks: 1 }), min(9999)).act, "none");
});
test("delivery states for Derek's card", () => {
  assert.equal(deliveryState(base(), min(1)), "sent");
  assert.equal(deliveryState(base({ last_note_at: iso(1) }), min(2)), "working");
  assert.equal(deliveryState(base({ status: "done" }), min(2)), "done");
  assert.equal(deliveryState(base({ stuck_marks: 1 }), min(2)), "stuck");
  assert.equal(deliveryState(base({ webhook_status: "failed" }), min(2)), "failed");
});
