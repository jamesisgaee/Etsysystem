# Charlie Brown / Peanuts style: style guide (v2)

Listing: Charlie Brown Style Custom Christmas Portrait (4596967115).
Approved refs (`refs/charlie_brown/`):
- 01 Person08 & Person09 (couple). **Its arcs are the house standard.**
- 02 Person12 (9-person family)
- 03 Person05 & Person06 + Person07 (couple + dog)
- 04 Person23 (single, Starbucks apron)

Side by side: `refs/charlie_brown/approved_finals_compare.jpg`.
Style source: `refs/charlie_brown/_style_source/ref_peanuts_tv_frame.png` (a real 1960s TV-special frame).

## Model and ref order (proven on Person46, Person08, Person12, Person05)

1. **Base:** Gemini 2.5 Flash Image via `/workspace/gemini/gen.py`, at aspect 3:4 or 4:5. Attach refs in this order:
   1. TV frame: `_small/style_ref_peanuts_tv_frame.jpg`
   2. **MANDATORY: an approved shop order.** Use `_small/01_daniel_couple_approved_11x14.jpg` for singles, couples and small groups, or `_small/02_karmen_family9_approved_16x20.jpg` for families of 5+.
   3. Onward: buyer photos, cropped tight.

   The TV frame alone does not get Derek's look. Person27 v1/v2 used TV frame + Flash + Pro redraw with a weaker image 2, and Derek said: "No no Charlie brown themed those look bad look at other ones you did right".
2. **4K pass:** Gemini 3 Pro (`gen_pro.py`, `GSIZE=4K`) as a *faithful redraw* of the Flash image only. Pro on its own drifts to long realistic legs, sneakers and borders. **Re-check head size after this pass.**
3. **Post (local, no AI):**
   - **Draw the eye arcs on EVERY face, every time**, with the one arcs script below, even if the generation already drew some. Remove or paint over generated arcs that are thick or hug the dot.
   - Recolor hair or collars with a mask: `/workspace/orders/daniel_1000000104/art/hair_darken.py` (no AI calls).
   - Add lettering only as an alt or when clearly requested.

**Budget:** about 3 paid generations per job, run one at a time. Person08 took 2. One recommended option, plus at most one alternative.

### THE arcs script (one script, used everywhere)

`/workspace/orders/daniel_1000000104/art/eyecurves/draw.py` produced Person08's APPROVED final (ref 01). Re-running it on Person08's pre-arc file reproduces the approved file bit for bit (0 px different).
- Copy it into your order folder and edit the `eyes` list to `(eye center x, y, eye width, eye height, side)` for every dot eye in your print file. Each eye gets ONE outer arc, as in Person08's: the viewer's-left eye uses side -1 (arc on its left) and the viewer's-right eye uses side +1 (arc on its right).
- Run: `python3 draw.py in.png out.png [scale offset_x offset_y]` (scale and offsets map the coordinates onto a 4K master or wrap file).
- Look it produces: a **thin** stroke (0.30 × eye width, about eyebrow weight or lighter), **short** (about 1.7 × eye height tall), **set out from the dot with a clear gap** (2.6 × eye width from the eye center), at eye height, with slightly tapered ends, in ink color sampled from the eye.
- **Do NOT use** `/workspace/orders/1000000105/art/add_eye_curves_v2.py`. It drew thick arcs hugging the dot on Person27 v2, which Derek rejected.

## MASTER PROMPT (fill every slot; don't remove lines)

```
Draw a new illustration of the {people_count} people{and_pets} shown in photos 3 to {last_photo}, in the exact art style of the FIRST image, which is a frame from a classic 1960s Charles Schulz holiday TV special. The SECOND image is our shop's finished, approved portrait showing exactly how real people must look in this style - match its head size, faces, line weight and colors. Copy ONLY the drawing style from images 1 and 2, not their characters, clothes, booth, pumpkins, hay or fence.

Style: every person, adults too, is a simple Schulz-style comic character: a HUGE round head that is about half of the whole character height, tiny black dot eyes, a small curved-line "C" nose, simple "C" ears on every head, a small simple curved smile, soft pink blush circles on the cheeks, a short stubby flat body with simple stubby arms and small oval shoes, no adult anatomy, no realistic proportions. HEADS MUST BE HUGE exactly like the people in image 2. Glasses, if any, are small thin round Peanuts-style frames. Every face is equally simple and Peanuts - nobody more realistic than the others. {height_order}. Even black ink outlines with a slight hand-drawn wobble, flat muted marker / gouache colors with no gradients or airbrush shading, warm cream paper, lots of open empty space. Hair is drawn as simple flat Schulz shapes copying each person's real hair color, length, part and bangs from their photo, with a few ink lines.

The people, left to right:
{one line per person: name (photo #) - age/role, hair copied from photo (color + length + part + bangs), glasses yes/no, facial hair drawn with little dots, skin tone, outfit: {outfit default: simple flat-color clothes or muted Christmas sweaters in reds, greens, navy and cream - not all-black - unless the buyer asks for specific clothes}}
{pets: name - species/breed, fur colors and markings, eye color, collar color FROM THE ORDER NOTE if given; drawn in the same simple Schulz cartoon style, round head, dot eyes, simple shapes}
Exactly {people_count} people and {pet_count} pets. No other people or animals.

Scene: {scene: cozy Christmas: a simple small decorated tree with a few round ornaments and a star, a few wrapped presents, soft pale watercolor wash, a few soft snowflakes | snowy hill with a two-rail wooden fence | pumpkin patch | non-holiday green hill if the buyer says no Christmas}. Keep it sparse. The group is centered and fills about 75-80% of the picture width, with even cream-paper margins. No text, no letters, no names, no border anywhere. Full-bleed art that reaches every edge, nothing important near the edges. Vertical {aspect}.
```

