# Formats: what the bots write, what the app sends, how bots report back

There are four pieces:

1. **`app.json`**: a small file in each order folder that the bots fill in.
2. **The push**: what `push_to_app.py` sends to the app (built from the tracker + `app.json`).
3. **The webhook**: what the app sends to a bot when Derek taps Approve or Adjust.
4. **Bot endpoints**: how a bot confirms a decision and reports progress.

---

## 1. `app.json` (one per order folder)

Path: `/workspace/orders/<order folder>/app.json`. Every field is optional except `review` when the
order is `Waiting for Derek`. File paths are relative to the order folder (absolute paths also work).

| Field | When to fill it | Example |
|---|---|---|
| `order_id` | Always. It's how the script matches the folder to the tracker row, so folder names don't matter. Use the Etsy order number. For a quote with no order yet, leave it out; the script uses the folder name. | `"1000000100"` |
| `artist_bot` | When an artist takes the order. Adjustments go back to this bot. | `"Designer 2"` |
| `review` | **Whenever status is `Waiting for Derek`.** What Derek is approving. See below. | |
| `printify_order_id` | When Messanger places the Printify order. | `"11985418.23"` |
| `printify_est_ship` | Printify's estimated ship date, `YYYY-MM-DD`. Use the *first* day if Printify gives a range. | `"2026-11-27"` |
| `tracking_carrier` / `tracking_number` | When shipped (or keep using the tracker's `tracking` column; either works). | `"UPS"`, `"REDACTED"` |
| `etsy_net` / `printify_cost` | Optional, numbers in dollars. If both are there, the app shows profit against the 20% goal. | `67.05`, `50.78` |
| `versions` | Optional. Leave it out and the script lists `art/v1`, `art/v2`, … previews automatically. | |
| `hide_from_app` | Optional. If `true`, the push leaves the *quote* row for this folder (tracker order `none-yet`) off the Viva Orders app; a real Etsy order that shares the folder stays. A list of ids hides only those ids. The worker drops omitted orders from the board. Clear the flag and push to show the quote again. The tracker row stays. | `true` |
| `messages` | Optional. The Etsy thread with this buyer, so Derek can read it on the approve screen. Newest last. The push also picks up `buyer_msgs/messages.json`, `buyer_msgs/messages.txt`, and thread screenshots in `buyer_msgs/` or `messages/`. Cap is the last 30. | `[{"from":"buyer","at":"2026-11-21 5:47 PM PT","text":"Can you make the hair longer?"}]` |

### `review`

| Field | Meaning |
|---|---|
| `kind` | `"art_proof"` (Approve = send to buyer) or `"printify_mockup"` (Approve = place the Printify order). |
| `version` | `"v12"`. **Must change every time a new mockup is posted** (v12 → v13). The app allows one decision per version, which is what stops double-sends. For a redone Printify mockup, use `"pfy2"`, `"pfy3"`, and so on. |
| `artist_bot` | Who made it. |
| `note` | Optional, one or two lines for Derek (what changed, weak spots). |
| `options` | The exact preview file(s) Derek reviews. One entry = a single mockup. Two = an A/B choice. Each is `{ "label": "A", "file": "art/v12/..._preview.jpg" }`. |
| `compare` | Optional photo-vs-art sheet. |
| `photos` | Optional. Leave it out to show everything in `photos/` or `buyer_msgs/`. |
| `buyer_feedback` | **Round 2 and later:** the buyer's change request, in one plain sentence ("Make mom's hair longer"). It's shown in big type at the top of Derek's card. |
| `round` | Optional. The app counts rounds by itself from Derek's earlier approvals. Set this (2, 3, …) only if the earlier approval happened outside the app. |
| `previous` | Optional. The proof file the buyer saw last time. The app usually finds it by itself; set it if the earlier approval happened outside the app. Derek gets "Sent before" and "Before + after" buttons. |

### When the buyer asks for changes (2nd approval)

Use the same order folder and `app.json`. The artist makes the next version, then writes:

```json
"review": {
  "kind": "art_proof",
  "version": "v4",
  "artist_bot": "Designer",
  "buyer_feedback": "Can you make mom's hair longer, past her shoulders?",
  "note": "Hair now past the shoulders, everything else the same as v3.",
  "options": [ { "file": "art/v4/maureen_v4_preview.jpg" } ]
}
```

Derek's card then says **"Buyer wants changes · 2nd approval"**, shows the buyer's request, and lets him
flip between the new mockup, the version sent before, a before/after view, and the buyer's photos.

Full example: `box/app.json.example`. Printify example:

```json
{
  "order_id": "1000000101",
  "artist_bot": "Designer",
  "review": {
    "kind": "printify_mockup",
    "version": "pfy1",
    "note": "8x10 canvas, black edge wrap, Jondo",
    "options": [ { "file": "printify/printify_mockup_front.png" } ]
  },
  "etsy_net": 67.05,
  "printify_cost": 50.78
}
```

After Derek decides and the status moves on, the bot can leave `review` in the file. The app shows it while the tracker status is `Waiting for Derek`, **and also while the status is `Needs mockup` if Derek hasn't tapped that version yet** (so starting the next version can never hide a proof he hasn't seen). If Derek already answered that version in chat, add `"withdrawn": true` to `review` (or replace it with the new version) and push.

