# Viva Orders: setup guide

Your phone app for approving mockups and seeing every order at a glance.

## How it works

```
   THE BOX (your bots)                       CLOUDFLARE (free)                    YOUR iPHONE
 ┌──────────────────────┐   push after    ┌─────────────────────────┐   open    ┌──────────────┐
 │ ORDER_TRACKER.csv    │   every edit    │  Viva Orders app        │◀──────────│ Needs my OK  │
 │ <order>/app.json     │ ──────────────▶ │  • database (D1)        │           │ All orders   │
 │ photos, mockups      │ push_to_app.py  │  • private images (R2)  │──────────▶│ Approve /    │
 └──────────────────────┘                 │  • your password login  │   tap     │ Adjust       │
          ▲                               └───────────┬─────────────┘           └──────────────┘
          │  bot confirms + reports back              │ wakes the right bot
          └───────────────────────────────────────────┘ (Grok Bot webhook)
                     Approve → Messanger      Adjust → the artist who made it
```

- **The bots push** the board to the app after every tracker change. Nobody polls, so it doesn't use extra bot runs.
- **You tap** Approve or Adjust. The app saves it, then wakes **Messanger** (approvals) or **the original
  artist** (changes) through their Grok Bot webhook. If that fails, the card says so and has a Retry button.
- **The bot checks** the decision with the app before acting, so only your real tap counts. Then it reports
  back ("sent to buyer ✓").
- The app **never** messages buyers or touches Printify. Buyer addresses, emails and phones never go in it.
  Images are private and need your login to view.

Everything runs on Cloudflare's free plan. At your volume you'll use well under 1% of the free limits.

---

## Setup (about 45 minutes, one time)

You need: a computer (Mac or Windows) for setup only, plus your iPhone. Copy and paste the commands exactly.

### 1. Create a free Cloudflare account
Go to **https://dash.cloudflare.com/sign-up** and sign up with your email. Verify the email.

