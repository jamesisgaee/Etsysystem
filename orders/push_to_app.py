#!/usr/bin/env python3
"""
push_to_app.py — sends the order board to Derek's Viva Orders app.

Run on the box (Python 3.8+, no extra packages needed; uses Pillow to shrink
images if it's installed).

  python3 push_to_app.py                 # push all orders + images (run after every tracker edit)
  python3 push_to_app.py --dry-run       # show what would be sent, send nothing
  python3 push_to_app.py pending [--bot Messanger]   # list Derek's decisions not done yet
  python3 push_to_app.py show <decision_id>          # confirm one decision is real
  python3 push_to_app.py ack <decision_id> --by Messanger --note "sent to buyer" [--done]

Settings come from environment variables, or from the file
/workspace/orders/.viva_app (lines like KEY=value, keep it chmod 600):
  VIVA_APP_URL    e.g. https://viva-orders.yourname.workers.dev
  VIVA_BOT_TOKEN  the BOT_TOKEN secret you set in Cloudflare
  VIVA_ORDERS_DIR optional, default /workspace/orders

What it reads:
  ORDER_TRACKER.csv              one row per order (unchanged format)
  <order folder>/app.json        small file the bots fill in (see FORMATS.md)
  <order folder>/photos/ or buyer_msgs/   buyer photos (auto)
  <order folder>/art/v*/         mockup previews for the history (auto)
  <order folder>/app.json messages, buyer_msgs/, messages/
                                 recent buyer/shop messages (last 30, auto)
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo('America/Los_Angeles')
except Exception:
    PT = None

try:
    from PIL import Image, ImageOps  # optional
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

STATUS_TO_STAGE = {
    "Problem": "problem",
    "Waiting for Derek": "needs_ok",
    "Needs mockup": "artist",
    "Waiting on buyer": "waiting_buyer",
    "Approved - ordering": "ordering",
    "In production": "printing",
    "Shipped": "shipped",
    "Delivered": "delivered",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIDE = 1200
MAX_PHOTOS = 8
MAX_VERSIONS = 8
MAX_MESSAGES = 30
MAX_MESSAGE_TEXT = 4000
SKIP_DIRS = {"STYLE_GUIDES", "_work", "raw", "ref", "__pycache__"}
# app.json keys copied straight onto the order (anything else is ignored)
APP_JSON_FIELDS = [
    "artist_bot", "printify_order_id", "printify_est_ship", "tracking_carrier", "tracking_number",
    "tracking_note", "etsy_net", "printify_cost", "stage_since",
]
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

warnings = []


def warn(msg):
    warnings.append(msg)


# ---------------------------------------------------------------- settings

def load_settings(args):
    orders_dir = os.environ.get("VIVA_ORDERS_DIR") or args.orders_dir or "/workspace/orders"
    cfg = {}
    cfg_file = os.path.join(orders_dir, ".viva_app")
    if os.path.exists(cfg_file):
        with open(cfg_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    url = os.environ.get("VIVA_APP_URL") or cfg.get("VIVA_APP_URL", "")
    token = os.environ.get("VIVA_BOT_TOKEN") or cfg.get("VIVA_BOT_TOKEN", "")
    return orders_dir, url.rstrip("/"), token


# ---------------------------------------------------------------- http

def http(method, url, token, body=None, content_type="application/json", timeout=60):
    data = None
    if body is not None:
        data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("User-Agent", "viva-push/1.0")
    if data is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(text).get("error", text)
        except Exception:
            msg = text[:300]
        raise SystemExit(f"ERROR: the app answered {e.code} for {method} {url}: {msg}")
    except urllib.error.URLError as e:
        raise SystemExit(f"ERROR: couldn't reach the app at {url}: {e.reason}")


# ---------------------------------------------------------------- folders

def index_folders(orders_dir):
    """Map order ids and buyer names to folders. app.json order_id wins, then a number in
    the folder name, then the folder name equal to the buyer's first name (only if unique)."""
    by_id, by_name, apps = {}, {}, {}
    for name in sorted(os.listdir(orders_dir)):
        path = os.path.join(orders_dir, name)
        if not os.path.isdir(path) or name.startswith(".") or name in SKIP_DIRS:
            continue
        app = read_app_json(path)
        apps[path] = app
        if app and app.get("order_id"):
            by_id[str(app["order_id"])] = path
        for num in re.findall(r"\d{6,}", name):
            by_id.setdefault(num, path)
        base = re.sub(r"[_\-]?\d{6,}$", "", name).lower()
        if base:
            by_name.setdefault(base, []).append(path)
    return by_id, by_name, apps


def read_app_json(folder):
    p = os.path.join(folder, "app.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception as e:
        warn(f"{p} isn't valid JSON ({e}); ignored it.")
        return None


def find_folder(order_id, first_name, by_id, by_name):
    if order_id in by_id:
        return by_id[order_id]
    cands = by_name.get((first_name or "").lower(), [])
    return cands[0] if len(cands) == 1 else None


def resolve(folder, rel):
    if not rel:
        return None
    p = rel if os.path.isabs(rel) else os.path.join(folder or "", rel)
    return p if os.path.isfile(p) else None


def list_images(folder):
    if not folder or not os.path.isdir(folder):
        return []
    out = []
    for n in sorted(os.listdir(folder)):
        if os.path.splitext(n)[1].lower() in IMAGE_EXTS and not n.startswith("."):
            out.append(os.path.join(folder, n))
    return out


# ---------------------------------------------------------------- images

class Images:
    """Turns local files into small JPGs named by content hash, remembering work between runs."""

    def __init__(self, orders_dir):
        self.cache_path = os.path.join(orders_dir, ".viva_push_cache.json")
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                self.cache = json.load(f)
        except Exception:
            self.cache = {}
        self.pending = {}  # key -> (bytes or path)
        self.used = set()

    def key_for(self, path):
        if not path:
            return None
        try:
            st = os.stat(path)
        except OSError:
            return None
        sig = f"{st.st_mtime_ns}:{st.st_size}"
        hit = self.cache.get(path)
        if hit and hit.get("sig") == sig:
            self.used.add(path)
            self.pending.setdefault(hit["key"], path)
            return hit["key"]
        data, ext = self._prepare(path)
        if data is None:
            return None
        key = hashlib.sha256(data).hexdigest() + ext
        self.cache[path] = {"sig": sig, "key": key}
        self.used.add(path)
        self.pending[key] = data
        return key

    def _prepare(self, path):
        ext = os.path.splitext(path)[1].lower()
        if HAVE_PIL:
            try:
                with Image.open(path) as im:
                    im = ImageOps.exif_transpose(im)
                    im.thumbnail((MAX_SIDE, MAX_SIDE))
                    if im.mode not in ("RGB", "L"):
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        im = im.convert("RGBA")
                        bg.paste(im, mask=im.split()[-1])
                        im = bg
                    buf = io.BytesIO()
                    im.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)
                    return buf.getvalue(), ".jpg"
            except Exception as e:
                warn(f"Couldn't read image {path} ({e}); skipped it.")
                return None, None
        with open(path, "rb") as f:
            data = f.read()
        if len(data) > 14_000_000:
            warn(f"{path} is over 14 MB and Pillow isn't installed to shrink it; skipped it.")
            return None, None
        return data, {".jpeg": ".jpg"}.get(ext, ext)

    def bytes_for(self, key):
        v = self.pending.get(key)
        if isinstance(v, (bytes, bytearray)):
            return v
        if isinstance(v, str):
            data, _ = self._prepare(v)
            return data
        return None

    def save_cache(self):
        keep = {p: v for p, v in self.cache.items() if p in self.used}
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(keep, f)
        except OSError:
            pass


