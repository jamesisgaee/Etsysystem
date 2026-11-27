"""Review-queue helpers for build_board.py.

Finds mockups, buyer photos, and request text for orders whose status is
Needs mockup or Waiting for Derek, and builds the asset manifest.

A Page holds at most 20 images and has no delete, so the queue uses a
fixed pool of asset slots (rq-slot-01.jpg through rq-slot-20.jpg). Each
card uses one mockup plus one reference-photo contact sheet. Rebuilds
write JPEG copies into those same slot files and WriteCanvasAsset
overwrites the same names, so the Page stays at or under 20 images even
as orders enter and leave the queue.
"""

from __future__ import annotations

import re
from pathlib import Path

# Only mockups waiting on Derek get image cards on the simple board (Nov 22 layout).
QUEUE_STATUSES = {"Waiting for Derek"}

FOLDER_MAP = {
    "1000000110": "person20",
    "1000000106": "1000000106",
    "1000000111": "1000000111",
    "1000000112": "karmen_1000000112",
    "none-yet": "person10",
}

SKIP_DIRS = {
    "_work",
    "qa",
    "tries",
    "raw",
    "photos",
    "photo",
    "ref",
    "refs",
    "kid_refs",
    "incoming",
    "nov11_attachments",
    "reply_attachments",
    "embroidery",
    "v7_requests",
    "v8_requests",
    "__pycache__",
}

SKIP_NAME_RE = re.compile(
    r"(pixel_diff|before_after|side_by_side|photos_vs|_vs_|mask|chk_|"
    r"compare|grid|crop|face_|stage\d|raw_|diff_|halo|contact_sheet_)",
    re.I,
)

PREVIEW_RE = re.compile(
    r"(preview|proof|mockup|final|contact_sheet|"
    r"\d+x\d+|5x7|8x10|11x14|12x16|16x20|18x24|crewneck|hoodie)",
    re.I,
)

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VERSION_RE = re.compile(r"^v(\d+)([a-z]*)(?:_.*)?$", re.I)

# Buyer-word quotes and a short context line, keyed by order number.
# Only wording recorded from the buyer or their order note; never invent.
REQUEST_CONTENT = {
    "1000000110": {
        "quotes": [
            {
                "text": "Make them look more like Jack and Sally.",
                "cite": "Person20 Person21, as recorded Nov 19",
            }
        ],
        "text": (
            "From the order: her hair down, him without a hat, a visible "
            "engagement ring, and a more romantic background. The latest "
            "Jack and Sally proof was sent to Person20 at 6:29 PM PT on Nov 20, "
            "and we are waiting on her reply."
        ),
    },
    "1000000106": {
        "quotes": [
            {
                "text": "Person07's collar should be pink, even though it is red in the photo.",
                "cite": "Person05 Person47, order note",
            }
        ],
        "text": (
            "No buyer messages yet. The v6 mockup was sent to Person05 at "
            "2:49 PM PT on Nov 20, and we are waiting on her reply."
        ),
    },
    "1000000111": {
        "quotes": [],
        "text": (
            "Recorded from the order: a Charlie Brown portrait of her boss "
            "Person23 in front of his Starbucks, in a black Coffee Master apron, "
            "with the name Person23, as a Christmas gift from the Person55 team. "
            "Her later revisions asked for a second wreath, red poinsettias, a "
            "curvier Person23, Coffee Master text, darker brown hair, and facial "
            "hair. Derek approved v2h A (connected mustache) and it was sent to "
            "Person24 at 6:05 PM PT on Nov 20. We are waiting on her reply. No "
            "verbatim message text was on file."
        ),
    },
    "1000000112": {
        "quotes": [],
        "text": (
            "No buyer message or order-note wording was on file. The v6 mockup "
            "is a Charlie Brown family portrait from her photos (Person12, Person13, "
            "Person14, Person15, Person16, Person17, Grandad, Person18, and Person19). It was "
            "sent to Person12 at 3:20 PM PT on Nov 20, and we are waiting on her reply."
        ),
    },
    "none-yet": {
        "quotes": [
            {
                "text": "amazing!!!",
                "cite": "Person10 Person11, Nov 20, after receiving her sample prints",
            },
            {
                "text": (
                    "Person28. The one without glasses is perfect. Can you add an "
                    "Apple Pencil drawing deal? She is right handed if that "
                    "matters. And can we make her headphones black/gray? Thank you!"
                ),
                "cite": "Person10 Person11, v8 request for Person28",
            },
            {
                "text": (
                    "Person34. I'm so sorry that I messed this one up. Can we make "
                    "her dress less cute? I'm attaching a few pics. Im sorry I "
                    "totally messed up her description. I love the bright peach "
                    "orange pattern on the dress with the scarf. That's totally her."
                ),
                "cite": "Person10 Person11, v8 request for Person34",
            },
            {
                "text": (
                    "Person30. The colors are absolutely amazing, perfect. Will you "
                    "please change the pattern of her sweater? She hates any "
                    "stripes or polka dots and wears like old man patterns. I'm "
                    "not sure how else to describe. The colors are exactly perfect. "
                    "And I was totally wrong about her shoes. She has black platform "
                    "Doc Marten's. And will you have her holding a Nalgene bottle? "
                    "She had one from some State park deal in Arkansas. It was "
                    "clear with like a badge or something on it and a green top. "
                    "And can you make her pants a longer - still flared? Thank you!"
                ),
                "cite": "Person10 Person11, v8 request for Person30",
            },
            {
                "text": (
                    "Person29. Okay I messed up the colors on her. I'm so sorry. "
                    "I'm attaching a picture of her actual sweatshirt and her "
                    "actual water bottle and her shoes. Thank you so much!"
                ),
                "cite": "Person10 Person11, Nov 17, v8 request for Person29",
            },
        ],
        "text": (
            "She also asked to see the word Cousins under the group of 7 kids, "
            "and whether she can mix hoodies, crewnecks, and colors. Brand and "
            "size questions from Nov 19 were answered. The v8 Cousins heather-gray "
            "crewneck and hoodie, plus the Person28, Person30, Person29, and Person34 5x7s, were "
            "sent at 6:50 PM PT on Nov 20. We are waiting on her reply. There is "
            "no Etsy order for the sweatshirts yet."
        ),
    },
}