### 2. Turn on R2 (image storage)
In the Cloudflare dashboard, click **Storage & databases → R2** in the left menu, then click **Get started** /
**Purchase R2** (it's the free plan). Cloudflare may ask for a card to turn on R2. The free tier is 10 GB,
and your mockups will use a tiny fraction of that.

### 3. Install Node.js on your computer
Go to **https://nodejs.org**, download the **LTS** version, and install it (click Next until done).

### 4. Open a terminal in this folder
Unzip `viva-orders.zip`.
- **Mac:** open the **Terminal** app, type `cd ` (with a space), drag the `viva-orders` folder onto the window, press Enter.
- **Windows:** open the `viva-orders` folder, click the address bar, type `cmd`, press Enter.

Then run:
```
npm install
npx wrangler login
```
A browser window opens. Click **Allow**.

### 5. Create the database and image storage
```
npx wrangler d1 create viva-orders
```
It prints a block with `"database_id": "…"`. Open `wrangler.jsonc` in any text editor (TextEdit or Notepad),
replace `PASTE-YOUR-DATABASE-ID-HERE` with that id (keep the quotes), and save.

```
npx wrangler r2 bucket create viva-orders-images
npm run setup-db
```
(When `setup-db` asks to continue, type `y`.)

### 6. Put the app online
```
npx wrangler deploy
```
The first time, it may ask you to pick a **workers.dev subdomain**. Pick anything, for example `vivamemoir`.
At the end it prints your app's address, like **`https://viva-orders.vivamemoir.workers.dev`**. Save it.

### 7. Set your secrets
Make two long random codes. Run this twice and copy each result:
```
node -e "console.log(crypto.randomUUID()+crypto.randomUUID())"
```
Then run each line below. Each one asks you to paste a value:
```
npx wrangler secret put APP_PASSWORD
npx wrangler secret put SESSION_SECRET
npx wrangler secret put BOT_TOKEN
```
- `APP_PASSWORD`: the password **you** will type on your phone. Make it long (at least 12 characters).
- `SESSION_SECRET`: paste random code #1.
- `BOT_TOKEN`: paste random code #2. The bots need this one too (step 9), so keep it.

### 8. Connect the bots' webhooks
In Grok Bot, send this to **Messanger, Designer, Designer 2, Designer 3 and Designer 4** (one at a time):
> Create a routine named "Derek's decisions" with a **Webhook** trigger. Instruction: "Derek made a decision
> in the Viva Orders app. Follow the section 'When the Derek's decisions routine wakes you' in
> /workspace/orders/BOT_INSTRUCTIONS.md, using your own bot name."

Open each routine in the Grok Bot **desktop** app. The Webhook section shows a **URL** and a **key**. Fill
them into this text (in a text editor):
```json
{
  "Messanger":  { "url": "PASTE-URL", "key": "PASTE-KEY" },
  "Designer":   { "url": "PASTE-URL", "key": "PASTE-KEY" },
  "Designer 2": { "url": "PASTE-URL", "key": "PASTE-KEY" },
  "Designer 3": { "url": "PASTE-URL", "key": "PASTE-KEY" },
  "Designer 4": { "url": "PASTE-URL", "key": "PASTE-KEY" }
}
```
Then run the line below and paste the whole text, all on one line:
```
npx wrangler secret put BOT_WEBHOOKS
```
You can leave out bots you haven't set up yet. Their decisions still save, and the card says the bot will
see it on its next check. To change this later, run the same command again.

### 9. Set up the box
Ask a bot (Manager is fine) to do this on the box. Replace the two values with yours:
> Copy `push_to_app.py` and `BOT_INSTRUCTIONS.md` and `FORMATS.md` into /workspace/orders/.
> Create /workspace/orders/.viva_app containing two lines:
> `VIVA_APP_URL=https://viva-orders.vivamemoir.workers.dev`
> `VIVA_BOT_TOKEN=<the BOT_TOKEN from step 7>`
> then run `chmod 600 /workspace/orders/.viva_app` and `python3 /workspace/orders/push_to_app.py`, and show me the output.

(Send the bot the three files from the `box/` folder and this folder, or paste their contents.)
Then paste **BOT_INSTRUCTIONS.md** to every bot.

### 10. Put it on your iPhone
1. Open your app address in **Safari**.
2. Tap **Share** (the square with the arrow) → **Add to Home Screen** → **Add**.
3. Open it from the home screen and log in with your password. You'll stay logged in for about 4 months.

You're done.

---

## Everyday use
Three tabs at the bottom, like the Etsy seller app:

- **To approve** (red number = how many are waiting). One order at a time; use **‹ ›** to move between them.
  - The label says what it is: **New mockup · 1st approval**, **Buyer wants changes · 2nd approval** (the
    buyer's request is shown at the top), or **Last check before ordering** (the Printify mockup).
  - Picture buttons: **Mockup** (A/B if there are two), **Their photo(s)**, **Photo + mockup** side by side,
    and on a 2nd round **Sent before** and **Before + after**. Tap any picture to zoom.
  - Tap **Approve** (or **Approve A** / **Approve B**). It goes to Messanger, who sends it to the buyer or
    places the Printify order. Or tap **Ask for changes**, type what's wrong in your own words, and it goes to the artist who made it.
  - The card then shows **"Sent to Messanger ✓"** and, later, the bot's note ("Sent proof to buyer").
    If it says **"didn't reach … Retry"**, tap Retry. Your decision is saved either way.
- **In progress**: everything being worked on. Late-risk orders sit at the top in red, then waiting on the buyer,
  artist working, ordering, printing.
- **Shipped**: tracking links, then delivered orders.
- Tap any order for its full details: all mockup versions, buyer photos, Printify number, tracking and your decision history.

## Changing things later
- **New password:** `npx wrangler secret put APP_PASSWORD` (from this folder on your computer).
- **App code updates:** replace the files, then `npx wrangler deploy`.
- **See your data:** Cloudflare dashboard → Storage & databases → D1 → viva-orders.

## Things I couldn't verify, or that you should check
1. **Grok Bot webhook body.** Grok Bot routines with a webhook trigger give a URL and a key, and the app sends
   them exactly as documented (`POST` with `Authorization: Bearer <key>`). I couldn't confirm the bot
   gets to *read* the JSON body. The bots don't depend on it: they always ask the app with `pending`. Test
   with one approval first. One forum post mentions the webhook option being missing until the desktop app was updated.
2. **R2 sign-up** may ask for a card even on the free plan (step 2).
3. **Free limits** (checked Nov 2026): Workers 100,000 requests/day; D1 5 GB, 5M row reads and 100k row writes per
   day; R2 10 GB. You'll use a tiny fraction. Cloudflare can change these.
4. **iPhone home-screen apps** keep their own login, separate from Safari. Log in once inside the home-screen app.
5. **Login choice.** I used a single password built into the app instead of Cloudflare Access, which I suggested
   earlier. The reason: the bots' endpoints must skip Access, and that path-by-path setup is fiddly and easy to
   get wrong. The password login slows down guessing (8 tries per 15 minutes) and the bot side has its own token.
6. **Etsy API:** it has no buyer-messaging feature, so buyer messages stay with Messanger. (Not used by the app.)
7. **Later (optional):** Printify can send shipping updates straight to an app through its webhooks. This
   could move orders to Shipped/Delivered with no bot run. It's left out to keep version 1 simple.
8. **Left out to keep it simple:** push notifications (a bot can still ping you in chat), and reading Etsy or
   Printify directly.

## Files
| File | What it is |
|---|---|
| `src/worker.js` | The app's server (login, data, decisions, webhooks) |
| `public/index.html` | The phone screen |
| `schema.sql` | Database tables |
| `wrangler.jsonc` | Cloudflare settings (no secrets in it) |
| `box/push_to_app.py` | Script the bots run on the box |
| `box/app.json.example` | Example per-order file |
| `FORMATS.md` | Exact formats: app.json, push, webhook payloads, ack |
| `BOT_INSTRUCTIONS.md` | Paste to your bots |
