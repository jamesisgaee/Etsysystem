#!/usr/bin/env python3
"""Rebuild the SIMPLE order board (Nov 22, 2026 layout) from ORDER_TRACKER.csv.

Writes:
  /workspace/orders/ORDER_TRACKER.md
  /workspace/orders/board_canvas.tsx    (Page source, from board_canvas.template.tsx)
  /workspace/orders/board_assets.json   (images for the "Needs your OK" cards)

To publish: WriteCanvas canvas_id=CANVAS_ID with the contents of
board_canvas.tsx, then WriteCanvasAsset for each item in board_assets.json
(same canvas_id, name, path). Asset names are a fixed slot pool
(rq-slot-01.jpg .. rq-slot-20.jpg) because the Page holds at most 20 images;
always overwrite those same names. Then touch /workspace/orders/.last_board_publish.

Layout: one-line summary, "Needs your OK" mockup cards (status
"Waiting for Derek") with the exact words to type to the Manager chat, then
plain status groups. Status -> group mapping is in group_of().
Old generator: build_board_v_old.py (writes *_v_old files only).
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _load_queue_build():
    path = Path(__file__).resolve().parent / "queue_build.py"
    spec = importlib.util.spec_from_file_location("queue_build", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_queue = _load_queue_build().build_queue

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "ORDER_TRACKER.csv"
MD_PATH = HERE / "ORDER_TRACKER.md"
TSX_PATH = HERE / "board_canvas.tsx"
TEMPLATE_PATH = HERE / "board_canvas.template.tsx"
ASSETS_PATH = HERE / "board_assets.json"

CANVAS_ID = "1264c983-ad4a-4860-afdb-f889abbca6bd"
CANVAS_URL = (
    "https://cursor.com/canvas/store-f5852bc5-2b96-4f64-98d7-469d08d2d921/"
    "1264c983-ad4a-4860-afdb-f889abbca6bd"
)
TZ = ZoneInfo("America/Los_Angeles")

FIELDS = ["order", "buyer", "what_they_got", "status", "latest_request",
          "next_step", "ship_by", "tracking", "updated"]

# Valid tracker statuses. "Waiting on buyer" is optional (Nov 22): a proof was
# sent to the buyer and we wait on their yes. "Needs mockup" rows whose text
# says a proof was sent and the next step is the buyer's approval are shown
# in that group too.
STATUSES = ["Problem", "Waiting for Derek", "Needs mockup", "Waiting on buyer",
            "Approved - ordering", "In production", "Shipped", "Delivered"]

# Group key, heading, collapsed?
GROUPS = [
    ("problem", "Something's wrong", False),
    ("artist", "Artist working on it", False),
    ("buyer", "Sent to buyer, waiting on their OK", False),
    ("ordering", "Approved, ordering", False),
    ("printing", "Printing at Printify", False),
    ("shipped", "Shipped", False),
    ("done", "Done / Delivered", True),
]
ACTIVE = {"ok", "problem", "artist", "buyer", "ordering"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Hand-written card text for a mockup waiting on Derek. Used only while the
# card's mockup file is exactly `mockup`, so it never goes stale on a new
# version. Real data only (buyer words / order notes / designer notes).
CARD_NOTES = {
    "1000000100": {
        "mockup": "kristen_1000000100/art/v12/kristin_v12_compare.jpg",
        "version": "Version 12, pick A (a few stitches, artist's pick) or B (more patchwork)",
        "ask": "Asked for: a Nightmare Before Christmas portrait of Person01, Person03 and their dog Person04. This round adds stitches to Person04, as you asked on v11B.",
        "commands": ["approve Person01 v12A", "approve Person01 v12B"],
    },
    "1000000101": {
        "mockup": "maureen_1000000101/printify/printify_mockup_front.png",
        "version": "Printify print preview of v1B (Person35 already said yes to the art)",
        "ask": "Asked for: \"Person36-a beagle, can you do Charlie Brown Xmas theme?\" OK this and the print gets ordered.",
        "commands": ["approve Person35"],
    },
}

CARRIERS = [
    ("UPS Mail Innovations", "https://www.ups.com/track?tracknum={n}"),
    ("USPS", "https://tools.usps.com/go/TrackConfirmAction?tLabels={n}"),
    ("UPS", "https://www.ups.com/track?tracknum={n}"),
    ("DHL", "https://www.dhl.com/us-en/home/tracking/tracking-ecommerce.html?submit=1&tracking-id={n}"),
    ("ONTRAC", "https://www.ontrac.com/tracking/?number={n}"),
    ("FedEx", "https://www.fedex.com/fedextrack/?trknbr={n}"),
]


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in FIELDS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"CSV missing columns: {missing}")
        rows = []
        for row in reader:
            status = (row.get("status") or "").strip()
            if status not in STATUSES:
                raise SystemExit(
                    f"Invalid status {status!r} on order {row.get('order')!r}. "
                    f"Use one of: {', '.join(STATUSES)}")
            rows.append({k: (row.get(k) or "").strip() for k in FIELDS})
        return rows


def sort_rows(rows):
    rank = {s: i for i, s in enumerate(STATUSES)}
    return sorted(rows, key=lambda r: (rank.get(r["status"], 99), r["ship_by"] or "9999", r["order"]))


def parse_day(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def nice_day(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}"


def parse_updated(raw: str) -> datetime | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2}) (\d{1,2}:\d{2} [AP]M)", raw)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %I:%M %p").replace(tzinfo=TZ)
    except ValueError:
        return None


def days_since(row, today: date) -> int | None:
    dt = parse_updated(row["updated"])
    return None if dt is None else max(0, (today - dt.date()).days)


def days_label(n: int | None) -> str:
    if n is None:
        return ""
    return "today" if n == 0 else f"{n} day" + ("" if n == 1 else "s")


def meta_label(n: int | None, group: str) -> str:
    if n is None or group == "done":
        return ""
    if group in ACTIVE:
        return "waiting since today" if n == 0 else f"waiting {days_label(n)}"
    return "checked today" if n == 0 else f"checked {days_label(n)} ago"


def first_name(row) -> str:
    return (row["buyer"].split() or ["?"])[0]


def order_label(row) -> str:
    o = row["order"]
    return "no order yet" if not o or o == "none-yet" else f"#{o}"


def waiting_on_buyer(row) -> bool:
    if row["next_step"].upper().startswith("WORKING NOW"):
        return False
    return bool(re.search(r"\bsent to\b", row["latest_request"], re.I)
                and re.search(r"approv", row["next_step"], re.I))


def group_of(row) -> str:
    s = row["status"]
    if s == "Waiting for Derek":
        return "ok"
    if s == "Needs mockup":
        return "buyer" if waiting_on_buyer(row) else "artist"
    return {
        "Problem": "problem",
        "Waiting on buyer": "buyer",
        "Approved - ordering": "ordering",
        "In production": "printing",
        "Shipped": "shipped",
        "Delivered": "done",
    }[s]


def est_ship(text: str) -> tuple[str, date | None]:
    m = re.search(r"est(?:imated|\.)? ship ([A-Z][a-z]{2}) (\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?", text)
    if not m:
        return "", None
    label = f"{m.group(1)} {m.group(2)}" + (f"-{m.group(3)}" if m.group(3) else "")
    try:
        start = date(2026, MONTHS.index(m.group(1)) + 1, int(m.group(2)))
    except ValueError:
        start = None
    return label, start


def parse_tracking(raw: str) -> tuple[str, str, str, str]:
    """Return carrier, number, note, url (empty strings if none)."""
    if not raw or raw.lower() in {"none", "unknown"}:
        return "", "", "", ""
    for name, url in CARRIERS:
        m = re.match(rf"{re.escape(name)}\s+([A-Za-z0-9]+)\s*(?:\((.*)\))?", raw, re.I)
        if m:
            return name, m.group(1), (m.group(2) or "").strip(), url.format(n=m.group(1))
    return "", raw, "", ""


def plain_status(row, group: str) -> tuple[str, str]:
    """Plain-English status, plus a red flag reason from the text (or '')."""
    nxt, latest = row["next_step"], row["latest_request"]
    if group == "artist":
        m = re.match(r"WORKING NOW:\s*(?:Designer|Manager|Messanger)(?: \d)?\s*(.*)", nxt, re.I)
        return ("Artist is " + m.group(1).rstrip(". ")) if m and m.group(1) else "Artist is making the mockup", ""
    if group == "buyer":
        ver = re.search(r"\bv\d+[A-Za-z]?\b", latest)
        when = re.search(r"\b(?:%s) \d{1,2}\b" % "|".join(MONTHS), latest)
        bits = "Proof" + (f" {ver.group(0)}" if ver else "") + " sent" + (f" {when.group(0)}" if when else "")
        return f"{bits}; waiting for {first_name(row)} to say yes", ""
    if group == "ordering":
        return "Approved; Printify order not placed yet", ""
    if group == "printing":
        base = "Printify has it on hold / pending production" if re.search(r"on hold", nxt, re.I) else "Printify is making it"
        label, start = est_ship(nxt)
        flag = ""
        due = parse_day(row["ship_by"])
        if start and due and start > due:
            flag = f"Ships after ship-by ({nice_day(due)})"
        return base + (f", ships about {label}" if label else ""), flag
    if group == "shipped":
        carrier, number, note, _ = parse_tracking(row["tracking"])
        note = re.sub(r"^on the way,?\s*", "", note, flags=re.I)
        txt = "On the way" + (f", {note}" if note else "")
        deliv = re.search(r"deliver(?:y|ed)?\s+(?:by\s+)?([A-Z][a-z]{2} \d{1,2}(?:-\d{1,2})?)", nxt + " " + row["tracking"])
        if deliv:
            txt += f", expected {deliv.group(1)}"
        if carrier:
            txt += f" ({carrier} {number})"
        return txt, ""
    if group == "done":
        m = re.search(r"Delivered ([A-Z][a-z]{2} \d{1,2})", row["tracking"] + " " + nxt)
        return "Delivered" + (f" {m.group(1)}" if m else ""), ""
    if group == "problem":
        return nxt or "Blocked; see the tracker", ""
    return row["status"], ""


def flags_for(row, group: str, today: date, text_flag: str) -> tuple[str, str]:
    """Return (label, tone) for the row's status pill."""
    due = parse_day(row["ship_by"])
    if group not in {"shipped", "done"} and due and today > due:
        return f"Past ship-by ({nice_day(due)})", "danger"
    if text_flag:
        return text_flag, "danger"
    n = days_since(row, today)
    if group in ACTIVE and n is not None and n > 2:
        return f"Waiting {n} days", "danger"
    if group == "problem":
        return "Problem", "danger"
    if group not in {"shipped", "done"} and due:
        left = (due - today).days
        if left == 0:
            return "Ship-by today", "warning"
        if left == 1:
            return "Ship-by tomorrow", "warning"
        return f"Ship-by {nice_day(due)}", ""
    return "", ""