def mockup_overrides(here: Path) -> dict[str, Path]:
    return {
        "1000000110": here / "person20/art/jack_sally_proof_final.png",
        "1000000106": here / "1000000106/art/v6/sharon_v6_preview.jpg",
        "1000000111": here / "1000000111/art/v2h/robert_v2h_A_preview.jpg",
        "1000000112": here / "karmen_1000000112/art/v6/karmen_v6_preview.jpg",
        "none-yet": here / "person10/kids_group/v8_fixes/contact_sheet.jpg",
        # v12A vs v12B side by side so Derek can pick one
        "1000000100": here / "kristen_1000000100/art/v12/kristin_v12_compare.jpg",
        # latest proof (v3); keeps the old art/v2/work/v2e_* WIP previews from being picked
        "1000000107": here / "1000000107/art/v3/chase_v3_preview.jpg",
    }


def find_order_folder(here: Path, row: dict[str, str]) -> Path | None:
    order = row["order"]
    buyer = row["buyer"]
    first = buyer.split()[0].lower() if buyer else ""
    candidates: list[Path] = []
    mapped = FOLDER_MAP.get(order)
    if mapped:
        candidates.append(here / mapped)
    if order and order != "none-yet":
        candidates.append(here / order)
        if first:
            candidates.append(here / f"{first}_{order}")
        for d in here.iterdir():
            if d.is_dir() and order in d.name:
                candidates.append(d)
    if first:
        candidates.append(here / first)
    seen: set[Path] = set()
    for p in candidates:
        try:
            p = p.resolve()
        except OSError:
            continue
        if p in seen or not p.is_dir():
            continue
        seen.add(p)
        return p
    return None


def version_key(name: str) -> tuple[int, str]:
    m = VERSION_RE.match(name)
    if not m:
        return (0, name.lower())
    return (int(m.group(1)), (m.group(2) or "").lower())