# ---------------------------------------------------------------- parsing helpers

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Phone numbers written with separators, e.g. (555) 123-4567 or 555.123.4567. Plain 10-digit
# runs are left alone because Etsy order numbers look exactly like that.
PHONE_RE = re.compile(r"(?<![\w.])(?:\+?1[\s.-])?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?!\w)")


def clean_text(s):
    """Keep private details out of the app: drop emails and phone numbers."""
    if not s:
        return s
    s = EMAIL_RE.sub("[email removed]", s)
    return PHONE_RE.sub("[phone removed]", s)


def parse_date(s):
    s = (s or "").strip()
    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None


def parse_month_day(text, ref_year):
    """'est ship Nov 27-29' -> '2026-11-27' (first day of a range)."""
    m = re.search(r"est(?:imated)?\.?\s*ship(?:s|ping)?\s*(?:date)?[:\s]+([A-Za-z]{3,9})\.?\s+(\d{1,2})", text or "", re.I)
    if not m:
        return None
    mon = MONTHS.get(m.group(1)[:3].lower())
    if not mon:
        return None
    try:
        return date(ref_year, mon, int(m.group(2))).isoformat()
    except ValueError:
        return None



def _truthy(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _hidden_from_app(app, raw_id, folder, first):
    """hide_from_app on a shared folder must not hide a real Etsy order too.

    If the value is true, only a quote row (order none-yet / none / n/a, or no
    id) is hidden. A list or comma-separated string hides only those ids
    (Etsy numbers or quote-<folder> slugs).
    """
    if not app:
        return False
    flag = app.get("hide_from_app")
    if flag is None or flag is False or flag == "":
        return False
    raw = (raw_id or "").strip()
    is_quote = (not raw) or raw.lower() in ("none-yet", "none", "n/a")
    slug = os.path.basename(folder) if folder else (first or "unknown")
    quote_id = "quote-" + re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    order_id = quote_id if is_quote else raw
    if isinstance(flag, (list, tuple)):
        ids = {str(x).strip() for x in flag if str(x).strip()}
        return order_id in ids or raw in ids
    if isinstance(flag, str) and not _truthy(flag):
        ids = {x.strip() for x in flag.split(",") if x.strip()}
        return order_id in ids or raw in ids
    if _truthy(flag):
        return is_quote
    return False

def parse_tracking(s):
    s = (s or "").strip()
    if not s or s.lower() == "none":
        return None, None, None
    m = re.match(r"^\s*([A-Za-z]+)\s+([A-Za-z0-9]{8,40})\s*(?:\((.*)\))?\s*$", s)
    if m:
        return m.group(1).upper(), m.group(2), (m.group(3) or None)
    m = re.search(r"([A-Za-z0-9]{10,40})", s)
    return (None, m.group(1), None) if m else (None, None, s)


def split_updated(s):
    s = (s or "").strip()
    for sep in (" — ", " – ", " - "):
        if sep in s:
            a, b = s.rsplit(sep, 1)
            return a.strip(), b.strip()
    return s or None, None


def version_label(path, version):
    """eddie_v1B_preview.jpg + v1 -> 'B'; compare sheets -> 'compare'."""
    n = os.path.basename(path).lower()
    if "vs_photo" in n or "compare" in n or "contact_sheet" in n:
        return "compare"
    m = re.search(re.escape(version.lower()) + r"([a-z])(?:[_\-.]|$)", n)
    return m.group(1).upper() if m else ""


# ---------------------------------------------------------------- build one order

def _vnum(v):
    m = re.match(r"v(\d+)", str(v or ""), re.I)
    return int(m.group(1)) if m else None


def unpushed_art_warning(folder, app, stage, first, order_id, now=None):
    """Person22 case: finished previews in art/vN sat on disk for a day while the app showed nothing.
    Warn when the newest art/vN preview is newer than the version Derek can see and is >45 min old."""
    if stage != "artist" or not folder:
        return None
    art = os.path.join(folder, "art")
    if not os.path.isdir(art):
        return None
    best = None
    for d in os.listdir(art):
        n = _vnum(d)
        if n is None or not os.path.isdir(os.path.join(art, d)):
            continue
        prev = [p for p in list_images(os.path.join(art, d)) if re.search(r"preview", os.path.basename(p), re.I)]
        if prev and (best is None or n > best[0]):
            best = (n, d, max(os.path.getmtime(p) for p in prev))
    if not best:
        return None
    review = (app or {}).get("review") if isinstance((app or {}).get("review"), dict) else {}
    shown = _vnum(review.get("version")) if review else None
    age_min = ((now or time.time()) - best[2]) / 60
    if (shown is None or best[0] > shown) and age_min > 45:
        return (f"{first} ({order_id}): finished-looking art {best[1]} preview has been on disk {age_min / 60:.1f} h "
                f"but Derek can't see it (status Needs mockup, app shows {review.get('version') or 'nothing'}). "
                f"If it's ready, put it in app.json review, set 'Waiting for Derek' and push.")
    return None


def build_order(row, folder, app, imgs, decided=None):
    raw_id = (row.get("order") or "").strip()
    first = (row.get("buyer") or "").strip().split(" ")[0]
    status = (row.get("status") or "").strip()
    latest = clean_text((row.get("latest_request") or "").strip())
    nxt = clean_text((row.get("next_step") or "").strip())

    if not raw_id or raw_id.lower() in ("none-yet", "none", "n/a"):
        slug = os.path.basename(folder) if folder else (first or "unknown")
        order_id = "quote-" + re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    else:
        order_id = raw_id

    stage = STATUS_TO_STAGE.get(status)
    if stage is None:
        warn(f"{first} ({order_id}): unknown status '{status}' — shown as Something's wrong.")
        stage = "problem"
    # Old quirk: proof already sent but status left at "Needs mockup".
    sent_to_buyer = latest.lower().startswith("sent") or re.search(r"buyer'?s? (ok|approval)", nxt, re.I) or (
        first and re.search(r"\bsent to (?:the buyer|" + re.escape(first) + r")\b", latest, re.I)
        and re.match(r"\s*" + re.escape(first) + r"(?:'s)? (?:ok|approval|reply|answer)\b", nxt, re.I))
    if stage == "artist" and sent_to_buyer:
        stage = "waiting_buyer"
        warn(f"{first} ({order_id}): status says 'Needs mockup' but the proof looks sent; shown as Waiting on buyer. Please fix the status.")

    ship_by = parse_date(row.get("ship_by"))
    ref_year = int(ship_by[:4]) if ship_by else date.today().year
    carrier, number, tnote = parse_tracking(row.get("tracking"))
    updated_at, updated_by = split_updated(row.get("updated"))

    m = re.search(r"Printify\s*(?:order)?\s*#?\s*(\d{5,}\.\d+)", f"{nxt} {latest}", re.I)
    order = {
        "order_id": order_id,
        "buyer_first_name": first,
        "product": (row.get("what_they_got") or "").strip(),
        "status": status,
        "stage": stage,
        "latest_request": latest,
        "next_step": nxt,
        "ship_by": ship_by,
        "printify_order_id": m.group(1) if m else None,
        "printify_est_ship": parse_month_day(f"{nxt} {latest}", ref_year),
        "tracking_carrier": carrier,
        "tracking_number": number,
        "tracking_note": tnote,
        "artist_bot": None,
        "updated_at": updated_at,
        "updated_by": updated_by,
    }
    work = re.match(r"WORKING NOW:\s*(Designer(?: \d)?)", nxt)
    if work:
        order["artist_bot"] = work.group(1)

    app = app or {}
    for k in APP_JSON_FIELDS:
        if app.get(k) not in (None, ""):
            order[k] = app[k]
    if order.get("printify_est_ship") and not parse_date(str(order["printify_est_ship"])):
        warn(f"{first}: printify_est_ship must be YYYY-MM-DD; ignored '{order['printify_est_ship']}'.")
        order["printify_est_ship"] = None
    for k in ("etsy_net", "printify_cost"):
        if order.get(k) is not None:
            try:
                order[k] = float(order[k])
            except (TypeError, ValueError):
                order[k] = None
    if order.get("stage_since") is None:
        order.pop("stage_since", None)

    # Buyer photos
    photo_files = []
    if folder:
        for sub in ("photos", "buyer_msgs"):
            photo_files += list_images(os.path.join(folder, sub))
    photos = [k for k in (imgs.key_for(p) for p in photo_files[:MAX_PHOTOS]) if k]
    order["photos"] = photos

    # Version history (display only)
    order["versions"] = build_versions(folder, app, imgs)

    # Buyer / shop message history (last 30), for the approve screen
    order["messages"] = build_messages(folder, app, imgs)

    # What Derek reviews — only from app.json, never guessed
    review = app.get("review") if isinstance(app.get("review"), dict) else None
    # Never hide a proof Derek hasn't decided on (the Person22 case: an artist set "Needs mockup" to start
    # the next version and the undecided card vanished). `decided` = review keys the app already has a
    # decision for; None means we couldn't ask the app, so keep the old behaviour.
    if (stage == "artist" and review and decided is not None and review.get("kind") and review.get("options")
            and not _truthy(review.get("withdrawn"))):
        key = f"{order_id}|{review.get('kind')}|{review.get('version') or ''}"
        if key not in decided:
            stage = "needs_ok"
            order["stage"] = stage
            order["status"] = "Waiting for Derek"
            order["artist_working"] = True
            warn(f"{first} ({order_id}): tracker says 'Needs mockup' but {review.get('version')} is still waiting for "
                 f"Derek's tap, so it stays on his Approve screen. If Derek already answered it in chat, set "
                 f"\"withdrawn\": true in app.json review (or post the new version).")
    if stage == "artist":
        w = unpushed_art_warning(folder, app, stage, first, order_id)
        if w:
            warn(w)
    if stage == "needs_ok":
        if not review:
            warn(f"{first} ({order_id}) is 'Waiting for Derek' but app.json has no review — Derek can't approve it.")
            order["review"] = {"kind": "art_proof", "version": None, "options": [], "photos": photos}
        else:
            order["review"] = build_review(review, folder, imgs, photos, order, first, order_id)
    else:
        order["review"] = None
    return order


def build_review(review, folder, imgs, photos, order, first, order_id):
    kind = review.get("kind")
    if kind not in ("art_proof", "printify_mockup"):
        warn(f"{first} ({order_id}): review.kind must be art_proof or printify_mockup; used art_proof.")
        kind = "art_proof"
    options = []
    for opt in review.get("options") or []:
        if isinstance(opt, str):
            opt = {"file": opt}
        path = resolve(folder, opt.get("file"))
        if not path:
            warn(f"{first} ({order_id}): review option file not found: {opt.get('file')}")
            continue
        key = imgs.key_for(path)
        if key:
            options.append({"label": opt.get("label") or None, "image": key, "source_path": os.path.abspath(path)})
    if len(options) > 1 and any(not o["label"] for o in options):
        for i, o in enumerate(options):
            o["label"] = o["label"] or "ABCDEFG"[i]
    if not options:
        warn(f"{first} ({order_id}): no review images found — Derek can't approve it yet.")
    rphotos = [k for k in (imgs.key_for(resolve(folder, p)) for p in (review.get("photos") or [])) if k] or photos
    compare = imgs.key_for(resolve(folder, review.get("compare"))) if review.get("compare") else None
    previous = imgs.key_for(resolve(folder, review.get("previous"))) if review.get("previous") else None
    try:
        rnd = int(review["round"]) if review.get("round") else None
    except (TypeError, ValueError):
        rnd = None
    return {
        "kind": kind,
        "version": review.get("version"),
        "artist_bot": review.get("artist_bot") or order.get("artist_bot"),
        "note": clean_text(review.get("note")),
        "options": options,
        "photos": rphotos,
        "compare": compare,
        # Round 2+: the buyer asked for changes after seeing an approved proof.
        "round": rnd,
        "buyer_feedback": clean_text(review.get("buyer_feedback")),
        "previous": previous,
    }


def build_versions(folder, app, imgs):
    if isinstance(app.get("versions"), list):
        out = []
        for v in app["versions"][-MAX_VERSIONS:]:
            if not isinstance(v, dict):
                continue
            images = []
            for im in v.get("images") or []:
                if isinstance(im, str):
                    im = {"file": im}
                k = imgs.key_for(resolve(folder, im.get("file")))
                if k:
                    images.append({"label": im.get("label") or "", "image": k})
            out.append({"version": v.get("version"), "made_by": v.get("made_by"), "note": clean_text(v.get("note")), "images": images})
        return out
    # Automatic: art/v1, art/v2, ... previews and compare sheets
    art = os.path.join(folder or "", "art")
    if not folder or not os.path.isdir(art):
        return []
    vdirs = [d for d in os.listdir(art) if re.fullmatch(r"v\d+", d) and os.path.isdir(os.path.join(art, d))]
    vdirs.sort(key=lambda d: int(d[1:]))
    out = []
    for vd in vdirs[-MAX_VERSIONS:]:
        files = [p for p in list_images(os.path.join(art, vd))
                 if re.search(r"preview|vs_photo|compare", os.path.basename(p), re.I)]
        images = []
        for p in files[:5]:
            k = imgs.key_for(p)
            if k:
                images.append({"label": version_label(p, vd), "image": k})
        if images:
            out.append({"version": vd, "made_by": None, "note": None, "images": images})
    return out



# ---------------------------------------------------------------- buyer messages

SCREENSHOT_NAME_RE = re.compile(
    r"(thread|msgs?|messages?|chat|screenshot|screen[_-]?shot|convo|conversation|^img_\d+|^image_\d+)",
    re.I,
)
MSG_HEADER_RE = re.compile(
    r"^\s*(?:\d+\.\s*)?(?:\#{1,6}\s*|[-*=]{3,}\s*)?\*{0,2}\s*"
    r"(?:\[(?P<at1>[^\]]{1,80})\]\s*)?"
    r"(?P<who>Buyer|Customer|Client|Shop|Seller|Derek|Viva(?:\s*Memoir(?:\s*Studio)?)?)"
    r"(?:\s*\([^)]{0,60}\))?\*{0,2}"
    r"(?:\s*[,:\u2014-]\s*|\s+)"
    r"(?:newest message,\s*)?"
    r"(?P<at2>[^\n]{0,80}?)"
    r"\s*:?\s*$",
    re.I,
)
# [2026-11-21 5:47 PM PT] Buyer: optional same-line text
BRACKET_HEADER_RE = re.compile(
    r"""^\s*\[(?P<at>[^\]]{1,80})\]\s*
        (?P<who>Buyer|Customer|Client|Shop|Seller|Derek|Viva(?:\s*Memoir(?:\s*Studio)?)?)\s*:
        \s*(?P<rest>.*)$
    """,
    re.I | re.X,
)
SEP_RE = re.compile(r"^\s*={3,}.*={3,}\s*$")
WHO_MAP = {
    "buyer": "buyer", "customer": "buyer", "client": "buyer",
    "shop": "shop", "seller": "shop", "derek": "shop",
    "viva": "shop", "viva memoir": "shop", "viva memoir studio": "shop",
}


def format_pt(ts):
    """Format a unix timestamp in the user's Pacific Time."""
    if ts is None:
        return None
    try:
        dt = datetime.fromtimestamp(float(ts), PT or timezone.utc)
        hour = dt.strftime("%I").lstrip("0") or "0"
        label = "PT" if PT else "UTC"
        return f"{dt.strftime('%Y-%m-%d')} {hour}:{dt.strftime('%M %p')} {label}"
    except (OSError, ValueError, OverflowError, TypeError):
        return None


def parse_at_ts(at, fallback=0):
    """Best-effort parse of a message timestamp into a sortable unix time.

    If a string has both an Eastern and a Pacific time, the PT time wins so
    "8:47pm EST / 5:47 PM PT" sorts as 5:47 PM Pacific, not 8:47.
    """
    if not at:
        return fallback
    s = str(at).strip()
    s = s.replace(" at ", " ").replace(" — ", " ").replace(" – ", " ").replace(" - ", " ")

    tz_names = {
        "PT": "America/Los_Angeles", "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
        "ET": "America/New_York", "EST": "America/New_York", "EDT": "America/New_York",
        "CT": "America/Chicago", "CST": "America/Chicago", "CDT": "America/Chicago",
        "MT": "America/Denver", "MST": "America/Denver", "MDT": "America/Denver",
        "UTC": "UTC", "GMT": "UTC",
    }

    def zone(name):
        key = (name or "PT").upper()
        if PT and key in tz_names:
            try:
                from zoneinfo import ZoneInfo
                return ZoneInfo(tz_names[key])
            except Exception:
                pass
        return PT or timezone.utc

    # ISO first (2026-11-21T17:47:00 or 2026-11-21 5:47 PM PT)
    iso = s.replace("Z", "+00:00")
    if re.match(r"\d{4}-\d{2}-\d{2} ", iso):
        iso_try = re.sub(r"(\d{4}-\d{2}-\d{2}) ", r"\1T", iso, count=1)
        # strip trailing zone abbreviations for fromisoformat
        iso_cut = re.sub(r"\s*(PT|PST|PDT|ET|EST|EDT|CT|CST|CDT|MT|MST|MDT|UTC|GMT)\s*$", "", iso_try, flags=re.I)
        try:
            dt = datetime.fromisoformat(iso_cut.strip())
            if dt.tzinfo is None:
                # use any zone suffix we stripped
                zm = re.search(r"(PT|PST|PDT|ET|EST|EDT|CT|CST|CDT|MT|MST|MDT|UTC|GMT)\s*$", iso_try, re.I)
                dt = dt.replace(tzinfo=zone(zm.group(1) if zm else "PT"))
            return dt.timestamp()
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=PT or timezone.utc)
        return dt.timestamp()
    except ValueError:
        pass

    # Date like "Sat, Nov 21" or "Nov 22, 2026"
    dm = re.search(
        r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*,?\s+)?([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:,?\s*(\d{4}))?",
        s, re.I,
    )
    iso_m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    year = date.today().year
    mon = day = None
    if iso_m:
        year, mon, day = (int(x) for x in iso_m.group(1).split("-"))
    elif dm:
        mon = MONTHS.get(dm.group(1)[:3].lower())
        day = int(dm.group(2))
        year = int(dm.group(3) or year)

    # Prefer a clock time labeled PT when several times appear
    clocks = list(re.finditer(
        r"(\d{1,2}:\d{2}\s*[AP]M)(?:\s*(PT|PST|PDT|ET|EST|EDT|CT|CST|CDT|MT|MST|MDT|UTC|GMT))?",
        s, re.I,
    ))
    clock = None
    if clocks:
        pt = [c for c in clocks if (c.group(2) or "").upper() in ("PT", "PST", "PDT")]
        clock = (pt or clocks)[0]

    if mon and day:
        try:
            if clock:
                tm = datetime.strptime(clock.group(1).upper().replace(" ", ""), "%I:%M%p")
                dt = datetime(year, mon, day, tm.hour, tm.minute, tzinfo=zone(clock.group(2)))
            else:
                dt = datetime(year, mon, day, 12, 0, tzinfo=PT or timezone.utc)
            return dt.timestamp()
        except ValueError:
            pass

    # Time only, e.g. "11:37 PM" — use fallback's date when it looks like a timestamp
    if clock:
        try:
            tm = datetime.strptime(clock.group(1).upper().replace(" ", ""), "%I:%M%p")
            if fallback and fallback > 100000:
                base = datetime.fromtimestamp(float(fallback), zone(clock.group(2)))
                dt = base.replace(hour=tm.hour, minute=tm.minute, second=0, microsecond=0)
            else:
                dt = datetime.now(zone(clock.group(2))).replace(hour=tm.hour, minute=tm.minute, second=0, microsecond=0)
            return dt.timestamp()
        except (ValueError, OSError, OverflowError):
            pass
    return fallback



