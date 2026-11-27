# Nightmare Before Christmas / Tim Burton stop-motion: style guide (v2)

Listing: Nightmare Before Christmas Custom Portrait (4595497386).
Approved refs (`refs/nightmare/`):
- **01 Person01 v10A: the DEFAULT look.** Victorian gothic, matte clay puppets, cinematic film grade. Derek, Nov 22, on Person25 Person26: "redo it exactly how Person01's was done." The buyer saw v10A and asked only that the dog be "a little more Tim Burton"; v12 (dog stitches) is still waiting on Derek.
- **02 Person20 v18:** a costume-couple variant with warm skin. Buyer-approved: "This is good! Please print."
- **03 Person37 v5d:** a couple + 2 dogs + 4 cats on a bench and swing. Buyer-approved: "That's it that one is perfect".

Side by side: `refs/nightmare/approved_finals_compare.jpg`.
Style source: `_style_source/derek_style_ref_film_still.png` (the matte puppet film still Derek sent; use it for lighting and texture only, and **always attach it LAST**).
Pet ref: **after Derek approves Person01 v12**, Manager adds the v12 dog as a pet ref. Until then, describe the v11B look (below).

## Model and ref order (the single source; README defers to this)

- **Gemini 3 Pro Image, 4K**: `GSIZE=4K python3 /workspace/orders/1000000103/art/gen_pro.py out.png "prompt" 3:4|4:5 refs...`
- **Ref order:**
  1. `_small/01_kristin_v10A_victorian_burton_5x7.jpg`, or `02_joanna...` when the buyer asks for a costume couple
  2. Onward: buyer photos, cropped tight to each person and pet (2–3 per person when available)
  3. **LAST, optional:** the film still, for lighting. Attaching it first triggered PROHIBITED_CONTENT on Person20.
- **Fallback:** Seedream 5.0 Pro at 1.5K (`/workspace/tools/seedream.py --model pro --resolution 1.5K`) if Gemini refuses or drifts. It made Person01 v7B. Upscale with RealESRGAN x4.
- **Film finish (MANDATORY on every Nightmare final, local, no AI):** `/workspace/orders/kristen_1000000100/art/v10/work/finish_v10.py` gives teal-shadow film grade, highlight roll-off, ground haze and soft grain, while protecting the moon and pumpkins.
  - Strength 0.55 is the v10A look Derek and the buyer saw; 1.0 is stronger.
  - Run it on the 4K master, then crop and resize to print.
- **Recipe for a new order:**
  1. ONE Pro base generation with the master prompt.
  2. If it isn't Burton enough, **ONE targeted Pro edit**: "more Tim Burton: longer thinner necks, deeper hollow eyes with small pupils, matte clay surfaces, keep faces, outfits and composition".
  3. Run `finish_v10.py`.

  That gives one recommended option, plus at most one alternative. Budget about 3 paid generations per job, one at a time.
- **How v10A was actually made** (from the order NOTES, for the record): a Gemini 3 Pro 4K base anchored on Person20 v18 (v5A5), with masked Pro fixes for sleeves, likeness and stitches. Then a Pro "Tim Burton face" edit (v8B), a Pro "even more Tim Burton" edit (v9B), and a Pro lighting/texture edit plus `finish_v10.py` at 0.55 (v10A). That took 12 rounds. The recipe above front-loads those rules so a new order gets there in 1–2 generations.
- No Midjourney or OpenAI for new Nightmare work.

## MASTER PROMPT