def image_info(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image as PILImage
    except ImportError:
        return None
    try:
        with PILImage.open(path) as im:
            return im.size
    except Exception:
        return None


def ratio_str(path: Path) -> str:
    size = image_info(path)
    if not size:
        return "1/1"
    return f"{size[0]}/{size[1]}"



def make_contact_sheet(paths: list[Path], labels: list[str], out: Path) -> Path:
    """Compose a labeled grid of buyer photos for the Review queue (asset cap)."""
    from PIL import Image as PILImage, ImageDraw, ImageFont
    from math import ceil

    out.parent.mkdir(parents=True, exist_ok=True)
    n = len(paths)
    if n == 0:
        raise ValueError("no photos")
    if n == 1:
        # Just copy/convert a single photo
        with PILImage.open(paths[0]) as im:
            im.convert("RGB").save(out, "JPEG", quality=90)
        return out

    cols = 3 if n >= 3 else n
    rows = ceil(n / cols)
    cell_w, cell_h = 520, 640
    pad = 18
    label_h = 42
    bg = (247, 245, 240)
    width = cols * cell_w + (cols + 1) * pad
    height = rows * (cell_h + label_h) + (rows + 1) * pad
    canvas = PILImage.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    for i, (path, label) in enumerate(zip(paths, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        with PILImage.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((cell_w, cell_h), PILImage.Resampling.LANCZOS)
            ox = x + (cell_w - im.width) // 2
            oy = y + (cell_h - im.height) // 2
            canvas.paste(im, (ox, oy))
        # Centered label under the cell
        text = label[:42]
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        tx = x + max(0, (cell_w - tw) // 2)
        ty = y + cell_h + 8
        draw.text((tx, ty), text, fill=(40, 38, 36), font=font)
    canvas.save(out, "JPEG", quality=90)
    return out


def find_mockup(here: Path, folder: Path, row: dict[str, str]) -> Path | None:
    override = mockup_overrides(here).get(row["order"])
    if override and override.is_file():
        return override
    printify = sorted((folder / "printify").glob("printify_mockup_front*.png")) if (folder / "printify").is_dir() else []
    candidates: list[tuple[tuple, Path]] = []
    for p in folder.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in IMG_EXT:
            continue
        parts = {x.lower() for x in p.parts}
        if parts & SKIP_DIRS:
            continue
        name = p.name
        if SKIP_NAME_RE.search(name):
            continue
        if not PREVIEW_RE.search(name):
            continue
        is_preview = (
            "preview" in name.lower()
            or "contact_sheet" in name.lower()
            or "proof" in name.lower()
        )
        ver = (0, "")
        for part in p.parts:
            vk = version_key(part)
            if vk[0]:
                ver = max(ver, vk)
        score = (
            3 if "proof_final" in name.lower() else 2 if is_preview else 1,
            ver[0],
            ver[1],
            p.stat().st_mtime,
        )
        candidates.append((score, p))
    if not candidates:
        return printify[0] if printify else None
    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0][1]
    # A Printify product mockup made after the latest art is what Derek OKs.
    if printify and printify[0].stat().st_mtime >= best.stat().st_mtime:
        return printify[0]
    return best



def _photo_label(path: Path, folder: Path) -> str:
    stem = path.stem
    m = re.match(r"^([A-Za-z]+)[_-]?0*1$", stem)
    if m:
        return m.group(1).title()
    parent = path.parent.name.lower()
    if path.parent != folder and parent not in {"photos", "photo", "refs", "ref"}:
        return path.parent.name.replace("_", " ").title()
    return stem.replace("_", " ")


def find_photos(folder: Path) -> list[Path]:
    photos_dir = folder / "photos"
    found: list[Path] = []
    seen_sizes: set[int] = set()
    if photos_dir.is_dir():
        for p in sorted(photos_dir.iterdir(), key=lambda x: x.name.lower()):
            if p.is_file() and p.suffix.lower() in IMG_EXT:
                sz = p.stat().st_size
                if sz in seen_sizes:
                    continue
                seen_sizes.add(sz)
                found.append(p)
        if found:
            return found
    msgs_dir = folder / "buyer_msgs"
    if msgs_dir.is_dir():
        for p in sorted(msgs_dir.iterdir(), key=lambda x: x.name.lower()):
            if p.is_file() and p.suffix.lower() in IMG_EXT:
                found.append(p)
        if found:
            return found
    # Named portraits in the order root, e.g. person10/nadia_1.jpg
    preferred = ["person29", "person33", "person31", "person30", "person32", "person34", "person28"]
    root_portraits: list[Path] = []
    used_names: set[str] = set()
    for name in preferred:
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            cand = folder / f"{name}_1{ext}"
            if cand.is_file():
                root_portraits.append(cand)
                used_names.add(name)
                break
    if root_portraits:
        return root_portraits

    refs = folder / "kid_refs"
    if refs.is_dir():
        dirs = [d for d in refs.iterdir() if d.is_dir()]

        def dir_key(d: Path) -> tuple[int, str]:
            name = d.name.lower()
            return (preferred.index(name) if name in preferred else 99, name)

        for child in sorted(dirs, key=dir_key):
            imgs = sorted(
                [
                    p
                    for p in child.iterdir()
                    if p.is_file() and p.suffix.lower() in IMG_EXT
                ],
                key=lambda x: x.name.lower(),
            )
            if imgs:
                found.append(imgs[0])
        if found:
            return found
    return found


MAX_PAGE_ASSETS = 20
SLOT_DIRNAME = "_queue_assets"


def slot_asset_name(index: int) -> str:
    """Stable Page asset name, 1-based: rq-slot-01.jpg ... rq-slot-20.jpg."""
    if index < 1 or index > MAX_PAGE_ASSETS:
        raise ValueError(f"asset slot {index} is outside 1..{MAX_PAGE_ASSETS}")
    return f"rq-slot-{index:02d}.jpg"


def write_slot_jpeg(src: Path, dest: Path) -> Path:
    """Write src to dest as JPEG so every slot has a fixed .jpg name."""
    from PIL import Image as PILImage

    dest.parent.mkdir(parents=True, exist_ok=True)
    with PILImage.open(src) as im:
        im.convert("RGB").save(dest, "JPEG", quality=90)
    return dest


def requests_for(row: dict[str, str], folder: Path | None) -> tuple[list[dict[str, str]], str]:
    curated = REQUEST_CONTENT.get(row["order"])
    quotes: list[dict[str, str]] = []
    text_parts: list[str] = []
    if curated:
        quotes = list(curated.get("quotes") or [])
        if curated.get("text"):
            text_parts.append(str(curated["text"]))
    if folder and not curated:
        for name in (
            "requests.txt",
            "REQUESTS.md",
            "order_note.txt",
            "personalization.txt",
            "buyer_requests.txt",
        ):
            for p in folder.rglob(name):
                parts = {x.lower() for x in p.parts}
                if parts & {"art", "_work", "qa"}:
                    continue
                try:
                    body = p.read_text(encoding="utf-8").strip()
                except OSError:
                    continue
                if body:
                    text_parts.append(body)
        latest = (row.get("latest_request") or "").strip()
        if latest and latest.lower() != "unknown":
            text_parts.append(latest)
    return quotes, " ".join(text_parts).strip()


def build_queue(
    here: Path,
    rows: list[dict[str, str]],
    sort_rows,
) -> tuple[list[dict], list[dict[str, str]], list[str]]:
    """Return queue items, asset manifest rows, and missing-note strings."""
    items: list[dict] = []
    assets: list[dict[str, str]] = []
    missing: list[str] = []
    slot = 0
    slot_dir = here / SLOT_DIRNAME

    def alloc_slot() -> tuple[str, Path] | None:
        nonlocal slot
        slot += 1
        if slot > MAX_PAGE_ASSETS:
            return None
        name = slot_asset_name(slot)
        return name, slot_dir / name

    for row in sort_rows(rows):
        if row["status"] not in QUEUE_STATUSES:
            continue
        folder = find_order_folder(here, row)
        if folder is None:
            missing.append(
                f"{row['buyer']} ({row['order']}): no order folder found; left out of the queue."
            )
            continue
        mockup = find_mockup(here, folder, row)
        if mockup is None:
            missing.append(
                f"{row['buyer']} ({row['order']}): folder {folder} has no mockup; left out of the queue."
            )
            continue
        photos = find_photos(folder)
        if not photos:
            missing.append(
                f"{row['buyer']} ({row['order']}): no reference photos found in {folder}/photos."
            )
        quotes, request_text = requests_for(row, folder)
        if not quotes and not request_text:
            missing.append(
                f"{row['buyer']} ({row['order']}): no buyer request text found."
            )
        mockup_slot = alloc_slot()
        if mockup_slot is None:
            missing.append(
                f"{row['buyer']} ({row['order']}): no free Page image slot "
                f"(max {MAX_PAGE_ASSETS}); left out of the queue."
            )
            continue
        m_name, m_dest = mockup_slot
        write_slot_jpeg(mockup, m_dest)
        assets.append(
            {
                "name": m_name,
                "path": str(m_dest),
                "role": "mockup",
                "buyer": row["buyer"],
                "source": str(mockup),
            }
        )
        photo_items = []
        if photos:
            photo_slot = alloc_slot()
            if photo_slot is None:
                missing.append(
                    f"{row['buyer']} ({row['order']}): no free Page image slot "
                    f"for reference photos (max {MAX_PAGE_ASSETS})."
                )
            else:
                pname, sheet_path = photo_slot
                labels = [_photo_label(p, folder) for p in photos]
                if len(photos) == 1:
                    write_slot_jpeg(photos[0], sheet_path)
                else:
                    make_contact_sheet(photos, labels, sheet_path)
                assets.append(
                    {
                        "name": pname,
                        "path": str(sheet_path),
                        "role": "photo",
                        "buyer": row["buyer"],
                        "source": ", ".join(str(p) for p in photos),
                    }
                )
                alt = (
                    f"Reference photos for {row['buyer']}"
                    if len(photos) > 1
                    else f"Reference photo for {row['buyer']}: {photos[0].name}"
                )
                photo_items.append(
                    {
                        "src": f"asset:{pname}",
                        "alt": alt,
                        "ratio": ratio_str(sheet_path),
                        "source_count": str(len(photos)),
                        "source_files": ", ".join(str(p) for p in photos),
                    }
                )
        items.append(
            {
                "order": row["order"],
                "buyer": row["buyer"],
                "whatTheyGot": row["what_they_got"],
                "status": row["status"],
                "mockupSrc": f"asset:{m_name}",
                "mockupAlt": f"Latest mockup for {row['buyer']}, {row['what_they_got']}",
                "mockupRatio": ratio_str(m_dest),
                "mockupFile": str(mockup),
                "photos": photo_items,
                "quotes": quotes,
                "requestText": request_text,
            }
        )
    return items, assets, missing
