# VivaMemoirStudio: how the whole shop runs today (for designing a cheaper automation)

Written Nov 27, 2026 (PT) by Designer 2 from the real files on the shared box. Every statement comes from a file, script, tracker row or note on the box. Anything I couldn't confirm is marked **unknown / confirm with Derek**. No API keys, tokens or webhook URLs are in this file. Only the environment variable or file names are given.

Main sources: `/workspace/orders/BOT_INSTRUCTIONS.md`, `FORMATS.md`, `TRACKER_README.md`, `CLAUDE_BUILD_PROMPT.md`, `STYLE_GUIDES/*.md`, `ORDER_TRACKER.csv`, `ORDER_TRACKER_detail.csv`, `push_to_app.py`, `build_board.py`, `queue_build.py`, `/workspace/viva-orders/README.md`, `/workspace/viva-orders/GUARANTEE-2026-11-27.md`, `/workspace/gemini/gen.py`, `/workspace/orders/1000000103/art/gen_pro.py`, `/workspace/tools/SEEDREAM_README.md` + `seedream.py`, `/home/box/.config/vivamemoir/README.md`, order folders (`notes.txt`, `art/vN/NOTES.txt`, `printify/README.txt`, `mike/printify/REPORT.txt`), `two_order_profit_notes.json`, `listing_variations/proposal.md`, the Grok Bot usage report, and bot memory.

---

## 1. The business in one screen

- **Shop:** VivaMemoirStudio on Etsy. Print-on-demand custom illustrated portraits made from the buyer's own photos (families, couples, kids, pets).
- **Fulfilment:** all printing and shipping goes through **Printify**, store ID `11985418`. Printify order numbers look like `11985418.NN`. Providers seen: Jondo (US), Printify Choice (provider 99, Miami), Print Pigeons (Latvia, for EU).
- **Pricing:** free US shipping. Coupon **CHRISTMAS50** (50% off) is running.
- **Profit goal:** about 20% per order. Profit = Etsy "You earned" net minus Printify cost (production + shipping).
  - Real example (`two_order_profit_notes.json`): $149.50 list, minus 50% = $74.75. Etsy fees: transaction $4.86, processing $2.64, renewal $0.20. Net $67.05, Printify about $50.78, profit about $16.27.
- **Volume:** about 28 rows in the tracker now, a handful of new orders per day in the holiday season.
- **Owner approval:** Derek approves every mockup and every Printify order. Today he does this by tapping in the **Viva Orders** app.

### Product lines and listing IDs

| Line | Etsy listing ID | Style guide | Status of guide |
|---|---|---|---|
| Charlie Brown / Peanuts style (biggest seller) | `4596967115` | `STYLE_GUIDES/charlie_brown.md` | 4 buyer-approved refs |
| Nightmare Before Christmas / stop-motion gothic | `4595497386` | `STYLE_GUIDES/nightmare.md` | 3 approved refs |
| Buddy the Elf (realistic costume photo) | `4597002678` | `STYLE_GUIDES/elf.md` | listing art only, no buyer order yet |
| Pet Christmas portraits (rustic painted) | **unknown / confirm with Derek** (guide says "Pet Christmas listings (dog, cat, fireplace, Santa suit)") | `STYLE_GUIDES/pet_christmas.md` | listing art only |
| Removed Nov 22 (Simpsons, Family Guy, anime goth, goth fairytale) | n/a | `STYLE_GUIDES/_removed/` | Orders in these lines have no guide; ask Manager first |

Also sold by request: merch/apparel follow-ups (for example a tumbler and sweatshirt mockups, embroidery tested at Printify and Printful). Printify embroidery has only 15 thread colors and no light skin tone, so Derek tried Printful for that (memory, Nov 19).

### Product formats and sizes (from tracker + style guide)

- 5x7 matte print. Printify blueprint **1220** "Rolled Posters", Jondo, matte, print area 1500x2100. Production about $4.46.
- Matte posters 8x10 to 18x24. Blueprint **282** (US only). For an EU buyer, blueprint **494** Giclée Art Print via Print Pigeons was used instead.
- Framed poster (for example black 8x10). Blueprint **unknown / confirm with Derek**.
- Stretched canvas 8x10 up to 24x36, 1.25" gallery wrap. Blueprint **1159** "Matte Canvas, Stretched, 1.25"", Jondo or Printify Choice.
  - Example costs: 11x14 Choice canvas production $16.01, standard shipping $12.89 including a $0.40 holiday surcharge.
- **SKU linking (important):** canvas variants are SKU-linked, so an Etsy order can **auto-import into Printify with the listing's sample art**. Those auto-imported orders must be canceled and replaced with a manual order using the buyer's art (seen on orders `.13` and `.14`).
  - The 5x7, matte poster and framed options are **not SKU-linked**, so they are always ordered by hand ("manual order").

---

## 2. The bots and who does what

All bots run on **Grok Bot**. They share one Linux machine (the "box"), where everything lives under `/workspace/orders/`. Each bot also has its own chat thread with Derek.