def normalize_from(value):
    s = re.sub(r"\s+", " ", str(value or "").strip().lower())
    s = re.sub(r"\s*\(.*\)$", "", s).strip()
    return WHO_MAP.get(s) or WHO_MAP.get(s.split()[0] if s else "")


def coerce_message(item, imgs, folder):
    """Turn an app.json / messages.json entry into {from, at, text, image} or None."""
    if isinstance(item, str):
        item = {"from": "buyer", "text": item}
    if not isinstance(item, dict):
        return None
    frm = normalize_from(item.get("from") or item.get("sender") or item.get("who")) or "buyer"
    if frm not in ("buyer", "shop"):
        frm = "buyer"
    at = item.get("at") or item.get("time") or item.get("date") or item.get("timestamp")
    at = clean_text(str(at).strip())[:80] if at not in (None, "") else None
    text = item.get("text") or item.get("body") or item.get("message") or ""
    text = clean_text(str(text).strip())[:MAX_MESSAGE_TEXT] if text else None
    image = None
    rel = item.get("file") or item.get("image_file")
    # image may be a local path or (rarely) an already-hashed key
    raw_img = item.get("image")
    if isinstance(rel, str) or (isinstance(raw_img, str) and not re.fullmatch(r"[a-f0-9]{64}\.(jpg|png|webp)", raw_img)):
        path = resolve(folder, rel or raw_img)
        if path:
            image = imgs.key_for(path)
    elif isinstance(raw_img, str) and re.fullmatch(r"[a-f0-9]{64}\.(jpg|png|webp)", raw_img):
        image = raw_img
    if not text and not image:
        return None
    out = {"from": frm}
    if at:
        out["at"] = at
    if text:
        out["text"] = text
    if image:
        out["image"] = image
    return out


