# viva-orders

Code and docs for the VivaMemoirStudio order workflow (Etsy + Printify custom portraits).

## Layout

- `app/` — the **Viva Orders** Cloudflare Worker app (D1 database `viva-orders`, KV for images).
  - `src/` worker code (`worker.js`, `plan.js`), `public/` live UI, `ui-next/` next UI (not yet deployed),
    `test/` tests, `schema.sql`, `wrangler*.jsonc`, `package.json`, plus README and design notes.
- `orders/` — the box-side scripts and instructions the bots use:
  - `push_to_app.py`, `build_board.py`, `queue_build.py`, `tracker_refresh.py`
  - `BOT_INSTRUCTIONS.md`, `FORMATS.md`, `WORKFLOW_FOR_AUTOMATION.md` (full shop workflow), `STYLE_GUIDES/` (text guides only)

## Not in this repo

Secrets (APP_PASSWORD, SESSION_SECRET, BOT_TOKEN, BOT_WEBHOOKS, API keys) live only as
`wrangler secret` values / local files and are never committed. Buyer order folders, the order
tracker, board files, buyer photos and art are excluded because they contain buyer PII.
Example tracking numbers in demo data are replaced with `REDACTED`.

Buyer names and Etsy order numbers in docs, scripts, tests and demo data are replaced with
placeholders (`PersonNN`, `Sample Buyer X`, `10000001NN`). The box copies keep the real values, so
the hard-coded sample data in `orders/queue_build.py` and `orders/build_board.py` is illustrative only.