def build_groups(rows, today: date) -> list[dict]:
    out = []
    for key, heading, collapsed in GROUPS:
        members = [r for r in sort_rows(rows) if group_of(r) == key]
        if not members:
            continue
        brs, links = [], []
        for r in members:
            text, tflag = plain_status(r, key)
            label, tone = flags_for(r, key, today, tflag)
            br = {
                "title": f"{r['buyer']} · {order_label(r)}",
                "detail": f"{r['what_they_got']}. {text}",
                "meta": meta_label(days_since(r, today), key),
            }
            if label:
                br["status"] = {"label": label, **({"tone": tone} if tone else {})}
            brs.append(br)
            if key == "shipped":
                carrier, number, _, url = parse_tracking(r["tracking"])
                if url:
                    links.append({"title": f"Track {r['buyer']}'s package", "site": f"{carrier} {number}", "href": url})
        out.append({"key": key, "heading": heading, "collapsed": collapsed, "rows": brs, "links": links})
    return out


def build_cards(rows, queue_items, today: date) -> list[dict]:
    by_order = {r["order"] + r["buyer"]: r for r in rows}
    firsts = [first_name(r) for r in rows if group_of(r) == "ok"]
    cards = []
    for q in queue_items:
        r = by_order.get(q["order"] + q["buyer"])
        if r is None:
            continue
        first = first_name(r)
        if firsts.count(first) > 1:
            first = f"{first} {r['buyer'].split()[-1][:1]}"
        note = CARD_NOTES.get(r["order"])
        mock_rel = str(Path(q["mockupFile"]).relative_to(HERE)) if q.get("mockupFile", "").startswith(str(HERE)) else ""
        if note and note["mockup"] != mock_rel:
            note = None
        if note:
            version, ask, commands = note["version"], note["ask"], list(note["commands"])
        else:
            m = re.search(r"v\d+[A-Za-z]?", Path(q["mockupFile"]).name)
            version = f"Version {m.group(0)[1:]}" if m else "Latest mockup"
            latest = r["latest_request"]
            ask = f"Asked for: {latest}" if latest and latest.lower() != "unknown" else ""
            commands = [f"approve {first}"]
        commands.append(f"change {first}: <what to fix>")
        n = days_since(r, today)
        _, flag_tone = flags_for(r, "ok", today, "")
        flag_label, _ = flags_for(r, "ok", today, "")
        photo = q["photos"][0] if q["photos"] else None
        cards.append({
            "key": q["order"] + q["buyer"],
            "heading": f"{first} · {order_label(r)}",
            "line": f"{r['what_they_got']} · {version} · {meta_label(n, 'ok')}",
            "ask": ask,
            "flag": flag_label if flag_tone == "danger" else "",
            "mockupSrc": q["mockupSrc"],
            "mockupAlt": q["mockupAlt"],
            "mockupRatio": q["mockupRatio"],
            "photoSrc": photo["src"] if photo else "",
            "photoAlt": photo["alt"] if photo else "",
            "photoRatio": photo["ratio"] if photo else "1/1",
            "commands": commands,
        })
    return cards