| Bot | Job | Never does |
|---|---|---|
| **Messanger** | The only bot that talks to buyers. It reads and answers Etsy messages "as Derek", takes in orders (saves photos and personalization to the order folder and starts the tracker row), and hands art jobs to Designer. It sends Derek-approved proofs to buyers and builds the Printify product and mockup. After Derek approves, it places and pays the Printify order. It adds tracking to Etsy and the tracker, sends thank-you notes, runs a daily 9 AM check, and escalates stuck art jobs to a backup artist. | Makes art |
| **Designer** | Main artist, and the only one by default. Makes mockups, compare sheets, revisions and 300 dpi print/wrap files. | Messages buyers, places orders, spends beyond image generation |
| **Designer 2, 3, 4** | Backup artists. A backup takes an order only when Messanger or Manager hands it over because Designer has **3+ jobs waiting**. It then owns that order to the end, and revisions always go back to whoever made the original. (The Claude build prompt also says "or quiet about 2+ hours"; BOT_INSTRUCTIONS says only 3+ jobs. **Confirm with Derek.**) | Same as Designer |
| **Manager** | Listings, marketing (Etsy ads, Pinterest), analytics, the style guides (it is the **only editor** of `STYLE_GUIDES/*.md`), the legacy order-board Page, and the Viva Orders app code. It no longer routes Derek's decisions. It can run `push_to_app.py audit` to find stuck work. | Messages buyers, places orders |

### How bots hand off

- **Priority (waking) bot-to-bot messages** (Grok Bot `SendToAgent` with priority) are allowed ONLY for a real handoff that needs action now. Examples: Messanger → Designer "new order", Designer → Messanger "final file ready", Messanger → backup artist "take this job". This is the Nov 23 usage rule.
- Everything else goes into `ORDER_TRACKER.csv` plus a push to the app, or a non-priority message.
- **Derek → bots:** a tap in the Viva Orders app. The app POSTs to that bot's **"Derek's decisions"** webhook routine:
  - **Approve** goes to Messanger.
  - **Adjust on an art proof** goes to the artist who made it (`artist_bot`).
  - **Adjust on a Printify mockup** goes to Messanger.
- Derek also often answers in a bot's chat instead of the app. The bots handle that too, and then mark the app card `"withdrawn": true`. The guarantee audit found that **no app tap was recorded after Nov 26 4:26 PM PT**. Later decisions went through chat, which the app cannot track.

---

## 3. Order lifecycle, step by step

### Step 0: Pre-order conversations (optional)
- Buyers often message before buying, for example sending photos in batches or asking about braids and locs.
- Messanger replies, saves photos to a folder (`sb_mcfarran/`, `apple_user_preorder/`) and logs everything in `notes.txt`. **No artist handoff until the order is actually placed.**
- A quote with no order yet uses tracker `order = none-yet`. `app.json` `hide_from_app` can hide it from the app.

### Step 1: The Etsy order arrives
- **How Messanger learns about it:**
  - Buyer messages: Etsy sends a "Conversation with ..." email to the shop Gmail. A Gmail filter forwards it to Messanger's alert inbox (a Grok Bot mail address), and that wakes Messanger.
  - **New-sale emails did NOT wake it** as of Nov 22 (CLAUDE_BUILD_PROMPT). Whether that changed is **unknown / confirm with Derek**.
  - The daily 9 AM PT check also catches orders.
  - Earlier (Nov 7) there were "midnight" read-only Etsy and Printify checks (`/workspace/etsy-midnight-check.txt`, `printify-midnight-check.txt`). Whether they still run is **unknown / confirm with Derek**.
- **How Etsy is read:** through a signed-in browser (Messanger's box browser, with the shop Gmail signed in). There is **no Etsy API token** on the box, and etsy.com blocks curl with a 403 or captcha (`listing_variations/proposal.md`).
- **What gets recorded** in `<order>/notes.txt`: order #, transaction #, order date, ship-by, listing title, variation/size, SKU, qty, price/coupon/total, exact personalization text, buyer note, photo-upload file names, Etsy thread URL.
  - Example: `1000000107/notes.txt`.
  - Addresses must never go in the tracker or app. Some older `report.txt` files do contain one, which is a privacy risk to clean up.

### Step 2: Buyer photos collected
- Photos come from the order's "Photo upload" field and/or Etsy messages. They are saved in `<order>/photos/` (older folders used `buyer_msgs/` or `incoming/`).
- **Rule:** `photos/` holds ONLY the buyer's real photos, because `push_to_app.py` shows everything in `photos/` and `buyer_msgs/` to Derek as "their photos". Style references (web images, the buyer's own mockup) go in `style_refs/`.
- Messanger keeps the buyer thread in `app.json` `messages` (or `buyer_msgs/messages.json` / `messages.txt` / screenshots) so Derek can read it on the approve screen. The last 30 messages are pushed, with emails and phones blanked.