**{height_order} default:** "Adults are only a little taller than the kids; the man is just a little taller than the woman, without stretching anyone." Derek said this on Person05; on Person12 he said "we still want them taller than the women... now they just look elongated". Change it only if the photo or order says otherwise.

## MUST-HAVE

- **Arcs beside every person's eyes**, drawn locally with `draw.py`: thin, short, set out from the dot, at eye height.
  - Derek has asked for them on Person10, Person08, Person05 (the girl), Person23 and Person27.
  - **Glasses:** use small thin round Peanuts frames. Put the arcs **outside the lenses**, or leave them off for that face if that's cleaner. Don't cram them inside the frames.
- **C-shaped ear arcs on every head**, babies included.
- **Pink blush circles on the cheeks.**
- **Dot eyes, C nose, simple one-line smile.** Each person is their own Peanuts character, not Charlie Brown himself ("not charlie brown the character but the theme").
- **All faces equally Peanuts.** No one face is more realistic or more detailed than the others.
- **Huge round head:** head height (including hair) **at least 45% of figure height** for singles, couples and small groups. Person08 measures about 50% for him and 47% for her. Short stubby flat bodies.
  - Big families are the exception: Person12's approved 9-person art is about 35% because people overlap and stand in rows. For 5+ people, match Person12's proportions rather than forcing 45%.
- **Hair copied from the photo first** (color, length, cut, bangs). Soften or restyle only when the buyer or Derek asks.
  - Person05 v2's generic bob was rejected ("the hair is not quite her hair").
  - The pixie copied from her photo (v3) was approved.
  - Later the buyer herself asked for "a little more feminine" hair, Derek said "Yes more feminine", and the chin-length bob v8c was approved.
- **Outfits:** simple flat colors or muted Christmas sweaters by default. Avoid muddy all-black unless the buyer asks.
- **Pets:** the right breed shape, the exact markings, and the collar color from the order note.

## NEVER

- No arcs *under* the eyes ("makes them feel tired"). No thick arcs hugging the dot (Person27 v2). No `add_eye_curves_v2.py`.
- No big, thick or realistic glasses frames.
- No realistic noses, lips, eyelashes, teeth, adult anatomy, long legs, sneakers or realistic hands. No 3D, Pixar, anime, gradients or airbrush shading.
- Never skip the approved shop ref as image 2. No OpenAI for the base.
- No franchise character names in the prompt. Don't copy the ref's booth, fence or pumpkins unless asked.
- No names or text on the main file unless clearly requested (lettering only as an alt). No borders.
- No long dog tongues ("tongue looks a little bit long").
- No white edges on the print file.

## Revision method (Person05 v3 / v6, works for any local fix)

From `/workspace/orders/1000000106/art/v3/` (`composite.py`) and `/workspace/orders/1000000106/art/v6/NOTES.md` (`compose_v6.py`, `fix_halo_and_grass.py`):
1. **Head or area crop:** cut a box around the part to change from the last-sent print (e.g. 800x800 around the head) and keep the box coordinates.
2. **Edit only the crop:** Gemini Pro 2K at 1:1 with the TV frame as the style ref, or a local pixel edit. Pick the best of a few edits.
3. **Feathered composite:** paste back through a mask about 3 px feathered. **0 px changed outside the mask** (prove it with a pixel diff).
4. **Resizing a figure** (e.g. "man a little taller"): extract the figure, scale it uniformly (e.g. 1.07) with premultiplied-alpha **LANCZOS around a foot anchor**, so the soles stay on the ground line and only the head rises.
5. **Gap-fill with texture:** fill leftover slivers of the old figure with nearby watercolor sky or grass that's copied and shifted so the grain continues. Never use a flat fill; it leaves ghost halos.
6. **QA at 2–3× zoom:** check the crown, jaw, ears, collar, feet, and any dotted remnants of the old outline. Then check the downscaled preview.

