# VivaMemoirStudio Style Guides: first-try portrait art

v2, Nov 22, 2026: merged feedback from Designer, Designer 2, Designer 3 and Designer 4. v1 is in `_v1_backup/`.
Every designer bot (Designer, Designer 2, Designer 3, Designer 4) follows this guide.
**Goal:** the first mockup Derek sees should already be right. No order starts from scratch, and Derek never has to repeat a spec.

## Files

| Product line | Guide | Refs |
|---|---|---|
| Charlie Brown / Peanuts | `charlie_brown.md` | `refs/charlie_brown/` (4 approved buyer orders + `_style_source/`) |
| Nightmare Before Christmas | `nightmare.md` | `refs/nightmare/` (3 approved or buyer-sent orders + `_style_source/`) |
| Buddy the Elf (realistic) | `elf.md` | `refs/elf/` (listing art only) |
| Pet Christmas portraits (rustic painted) | `pet_christmas.md` | `refs/pet_christmas/` (listing art only) |

Removed Nov 22 per Derek (kept, not deleted): the Simpsons, Family Guy, anime goth and goth fairytale guides, and 2 Nightmare refs, all in `_removed/`. Orders in those lines have no guide for now; ask Manager before starting one.
- `guide_overview.jpg` is a contact sheet of every ref, for Derek to review.
- `refs/<line>/approved_finals_compare.jpg` puts that line's finals side by side, at full view and at the downscaled preview size Derek sees. Match it before you send.
- `refs/<line>/_small/` holds 1024 px JPG copies (style sources are prefixed `style_`). **Send these to the image model, not the full-res PNGs.**
- Refs are COPIES. The originals stay in the order folders.

## Ownership of this guide

**One owner edits the guides: Manager.** The designer who did an order *proposes* a correction (Derek's exact words, the order #, the proposed rule) in their hand-back. Manager adds it to the line's "Derek corrections" list and to MUST-HAVE / NEVER if it applies to every order. Designers don't edit the `.md` files directly.

## The workflow (every order, every line)

1. **Claim it.** Set the order's `ORDER_TRACKER.csv` row to `WORKING NOW: <bot> <what>` (e.g. `WORKING NOW: Designer 2 v1 mockup`) before you start.
2. **Read everything first.** That means:
   - the personalization text word for word and the order note;
   - every buyer photo in `/workspace/orders/<order>/photos/`;
   - **the buyer thread, including what was already sent to the buyer and what they said about it**;
   - the tracker row.

   Write a short WHO'S WHO in `art/vN/NOTES.txt`. Give one line per person and pet: name, which photo, hair color/length/part, glasses, facial hair, skin tone, outfit, and for pets the markings and collar color.
   **Order-note overrides go in WHO'S WHO and the checklist** (e.g. Person05: "pink collar on Person07" even though it's red in the photo). If who's who can't be worked out, flag it rather than guessing quietly.