### `messages` (buyer / shop thread)

Messanger keeps this current whenever the Etsy conversation changes, then runs the push. Preferred form in `app.json`:

```json
"messages": [
  { "from": "buyer", "at": "2026-11-21 5:47 PM PT", "text": "Hi, Derek! Can you make mom's hair longer?" },
  { "from": "shop",  "at": "2026-11-21 6:10 PM PT", "text": "On it — I'll send a new proof shortly." }
]
```

- `from` is `"buyer"` or `"shop"`. List messages oldest first, newest last.
- `at` is a short date/time (Pacific Time is best). `text` is the message body.
- Optional `file` is a screenshot or attachment, relative to the order folder.
- You can also write the same JSON to `buyer_msgs/messages.json`, or a plain transcript at `buyer_msgs/messages.txt` with lines like `[2026-11-21 5:47 PM PT] Buyer:` before each message. Save thread screenshots in `buyer_msgs/` (names like `thread_nov22.png` or `IMG_1234.jpg`).
- Never include addresses, emails or phone numbers. The script blanks any it finds, and only sends the last 30 messages.

---

## 2. The push (`POST /api/bot/push`)

`push_to_app.py` builds this for you. It's documented here in case you ever want to send it another way.

Optional top-level fields (added 2026-11-23, older pushes without them still work):
`"pushed_by": "Messanger"` (shown to Derek as who last updated the board; `push_to_app.py --by <name>`),
`"warnings": [...]` (the script's WARNING lines, kept with the last-push record).
An empty `"orders": []` is refused (it would erase the board) unless you also send `"allow_empty": true`.

```json
{
  "orders": [
    {
      "order_id": "1000000100",
      "buyer_first_name": "Person01",
      "product": "Nightmare 5x7 matte print",
      "status": "Waiting for Derek",
      "stage": "needs_ok",
      "latest_request": "Derek: v11B is best; add Nightmare-style stitches to the dog",
      "next_step": "v12 stitched-dog options sent to Derek",
      "ship_by": "2026-11-27",
      "printify_order_id": null,
      "printify_est_ship": null,
      "tracking_carrier": null,
      "tracking_number": null,
      "tracking_note": null,
      "artist_bot": "Designer",
      "updated_at": "2026-11-22 4:02 AM PT",
      "updated_by": "Designer",
      "etsy_net": 67.05,
      "printify_cost": 50.78,
      "photos": ["<sha256>.jpg", "<sha256>.jpg"],
      "messages": [
        { "from": "buyer", "at": "2026-11-21 5:47 PM PT", "text": "Can you add stitches to the dog?" }
      ],
      "review": {
        "kind": "art_proof",
        "version": "v12",
        "artist_bot": "Designer",
        "note": "Added stitches to the dog on both.",
        "options": [
          { "label": "A", "image": "<sha256>.jpg", "source_path": "/workspace/orders/kristin_1000000100/art/v12/kristin_v12A_preview.jpg" },
          { "label": "B", "image": "<sha256>.jpg", "source_path": "/workspace/orders/kristin_1000000100/art/v12/kristin_v12B_preview.jpg" }
        ],
        "photos": ["<sha256>.jpg"],
        "compare": "<sha256>.jpg"
      },
      "versions": [
        { "version": "v11", "made_by": null, "note": null, "images": [ { "label": "A", "image": "<sha256>.jpg" } ] }
      ]
    }
  ]
}
```

- `stage` is one of `problem, needs_ok, artist, waiting_buyer, ordering, printing, shipped, delivered` (from the tracker status).
- Images are uploaded first (`PUT /api/bot/images/<sha256>.jpg`) and named by a hash of their content, so names can't be guessed and the same image is never uploaded twice. The app serves them only to a logged-in browser.
- Each push is the **whole board**. An order missing from the push is removed from the board. Its decisions are kept.
- The app tracks "days in this stage" itself, from the moment a push first shows the new stage.
- No addresses, emails or phone numbers are ever sent. The script also blanks any emails or phone numbers it finds in the text.

---

## 3. The webhook (app → bot)

When Derek taps, the app saves the decision, then POSTs this JSON to the target bot's Grok Bot routine
webhook with `Authorization: Bearer <routine key>`.

- **Approve** (art proof or Printify mockup) → **Messanger**
- **Adjust** on an art proof → **the artist who made it** (`artist_bot`)
- **Adjust** on a Printify mockup → **Messanger** (Messanger made it)

### Approve example

```json
{
  "type": "derek_decision",
  "task": "Derek approved option B of v12 for order 1000000100 (Person01). Confirm this decision first (GET confirm_url with your bot token), then send the approved proof file to the buyer on Etsy. Then POST to ack_url with done=true.",
  "decision_id": "13789b18-1dba-4895-8e8c-63c084bbcf2e",
  "order_id": "1000000100",
  "buyer_first_name": "Person01",
  "product": "Nightmare 5x7 matte print",
  "kind": "art_proof",
  "action": "approve",
  "option": "B",
  "version": "v12",
  "adjust_text": null,
  "approved_files": ["/workspace/orders/kristin_1000000100/art/v12/kristin_v12B_preview.jpg"],
  "artist_bot": "Designer",
  "target_bot": "Messanger",
  "decided_by": "Derek",
  "decided_at": "2026-11-22T22:05:00.000Z",
  "decided_at_pt": "2026-11-22 2:05 PM PT",
  "confirm_url": "https://viva-orders.YOU.workers.dev/api/bot/decisions/13789b18-1dba-4895-8e8c-63c084bbcf2e",
  "ack_url": "https://viva-orders.YOU.workers.dev/api/bot/decisions/13789b18-1dba-4895-8e8c-63c084bbcf2e/ack"
}
```

### Adjust example

```json
{
  "type": "derek_decision",
  "task": "Derek wants changes to v12 for order 1000000100 (Person01). Confirm this decision first (GET confirm_url with your bot token). Pass his exact words to Designer: \"Make the dog's stitches smaller and keep option B's face\". The artist makes the next version and pushes it to the app. POST to ack_url when work starts, and with done=true when the new version is pushed.",
  "decision_id": "6f1c2a8e-0b7d-4c55-9a1e-2f3b4c5d6e7f",
  "order_id": "1000000100",
  "buyer_first_name": "Person01",
  "product": "Nightmare 5x7 matte print",
  "kind": "art_proof",
  "action": "adjust",
  "option": null,
  "version": "v12",
  "adjust_text": "Make the dog's stitches smaller and keep option B's face",
  "approved_files": [],
  "artist_bot": "Designer",
  "target_bot": "Designer",
  "decided_by": "Derek",
  "decided_at": "2026-11-22T22:07:00.000Z",
  "decided_at_pt": "2026-11-22 2:07 PM PT",
  "confirm_url": "https://viva-orders.YOU.workers.dev/api/bot/decisions/6f1c2a8e-0b7d-4c55-9a1e-2f3b4c5d6e7f",
  "ack_url": "https://viva-orders.YOU.workers.dev/api/bot/decisions/6f1c2a8e-0b7d-4c55-9a1e-2f3b4c5d6e7f/ack"
}
```

`adjust_text` is always Derek's exact words. If the webhook fails, the card shows **"didn't reach … Retry"**
and the decision stays saved. Bots that check `pending` still see it.

**Why bots must confirm:** anyone who has a webhook URL and key could wake a bot with made-up JSON.
The decision is real only if `GET confirm_url` (with the bot token) returns it. The app creates a
decision only when Derek taps while logged in.

---

## 4. Bot endpoints

All use `Authorization: Bearer <BOT_TOKEN>`. `push_to_app.py` has shortcuts for each.

| What | Request | Shortcut |
|---|---|---|
| Push the board | `POST /api/bot/push` | `python3 push_to_app.py` |
| Which images are new | `POST /api/bot/images/missing` `{"keys": [...]}` | (automatic) |
| Upload an image | `PUT /api/bot/images/<sha256>.jpg` (raw bytes) | (automatic) |
| List open decisions | `GET /api/bot/decisions?status=pending&bot=Messanger` | `python3 push_to_app.py pending --bot Messanger` |
| Confirm one decision | `GET /api/bot/decisions/<id>` (404 = fake, don't act) | `python3 push_to_app.py show <id>` |
| Report progress | `POST /api/bot/decisions/<id>/ack` `{"by":"Messanger","note":"sent to buyer","done":true}` | `python3 push_to_app.py ack <id> --by Messanger --note "sent to buyer" --done` |

Derek can tap **Resend** on a decision that failed to deliver, or on one that was delivered but has no
ack after 30 minutes. Either way the bot gets the **same decision_id** again, so treat decisions as
"do once": if you already started or finished it, just ack where things stand.

`done: false` = a progress note ("artist started v13"). `done: true` = finished. Derek's card shows the
latest note either way, and turns to "Done" when `done` is true.