def parse_messages_text(raw, default_from="buyer"):
    """Parse a transcript into message dicts. Supports a few formats Messanger already uses."""
    if not raw or not raw.strip():
        return []
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    messages = []

    def tidy_body(body):
        body = (body or "").strip()
        # Drop trailing capture notes the transcriber added after the real message
        body = re.split(
            r"\n\s*(?:Images:|(?:The buyer's open order|NO LATER MESSAGES|Captured read-only)\b)",
            body, maxsplit=1, flags=re.I,
        )[0].strip()
        # Unwrap a single surrounding quote
        if len(body) >= 2 and body[0] in "\"“'" and body[-1] in "\"”'":
            body = body[1:-1].strip()
        return clean_text(body)[:MAX_MESSAGE_TEXT]

    def flush(who, at, body):
        body = tidy_body(body)
        if not body:
            return
        if len(body) < 8 and not re.search(r"[.!?]", body):
            return
        # Skip file headers / capture notes that aren't a real buyer or shop message
        if re.search(r"captured read-only|buyer message thread|timestamp note:|transcribed from", body, re.I) and not re.search(
            r"\b(Hi[, ]|Hello|Thank you|Please|Can you)\b", body, re.I
        ):
            return
        if at:
            at = re.sub(r"[*]+", "", str(at))
            at = re.sub(r",?\s*quoted verbatim\s*$", "", at, flags=re.I).strip(" ,:—-")
            at = clean_text(at)[:80] or None
        msg = {"from": who or default_from, "text": body}
        if at:
            msg["at"] = at
        messages.append(msg)

    # Format 1: ==== separator blocks (Person10 Nov 21 style)
    if sum(1 for ln in lines if SEP_RE.match(ln)) >= 2:
        chunks, cur = [], []
        for ln in lines:
            if SEP_RE.match(ln):
                if cur:
                    chunks.append(cur)
                cur = [ln]
            else:
                cur.append(ln)
        if cur:
            chunks.append(cur)
        last_at = None
        for chunk in chunks:
            header = next((ln for ln in chunk if SEP_RE.match(ln)), "")
            if not header:
                continue  # preamble before the first ====
            body = "\n".join(ln for ln in chunk if not SEP_RE.match(ln))
            at = None
            who = default_from
            hm = re.search(r"\[([^\]]{1,80})\]", header)
            if hm:
                at = hm.group(1).strip()
            who_m = re.search(r"\b(buyer|shop|seller|customer|derek)\b", header, re.I)
            if who_m:
                who = normalize_from(who_m.group(1)) or who
            if at:
                last_at = at
            flush(who, at or last_at, body)
        if messages:
            return messages

    # Format 2: [date] Buyer: / Buyer, date: headers
    who = at = None
    body = []
    started = False
    for ln in lines:
        bm = BRACKET_HEADER_RE.match(ln)
        hm = None if bm else MSG_HEADER_RE.match(ln)
        if bm or hm:
            if started:
                flush(who, at, "\n".join(body))
            started = True
            body = []
            if bm:
                who = normalize_from(bm.group("who")) or default_from
                at = (bm.group("at") or "").strip() or None
                rest = (bm.group("rest") or "").strip()
                if rest:
                    body.append(rest)
            else:
                who = normalize_from(hm.group("who")) or default_from
                at = (hm.group("at1") or hm.group("at2") or "").strip(" ,:—-") or None
            continue
        if started:
            body.append(ln)
    if started:
        flush(who, at, "\n".join(body))
        if messages:
            return messages

    # Format 3: one quoted block after a "Buyer" / "quoted verbatim" intro (Person10 Nov 22)
    qm = re.search(
        r'(?:Buyer|Shop)[^\n]{0,120}\n+.*?[“"]{1,3}\s*(.+?)\s*[”"]{1,3}\s*$',
        text, re.I | re.S,
    )
    if qm and len(qm.group(1).strip()) > 40:
        who = "buyer" if re.search(r"\bbuyer\b", text[: qm.start(1)], re.I) else default_from
        at_m = re.search(r"(\d{1,2}:\d{2}\s*[AP]M(?:\s*PT)?|\w{3},?\s+\w+\s+\d{1,2}[^\n]{0,40})", text[: qm.start(1)], re.I)
        flush(who, at_m.group(1) if at_m else None, qm.group(1).strip())
        if messages:
            return messages

    # Fallback: the whole file is one message
    body = text.strip()
    # Strip a short title line if the rest is the message
    parts = body.split("\n", 2)
    if parts and re.search(r"message thread|etsy message|transcribed from|captured read-only", parts[0], re.I):
        body = "\n".join(parts[1:]).strip() or body
    flush(default_from, None, body)
    return messages