def summary_line(rows) -> str:
    counts: dict[str, int] = {}
    for r in rows:
        g = group_of(r)
        counts[g] = counts.get(g, 0) + 1
    def plural(n, one, many):
        return one if n == 1 else many
    phrases = [
        ("problem", lambda n: f"{n} {plural(n, 'problem', 'problems')}"),
        ("ok", lambda n: f"{n} {plural(n, 'mockup needs', 'mockups need')} your OK"),
        ("artist", lambda n: f"{n} being drawn"),
        ("buyer", lambda n: f"{n} waiting on buyer"),
        ("ordering", lambda n: f"{n} approved, ordering"),
        ("printing", lambda n: f"{n} printing"),
        ("shipped", lambda n: f"{n} shipped"),
        ("done", lambda n: f"{n} delivered"),
    ]
    return " · ".join(fn(counts[k]) for k, fn in phrases if counts.get(k))


def write_md(rows, groups, cards, summary, last_updated) -> str:
    lines = ["# VivaMemoir order board", "", summary, "",
             f"Page: [VivaMemoir Order Board]({CANVAS_URL})", ""]
    if cards:
        lines += ["## Needs your OK", ""]
        for c in cards:
            lines += [f"### {c['heading']}", c["line"], c["ask"], ""]
            lines += [f"- `{cmd}`" for cmd in c["commands"]] + [""]
    for g in groups:
        lines += [f"## {g['heading']} ({len(g['rows'])})", ""]
        for br in g["rows"]:
            pill = f" — {br['status']['label']}" if br.get("status") else ""
            lines.append(f"- {br['title']}: {br['detail']} ({br['meta']}){pill}")
        for l in g["links"]:
            lines.append(f"  - {l['title']}: {l['href']}")
        lines.append("")
    lines.append(f"Last updated {last_updated}.")
    return "\n".join(lines) + "\n"