```
Create a brand-new full-frame vertical portrait that looks like a real frame from a handmade gothic Tim Burton-style stop-motion Halloween film, in exactly the same art style, lighting, texture and atmosphere as the first image (our shop's approved portrait). Copy ONLY the style from it, not its people, clothes or animals.

Style: a photographed miniature tabletop set with MATTE sculpted clay puppets: visible fingerprint and tool texture, slightly lumpy hand-sculpted forms, stitched fabric clothes with real cloth weave, painted wood and cardboard set pieces, practical miniature lighting, shallow depth of field, fine film grain. Strong Tim Burton look: slightly long faces, long thin necks, thin spindly arms and legs, tall slim silhouettes, BIG round hollow puppet eyes with creamy sclera and small dark pupils set in dark shadowed sockets, a few tidy dark stitched seams on every face (forehead, mouth corners, cheek), necks and wrists. Hands are soft fleshy puppet hands with five fingers, not bony or skeletal. Skin is {skin: pale ivory-grey porcelain clay | warm natural peach clay}, with a soft hand-painted blush - NOT blue, not green, not zombie. Clearly human puppets of these specific people, not skeletons, not photoreal heads, not Pixar/CG, not glossy plastic, not yarn hair, not scary or deformed.

People ({people_count}), left to right:
{one line per person: name (photo #): face shape, hair color/length/part (sculpted matte clay hair), facial hair, freckles, glasses, tattoos, ring, smile type, REAL body type}
Outfits (original designs, inspired by a gothic Halloween-town film, not copies of any film costume): {outfit default: Victorian gothic black - long tailcoat, waistcoat, cravat; lace high-collar gown | costume couple: a dark charcoal-and-black striped tailcoat suit with a dark bow tie / an ANKLE-LENGTH hand-patched rag dress in {her colors}, with visible dark hand stitching along the seams | the buyer's own outfit described}. Full sleeves on both arms.
Pets ({pet_count}): {one line per pet: breed, exact colors and markings, eye color}. Matching stop-motion puppet pets: matte sculpted fur, bulging inset hollow puppet eyes, a slightly longer snout, a spindly angular body, a few small dark stitched seams on the muzzle, neck and one ear; real markings and pose kept exactly so it is clearly their pet.

Scene: Halloween Town at night. A huge pale cratered full moon backlights the group; a tall black spiral hill curls into one tight spiral against the moon; twisted bare trees with curly branches frame the sides; crooked gravestones, a wrought-iron fence, glowing carved jack-o'-lanterns, low teal-grey mist. {scene_extra}. Lighting: cool cinematic moonlight with a rim light, deep shadows, warm orange pumpkin glow on the faces; the people are the brightest, clearest part of the image. Palette: deep teal, blue-black, slate grey, warm pumpkin orange, pale moonlight; desaturated, grainy film still.

Composition: {pose from photo}. Large in frame with comfortable space at every edge. Full-bleed painted background reaching all four edges. No frame, no wall, no room, no text, no "RIP" or letters on tombstones, no border, no watermark. Vertical {aspect}.
```

**Costume note:** the default is the *inspired-but-original* costume above. Exact film signatures (Jack's pinstripe suit with a bat-wing bow tie, Sally's exact patchwork) caused refusals on Person20 and aren't recreated by default. Use a closer look **only if the buyer asks in their own words**, and keep it a stylized nod, not a copy. Person20 v18 shows how far an approved order went.

## MUST-HAVE

- **A strong Tim Burton look:** spindly limbs, long thin necks, big hollow eyes with small pupils in dark sockets, stitched seams, matte clay with tool marks, and the Halloween Town palette with a warm moon and pumpkins.
  - **`finish_v10.py` is applied to every final.** If it looks like a cute 3D cartoon, it fails.
