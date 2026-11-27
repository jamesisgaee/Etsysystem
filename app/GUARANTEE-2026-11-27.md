# Viva Orders: delivery guarantee (Nov 27 2026, Manager) — NOT DEPLOYED

## Audit (Nov 23 – Nov 27 1:50 AM PT)
19 app decisions (8 approves, 11 adjusts). All 19: webhook delivered on try 1, acked by the right bot, marked done,
and the outcome checked out (proof in buyer thread / tracker moved on, or a newer version posted).
`python3 /workspace/orders/push_to_app.py audit --hours 120` reproduces this.
Slow: Person22 v1 adjust (tapped Nov 25 10:05 PM PT, "started" 10:06 PM, art done 10:45 PM, pushed Nov 26 11:27 PM = 25 h);
Person39 v3 adjust (2 h). No tap has been recorded since Nov 26 4:26 PM PT: later approvals/changes
(Person39 v5, Person45 v6+v8, Person10 v17, Person22 v2–v4) went through bot chats, which the app cannot track.

## What changed
- src/plan.js (new, pure logic) + src/worker.js: cron sweep every 10 min (`scheduled`), re-send failed webhooks with backoff,
  re-wake no-ack decisions at 20/60/180 min, nudge started-not-done after 2 h (approve) / 4 h (adjust) twice, then mark STUCK
  (red card) and escalate artist jobs to ESCALATE_TO_BOT (Messanger). One grouped reminder per bot. Every wake carries
  pending_for_you / pending_ids / handle_all. Resend (force) now also works for started-but-stale. /api/state adds
  delivery_state + auto_wakes. Bot list of done decisions = newest first, 300. Retry log lives in decision_notes
  (by_bot = "Viva app"): no schema change.
- wrangler.jsonc + wrangler.next.jsonc: triggers.crons ["*/10 * * * *"], vars.ESCALATE_TO_BOT "Messanger".
- public/index.html + ui-next/index.html: "stuck" state (red, Resend), "X is on it · app reminded them N×".
- /workspace/orders/push_to_app.py (LIVE for bots now; safe with the old worker): undecided proofs never hide when status is
  Needs mockup (unless review.withdrawn); warns on finished art/vN previews Derek can't see; `pending --brief`; `audit`.
- BOT_INSTRUCTIONS.md, FORMATS.md (both copies), box/push_to_app.py.
- Tests: node --test test/plan.test.mjs; test/burst_test.py + test/sweep_test.py (local wrangler dev, fake secrets/hooks).
Backups: backups/*.bak.2026-11-27-guarantee

## Deploy (after Derek OKs)
Guarantee only, current UI:
    cd /workspace/viva-orders && node --test test/plan.test.mjs && npx wrangler deploy
Note: src/worker.js also carries the MAN-20 server changes (meta table auto-created on first use, empty-push guard, health).
With the MAN-20 UI too:
    cd /workspace/viva-orders && cp ui-next/index.html public/index.html && node --test test/plan.test.mjs && npx wrangler deploy
Check: `npx wrangler deployments list`, then `npx wrangler tail --format pretty` and wait for a `sweep {"checked":...}` line at the next :x0.
Then: python3 /workspace/orders/push_to_app.py --by Manager

## Rollback
    cd /workspace/viva-orders && npx wrangler rollback 8b1ac0b8-7785-481b-80e4-fd2c24488d1a
Rollback may keep the cron. To stop it: restore the old files (cp backups/worker.js.bak.2026-11-27-guarantee src/worker.js;
cp backups/index.html.bak.2026-11-27-guarantee public/index.html), set "triggers": { "crons": [] } in wrangler.jsonc, then npx wrangler deploy.
push_to_app.py: cp backups/push_to_app.py.bak.2026-11-27-guarantee /workspace/orders/push_to_app.py
