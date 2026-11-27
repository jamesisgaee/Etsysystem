# Run after burst_test.py. Time-travels decided_at in the LOCAL test DB only, then runs the cron sweep.
import json, sys
sys.path.insert(0, "/workspace/viva-orders/test")
from burst_test import d1, sweep, hooks, req

def state():
    return {r["order_id"]: (r["webhook_status"], r["webhook_attempts"], r["status"]) for r in d1("SELECT order_id, webhook_status, webhook_attempts, status FROM decisions ORDER BY order_id")}
def shift(minutes):
    d1(f"UPDATE decisions SET decided_at = strftime('%Y-%m-%dT%H:%M:%fZ', decided_at, '-{minutes} minutes')")
    d1(f"UPDATE decision_notes SET at = strftime('%Y-%m-%dT%H:%M:%fZ', at, '-{minutes} minutes')")
    d1(f"UPDATE decisions SET last_note_at = strftime('%Y-%m-%dT%H:%M:%fZ', last_note_at, '-{minutes} minutes') WHERE last_note_at IS NOT NULL")
n0 = len(hooks())
print("1) 3 minutes later, cron sweep: the 3 rate-limited approves are re-sent in ONE wake to Messanger")
shift(3); sweep()
new = hooks()[n0:]; n0 += len(new)
print("   wakes:", [(x["path"], x["code"], x["body"].get("type"), len(x["body"].get("decision_ids", []))) for x in new])
print("   state:", state())
# Messanger handles all 5 approvals (acks), Designer starts 2 of 3 adjusts, Designer 2 never answers
ids = {r["order_id"]: r["id"] for r in d1("SELECT id, order_id FROM decisions")}
for i in range(5): req("POST", f"/api/bot/decisions/{ids[f'T{i}']}/ack", {"by": "Messanger", "note": "sent proof", "done": True}, bot=True)
for i in (5, 6): req("POST", f"/api/bot/decisions/{ids[f'T{i}']}/ack", {"by": "Designer", "note": "started v2"}, bot=True)
print("2) bots: Messanger did all 5, Designer started T5+T6 (missed nothing yet), Designer 2 silent on T7")
shift(21); sweep()
new = hooks()[n0:]; n0 += len(new)
print("   after 24 min, wakes:", [(x["path"], x["body"].get("wake_reason"), x["body"].get("decision_ids")) for x in new])
print("3) Designer finishes T5 but forgets T6 (the Person22 case); 4h later:")
req("POST", f"/api/bot/decisions/{ids['T5']}/ack", {"by": "Designer", "note": "pushed v2", "done": True}, bot=True)
shift(250); sweep()
new = hooks()[n0:]; n0 += len(new)
print("   wakes:", [(x["path"], x["body"].get("wake_reason"), x["body"].get("pending_for_you")) for x in new])
print("4) jump far ahead: T7 (never acked) and T6 (never finished) end up STUCK; T7 escalates to Messanger")
for _ in range(4): shift(300); sweep()
new = hooks()[n0:]
print("   wakes:", [(x["path"], x["body"].get("type"), x["body"].get("wake_reason")) for x in new])
req("POST", "/api/login", {"password": "test-pass"})
code, st = req("GET", "/api/state")
print("   app shows:", {d["order_id"]: (d["delivery_state"], d["auto_wakes"]) for d in st["decisions"]})
notes = d1("SELECT d.order_id, n.by_bot, n.note FROM decision_notes n JOIN decisions d ON d.id = n.decision_id WHERE n.by_bot = 'Viva app' ORDER BY d.order_id, n.at")
for n in notes: print("   note", n["order_id"], n["note"][:90])
