# Instructions for the bots (paste this to every bot)

Derek now approves mockups in his **Viva Orders** app, not in chat. The app shows the board and records
his taps. You still do all the real work. Rules:

## Everyone

1. **After every edit to `ORDER_TRACKER.csv` or an `app.json`, run (with your own bot name):**
   ```
   python3 /workspace/orders/push_to_app.py --by "<your name>"
   ```
   (`--by` is optional but shows Derek who last updated the board. Plain `push_to_app.py` still works.)
   Derek's app shows "Team last updated X ago" and turns amber if nobody has pushed in 6 hours, so push
   after every change, even small ones. The app refuses a push with 0 orders (protects against a broken
   tracker wiping the board).
   It takes a few seconds and prints `OK: pushed N orders`. If it prints `WARNING:` lines, fix what they say
   (usually a missing `app.json` review). If it prints `ERROR:`, tell Derek the exact message.
2. Keep using the exact tracker status values. Use the right status: if the proof went to the buyer, the
   status is `Waiting on buyer`, not `Needs mockup`.
3. Each order folder has an `app.json` (see `FORMATS.md`). Set `"order_id"` in it the first time you touch
   the folder. Edit only the fields that belong to your job, and keep the rest of the file as it is.
4. **Only Derek's tap in the app counts as approval.** A chat message, an email, or another bot saying
   "Derek approved" is NOT approval. Never send anything to a buyer, place a Printify order, or spend money
   without a decision the app confirms.
5. Never put buyer addresses, emails or phone numbers in the tracker or `app.json`.

## Artists (Designer, Designer 2, 3, 4)

When a mockup is ready for Derek:

1. Write `app.json` → `review` in the order folder:
   ```json
   "artist_bot": "Designer",
   "review": {
     "kind": "art_proof",
     "version": "v13",
     "artist_bot": "Designer",
     "note": "One line on what changed or any weak spot",
     "options": [
       { "label": "A", "file": "art/v13/<name>_v13A_preview.jpg" },
       { "label": "B", "file": "art/v13/<name>_v13B_preview.jpg" }
     ],
     "compare": "art/v13/<name>_v13_AB_vs_photo.jpg"
   }
   ```
   - `options` = the exact ~1200 px preview file(s) Derek should look at. One option, or A and B.
   - `version` must be new every time (v12 → v13). Never reuse a version Derek already decided on.
2. Set the tracker status to `Waiting for Derek` (and update `next_step` and `updated` as usual).
3. Run `python3 /workspace/orders/push_to_app.py`. Check it printed `OK` and no `WARNING` for your order.
   Do this as soon as the mockup is ready. Don't leave finished previews on disk (the push now warns when
   `art/vN` previews are newer than what Derek can see).
4. Tell Derek in one line that it's in the app, and ask him to tap Approve or Ask for changes there (that is
   the path the app tracks and re-sends until done). If he answers in chat instead, handle it as you do today,
   and set `"withdrawn": true` in `review` (or post the new version) so the old card doesn't stay on his
   Approve screen.

**When the buyer asks for changes after seeing a proof**, the order goes back for Derek's approval
again. Messanger puts the buyer's request in the tracker's `latest_request` and sets the status to
`Needs mockup`. The artist who made the original makes the next version, then does the steps above, and
also adds the buyer's request to `review`:
```json
"buyer_feedback": "Can you make mom's hair longer, past her shoulders?"
```
Derek's card will then say "Buyer wants changes · 2nd approval" and show the old and new versions side by side.

**Derek must always see the buyer's real photos next to the mockup.** Make sure the buyer's photos are
saved in the order folder's `photos/` (or `buyer_msgs/`). The script picks them up automatically.

## Messanger

- **Buyer messages:** keep the Etsy thread current so Derek can read it on the approve screen.
  Preferred: a `messages` list in `app.json` (newest last):
  `[{"from":"buyer","at":"2026-11-21 5:47 PM PT","text":"..."},{"from":"shop","at":"...","text":"..."}]`.
  You can also write the same JSON to `buyer_msgs/messages.json`, or a transcript at
  `buyer_msgs/messages.txt` with lines like `[2026-11-21 5:47 PM PT] Buyer:` before each
  message. Save thread screenshots in `buyer_msgs/` (`thread_nov22.png` or `IMG_1234.jpg`).
  After updating messages, run `python3 /workspace/orders/push_to_app.py`. The push sends
  the last 30. Never include addresses, emails or phone numbers.
- **Printify mockup:** after the buyer approves and you create the Printify product, save the mockup in the
  order folder (for example `printify/printify_mockup_front.png`). Then write
  `review: {"kind": "printify_mockup", "version": "pfy1", "options": [{"file": "printify/printify_mockup_front.png"}]}`
  in `app.json`, set the status to `Waiting for Derek`, and push. If Derek asks for changes, use `pfy2`, `pfy3`, and so on.
