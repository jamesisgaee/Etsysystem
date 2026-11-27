# Build the VivaMemoirStudio shop automation system

Hi Claude. I'm Derek, owner of the Etsy shop **VivaMemoirStudio**. I'm not a developer. I want you to build a cheaper, mostly automatic version of my shop system, starting from this repo:

**https://github.com/jamesisgaee/Etsysystem**

Clone it, read `README.md`, `orders/WORKFLOW_FOR_AUTOMATION.md`, `orders/BOT_INSTRUCTIONS.md`, `orders/FORMATS.md`, `orders/STYLE_GUIDES/`, `app/README.md`, `app/GUARANTEE-2026-11-27.md`, `app/schema.sql`, and `app/src/`. Then follow this brief.

Do not invent API features. Check current official docs (Etsy: https://developers.etsy.com/documentation/ and the OpenAPI spec; Printify: https://developers.printify.com/). If you can't verify something, say so, mark it as a risk, and give a fallback. Ask me the questions in each phase before you start that phase.

Work on a **separate preview Worker and database**, never the live production app, until I explicitly say to deploy.

---

## 1. Goal

Today the shop is run by several AI chat bots. That is slow and expensive. I want a system that runs mostly inside the existing **Cloudflare Worker** (cron, Queues, D1) and talks to the **Etsy**, **Printify**, and image-model APIs directly. A human (me) or an AI should only step in where a judgment call is needed: writing a who's-who from photos, judging a portrait, approving a mockup, or sending a message that no API can send.

Keep the **Viva Orders** phone app I already use. I still approve and request changes there. Automate everything around that tap.

The live shop must keep working the whole time. New code starts in dry-run mode and must not message real buyers, place real Printify production orders, or mark real Etsy orders shipped until I say go.

---

## 2. Hard rules (never break these)

1. **Only my tap in the Viva Orders app, while I am logged in, counts as approval.** A bot, a script, a comment, or an email saying "Derek approved" is not approval.
2. **Nothing goes to a buyer, no Printify order is sent to production, and no money is spent** without that tap. Creating a Printify *draft* or an on-hold order is fine in later phases; `send_to_production` and payment are not, until I approve the Printify mockup.
3. **Never print listing / stock art.** Every Printify order must use the buyer's approved custom file. Cancel any Etsy auto-import that comes in with sample art.
4. **Secrets stay in `wrangler secret` or `.dev.vars`.** Never commit them, never paste them into chat, never put them in the repo. If you need a key, tell me the name and where to set it, and I will add it on this computer.
5. **No buyer PII in the repo.** No addresses, emails, phones, real photos, or real order folders. Buyer names in this repo are already faked as `PersonNN` / `Sample Buyer X`, and order numbers as `10000001NN`. Keep it that way. Addresses needed to place a Printify order may live only in Worker secrets / D1, never in git.
6. A decision is handled **once**. The same `decision_id` must never send a proof twice or place two orders.
7. Print files are exact pixels at **300 dpi**. Canvas wrap sides are solid colors sampled from the art edges: never white, mirrored, or stretched art.
8. No film, character, director, or studio names in image prompts; no "Disney" in buyer-facing text; no text on the art unless the buyer asked for it.
9. Times are **America/Los_Angeles (Pacific)**.

---

## 3. How the shop works today

Custom cartoon-style portraits (Charlie Brown, Nightmare Before Christmas, Elf, pet Christmas, and some older lines) sold on Etsy, printed through **Printify store `11985418`**.

Current flow, all still done by bots and a browser:

1. Buyer orders on Etsy and messages photos.
2. An artist generates the art (Gemini and/or Seedream via OpenRouter), following `orders/STYLE_GUIDES/`.
3. I approve or adjust it in the Viva Orders app.
4. The proof (preview JPG only, never the print file) is sent to the buyer on Etsy Messages.
5. The buyer approves or asks for changes. Changes go back to the same artist, then to me again, then to the buyer.
6. A **manual** Printify order is placed with the custom file. Any Etsy auto-import with stock art is canceled.
7. When Printify ships, tracking is added to the Etsy receipt.

Statuses, in order: `Needs mockup` → `Waiting for Derek` → `Waiting on buyer` → (optional Printify-mockup review) → `Approved - ordering` → `In production` → `Shipped` → `Delivered`. `Problem` can be set at any time.

The app already exists and is live at a `*.workers.dev` URL. Bots push the board to it; my tap is saved in D1, then a webhook wakes a bot. That bot-wake step is what we want to replace with Worker code over time.

---

## 4. Reuse what is already in the repo

Do not rebuild the approval app from scratch.

| Path | What it is |
|---|---|
| `app/` | Cloudflare Worker "Viva Orders": login, board, Approve / Adjust, D1 schema, image store, bot push/ack APIs, decision webhooks. |
| `app/src/worker.js` + `app/src/plan.js` | Live worker, plus the 10-minute delivery-guarantee sweep (written, **not deployed** to production yet). |
| `app/public/` | Live UI. `app/ui-next/` is a newer UI, also not deployed. |
| `app/schema.sql` | `orders`, `decisions`, `decision_notes`, `images`, `login_fails`, `meta`. |
| `app/test/` | Unit tests for the sweep, plus burst/sweep integration tests. |
| `app/GUARANTEE-2026-11-27.md` | How the reliability cron should work, and how to deploy / roll it back. |
| `orders/WORKFLOW_FOR_AUTOMATION.md` | Full current workflow, product blueprints, costs, pain points. |
| `orders/BOT_INSTRUCTIONS.md` + `FORMATS.md` | Decision meanings, `app.json` shape, webhook/ack contract. Keep this contract. |
| `orders/STYLE_GUIDES/` | Master prompts, MUST-HAVE / NEVER rules, size table, revision rules. **Text only.** Approved style-reference images are not in the repo (they are buyer art). I will add refs locally if you need them; do not commit them. |
| `orders/push_to_app.py` | How the board is pushed today. New automation can post the same JSON to `/api/bot/push`. |

**Important:** `app/wrangler.jsonc` already points at the **live** D1 database and KV namespace. Do not deploy over them. Create a Worker named something like `viva-orders-dev`, with its own D1 and KV, for all development.

Note: the app README mentions R2, but the live Worker stores images in **Workers KV** (`IMAGES`). Keep KV unless we deliberately migrate.

---

## 5. API facts I already checked (re-verify; flag if docs disagree)

### Etsy Open API v3 — what works

- Register an app at https://www.etsy.com/developers/your-apps. OAuth 2.0. Every request needs `x-api-key` and `Authorization: Bearer`.
- Useful scopes to start: `transactions_r` (orders), `transactions_w` (write tracking), `shops_r`. Ask for no extra scopes until needed.
- Orders: `GET /v3/application/shops/{shop_id}/receipts` and `.../receipts/{receipt_id}`. Receipts include `message_from_buyer`. Personalization and photo-upload answers live on each transaction's `variations` (photo uploads are often a URL + mime type — confirm in a test receipt).
- Webhooks (configured in the Etsy Webhook portal, not by API): `order.paid`, `order.canceled`, `order.shipped`, `order.delivered`. Payload is thin (`event_type`, `shop_id`, `resource_url`); fetch the receipt. Verify `webhook-id` / `webhook-timestamp` / `webhook-signature`.
- Tracking write-back: `POST /v3/application/shops/{shop_id}/receipts/{receipt_id}/tracking` with `tracking_code` and `carrier_name`. This emails the buyer, so it is a live action.

### Etsy — hard limits and risks

1. **Buyer Messages cannot be read or sent through the API.** In July 2026 Etsy's own Open API support said there are no v3 conversation endpoints or `conversations_r` / `conversations_w` scopes. A public count of the OpenAPI spec in August 2026 found 76 endpoints and none for messaging. **Do not design Phase 5 as if you can POST to the buyer's Etsy thread.** See fallbacks below.
2. **Shipping addresses and `buyer_email` may be restricted.** Address fields can require a "preferred partnership" in some regions. `buyer_email` needs a separate Etsy approval. Test this in Phase 1 before building Printify placement around it. Fallback: I paste the ship-to address into the app at order time, or I finish the Printify address step myself.
3. **Tracking write-back has had 403s** for some apps ("preferred shipping partners"). Test on a cheap order I approve, and have a fallback: show me the tracking and I add it in the Etsy seller dashboard.
4. There is no Etsy API token in the current operation. We are starting from zero.

### Etsy messaging fallback (required, not optional)

Inbound, in this order of preference:
- Parse Etsy's "Conversation with …" notification emails (today a Gmail filter already forwards these). Use this to learn that a buyer replied, then show me the text and prompt me, or open a "needs a reply" card in the app.
- I (or a remaining helper) paste or screenshot the thread into the app, as today.

Outbound proofs, welcome notes, check-ins, thank-yous:
- The Worker drafts the exact message and attaches the approved preview.
- I send it from Etsy Messages (one tap / copy-paste), and the app does not mark `Waiting on buyer` until I confirm it went out — or a helper still posts it and acks the decision.
- Do **not** email the buyer outside Etsy unless I later get `buyer_email` access *and* I say that is OK. Buyers expect Etsy Messages.
- Do not build a brittle "drive the Etsy website" bot as the main path.

### Printify API — what works

- Base URL `https://api.printify.com/v1/`. Header `Authorization: Bearer <token>`. Personal access token from the Printify dashboard. Store ID **`11985418`**.
- Upload art: `POST /v1/uploads/images.json` (HTTPS URL or base64).
- Create a product in the shop, or create an order with `blueprint_id` + `print_provider_id` + `variant_id` and `print_areas` pointing at the **custom** file URL — never a listing sample.
- `POST /v1/shops/{shop_id}/orders.json` creates an order. **New shops often auto-send to production and charge the card.** Before any live create, I must set this shop to **manual approval**. Then production starts only on `POST .../orders/{id}/send_to_production.json`, and only after my Printify-mockup tap.
- Cancel: `POST .../orders/{id}/cancel.json` only while status is `on-hold` or `payment-not-received`. Use this for auto-imports with stock art. Once it is in production, the API cannot cancel it.
- Shipping quote: `POST .../orders/shipping.json`. Methods are typically 1 = standard, 2 = priority, 3 = express, 4 = economy — **re-verify**. We use Standard or Economy. Printify needs a recipient phone; use a secret I will set (my shop phone), never commit it.
- Webhooks can be created per shop (`order:shipment:created` and similar). Use them to pull carrier + tracking. Confirm topics in current docs.
- Known product details (from the workflow doc; confirm before hard-coding): 5x7 matte rolled poster = blueprint **1220**, Jondo, 1500×2100 px; US matte posters = **282** (US only — EU used **494** via Print Pigeons); stretched canvas 1.25" = **1159**. Put the Etsy order number in the product title.

---

## 6. Build this in phases

Finish and let me test a phase before starting the next. Default every write action to **dry-run** (`DRY_RUN=1` in Worker vars). Dry-run logs the exact request it would have made and updates a "would do" note in the app, but does not call the live write endpoint.

### Phase 0 — Project setup (do this first)

- Clone the repo. Create `viva-orders-dev` with its own D1 + KV. Copy schema. Do not touch production IDs.
- Add `.dev.vars` (gitignored) and document every secret name in a `SECRETS.md` that lists names only, no values.
- Confirm `node --test test/plan.test.mjs` passes.
- **Ask me:** Cloudflare account ready? OK to create a dev Worker? Should the GitHub repo be switched back to private once you have access?

**Milestone:** I can open the dev app, log in, and see a sample board with fake `PersonNN` data. Production app unchanged.

### Phase 1 — Etsy OAuth + order sync (not messages)

- I register the Etsy app; you give me click-by-click steps. You add an OAuth start/callback on the dev Worker and store refresh tokens as secrets / in D1, not in git.
- On `order.paid` (plus a periodic receipts poll as backup), create or update the order in D1: Etsy receipt id, listing, size/variation, personalization text, `message_from_buyer`, ship-by, amount, photo-upload URLs if present.
- Download buyer photos from those URLs into private KV, not the repo.
- New orders appear in the app as `Needs mockup`. No artist run and no buyer message yet.
- **Ask me:** Etsy shop name / numeric shop id if I have it; whether I already have an Etsy app; OK to subscribe to `order.paid` on a test listing; whether addresses appear on a real receipt.

**Milestone:** A test order I place (or a recent receipt I approve you to read) shows up in the dev app with the right size, note, and photos. Message threads may be missing — that is expected.

### Phase 2 — Printify drafts, auto-import cancel, no production

- I create a Printify API token; you tell me where to put it.
- From an approved print file (start with a dummy PNG I provide), create a **draft product** in a way that cannot charge me: upload the custom file, enable only the ordered variant, title contains the Etsy order number, pull the Printify mockup image into the app as `review.kind = printify_mockup`.
- Detect auto-imported Etsy orders that still have listing art and, in dry-run, show me a "would cancel" card. Only cancel for real when I say so, and only if the order is still cancelable.
- Shipping quote on screen (Standard vs Economy) against the 20% profit goal if Etsy net is available.
- **Ask me:** confirm the shop is on manual order approval; my usual provider (Jondo / Printify Choice / Print Pigeons); whether you may cancel a *test* auto-import; the phone secret for later live orders.

**Milestone:** I see a Printify mockup in the dev app for a dummy file. No order is in production. I can tell the difference between a custom-file draft and a stock-art auto-import.

### Phase 3 — Art generation pipeline

- Build a Worker- or queue-driven pipeline that, given an order's photos, personalization, and product line, fills the style guide's MASTER PROMPT, calls the models, and writes preview + print-size files + a photo-vs-art compare sheet into the app as `review.kind = art_proof`.
- Models, from the workflow doc (re-check prices): Gemini Flash for cheap drafts, Gemini Pro 4K for harder jobs and edits, Seedream via OpenRouter as fallback when Gemini refuses. Hard cap about 3 paid generations per job unless I raise it. Run one call at a time.
- Follow each guide's ref order, MUST-HAVE / NEVER lines, and revision rule: edit the last-sent image, 0 px change outside the mask.
- Cloudflare Workers cannot run heavy local tools (RealESRGAN, custom eye-arc scripts). Prefer API-side sizing, or a small optional script on this computer for wrap edges and compare sheets. Do not block the phase on those extras.
- **Ask me:** I will need to provide `GEMINI_API_KEY` and `OPENROUTER_API_KEY`, plus local style-ref images. Which line should we try first (Charlie Brown is the biggest seller)? OK to spend a few dollars on test generations of my own photos, not a real buyer's?

**Milestone:** I run a test on my own photos, get a v1 preview in the dev app, tap Adjust, and get a v2 that only changes what I typed.

### Phase 4 — Hook the pipeline to the existing approval flow

- Reuse `decisions`, the unique `review_key`, Approve / Adjust / "Approve & send all", acks, and `FORMATS.md` payloads.
- My Approve on `art_proof` must **not** auto-message the buyer (see Phase 5). It should put a "ready to send" card in the app with the draft message and the preview.
- My Approve on `printify_mockup` must **not** call `send_to_production` until dry-run is off *and* I have confirmed. It may create an on-hold order if I have already agreed to that in Phase 2.
- Adjust goes back to the same generation job with my exact `adjust_text`.
- **Ask me:** is the Printify-mockup approval still required on every order before placement? (It is supposed to be; some recent orders skipped it.)

**Milestone:** I can take a test order from "Needs mockup" to "ready to send proof" and "ready to place Printify order" using only the app, with nothing leaving the building.

### Phase 5 — Buyer proof messaging (API cannot do this)

- Build the outbound draft (welcome, proof, check-in, thank-you, ship-by warning) and the inbound email parser.
- The app shows: draft text, attached preview, a copy button, and a "I sent this" confirm. Only then set `Waiting on buyer`.
- When a "Conversation with …" email arrives, or I paste a reply, show it on the order and, if they asked for changes, move the order back to `Needs mockup` with `buyer_feedback` and require my approval again before a new proof is prepared.
- **Ask me:** shop Gmail access (how you should read notification emails — I will not paste passwords in chat); the exact wording I want for welcome / proof / thank-you if I have a preference; who sends the Etsy message for now (me, or a helper).

**Milestone:** For a test conversation (not a real buyer, or a buyer I name), I can send a proof from Etsy using your draft, confirm in the app, and a fake "please change X" reply comes back as a new review card.

### Phase 6 — Tracking sync

- Subscribe to Printify shipment webhooks (and poll as backup). When tracking appears, show it on the order, set `Shipped`, and in dry-run show "would add tracking to Etsy receipt …".
- Only call Etsy's tracking endpoint when dry-run is off and I have approved that order's ship action (a one-time "auto-add tracking for this shop" toggle is OK *after* a successful manual test).
- Flag red when Printify's estimated ship date is after the Etsy ship-by, or the ship-by is today/past with no tracking.
- **Ask me:** after one successful test, may tracking auto-post to Etsy?

**Milestone:** A shipment event (real or replayed) updates the dev app. Etsy is not touched until I turn dry-run off for that order.

### Phase 7 — Reliability cron from GUARANTEE, then cut over

- Deploy the already-written 10-minute sweep (`app/src/plan.js`) to the **dev** Worker first: re-send failed work, re-wake stale jobs, mark stuck (red Resend card), escalate artist jobs.
- Adapt it so the Worker itself retries API work, not only bot webhooks. Keep "do once" by `decision_id`.
- Add a visible dry-run / live switch in the app, defaulting to dry-run.
- Only after I test this, and only if I say so, deploy to production. Use `npx wrangler deploy` from `app/`, then `npx wrangler deployments list` and `npx wrangler tail`.
- Rollback: `npx wrangler rollback <previous-deployment-id>`. Record the current production deployment id *before* any production deploy. If a cron was added and must be stopped, clear `triggers.crons` and redeploy, as in `GUARANTEE-2026-11-27.md`.
- **Ask me:** OK to deploy guarantee + new phases to production? Which phase may leave dry-run?

**Milestone:** I can hammer 5 Approves and 3 Adjusts in a row on the dev app, including a fake failed send, and every one is either finished or visibly stuck with Resend. Nothing is silently lost.

---

## 7. Accounts, keys, and where they go

I will create these. You tell me the exact clicks and the secret names. You never see the values in chat if we can avoid it.

| Secret / account | Where it goes | Used for |
|---|---|---|
| Cloudflare login | this computer, `wrangler login` | Deploy the dev (and later live) Worker |
| `APP_PASSWORD`, `SESSION_SECRET` | `wrangler secret` / `.dev.vars` | My app login (dev should use a *different* password from production) |
| Etsy keystring + shared secret, OAuth refresh token | same | Order sync, later tracking |
| Etsy webhook signing secret | same | Verify `order.paid` etc. |
| Printify API token, webhook secret, shop id `11985418` | same | Drafts, cancel auto-imports, later orders + tracking |
| `PRINTIFY_RECIPIENT_PHONE` | same | Required by Printify; my shop phone |
| `GEMINI_API_KEY` | same | Image generation |
| `OPENROUTER_API_KEY` | same | Seedream fallback |
| Gmail access for "Conversation with …" mail, if we use it | same, OAuth preferred | Inbound buyer-message notifications |
| `DRY_RUN` | Worker `vars`, default `"1"` | Block all live writes |

Do not commit `.dev.vars`, tokens, webhook URLs, or buyer photos. If this GitHub repo is public, treat it as public even if we later make it private.

---

## 8. How to work with me

- Before each phase, ask the questions listed above and wait for my answers.
- Give me short, click-by-click instructions for anything I have to do in a browser (Etsy app, Printify token, Cloudflare secrets).
- After each phase, tell me exactly how to test, what I should see, and what must *not* have happened (no buyer mail, no Printify charge, no Etsy "shipped").
- Prefer small pull requests / commits on a branch. Keep `main` deployable.
- If a feature needs a paid Cloudflare plan or a new vendor, stop and ask me first.
- If you are unsure an endpoint exists, stop and say so. The Etsy messaging gap is real; do not work around it by scraping the seller inbox as the primary design.

When you are ready, start at Phase 0, show me the dev-Worker plan, and ask the Phase 0 questions.