def iter_message_files(folder):
    """Yield (path, kind) for known message files. kind is 'json', 'text', or 'image'."""
    if not folder or not os.path.isdir(folder):
        return
    candidates = []

    def add_dir(path, images="screenshots_only"):
        if not path or not os.path.isdir(path):
            return
        for n in sorted(os.listdir(path)):
            if n.startswith("."):
                continue
            fp = os.path.join(path, n)
            if not os.path.isfile(fp):
                continue
            ext = os.path.splitext(n)[1].lower()
            low = n.lower()
            if low in ("buyer_notes.txt", "notes.txt", "readme.txt", "readme.md"):
                continue
            if ext == ".json" and (low == "messages.json" or low.endswith("_messages.json")):
                candidates.append((fp, "json"))
            elif ext in {".txt", ".md"} and (
                low in ("messages.txt", "messages.md", "thread.txt", "chat.txt")
                or low.endswith("_messages.txt")
            ):
                candidates.append((fp, "text"))
            elif ext in IMAGE_EXTS and images in ("all", "screenshots_only"):
                if images == "all" or SCREENSHOT_NAME_RE.search(low):
                    candidates.append((fp, "image"))

    add_dir(folder, images="none")
    # Root-level messages.txt / messages.json only (already handled: images="none")
    # Re-scan root for the named files; add_dir with images=none still picks json/text
    add_dir(os.path.join(folder, "buyer_msgs"), images="screenshots_only")
    add_dir(os.path.join(folder, "messages"), images="all")
    incoming = os.path.join(folder, "incoming")
    if os.path.isdir(incoming):
        add_dir(incoming, images="none")
        for n in sorted(os.listdir(incoming)):
            sub = os.path.join(incoming, n)
            if os.path.isdir(sub) and not n.startswith(".") and n not in SKIP_DIRS:
                add_dir(sub, images="none")

    seen = set()
    for fp, kind in candidates:
        if fp in seen:
            continue
        seen.add(fp)
        yield fp, kind


