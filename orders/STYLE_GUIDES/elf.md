# Buddy the Elf (realistic photo costume): style guide (v2)

Listing: Elf Movie Inspired Custom Christmas Family Portrait (4597002678).
Refs: `refs/elf/01_elf_listing_family_v3.png` (current listing art), `02_elf_listing_sample_couple.png` (couple), `03_elf_listing_sample_pets.png` (pets in elf hats); all are listing sample art.
**No buyer-approved order yet.** The refs are the shop's listing sample art, which Derek published. When the first order in this line is approved, copy its final art in as `03_...` and note it here.

## Model

Gemini 2.5 Flash Image via `/workspace/gemini/gen.py` made the listing art. For a buyer order use **Gemini 3 Pro 4K** (`gen_pro.py`), because face likeness matters most here: this is the one line where faces stay photo-real. Seedream 5.0 Pro is the fallback.
Budget: **one recommended option plus at most one alternative**, about 3 paid generations per job at most, run one at a time. Revisions are targeted edits of the last-sent image, with a 0 px diff outside the mask (see README). Follow the README workflow: tracker `WORKING NOW: <bot> <what>` → Waiting for Derek, read the buyer thread first, the hard stop, and the approval flow.

## MASTER PROMPT (fill every slot; ref order: image 1 = a ref from `refs/elf/_small/`, then the buyer photos)

```
Create a photo-realistic Christmas portrait of the {people_count} people{and_pets} from photos 2 onward, keeping their REAL faces exactly: same face shape, skin tone, eyes, smile, hair color and style, glasses and facial hair. Do not cartoonize or beautify the faces. Image 1 shows our shop's style: copy only the costume, pose, lighting and background style from it, not its people.

Everyone wears a classic Buddy-the-Elf style costume: bright green coat with white fur trim, black belt with a gold buckle, yellow tights, curly-toe elf shoes and a green elf hat with a white fur band and a feather. Pets: {pet lines: breed, colors, markings} each wearing a small matching elf hat (and optional green collar), real fur and markings.
People, left to right: {one line per person: name (photo #), height order, hair, glasses, facial hair, skin tone}.
Pose: standing hands-on-hips, cheerful, full body, feet visible, in front of a pale blue New York-style city skyline with soft snow on the ground and lightly falling snow. Bright, vibrant, high-key, even daylight lighting. Exactly {people_count} people and {pet_count} pets.
Full-bleed photo that reaches every edge, with nothing important near the edges. No text, names, logos, border or watermark (lettering only as an optional alt, added in post, unless the order clearly asks). Vertical {aspect}.
```

## MUST-HAVE

- Real, photo-true faces of each buyer, with the correct skin tone and hair. Only the costume changes.
- The full costume: green coat + white fur trim + black belt with gold buckle + yellow tights + curly shoes + feathered hat.
- Hands-on-hips Buddy pose, a pale blue city skyline and snow. Bright and vibrant (Derek liked the brighter Elf cover so much he asked to match the other listings to it).
- Pets in little elf hats.
- Outfits always the full costume; a hair recolor or similar fix is a local masked edit (`/workspace/orders/daniel_1000000104/art/hair_darken.py`), not a regeneration.

## NEVER

- Don't cartoonize, plasticize or "AI-beautify" faces. No face swaps between family members.
- No dim or dark lighting. No movie stills or actor faces, and no text.
- No missing tights/shoes, or cropped feet.

## Size and aspect

Generate at 4:5 (8x10, 11x14, 16x20) or 3:4 (5x7, 12x16, 18x24); for landscape goth canvases use 5:4 / 4:3. Crop and resize to the exact pixels in the README table at 300 dpi, then upscale with RealESRGAN if needed. Keep faces, hands and paws at least 5% in from every edge. **Canvas:** the whole approved image goes on the front, and each side gets **450 px of solid color sampled from the art edge** (11x14 wrap = 4200x5100; see the README table). Never white, never mirrored, never wrapped art. (PENDING DEREK: art wraps vs. solid sides; keep solid sides for now.)

## PRE-SEND CHECKLIST (all YES before Derek sees it)

- [ ] Face count = order; every face matches its photo side by side (100% crops).
- [ ] Every pet is there with an elf hat and the right markings.
- [ ] Every costume piece is present on every person; hands have 5 fingers, and there are no extra limbs.
- [ ] Bright, high-key lighting; skyline and snow present; no text or garbled signs.
- [ ] Exact print pixels, safe margin, no white edges.
- [ ] Order-note overrides (e.g. collar color) are copied into WHO'S WHO and match the art.
- [ ] Mask seams checked at 100% on any composited edit (no halos or fringes).
- [ ] Checked on the downscaled preview Derek sees.
- [ ] Photo-vs-art compare sheet made for the first mockup.
- [ ] NOTES.txt has WHO'S WHO, model, prompt files and the paid-call count.

## Derek corrections (designer proposes, Manager appends: date, order, exact words, rule)

- (none on buyer orders yet) From the listing work, Derek: "so here is the new elph photo is more vibrant more light and a christmas reef above cna you apply that to the other dim listings". Rule: bright, vibrant, light.