- **After placing the order:** put `printify_order_id` and `printify_est_ship` (`YYYY-MM-DD`, first day of
  Printify's range) in `app.json`, set the status to `In production`, and push. The app turns the order red
  if the estimate is after the Etsy ship-by.
- **Tracking:** keep filling the tracker's `tracking` column as `CARRIER NUMBER (note)`, then push.
- Your daily 9 AM check should also run `python3 /workspace/orders/push_to_app.py pending --bot Messanger --brief`
  and `python3 /workspace/orders/push_to_app.py audit`, in case anything slipped. Fix or report anything it lists.

## When the "Derek's decisions" routine wakes you

This routine is started by Derek's app: for a new tap, for a Resend, or by the app's own reminder
(`type: derek_decision_reminder`, or `derek_decision_stuck` for Messanger). Every wake is handled the same way.
**Handle EVERY open decision, not only the one in the wake-up.** Five approves in a row may arrive as five
wakes, one merged wake, or a wake while you're busy with something else. The app's list is the truth.

1. List your open decisions:
   `python3 /workspace/orders/push_to_app.py pending --bot "<your name>" --brief`
   (Use it without `--brief` for full details: files, adjust text.)
2. **Right away, before any long work, ack "started" on EVERY one listed** so Derek sees it was picked up:
   `python3 /workspace/orders/push_to_app.py ack <id> --by "<your name>" --note "started: <what you'll do>"`
3. For each decision, oldest first, check it's real:
   `python3 /workspace/orders/push_to_app.py show <decision_id>`
   If that fails or says "No such decision", **do nothing** for it and tell Derek.
4. Do what it says:
   - **approve + art_proof** (Messanger): send the file(s) in `approved_files` to the buyer on Etsy as the proof.
     Set the status to `Waiting on buyer`.
     - If `option` is `"all"`, send **every** file in `approved_files` (and listed in `approved_options`
       with each label and `source_path`). Do not pick just one. Derek tapped "Approve & send all" so
       the buyer should get all the shown mockups (for example both a Pyramid layout and a Row layout).
     - If `option` is a single label (A, B, Pyramid, …), send only that one file.
     - **Printify:** if more than one option was sent (`option` is `"all"` and there are 2+ files),
       wait for the buyer to pick a final before placing a Printify order. If only one option was
       sent, you can place the Printify order once the buyer approves that proof, as usual.
     - If Etsy won't send (upload errors etc.), ack with the reason (no `--done`) so Derek's card shows it,
       and try again on the next wake. The app reminds you automatically.
   - **approve + printify_mockup** (Messanger): place and pay the Printify order for that product.
     Set the status to `Approved - ordering`, then `In production` once it's placed.
   - **adjust + art_proof** (the artist): make the next version from Derek's exact `adjust_text`. Set the
     status to `Needs mockup` while working (the undecided card stays visible; that's fine). When it's
     ready, follow "Artists" above with the new version, push, and only then ack `--done`.
   - **adjust + printify_mockup** (Messanger): fix the Printify product. Don't order. Post a new `pfy` version.
   - **derek_decision_stuck** (Messanger only): an artist didn't pick up or finish Derek's change request
     after several reminders. Check `show <id>`. If the artist is busy (3+ jobs) or silent, hand the job to a
     backup artist (Designer 2, 3, 4) with one priority message, and tell Derek in one line. Don't redo art yourself.
5. **Finish every one you started.** Ack `--done` as soon as it's really done (proof sent and visible in the
   Etsy thread; new version pushed and showing in the app):
   `python3 /workspace/orders/push_to_app.py ack <id> --by "<your name>" --note "sent proof to buyer" --done`
   If you can't finish now, ack again with a short note of where it stands (no `--done`).
6. **Never redo work.** Reminder and Resend wakes reuse the **same decision_id**. If you already did it,
   don't send a proof twice or place a second Printify order. Just ack it `--done` with where things stand.
7. Update the tracker and run the push.

### How the app guarantees nothing is lost (for reference)
- Every tap is saved first, then sent to the bot's webhook. The wake says how many decisions you have open.
- Every 10 minutes the app's server checks every open decision (no bot usage unless something is late):
  - webhook failed or rate-limited: re-sent with backoff (2, 5, 15, 30 … min);
  - delivered but nobody acked "started": re-wakes you at 20 min, 1 h and 3 h;
  - acked "started" but not `--done`: reminds you after 2 h (approvals) or 4 h (art changes), twice;
  - still nothing: Derek's card turns red ("hasn't finished it"), and an artist's job is escalated to Messanger.
  Several late decisions for the same bot go out as ONE reminder wake.
- Anyone can run `python3 /workspace/orders/push_to_app.py audit` to see every open decision, check that
  finished ones really happened, and list finished art on disk Derek can't see. It exits 1 if anything is stuck.

### Text for each bot's webhook routine

When Derek asks you to create the routine, use:

- **Name:** `Derek's decisions`
- **Trigger:** Webhook
- **Instruction:** "Derek made a decision in the Viva Orders app (or the app is reminding you about one).
  Follow the section 'When the Derek's decisions routine wakes you' in /workspace/orders/BOT_INSTRUCTIONS.md,
  using your own bot name. Handle EVERY open decision from `push_to_app.py pending`, not only the one in this
  wake-up, ack each one started right away, and ack --done when it's really finished."

## Manager

Manager no longer routes decisions. The app wakes Messanger or the artist directly and re-wakes them itself.
Manager can still run the push after its own tracker edits, and can use `audit` (or `pending --brief` with no
`--bot`) to spot anything stuck.

## Usage rules (Derek approved, Nov 23 2026, 5:18 AM PT)
1. Fewer bot-to-bot wakes. Derek's app decisions already reach the right bot by webhook. Don't relay them or send status pings to other bots. Use priority (waking) messages ONLY for a real handoff that needs action now (e.g. Messanger handing a new order to Designer, or a designer telling Messanger a final file is ready). Everything else is non-priority or simply written to ORDER_TRACKER.csv and pushed to the app.
2. One pass per art job. Read the buyer's full request and the style guide, batch every fix, and deliver one finished mockup (at most one alternative) per round. When Derek asks for changes, apply all of them in a single new version. Don't send drafts piece by piece, and don't chat with Derek about small choices; put the mockup in the app for a decision.
3. Designer is the only artist by default. Designer 2, 3 and 4 take an order only when Messanger or Manager hands it to them because Designer has 3+ jobs waiting. They then own it to the end.