def load_json_messages(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        warn(f"{path} isn't valid JSON ({e}); ignored it.")
        return []
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return data["messages"]
    if isinstance(data, list):
        return data
    warn(f"{path} has no messages list; ignored it.")
    return []


def build_messages(folder, app, imgs):
    """Collect up to the last 30 buyer/shop messages, newest last."""
    collected = []  # (ts, seq, msg)
    seq = 0

    def add(msg, ts=None, source_mtime=None):
        nonlocal seq
        if not msg:
            return
        if ts is None:
            ts = parse_at_ts(msg.get("at"), source_mtime if source_mtime is not None else seq)
        collected.append((ts, seq, msg))
        seq += 1

    app = app or {}
    if isinstance(app.get("messages"), list):
        for raw in app["messages"]:
            m = coerce_message(raw, imgs, folder)
            add(m, parse_at_ts(m.get("at") if m else None, seq))

    for path, kind in iter_message_files(folder):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None
        if kind == "json":
            for raw in load_json_messages(path):
                m = coerce_message(raw, imgs, folder)
                add(m, parse_at_ts(m.get("at") if m else None, mtime or seq))
        elif kind == "text":
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    raw_text = f.read()
            except OSError as e:
                warn(f"Couldn't read {path} ({e}); skipped it.")
                continue
            parsed = parse_messages_text(raw_text)
            # If a file is clearly a shop-side capture note, default already buyer
            for i, m in enumerate(parsed):
                ts = parse_at_ts(m.get("at"), (mtime or 0) + i * 0.001)
                add(m, ts)
        elif kind == "image":
            key = imgs.key_for(path)
            if not key:
                continue
            name = os.path.basename(path).lower()
            frm = "shop" if re.search(r"(shop_sent|sent_by_shop|from_shop|^shop[_-])", name) else "buyer"
            add({"from": frm, "at": format_pt(mtime), "image": key}, mtime or seq)

    # Dedupe identical from/text/image, keeping the first (usually app.json)
    seen = set()
    unique = []
    for ts, s, msg in collected:
        sig = (msg.get("from"), msg.get("text") or "", msg.get("image") or "")
        if sig in seen:
            continue
        seen.add(sig)
        unique.append((ts, s, msg))
    unique.sort(key=lambda t: (t[0], t[1]))
    out = []
    for _, _, msg in unique[-MAX_MESSAGES:]:
        out.append({k: msg[k] for k in ("from", "at", "text", "image") if msg.get(k)})
    return out



# ---------------------------------------------------------------- commands

def cmd_push(args, orders_dir, url, token):
    tracker = os.path.join(orders_dir, "ORDER_TRACKER.csv")
    if not os.path.exists(tracker):
        raise SystemExit(f"ERROR: {tracker} not found.")
    by_id, by_name, apps = index_folders(orders_dir)
    imgs = Images(orders_dir)
    decided = fetch_decided_keys(url, token)
    orders = []
    with open(tracker, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not any((v or "").strip() for v in row.values()):
                continue
            oid = (row.get("order") or "").strip()
            first = (row.get("buyer") or "").strip().split(" ")[0]
            folder = find_folder(oid, first, by_id, by_name)
            if not folder:
                warn(f"{first} ({oid}): no order folder found (photos/mockups won't show).")
            app = apps.get(folder)
            if _hidden_from_app(app, oid, folder, first):
                warn(f"{first} ({oid}): hide_from_app is set — left off the Viva Orders app.")
                continue
            orders.append(build_order(row, folder, app, imgs, decided))

    # make ids unique (two quotes with the same name)
    seen = {}
    for o in orders:
        if o["order_id"] in seen:
            seen[o["order_id"]] += 1
            o["order_id"] = f"{o['order_id']}-{seen[o['order_id']]}"
        else:
            seen[o["order_id"]] = 1

    if args.dry_run:
        print(json.dumps({"orders": orders}, indent=2))
        with_msgs = sum(1 for o in orders if o.get("messages"))
        print(f"\n(dry run) {len(orders)} orders, {len(imgs.pending)} images referenced, {with_msgs} with messages.", file=sys.stderr)
        for w in warnings:
            print("WARNING:", w, file=sys.stderr)
        return

    if not url or not token:
        raise SystemExit("ERROR: set VIVA_APP_URL and VIVA_BOT_TOKEN (env or /workspace/orders/.viva_app).")
    if not orders:
        raise SystemExit("ERROR: found 0 orders in ORDER_TRACKER.csv; refusing to push (it would empty Derek's board).")

    keys = list(imgs.pending.keys())
    missing = []
    for i in range(0, len(keys), 200):
        missing += http("POST", url + "/api/bot/images/missing", token, {"keys": keys[i:i + 200]}).get("missing", [])
    uploaded = 0
    for key in missing:
        data = imgs.bytes_for(key)
        if data is None:
            continue
        ctype = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[key.rsplit(".", 1)[1]]
        http("PUT", f"{url}/api/bot/images/{key}", token, data, content_type=ctype, timeout=120)
        uploaded += 1
    imgs.save_cache()

    body = {"orders": orders, "warnings": warnings[:50]}
    by = (getattr(args, "by", None) or os.environ.get("VIVA_BOT_NAME") or "").strip()
    if by:
        body["pushed_by"] = by
    res = http("POST", url + "/api/bot/push", token, body)
    with_msgs = sum(1 for o in orders if o.get("messages"))
    print(f"OK: pushed {res.get('orders')} orders, uploaded {uploaded} new image(s), {with_msgs} with messages.")
    for c in res.get("stage_changes", []):
        print(f"  moved: {c['order_id']} {c['from']} -> {c['to']}")
    for w in warnings + res.get("warnings", []):
        print("WARNING:", w)


def fetch_decided_keys(url, token):
    """Review keys Derek already tapped (any status). None if the app can't be asked."""
    if not url or not token:
        return None
    keys = set()
    try:
        for st in ("pending", "done"):
            for d in _get_quiet(url + "/api/bot/decisions?status=" + st, token).get("decisions", []):
                v = d.get("version") or ""
                if d.get("order_id") and d.get("kind"):
                    keys.add(f"{d['order_id']}|{d['kind']}|{v}")
    except Exception as e:  # never block a push on this
        warn(f"Couldn't read Derek's decisions from the app ({e}); undecided proofs may hide if status is 'Needs mockup'.")
        return None
    return keys


def _get_quiet(u, token):
    req = urllib.request.Request(u, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("User-Agent", "viva-push/1.0")
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8") or "{}")


def _age(iso):
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds() / 60
    except Exception:
        return None


def _brief(d):
    started = d.get("last_note")
    age = _age(d.get("decided_at"))
    what = d.get("action", "?") + (" " + d["option"] if d.get("option") else "")
    return (f"{d.get('decision_id')}  {d.get('order_id')} ({d.get('buyer_first_name') or '?'})  {what} {d.get('version') or ''}"
            f"  -> {d.get('target_bot')}  tapped {d.get('decided_at_pt') or d.get('decided_at')}"
            f"{f' ({age / 60:.1f} h ago)' if age is not None else ''}"
            f"  webhook={d.get('webhook_status')}  {'started: ' + started if started else 'NOT STARTED'}")


def cmd_pending(args, orders_dir, url, token):
    q = "?status=pending" + (f"&bot={urllib.request.quote(args.bot)}" if args.bot else "")
    res = http("GET", url + "/api/bot/decisions" + q, token)
    ds = res.get("decisions", [])
    if not ds:
        print("No pending decisions.")
        return
    if getattr(args, "brief", False):
        print(f"{len(ds)} open decision(s). Handle EVERY one, oldest first:")
        for d in ds:
            print("  " + _brief(d))
        return
    print(f"# {len(ds)} open decision(s). Handle EVERY one below, oldest first (not only the one in your wake-up).")
    for d in ds:
        print(json.dumps(d, indent=2))


def cmd_audit(args, orders_dir, url, token):
    """Cheap safety net (no LLM needed to run it): is every one of Derek's taps actually done?
    Exit code 1 if anything needs attention."""
    hours = args.hours
    problems = []
    pend = http("GET", url + "/api/bot/decisions?status=pending", token).get("decisions", [])
    done = http("GET", url + "/api/bot/decisions?status=done", token).get("decisions", [])
    print(f"Open decisions: {len(pend)}")
    for d in pend:
        age = _age(d.get("decided_at")) or 0
        line = "  " + _brief(d)
        late = (not d.get("last_note") and age > 30) or (d.get("webhook_status") != "delivered" and age > 5) or age > 6 * 60
        print(line + ("   <-- STUCK?" if late else ""))
        if late:
            problems.append(f"open decision {d.get('decision_id')} for {d.get('order_id')} ({d.get('target_bot')})")
    # Outcome check for recent finished decisions
    tracker = os.path.join(orders_dir, "ORDER_TRACKER.csv")
    status_by = {}
    if os.path.exists(tracker):
        with open(tracker, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                status_by[(row.get("order") or "").strip()] = (row.get("status") or "").strip()
    by_id, by_name, apps = index_folders(orders_dir)
    recent = [d for d in done if (_age(d.get("decided_at")) or 1e9) < hours * 60]
    print(f"Done in the last {hours} h: {len(recent)}")
    for d in recent:
        oid = d.get("order_id") or ""
        folder = find_folder(oid, d.get("buyer_first_name") or "", by_id, by_name)
        app = apps.get(folder) or {}
        st = status_by.get(oid) or status_by.get(oid.replace("quote-", ""), "")
        ok, why = True, ""
        if d.get("action") == "approve" and d.get("kind") == "art_proof":
            ok = st in ("Waiting on buyer", "Approved - ordering", "In production", "Shipped", "Delivered") or not st
            why = f"tracker status {st or '(order not in tracker)'}"
        elif d.get("action") == "adjust":
            rv = (app.get("review") or {}).get("version") if isinstance(app.get("review"), dict) else None
            newer = _vnum(rv) is not None and _vnum(d.get("version")) is not None and _vnum(rv) > _vnum(d.get("version"))
            moved_on = st in ("Waiting on buyer", "Approved - ordering", "In production", "Shipped", "Delivered")
            ok = newer or moved_on or not folder
            why = f"app.json review now {rv or 'none'}, tracker {st or '?'}"
        print(f"  {'ok ' if ok else 'CHECK'} {oid} {d.get('action')} {d.get('version') or ''} -> {d.get('target_bot')}: {d.get('last_note') or ''} [{why}]")
        if not ok:
            problems.append(f"{oid} {d.get('action')} {d.get('version')} marked done but {why}")
    # Proofs on disk Derek can't see
    for oid, folder in by_id.items():
        st = status_by.get(oid)
        if st == "Needs mockup":
            w = unpushed_art_warning(folder, apps.get(folder), "artist", os.path.basename(folder), oid)
            if w:
                print("  UNPUSHED " + w)
                problems.append(w)
    if problems:
        print(f"\nNEEDS ATTENTION ({len(problems)}):")
        for p in problems:
            print(" - " + p)
        raise SystemExit(1)
    print("\nAll of Derek's taps are delivered, picked up and done. Nothing stuck.")


def cmd_show(args, orders_dir, url, token):
    print(json.dumps(http("GET", f"{url}/api/bot/decisions/{args.id}", token), indent=2))


def cmd_ack(args, orders_dir, url, token):
    body = {"by": args.by, "note": args.note or "", "done": bool(args.done)}
    http("POST", f"{url}/api/bot/decisions/{args.id}/ack", token, body)
    print("OK: reported back" + (" (done)" if args.done else ""))


def main():
    p = argparse.ArgumentParser(description="Send the order board to the Viva Orders app.")
    p.add_argument("--orders-dir", default=None)
    p.add_argument("--dry-run", action="store_true", help="print the JSON, send nothing")
    p.add_argument("--by", default=None, help="optional: your bot name, shown as who last updated the board")
    sub = p.add_subparsers(dest="cmd")
    sp = sub.add_parser("pending", help="list decisions not done yet")
    sp.add_argument("--bot", default=None, help="only decisions for this bot, e.g. Messanger")
    sp.add_argument("--brief", action="store_true", help="one line per decision")
    su = sub.add_parser("audit", help="check every recent tap was delivered, picked up and really done")
    su.add_argument("--hours", type=int, default=72, help="how far back to check finished decisions")
    ss = sub.add_parser("show", help="confirm one decision is real")
    ss.add_argument("id")
    sa = sub.add_parser("ack", help="report progress on a decision")
    sa.add_argument("id")
    sa.add_argument("--by", required=True, help="your bot name")
    sa.add_argument("--note", default="", help='e.g. "sent to buyer" or "started v13"')
    sa.add_argument("--done", action="store_true", help="the decision is fully handled")
    args = p.parse_args()

    orders_dir, url, token = load_settings(args)
    if args.cmd in ("pending", "show", "ack", "audit") and (not url or not token):
        raise SystemExit("ERROR: set VIVA_APP_URL and VIVA_BOT_TOKEN (env or /workspace/orders/.viva_app).")
    {"pending": cmd_pending, "show": cmd_show, "ack": cmd_ack, "audit": cmd_audit}.get(args.cmd, cmd_push)(args, orders_dir, url, token)


if __name__ == "__main__":
    main()