def write_tsx(summary, last_updated, cards, groups) -> str:
    t = TEMPLATE_PATH.read_text(encoding="utf-8")
    js = lambda v: json.dumps(v, ensure_ascii=False, indent=2)
    return (t.replace("__SUMMARY__", js(summary))
             .replace("__LAST_UPDATED__", js(last_updated))
             .replace("__CARDS__", js(cards))
             .replace("__GROUPS__", js(groups)))


def main() -> int:
    rows = load_rows(CSV_PATH)
    now = datetime.now(TZ)
    today = now.date()
    last_updated = f"{now.strftime('%a')}, {nice_day(today)}, {now.strftime('%-I:%M %p')} PT"
    queue_items, assets, missing = build_queue(HERE, rows, sort_rows)
    cards = build_cards(rows, queue_items, today)
    groups = build_groups(rows, today)
    summary = summary_line(rows)
    MD_PATH.write_text(write_md(rows, groups, cards, summary, last_updated), encoding="utf-8")
    TSX_PATH.write_text(write_tsx(summary, last_updated, cards, groups), encoding="utf-8")
    ASSETS_PATH.write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MD_PATH}\nWrote {TSX_PATH}\nWrote {ASSETS_PATH} ({len(assets)} images)")
    print(f"Publish: WriteCanvas canvas_id={CANVAS_ID} with board_canvas.tsx, then "
          "WriteCanvasAsset each board_assets.json item (same name + path), then "
          "touch /workspace/orders/.last_board_publish")
    print(f"Page: {CANVAS_URL}")
    print("Summary:", summary)
    for c in cards:
        print(f"  OK card: {c['heading']} | {c['line']}")
    for g in groups:
        print(f"  {g['heading']}: {len(g['rows'])}")
        for br in g["rows"]:
            print(f"     - {br['title']} | {br['detail']} | {br['meta']} | {br.get('status')}")
    if missing:
        print("Missing / notes:")
        for line in missing:
            print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