### Step 3: Tracker row + handoff to an artist
- Messanger adds or updates the row in `ORDER_TRACKER.csv` and wakes Designer with one priority message (or a backup if Designer has 3+ jobs).
- **Start-of-work rule** (Derek, Nov 20): the moment a bot starts, its row's `next_step` begins with `WORKING NOW: <bot> <what>`. It also sets the status (`Needs mockup`) and `updated`, runs `build_board.py`, then runs `push_to_app.py`.

### Step 4: The mockup is made (artist)
This follows the `STYLE_GUIDES/README.md` workflow:
1. **Claim it** in the tracker (above).
2. **Read everything first:** the personalization word for word, every buyer photo, the whole buyer thread (including what was already sent), and the tracker row.
3. Write a **WHO'S WHO** in `art/vN/NOTES.txt`: one line per person or pet (name, which photo, hair color/length/part, glasses, facial hair, skin tone, outfit; for pets, markings and collar color). Order-note overrides beat the photo, for example "pink collar" even though it's red in the photo.
4. Copy the line's **MASTER PROMPT** into `art/vN/prompt_A.txt` and fill every `{slot}`. The MUST-HAVE and NEVER lines stay in.
5. **Attach refs in the exact order the guide lists:** style ref(s) first, then buyer photos cropped tight. A film still, if used at all, goes LAST.
6. **Generate** one recommended option plus at most one alternative.
   - Budget: about **3 paid generations per job**, counting retries.
   - Run calls **one at a time** and review between them. No A/B/C sets "just in case".
7. **Local post-processing (no AI):**
   - Peanuts eye arcs on every face (`daniel_1000000104/art/eyecurves/draw.py`)
   - hair recolor (`daniel_1000000104/art/hair_darken.py`)
   - Nightmare film finish (`kristen_1000000100/art/v10/work/finish_v10.py`, strength 0.55)
   - RealESRGAN x4 upscaling
   - lettering in post only, with a font (Peanuts font Groundnut, which has no &/+ glyph, so write "AND")
8. **PRE-SEND CHECKLIST** (per guide): the count of people and pets matches the order, likeness traits are right, there are no extra limbs, the safe area is respected, there is no text unless asked, exact print pixels at 300 dpi, mask seams are checked at 100%, everything is checked on the **downscaled preview Derek sees**, a compare sheet is made, and NOTES has the paid-call count.
9. **Make the files** (see section 5): the print file, the canvas wrap if it's a canvas, a ~1200 px preview, and a photo-vs-art compare sheet.

### Step 5: Review in the Viva Orders app (Derek, 1st approval)
1. The artist writes `app.json` → `review`: `kind: "art_proof"`, a **new** `version` (never reused), `artist_bot`, a one-line `note`, `options` (1 preview, or A/B with labels), `compare`, and optionally `previous`.
2. The tracker status is set to **`Waiting for Derek`**.
3. The artist runs `python3 /workspace/orders/push_to_app.py --by "<bot>"` and checks it printed `OK: pushed N orders` with no `WARNING` for that order.
4. The artist tells Derek in one line that it's in the app.
5. Derek opens the app (a phone web app on Cloudflare) and sees the mockup, the buyer's photos, the compare sheet and the thread. He taps **Approve** (or Approve A/B, or "Approve & send all") or **Ask for changes** (free text).

### Step 6: Derek's decision reaches the bot (webhook)
1. The app saves the decision first, then POSTs JSON to the target bot's Grok Bot routine webhook (`Authorization: Bearer <routine key>`).
   - Payload fields: `type, task, decision_id, order_id, buyer_first_name, product, kind, action (approve|adjust), option, version, adjust_text (Derek's exact words), approved_files, artist_bot, target_bot, decided_at(_pt), confirm_url, ack_url`. Full examples are in `FORMATS.md` §3.
2. The bot's "Derek's decisions" routine wakes it, and the bot then:
   1. lists all open decisions: `push_to_app.py pending --bot "<name>" --brief`
   2. acks **"started"** on every one right away: `push_to_app.py ack <id> --by <name> --note "started: ..."`
   3. **confirms** each one is real: `push_to_app.py show <id>` (a 404 means fake, so it does nothing). Only a logged-in Derek tap creates a decision.
   4. does the work, then acks with `--done`.
3. Decisions are **do-once**. Resends and reminders reuse the same `decision_id`, so a bot must never send a proof twice or place two orders.
4. **Meanings:**
   - approve + art_proof → Messanger sends the approved file(s) to the buyer.
     - With `option: "all"`, it sends every file, and the buyer must pick one before any Printify order.
   - adjust + art_proof → the artist makes the next version from `adjust_text`, then goes back to Step 5.
   - approve + printify_mockup → Messanger places and pays the order.
   - adjust + printify_mockup → Messanger fixes the product and posts `pfy2`, `pfy3`, and so on.