## Size and aspect

Generate at 4:5 (8x10, 11x14, 16x20) or 3:4 (5x7, 12x16, 18x24), then crop and resize to the exact pixels (README table). Keep figures inside a 375 px safe margin at 11x14.
- **Canvas:** the full art goes on the front, with **450 px solid cream sides** sampled from the art edge. 11x14 = **4200x5100** (unverified; confirm the side and back mockup show no white after reload). Person08 was actually ordered on the 4050x4950 plain-sides file because 4200x5100 uploads kept reverting in Printify.
- **12x16 width pad:** solid paper color, never mirrored.
- **Framed:** add an extra margin.

## PRE-SEND CHECKLIST (all must be YES before Derek sees it)

- [ ] Head count = order count; the left-to-right order matches the order or photo.
- [ ] Every pet is there, with the right breed shape, markings, eye color, and the **order-note collar color / any order-note override** (listed in WHO'S WHO).
- [ ] **Every face has `draw.py` arcs** (thin, short, gap from the dot, eye height), plus C ears, dot eyes, C nose and blush. Glasses wearers have small round frames, with arcs outside or omitted.
- [ ] **All faces are equally Peanuts.** Compare the faces to each other side by side; none is more realistic.
- [ ] **Head height ≥ 45% of figure height** on every person (big families: about Person12's 35% is OK), **re-measured after the 4K pass**. Bodies are stubby; no adult anatomy.
- [ ] Hair, glasses and facial hair match each photo. The man is a little taller than the woman, and nobody looks stretched.
- [ ] Outfits are flat colors or muted sweaters (not all-black unless asked).
- [ ] No extra limbs or fingers, no merged people, no garbled text or random letters.
- [ ] Flat colors, sparse background, cream margins.
- [ ] **Checked on the downscaled preview:** the arcs and big heads still read at the size Derek sees.
- [ ] Exact print pixels, 300 dpi, nothing important in the outer 5%, no white edge pixels.
- [ ] A photo-vs-art compare sheet is made for the first mockup. NOTES has WHO'S WHO, model, prompt files and the call count.

## Derek corrections (designer proposes, Manager appends: date, order, exact words, rule)

- Person10 kids: "there missign teh charlie brown style like on the eyes the half circles". Rule: arcs beside the eyes.
- Person10: "it put the half circles under some of there eyes which makes the feel tired". Rule: arcs at eye height, never under.
- Person40 (Designer 2): "this failed the charlie brown theme pretty drastically". Rule: TV frame + Derek's Schulz prompt (the master prompt above).
- Person40: "tongue looks a little bit long can you shorten it a little bit". Rule: dog tongues short.
- Person08: "for this image just add the half circles taht go on the right and left side of the eyes that really give that charlie borwn look". Rule: arcs, drawn with `draw.py`.
- Person08: the buyer asked to remove the names. Rule: no names by default; lettering only as an alt.
- Person05 (Designer 3): "make sharron somehow a little bit more charlie brown style the hair is not quite her hair". Rule: copy hair from the photo; Peanuts face.
- Person05: "good now make the girls face more charlie borwn like her smile is not charlie brown like her ears just her face in general.. and not hcarlie brown a teh character but the theme". Rule: Peanuts smile, C ears and face shape on every person; all faces equally Peanuts.
- Person05: "now add the half cirlces on teh sides of the eyes for the girl.. on the right". Rule: arcs on EVERY face, drawn locally by default.
- Person05 (Designer 3, t7u): "now make the man taller than the women just a little bit". Rule: the default {height_order}.
- Person05 (in Designer's chat, after the buyer asked for "a little more feminine" hair): "Yes more feminine". Rule: soften hair only when asked.
- Person12 (Designer): "we still want them taller than the women just the guy in yellow hair needed a fix ... now they just look elongated". Rule: men a little taller, without stretching anyone.
- Person24/Person23: "This does not look like Charlie brown make it more Charlie brown theme"; "add the starbuks logo and name to his suit like is on the other ones"; "have the little blush cirlces on his cheeks". Rules: blush; keep real logos and outfit details from the buyer photos.
- Person27 #1000000105 (Designer 2), on v1: "Good just add the half circles on left and right side of eyes". Then on v2 (thick arcs from `add_eye_curves_v2.py` on small-headed v1 art): "No no Charlie brown themed those look bad look at other ones you did right". Rules: approved ref as image 2 is mandatory; heads ≥45%; small round glasses; arcs only with `draw.py`.