3. **Open the line's guide.** Copy its MASTER PROMPT into `art/vN/prompt_A.txt` and fill **every** `{slot}`. Don't delete the MUST-HAVE or NEVER lines from the prompt.
4. **Attach refs in the exact order the guide lists** (each line's guide is the single source for its ref order).
5. **Generate one recommended option, plus at most one alternative.** Use the model the guide names and run calls one at a time.
   - **Budget:** about 3 paid generations per person or job at most, counting retries.
   - No A/B/C sets "just in case."
6. **Run the PRE-SEND CHECKLIST** on the full image, on 100% crops of every face and mask seam, and on the **downscaled preview Derek will actually see** (arcs, stitches and head size must read there).
   - If something fails, fix that one thing with a targeted edit, not a full regeneration.
7. **Make the print file** from the size table below: exact pixels, 300 dpi, plus a 1200 px preview.
8. **Send to Derek with the FIRST mockup:** the preview, a **photo-vs-art compare sheet** (each buyer photo beside its person or pet), one line on what it is, one line on the known weak spot, and file paths.
   - Set the tracker row to **Waiting for Derek**.
   - Send it through the board or Manager, never to the buyer.

## Revisions: change ONLY what Derek named

- Edit the **exact last-sent image**, never a fresh redraw. Local pixel edits come first: recolor, arcs, scaling, moving. If you need generation, crop the head or area, edit it, and composite it back with a feathered mask.
- **Pixel-diff** the result. Outside the mask the diff must be **0 px**. Put the numbers in NOTES.
- One revision = one change set = one recommended option (plus at most one alt if Derek asks for choices).
- The full Peanuts revision method (head crop, scale around a foot anchor, gap-fill, QA) is in `charlie_brown.md`. It works for any line.

## Hard stop

When Derek says **stop**, **don't regenerate**, or anything like it, **halt all generation on that order immediately** (no "one last try") until he says to continue. Local, non-generative fixes he asked for are fine.

## Approval flow and handoff

1. Derek approves **in his own words** (an agent's "approved" doesn't count). Only then does the art go to the buyer, sent by Messanger.
2. After the buyer approves, **make a Printify mockup with the exact approved art** for Derek before anything is ordered. Ordering is Messanger's lane; designers never place Printify orders.
3. Printify checks (for whoever builds the product):
   - Upload the final **wrap** file (canvas) or exact print file, then **reload the editor and confirm the art stuck**. The editor has reverted re-uploads before.
   - Check the front, **side and back-fold mockups: no white anywhere**, and the art fills the front.
   - Put the **Etsy order # in the Printify product title**.
   - Printify orders need a **recipient phone**. Use the vault entry named **'Me'** (Derek's). Never write the number in notes, chat or files.
   - Use the buyer's approved file, never the listing sample.

## After Derek approves: grow the guide

The designer proposes, and Manager appends to "Derek corrections": the date, order #, Derek's exact words and the rule. If the approved art beats an existing ref, Manager copies it into `refs/<line>/` (and `_small/`) and rebuilds `approved_finals_compare.jpg` and `guide_overview.jpg`.

## Rules that apply to every line

- Likeness comes from the small traits: hair color, length and part, glasses, beard or goatee, freckles, tattoos, ring, real body type, and pet markings plus collar color. The buyer's note beats the photo when they conflict.
- Faces are never covered, cut off or near an edge. Keep heads, hands and paws inside the safe area.
- **Names and text: none on the art by default.** If the personalization doesn't clearly ask for text, make the plain version the main file and a lettered version as an optional alt (Person08 asked for the names to be removed). When it does ask, letter it in post with a font, never in the generation. Peanuts uses Groundnut (`/workspace/orders/person10/_work/v4f/Groundnut.otf`), which has no & or + glyph, so write "AND".
- Brighter beats dim ("more vibrant more light").
- Never write "Disney" in any listing or buyer-facing text.
- Never print or log `OPENROUTER_API_KEY`, `GEMINI_API_KEY` or any phone or card number.

## Print sizes (300 dpi, portrait unless the order says landscape)

| Size | Print / front pixels | Canvas wrap file (front + 450 px solid edge color per side) | Generate at | Then |
|---|---|---|---|---|
| 5x7 print | 1500x2100 | n/a | 3:4 | crop to 5:7, LANCZOS |
| 8x10 | 2400x3000 | 3300x3900 | 4:5 | resize |
| 11x14 | 3300x4200 | **4200x5100** (unverified; confirm the side and back mockup show no white after reload. Person08 was ordered on the 4050x4950 plain-sides file) | 4:5 | crop to 11:14 |
| 12x16 | 3600x4800 | 4500x5700 | 3:4 | resize; if a few px short, pad with a **SOLID color sampled from the paper/edge, never mirrored** |
| 16x20 | 4800x6000 | 5700x6900 | 4:5 | resize |
| 18x24 | 5400x7200 | 6300x8100 | 3:4 | resize + RealESRGAN if needed |
| 24x36 | 7200x10800 | 8100x11700 | 2:3 | resize + upscale |
| Landscape canvases | swap W/H | swap W/H | 5:4 / 4:3 / 3:2 | crop |

- **Safe area:** keep faces, hands, paws and lettering at least 5% in from every edge of the front.
- **Prints, posters, framed:** full-bleed art at the exact pixels. For a frame, add an extra ~0.25" margin under the frame lip.
- **Canvas (1.25" gallery wrap):** the *whole* approved image goes on the **front** (nothing cut off). Each side gets **450 px of SOLID color sampled from the art's edge**: 1.25" wrap plus 0.25" because Printify's print area is bigger per edge. The old 375 px (4050x4950) left a **white strip on the back fold**. Sides are never white, never green, never mirrored, never stretched art. All non-11x14 wrap sizes in the table are scaled the same way and haven't been verified in Printify yet, so check the side and back mockup.

> **PENDING DEREK: art wraps the edges vs. solid sides.** The brief that started these guides mentioned art wrapping the edges. Derek's standing words are "make sure the sides... flow with the image. They're not like green", and every order so far shipped with solid sides sampled from the art. **Keep using solid edge-color sides** until Derek answers; Manager will update this section.

## Models and tools (what has actually worked)

| Tool | Use for | How |
|---|---|---|
| Gemini 2.5 Flash Image | Peanuts base generation, cheap drafts | `python3 /workspace/gemini/gen.py out.png "prompt" <aspect> ref1 ref2 ...` (no model option) |
| Gemini 3 Pro Image (4K) | Nightmare base and all targeted edits; Peanuts faithful 4K redraw only | `GSIZE=4K python3 /workspace/orders/1000000103/art/gen_pro.py out.png "prompt" <aspect> refs...` |
| Seedream 5.0 Pro via OpenRouter | Fallback when Gemini refuses or drifts | `/workspace/tools/seedream.py --model pro --resolution 1.5K --aspect 3:4` (see `/workspace/tools/SEEDREAM_README.md`) |
| OpenAI gpt-image | Pet Christmas painted art only | `/home/box/.config/vivamemoir/openai_images.py` (`--allow-paid`; refuses face edits) |
| Peanuts eye arcs (local, no AI) | Every Peanuts face | `/workspace/orders/daniel_1000000104/art/eyecurves/draw.py` (see `charlie_brown.md`) |
| Hair recolor (local, no AI) | Hair darker or lighter on any line | `/workspace/orders/daniel_1000000104/art/hair_darken.py` (color-component mask, locked areas, tone curve) |
| Nightmare film finish (local) | Every Nightmare final | `/workspace/orders/kristen_1000000100/art/v10/work/finish_v10.py` |
| RealESRGAN x4 | Upscaling Flash or Seedream output | as in Person01 v6B / Person41 v5 |

Gemini refuses (PROHIBITED_CONTENT) when the prompt describes skull faces literally, names exact film costumes, or attaches a film still first. Describe "puppet", "clay" and "inspired" outfits, and attach any film still **last**.