5. **Redelivery and reminder logic** (described in BOT_INSTRUCTIONS):
   - failed webhooks are re-sent at 2/5/15/30 min
   - delivered but not started: re-wake at 20 min, 1 h and 3 h
   - started but not done: reminders after 2 h (approve) or 4 h (adjust)
   - after that: a red "stuck" card, and the artist's job escalates to Messanger (`derek_decision_stuck`), which hands it to a backup artist
   - **However, `GUARANTEE-2026-11-27.md` says this cron sweep is "NOT DEPLOYED" yet** and waits for Derek's OK. So the live app may only send the initial webhook plus a manual Resend. **Confirm with Derek.**

### Step 7: Proof sent to the buyer (Messanger)
- Messanger uploads the approved preview JPG to the buyer's Etsy thread in the browser (preview only, never print files).
- It checks the message really posted. Etsy site errors have dropped messages before.
- It saves a thread screenshot to `buyer_msgs/`.
- It sets the status to **`Waiting on buyer`**, updates `latest_request` / `next_step`, pushes, and acks `--done`.
- If no reply comes, it sends a check-in when Derek asks.

### Step 8: Buyer revisions (2nd+ approval)
1. Messanger writes the buyer's request into `latest_request` and sets the status to `Needs mockup`. It wakes the **original artist** (one priority message).
2. The artist edits the **exact last-sent image** (never a fresh redraw):
   - local pixel edits first; otherwise crop the area, regenerate just that crop, and composite it back with a feathered mask
   - **pixel-diff: 0 px changed outside the mask**, with the numbers recorded in NOTES
3. The artist posts a new `review` version with `buyer_feedback` (one plain sentence). Derek's card shows "Buyer wants changes · 2nd approval" with before/after.
4. Back to Steps 5–7.
5. **Hard stop:** if Derek says "stop" or "don't regenerate", all generation on that order halts until he says to continue.

### Step 9: Final print files (artist)
These are made at the same time as each version, so they're ready once the buyer approves:
- an exact-pixel print file at **300 dpi**
- for canvas, a **wrap** file: the front plus **450 px of SOLID color per side, sampled from the art's edge pixels**
- per-side colors recorded in NOTES or `printify/side_colors.json` (for example top `(9,5,27)`, bottom `(59,59,79)`)

Wrap sides are **never white, never green, never mirrored, never stretched art**. The whole approved image goes on the front, nothing cut off. (Section 5 has the size table.)

### Step 10: Printify product + mockup (Messanger, 3rd approval)
1. In the Printify web dashboard (browser, no API token on the box), create a draft product in store `11985418`:
   - the right blueprint, provider and variant, with only the ordered size enabled
   - **Etsy order # in the product title** (for example `Person44 1000000108 Peanuts Christmas 5x7`)
   - upload the buyer's approved file, never the listing sample
2. Prints use "Fill to placeholder" at the exact print area. Canvas uses one of two methods:
   - the full wrap file covering the whole print area, or
   - the front file fitted to the front, with sides set to a solid hex color
3. **Reload the editor and check the art stuck.** The editor has reverted re-uploads before.
4. Check the front, side and back-fold mockups: **no white anywhere**.
5. Download the mockup to `<order>/printify/printify_mockup_front.png` and write `printify/README.txt` (product ID, URL, blueprint, provider, print area, cost).
6. Write `app.json` `review: {kind: "printify_mockup", version: "pfy1", ...}`, set the status to `Waiting for Derek`, and push.
   - In practice, several recent orders went straight from buyer approval to the manual order. **Whether the Printify-mockup approval is still required for every order: confirm with Derek.**

