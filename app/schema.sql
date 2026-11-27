-- VivaMemoirStudio order app database (Cloudflare D1 / SQLite)
-- Run once:  npx wrangler d1 execute viva-orders --remote --file=schema.sql

-- One row per order. "data" is the full order JSON the bots pushed.
CREATE TABLE IF NOT EXISTS orders (
  order_id     TEXT PRIMARY KEY,
  stage        TEXT NOT NULL,
  stage_since  TEXT NOT NULL,   -- ISO time this order entered its current stage
  data         TEXT NOT NULL,   -- JSON (see FORMATS.md); may include messages: [{from, at, text, image}]
  pushed_at    TEXT NOT NULL
);

-- Every Approve / Adjust Derek taps. Never deleted.
CREATE TABLE IF NOT EXISTS decisions (
  id               TEXT PRIMARY KEY,
  order_id         TEXT NOT NULL,
  review_key       TEXT NOT NULL,   -- order_id|kind|version : one decision per review
  kind             TEXT NOT NULL,   -- art_proof | printify_mockup
  action           TEXT NOT NULL,   -- approve | adjust
  option           TEXT,            -- A / B / null
  version          TEXT,
  adjust_text      TEXT,
  artist_bot       TEXT,
  target_bot       TEXT NOT NULL,   -- bot that was woken (Messanger or the artist)
  payload          TEXT NOT NULL,   -- exact JSON sent to the bot
  decided_by       TEXT NOT NULL,
  decided_at       TEXT NOT NULL,
  webhook_status   TEXT NOT NULL,   -- delivered | failed | not_configured
  webhook_error    TEXT,
  webhook_attempts INTEGER NOT NULL DEFAULT 0,
  status           TEXT NOT NULL,   -- pending | done
  last_note        TEXT,
  last_note_by     TEXT,
  last_note_at     TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS decisions_review ON decisions(review_key);
CREATE INDEX IF NOT EXISTS decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS decisions_order ON decisions(order_id);

-- Progress notes bots send back ("sent to buyer", "artist started v13").
CREATE TABLE IF NOT EXISTS decision_notes (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  decision_id  TEXT NOT NULL,
  at           TEXT NOT NULL,
  by_bot       TEXT,
  note         TEXT,
  done         INTEGER NOT NULL DEFAULT 0
);

-- Images the bots have uploaded to R2 (names are content hashes).
CREATE TABLE IF NOT EXISTS images (
  key    TEXT PRIMARY KEY,
  bytes  INTEGER,
  at     TEXT NOT NULL
);

-- Failed logins, for slowing down password guessing.
CREATE TABLE IF NOT EXISTS login_fails (
  ip  TEXT NOT NULL,
  at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS login_fails_ip ON login_fails(ip, at);

-- Small key/value facts for the app (e.g. last_push: when bots last updated the board).
-- The Worker also creates this on first use, so old databases keep working.
CREATE TABLE IF NOT EXISTS meta (
  k   TEXT PRIMARY KEY,
  v   TEXT NOT NULL,
  at  TEXT NOT NULL
);
