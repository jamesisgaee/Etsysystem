# Pet Christmas portraits (rustic painted, cream background): style guide (v2)

Listing: Pet Christmas listings (dog, cat, fireplace, Santa suit; Pinterest board "Custom Pet Portraits"). This line is for pet-only orders. A pet inside a Peanuts or Nightmare order follows that line's guide, e.g. Person35's beagle Person36 is Peanuts.
Refs: `refs/pet_christmas/01_dog_listing.png`, `02_cat_listing.png`, `03_fireplace_listing.png`, `04_santa_suit_listing.png`.
**No buyer-approved order yet.** The refs are the shop's listing sample art, which Derek published. When the first order in this line is approved, copy its final art in as `03_...` and note it here.

## Model

OpenAI `gpt-image` edit (`/home/box/.config/vivamemoir/openai_images.py`, `--allow-paid`, quality high, 1024x1536) made all four listing arts with Derek's rustic painting as the style ref, and one attempt each was kept. For buyer orders use the same model with the matching listing art as the style ref plus the pet photo. Gemini 3 Pro 4K can be used to upscale for large sizes.
Budget: **one recommended option plus at most one alternative**, about 3 paid generations per job at most, run one at a time. Revisions are targeted edits of the last-sent image, with a 0 px diff outside the mask (see README). Follow the README workflow: tracker `WORKING NOW: <bot> <what>` → Waiting for Derek, read the buyer thread first, the hard stop, and the approval flow.

## MASTER PROMPT (fill every slot; ref order: image 1 = a ref from `refs/pet_christmas/_small/`, then the buyer photos)

```
Paint a new vertical portrait in the exact same loose, rustic painting style as the FIRST image: oil and gouache with a watercolor feel, visible brushstrokes, soft painterly edges, a muted palette of deep red, forest green, antique gold and warm glow, and a plain warm cream background with lots of empty space at the top and around the subject.

The subject is {pet: name, species, breed, EXACT fur colors and markings from photo 2, eye color, collar/tag color}, {pose: sitting / lying by a fireplace / batting an ornament}, {costume: soft red Santa hat with white brim and pom-pom | Santa suit | no costume}, with {props: a small simple holiday tree with a few red, green and gold baubles, gold bead garland and a gold star | a stone fireplace with stockings}. Soft shadow on the cream ground. Keep the pet's face, markings and proportions true to the photo. Minimal, uncluttered composition. Keep all important content away from the edges.

This is a simple rustic painting, not photoreal and not a busy room. No furniture, no patterned rug, no stacked gifts, no text, no frame, no border, no watermark, no signature. Vertical {aspect}.
```

## MUST-HAVE

- The pet's exact markings, eye color, ear shape and collar color, so the owner instantly knows it's theirs.
- Rustic oil/gouache brushwork, a muted red/green/gold palette, and a lot of cream negative space.
- One simple holiday prop (tree, fireplace or Santa hat), as in the listing.

## NEVER

- No breed swap (e.g. not a black dog when the photo is golden). No busy rooms, rugs or furniture, and no text or signature.
- No photoreal or 3D render. No cropped ears or tail.

## Size and aspect

Generate at 4:5 (8x10, 11x14, 16x20) or 3:4 (5x7, 12x16, 18x24); for landscape goth canvases use 5:4 / 4:3. Crop and resize to the exact pixels in the README table at 300 dpi, then upscale with RealESRGAN if needed. Keep faces, hands and paws at least 5% in from every edge. **Canvas:** the whole approved image goes on the front, and each side gets **450 px of solid color sampled from the art edge** (11x14 wrap = 4200x5100; see the README table). Never white, never mirrored, never wrapped art. (PENDING DEREK: art wraps vs. solid sides; keep solid sides for now.)

## PRE-SEND CHECKLIST (all YES before Derek sees it)

- [ ] Pet count = order; each pet matches its photo (markings, eye color, collar).
- [ ] No extra legs or tails, and no fused pets.
- [ ] Cream space at top; nothing important near the edges; no text.
- [ ] Exact print pixels at 300 dpi; canvas sides are solid cream from the art.
- [ ] Order-note overrides (e.g. collar color) are copied into WHO'S WHO and match the art.
- [ ] Mask seams checked at 100% on any composited edit (no halos or fringes).
- [ ] Checked on the downscaled preview Derek sees.
- [ ] Photo-vs-art compare sheet made for the first mockup.
- [ ] NOTES.txt has WHO'S WHO, model, prompt files and the paid-call count.

## Derek corrections (designer proposes, Manager appends: date, order, exact words, rule)

- (none yet)