### Step 11: Printify order placed (Messanger)
1. On Derek's approve: status **`Approved - ordering`**.
2. Place a **manual order** at `printify.com/app/store/manual-order/...` with the Etsy ship-to address. Choose Standard or Economy shipping (both have been used; for example "Economy" on a 30-print order).
3. Printify requires a **recipient phone**. Use Derek's vault entry **"Me"**, and never write it in files. This step has blocked orders when the vault entry wasn't available, and Derek had to step in.
4. Pay (a card on the Printify account).
5. Cancel any wrong **auto-imported** Etsy→Printify order that carries sample art.
6. Then: `app.json` `printify_order_id` + `printify_est_ship` (first day of Printify's range, `YYYY-MM-DD`), optional `etsy_net` / `printify_cost` for profit, status **`In production`**, push. The app turns the order red if the estimate falls after the Etsy ship-by.

### Step 12: Thank-you, shipping, delivery (Messanger)
- **Thank-you message:** sent on Etsy when the buyer approves or after payment (for example "Thank-you sent 8:58 AM PT", "Shop thanked her 3:23 AM PT"). The shop also sends a "welcome / got your photos, I'm working on it" message after an order arrives.
  - **There is no saved template file on the box.** Messanger writes each one fresh. Exact standard wording: **unknown / confirm with Derek**.
- **Tracking:** when Printify shows tracking, Messanger adds it to the Etsy order (marks it shipped) and fills the tracker `tracking` column as `CARRIER NUMBER (note)`. It sets the status to **`Shipped`** and pushes.
  - Carriers seen: UPS, UPS Mail Innovations, USPS, DHL, LaserShip/OnTrac.
- **Delivered:** set only when the carrier or Etsy shows delivered.
- **Problem** status: anything blocked or at risk.

### Status flow (exact tracker values → app stage)

```
(new order) → Needs mockup [artist] → Waiting for Derek [needs_ok]
   ├─ Adjust → Needs mockup → Waiting for Derek ...
   └─ Approve → Waiting on buyer [waiting_buyer]
         ├─ buyer wants changes → Needs mockup → Waiting for Derek → Waiting on buyer ...
         └─ buyer approves → (Printify mockup: Waiting for Derek, kind printify_mockup)
               → Approved - ordering [ordering] → In production [printing]
               → Shipped [shipped] → Delivered [delivered]
Problem [problem] can be set at any point.
```

Counts on Nov 27: Shipped 13, In production 5, Waiting on buyer 4, Delivered 4, Waiting for Derek 2.

---

## 4. Image generation: tools, models, caps, lessons

### Tools (all run on the box; keys come from environment variables, never printed)

| Tool | Model | Command | Key (env var / file) | Used for |
|---|---|---|---|---|
| `/workspace/gemini/gen.py` | `gemini-2.5-flash-image` | `python3 gen.py out.png "prompt" <aspect> ref1 ref2 ...` | `GEMINI_API_KEY` | Peanuts base generation, cheap drafts |
| `/workspace/orders/1000000103/art/gen_pro.py` | `gemini-3-pro-image-preview` (override with env `GM`), size via `GSIZE` (default 2K; 4K used) | `GSIZE=4K python3 gen_pro.py out.png "prompt" <aspect> refs...` | `GEMINI_API_KEY` | Nightmare base, ALL targeted edits, Peanuts 4K faithful redraw, Elf orders |
| `/workspace/tools/seedream.py` | Seedream via OpenRouter Images API. flash $0.018 / pro $0.045 at ≤1.5K, $0.09 high-res / lite $0.035 / 4.5 $0.04 / 5.5 $0.02 (prices as of Nov 20, `SEEDREAM_README.md`) | `seedream.py --model pro --resolution 1.5K --aspect 3:4 --prompt ... --ref ... --out ...` | `OPENROUTER_API_KEY` | Fallback when Gemini refuses or drifts. Prints `usage.cost`. May add an "AI-generated" watermark, so check the corners |
| `/home/box/.config/vivamemoir/openai_images.py` | OpenAI `gpt-image` (README example `gpt-image-2.5-sunburst`), 1024x1536 | `openai_images.py edit --model ... --prompt-file ... --reference ... --output ... --allow-paid` | credential file `openai-api.json` in that folder (0600) | Pet Christmas painted art only. Refuses face edits. Needs `--allow-paid`, which means Derek's OK |
| RealESRGAN x4 | local | (`/workspace/sr_venv`, `sr_models`) | none | upscaling |
| rembg / isnet person masks | local | (`/workspace/rembg_venv`) | none | masks for composited edits |

Gemini per-image prices aren't recorded on the box: **unknown / confirm with Derek** (check the Google AI Studio billing page).

### Per-line recipes
- **Peanuts:**
  1. Gemini Flash base, with refs in order: TV-special frame → an approved shop order (couple ref for small groups, the 9-person family ref for 5+) → buyer photos.
  2. Optional Gemini Pro 4K faithful redraw, then re-check head size.
  3. Eye arcs drawn locally on every face, C ears, blush, huge heads (≥45% of figure height for small groups).
- **Nightmare:**
  1. ONE Gemini Pro 4K base anchored on the approved default ref. Pale ivory or warm clay skin, not blue (blue has been allowed only when Derek or the buyer asked).
  2. Optionally ONE targeted "more stop-motion" edit.
  3. Film-finish script at 0.55 (mandatory).
- **Elf:** Gemini Pro 4K (faces stay photo-real); Seedream fallback.
- **Pet Christmas:** OpenAI gpt-image edit with the listing art as style ref; Gemini Pro to upscale.

### Caps and rules
- About **3 paid generations per job**, run one at a time, reviewed between calls. One recommended option plus at most one alt. Record the paid-call count in NOTES.
- Send the 1024 px `_small/` copies of refs to the model, not full-res PNGs.
- Revisions = targeted edits with 0 px change outside the mask, not new generations.
- In practice caps are often blown on hard orders. Examples:
  - Nightmare default ref v10A took **12 rounds**
  - order 1000000109 reached **v8** with many generations, each round driven by Derek's explicit requests
  - one order's tracker backups show up to **v17**

### Moderation lessons
- Gemini returns **PROHIBITED_CONTENT** when a prompt describes skull faces literally, names exact film costumes, or **attaches a film still first**. Describe "puppet", "clay" and "inspired" outfits, and attach any film still **last** (or not at all).
- Seedream moderation blocked **every** request that included film-still reference images (order 1000000109, Nov 26). Text-only prompts went through.
- House rule: keep **film, character, director and studio names out of prompts and out of the art**. Never write "Disney" in listings or buyer-facing text. Blank out signs and text on buyer-supplied mockups before using them as refs.
- No names or text on the art by default. Lettering is added in post only when asked, with the plain version as the main file.

---

## 5. Files: folder layout, naming, sizes

### Order folder (newer orders are named by Etsy order #, older ones `<firstname>_<order#>/` or `<firstname>/`)

```
/workspace/orders/<order#>/
  app.json              order_id, artist_bot, review, messages, printify_order_id, printify_est_ship, etsy_net, printify_cost, ...
  notes.txt             order intake + running log (Messanger)
  photos/               buyer's real photos ONLY
  style_refs/           web/style refs, buyer's own mockups (NOT shown as buyer photos)
  buyer_msgs/           thread screenshots, messages.json / messages.txt
  art/v1/ v2/ ...       one folder per version
     NOTES.txt          WHO'S WHO, model, prompts, paid-call count, edit method, pixel-diff numbers, wrap side colors, honest weak spots
     prompt_A.txt ...   exact prompts
     <name>_vN_preview.jpg           ~1200 px preview (what Derek reviews / buyer receives)
     <name>_vN_compare*.jpg / _vs_photos.jpg   photo-vs-art (or old-vs-new) sheet
     contact_sheet_vN_<name>.jpg
     <name>_vN_front_<W>x<H>.png or <name>_vNA_<size>_<W>x<H>.png   print file
     <name>_vN_wrap.png / <name>_vNA_canvas_wrap_<W>x<H>.png        canvas wrap
     work/ _work/ raw/ ref/          scratch (skipped by the push)
  printify/
     printify_mockup_front.png, README.txt (product id/URL/blueprint/provider/cost), side_colors.json
```

Example names: `david_1000000109_v6_preview.jpg`, `david_1000000109_v6_front_7200x10800.png`, `morgan_v3A_canvas_wrap_6300x8100.png`, `sharon_v8c_5x7_1500x2100.png`.

### Print sizes (300 dpi, portrait unless the order says landscape) from `STYLE_GUIDES/README.md`

| Size | Print/front px | Canvas wrap file (front + 450 px solid side each edge) | Generate at |
|---|---|---|---|
| 5x7 | 1500x2100 | n/a | 3:4 → crop 5:7 (LANCZOS) |
| 8x10 | 2400x3000 | 3300x3900 | 4:5 |
| 11x14 | 3300x4200 | 4200x5100 (marked unverified) | 4:5 → crop |
| 12x16 | 3600x4800 | 4500x5700 | 3:4 |
| 16x20 | 4800x6000 | 5700x6900 | 4:5 |
| 18x24 | 5400x7200 | 6300x8100 | 3:4 + RealESRGAN |
| 24x36 | 7200x10800 | 8100x11700 | 2:3 + upscale |

- Safe area: faces, hands, paws and lettering at least 5% in from every edge.
- Frames: add about 0.25" extra margin under the frame lip.
- History: the old 375 px side (4050x4950 for 11x14) left a **white strip on the back fold**, which is why it's now 450 px. Only the 11x14 wrap has been checked in Printify; other sizes are scaled the same way, so check the side and back mockup on each.
- Pending with Derek: art wrapping around the edges vs. solid sides. **Solid sides stay** until he decides.

---

## 6. Tracker and app update rules

### `ORDER_TRACKER.csv`
- Columns, in this order: `order, buyer, what_they_got, status, latest_request, next_step, ship_by, tracking, updated`.
- `updated` = Pacific time + bot name, for example `2026-11-20 3:00 PM PT — Messanger`.
- `latest_request` is one plain sentence; write `unknown` if you can't find it, never invent.
- `next_step` starts with `WORKING NOW: <bot> <what>` while a bot is on it.
- Edit **only your own row** with a real CSV writer (Python `csv`), never rewrite the whole file. Bots make timestamped `.bak` copies before edits; there are about 45 in the folder.
- Exact statuses: `Needs mockup`, `Waiting for Derek`, `Waiting on buyer`, `Approved - ordering`, `In production`, `Shipped`, `Delivered`, `Problem`.
- No addresses, emails or phone numbers.
- `ORDER_TRACKER_detail.csv` holds older extra background (order date, listing, total, Printify ID/status, owner bot). It's not the main board.

### After every edit to the tracker or an `app.json`
1. `python3 /workspace/orders/build_board.py`. This rebuilds `ORDER_TRACKER.md` plus the legacy Grok Bot Page source (`board_canvas.tsx`, `board_assets.json`, with a 20-image slot pool).
   - Publishing that Page needs a bot to call WriteCanvas on canvas `1264c983-ad4a-4860-afdb-f889abbca6bd`. It's mostly superseded by the app and often isn't republished.
2. `python3 /workspace/orders/push_to_app.py --by "<bot>"`. This sends the **whole board** to the app.
   - Missing orders are removed from the board (their decisions are kept). An empty push is refused.
   - Images are resized to 1200 px, hashed and uploaded only if new: up to 8 photos and 8 versions per order.
   - It warns when an order is `Waiting for Derek` without a `review`, or when `art/vN` previews are newer than what Derek can see.
   - Settings: `VIVA_APP_URL`, `VIVA_BOT_TOKEN` (environment or `/workspace/orders/.viva_app`, chmod 600). Optional `VIVA_BOT_NAME`, `VIVA_ORDERS_DIR`.
3. Other subcommands: `--dry-run`, `pending [--bot X] [--brief]`, `show <id>`, `ack <id> --by X --note ... [--done]`, `audit [--hours N]` (exits 1 if anything is stuck).
4. The app shows "Team last updated X ago" and turns amber if nobody has pushed in 6 h.

### The Viva Orders app (`/workspace/viva-orders/`)
- **Hosting:** Cloudflare Workers + D1 (database) + R2 (private images), free tier. One password login for Derek, a phone home-screen web app. Bots authenticate with a bearer `BOT_TOKEN`.
- **Secrets** (Cloudflare): `APP_PASSWORD`, `SESSION_SECRET`, `BOT_TOKEN`, `BOT_WEBHOOKS` (JSON of each bot's routine webhook URL + key). The same webhook map is also kept on the box in `/workspace/orders/.viva_webhooks.json` (chmod 600) for Messanger, Designer and Designer 2/3/4.
- **Bot endpoints:**
  - `POST /api/bot/push`
  - `POST /api/bot/images/missing`
  - `PUT /api/bot/images/<sha256>.jpg`
  - `GET /api/bot/decisions?status=pending&bot=`
  - `GET /api/bot/decisions/<id>`
  - `POST /api/bot/decisions/<id>/ack`
- **Tabs:** To approve / In progress / Shipped.
- **Flags:** red if the Printify estimate is after the ship-by, or the ship-by is past without shipping; amber if waiting 2+ days, or the ship-by is within 2 days with no tracking.
- **Not built:** reading Etsy or Printify directly, Printify shipping webhooks, push notifications.

---

## 7. Routines and webhooks (what wakes bots)

| Trigger | Bot(s) | What it does | Source |
|---|---|---|---|
| Webhook routine **"Derek's decisions"** | Messanger, Designer, Designer 2, 3, 4 | Woken by an app tap / Resend / (planned) reminder. Handles every open decision as in Step 6 | BOT_INSTRUCTIONS, `.viva_webhooks.json` |
| Etsy "Conversation with ..." email → Gmail filter → Messanger's alert inbox | Messanger | Wakes instantly on buyer messages | CLAUDE_BUILD_PROMPT, memory |
| Daily **9 AM PT** check | Messanger | Light daily sweep, plus `push_to_app.py pending --bot Messanger --brief` and `push_to_app.py audit` | BOT_INSTRUCTIONS |
| Midnight Etsy / Printify read-only checks | Messanger (likely) | Seen Nov 7 output files. Still active? **unknown / confirm with Derek** | `/workspace/*midnight-check.txt` |
| Designer routines (3% of usage) | Designer | Which routine this is: **unknown / confirm with Derek** (one order's v3 was "made by the routine") | usage report |
| App cron sweep every 10 min | (app server, no bot usage) | Re-send / re-wake / escalate | GUARANTEE doc says **NOT DEPLOYED** yet |
| Bot-to-bot priority messages | all | Handoffs only | usage rules |

The exact list of routines configured in each bot's Grok Bot settings is not on the box: **confirm with Derek**.

---

## 8. Where the cost comes from

### Agent runs (the biggest cost)
- Grok Bot usage over the last 7 days (Nov 20–27):

  | Bot | Share | Split |
  |---|---|---|
  | Designer | 50% | chats 25%, **bot-to-bot 22%**, routines 3% |
  | Manager | 16% | chats 14% |
  | Designer 2 | 15% | chats 11%, bot-to-bot 4% |
  | Messanger | 12% | routines 5%, chats 4%, bot-to-bot 3% |
  | Designer 3 | 6% | |
  | Designer 4 | 1% | |

- The weekly limit was **76% used** with $0 extra credits. When it runs out, every bot stops.
- What drives agent usage:
  - long LLM agent sessions doing deterministic chores (tracker CSV edits, pushes, acks, board rebuilds)
  - reading long instruction files every wake
  - driving Etsy and Printify through a browser (slow, many steps)
  - bot-to-bot relays
  - chatting with Derek about small choices
  - many revision rounds per order

### Image generation (pay-per-call APIs)
- Gemini Flash / Pro 4K: price per image **unknown / confirm**.
- Seedream: $0.018–$0.09 per image.
- OpenAI gpt-image: price **unknown / confirm**.
- The ~3-per-job cap is often exceeded on hard orders (10–20+ generations).

### Fixed services
- Cloudflare free tier ($0 at this volume).
- Printify and Etsy fees are part of the cost of goods, not automation cost.

### Obvious places automation could cut cost (suggestions, not current practice)
1. **Make the bookkeeping plain code, not an LLM.** Status changes, tracker rows, `app.json` writes, push, ack and audit are all deterministic. A small service (or a cron job on the box) can do them with zero agent tokens.
2. **Order intake from email or API instead of an agent reading Etsy in a browser.** Parse the Etsy sale email, or use the Etsy Open API v3 (needs a registered app + OAuth; **verify** it exposes personalization text and photo uploads). That would create the folder, `notes.txt` and tracker row automatically.
   - Buyer messaging can't move to the API: per the app README, the Etsy API has no buyer-messaging feature, so a human or browser step stays there.
3. **Printify via its API** (personal access token; none exists on the box today). Create the product with the order # in the title, upload the file, enable the one variant, pull the mockup, and place the order after Derek's tap. Printify **webhooks** for shipped/tracking could move orders to Shipped with no bot run.
   - Still needs: a recipient phone, and payment on file.
4. **Fixed image pipeline:** a script that fills the guide's master prompt from a structured WHO'S WHO, attaches refs in the right order, makes exactly N calls (hard cap), then runs the local steps automatically (arcs, film finish, upscale, wrap with sampled solid sides, preview, compare sheet). An LLM or human is only needed for writing the WHO'S WHO and judging quality.
5. **Cheaper models first:** Seedream Flash ($0.018) or Gemini Flash for drafts; Pro or 4K only after Derek picks a direction (already advised in `SEEDREAM_README.md`).
6. **One artist instead of four.** Backups exist only for throughput. A queue with a worker pool does the same job without separate agent contexts.
7. **Approvals only in the app.** Chat approvals cost agent turns and can't be tracked. Deploy the reminder sweep so bots aren't asked "is it done?" in chat.
8. **Retire the legacy board Page** (`build_board.py` + WriteCanvas). The app replaces it.
9. **Templates** for welcome, proof, check-in, thank-you and shipped messages, so writing a buyer message isn't an LLM task every time.

---

## 9. Pain points seen (real incidents)

- **Phone uploads never reached the box.** Images Derek attached in chat from his phone (an Android phone) twice didn't arrive, and copying from his machine fails when the phone is offline. The workaround was web images of the same look.
- **Moderation blocks:**
  - Seedream refused every request that had film-still refs.
  - Gemini returns PROHIBITED_CONTENT on film costumes or skull faces, or when a film still is attached first.
  - So prompts must avoid film, character and studio names.
- **Style refs showed up as "buyer photos" in the app,** because the push treats everything in `photos/` as buyer photos. The fix was to move them to `style_refs/`.
- **Approvals happening in chat instead of the app** (no app tap recorded since Nov 26 4:26 PM PT). Cards then have to be withdrawn by hand, and the app can't track or remind.
- **Slow adjustments:** one adjust took 25 h from tap to new version pushed. Backups get pulled in by hand.
- **Generation overruns:** hard orders take 8–17 versions, far past the ~3-call budget. Pushing the Nightmare style further risks drifting too close to the film character.
- **Printify friction:**
  - the required recipient phone (vault "Me") blocked manual orders until Derek stepped in
  - blueprint 282 posters ship US only, so an EU order needed a different blueprint
  - the editor reverted re-uploaded art
  - the old 375 px wraps left a white strip on the back fold
  - auto-imported Etsy orders came in with listing sample art and had to be canceled
  - ship estimates sometimes fall after the Etsy ship-by (red flag, plus a heads-up to the buyer)
- **Etsy friction:** no API token; etsy.com blocks scripted access; replies sometimes fail to post (site error), so each send has to be checked.
- **Low-res buyer photos** (for example 239x356, or an 864x1152 source for an 11x14), so detail gets synthesized when upscaling.
- **Messy data:** inconsistent folder names, an older flat `art/` layout, key facts (Printify #, estimates) buried in free-text tracker cells, about 45 tracker `.bak` copies, and a hand-kept `FOLDER_MAP` in `queue_build.py`.
- **Privacy leftovers:** a few older intake `report.txt` files include a buyer's shipping address and phone, against the shop's own rule.
- **Usage pressure:** the weekly limit was 76% used with no extra credits. Designer's bot-to-bot traffic alone was 22% of all usage.

---

## 10. Hard rules any new system must keep

1. Only Derek's own action approves: a tap while logged in, or his own words. Another bot saying "approved" never counts.
2. Nothing goes to a buyer, no Printify order is placed and no money is spent without Derek's approval.
3. Revisions change only what was asked: edit the last-sent image, 0 px change outside the mask.
4. 300 dpi exact-pixel print files. Canvas sides are solid colors sampled from the art edges: never white, mirrored or stretched.
5. No film, character, director or studio names in prompts or art; no "Disney" in buyer-facing text; no text on art unless asked.
6. No buyer addresses, emails or phones in the tracker, app or notes. Never print API keys.
7. A decision is handled once (same `decision_id` = same job). Every action is acked, and every state change is pushed.