- **Stitches on every person's face**, including the man's. Pets get a few seams too.
- **Likeness:** each person's real face shape, hair, facial hair, freckles, tattoos, ring and real body type (curvy stays curvy). Use 2–3 photos per person when available.
- **Spiral hill, big moon and jack-o'-lanterns** in every scene.
- **Dresses are ankle-length** on the costume couple. Person25 v1's knee-length dress was a weak spot.
- **Hands are fleshy puppet hands**, not bony (Person25 v1's bony hand was a weak spot, and Person01 v1 drafts were dropped for skeletal hands).
- **Pets in the v11B look:** bulging inset eyes, a slightly longer snout, a spindly body, a few seams. Still clearly their pet, and not Zero unless asked.

## NEVER

- **No blue skin** ("i dont like the blue"), unless the buyer explicitly asks for it.
- No glossy plastic, Pixar, smooth CG or photoreal heads (Person37 v1 was rejected for photoreal heads). No felt or yarn rag-doll faces unless Derek asks.
- No skull or skeleton faces unless the buyer asks. Skull wording triggers refusals.
- No exact film costumes by default (see the costume note). No broken outfits: both sleeves on, and tattoos only where the person has them.
- No top hat hiding the hair unless asked. No extra people from photo backgrounds. No text on tombstones.
- Not too scary, no deformed or skeletal hands, no knee-length costume dress.

## Size and aspect

Generate at 3:4 (5x7, 12x16, 18x24) or 4:5 (8x10, 11x14, 16x20). Apply the finish, then crop and resize to the exact pixels (README table).
- **Canvas wrap:** front plus **450 px solid dark purple or navy sides sampled from the edge** (11x14 = 4200x5100; Person37 and Person20 used solid sides). Never mirrored or white.
- Check that no edge pixels are pure white, except moon or pumpkin glow.

## PRE-SEND CHECKLIST

- [ ] Face count = order; every person is recognizable next to their photo (photo-vs-art face strip made for the first mockup).
- [ ] Every pet is there once, with the right breed, markings and eye color. No duplicates or missing pets.
- [ ] Burton marks: hollow big eyes with small pupils, long necks, spindly limbs, stitches on every face, matte clay, spiral hill, moon and pumpkins. **`finish_v10.py` applied.**
- [ ] Skin is not blue (unless asked). Not glossy. Not photoreal.
- [ ] Hands are fleshy with 5 fingers; no extra limbs; both sleeves on; costume dress is ankle-length.
- [ ] **Mask seams checked at 100%** on every composited edit: no halos, color steps, ghost outlines or fringes (e.g. the grey-blue tail-tip fringe on Person01 v11/v12).
- [ ] No text or garbled letters (tombstones, signs). No watermark.
- [ ] Checked on the downscaled preview: the stitches and hollow eyes read at Derek's view size.
- [ ] Exact print pixels at 300 dpi, nothing important in the outer 5%.
- [ ] NOTES has WHO'S WHO, model, prompt files and the call count. Tracker is set to Waiting for Derek.

## Derek corrections (designer proposes, Manager appends: date, order, exact words, rule)

- Person01 v2: "no thats not very godo maybe we need to feed it more reference photos this is not good at all". Rule: 2–3 photos per person.
- Person01 v5: "take reference from joannas listing try nad make them like that style but with this couple i dont like the blue". Rule: no blue skin; start from an approved ref.
- Person01 v5A: "add stitches to the man". Person01: "Now add the stitches back yo her face". Rule: stitches on every face.
- Person01: "the suit is broken its a suit but on arm has tatoos with no sleev efix this". Rule: check both sleeves.
- Person01: "Now only adjust features but make the girl on the right look more like the one in photo". Rule: likeness first.
- Person01 v6: "we need more of that tim burton style this photo is drastically lacking it..". Person01 v8: "v8 is best can you try and make it even more tim burton on that one?" Person01 v9: "make the textures lighting and everything a little more tim burton style." Rule: strong Burton look by default, plus the mandatory film finish.
- Person01 v11 (buyer: dog "a little more, Tim Burton"), then Derek: "maybe try stitches or whatever the dogs have in nightmare before christmas v11b is best." Rule: pets in the v11B look with stitches from v1.
- Person20 v16: "still not quit there can you try a couple more time we want that cuter nightmare before christmas style just like this" (film still). Rule: matte puppet film-still finish.
- Person25 Person26, Nov 22: "redo it exactly how Person01's was done". Rule: Person01 v10A is the default ref.
- Nov 22, guide review: Derek removed the Person43 v5 skeleton-Jack ref and the listing-hero ref ("remove the 4th and last one down"). Rule: don't use them as style refs.
- Standing (Designer role brief): "Not too scary, not deformed or glitchy, faces should look like the people."
