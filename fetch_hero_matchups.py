"""
Step 1 of 2 — fetch raw hero data (including skills) from the MLBB API.
Output: api_matchups.json (raw array of API records, one per hero)

Hero count is detected automatically from the stats API — no hardcoding needed.
When a new hero is added, just run:
  1. python3 fetch_hero_matchups.py
  2. python3 build_hero_data.py
"""

import json, time, urllib.request

BASE    = "https://api.gms.moontontech.com/api/gms/source/2669606"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://www.mobilelegends.com",
    "referer": "https://www.mobilelegends.com/",
    "user-agent": "Mozilla/5.0",
    "x-actid": "2669607",
    "x-appid": "2669606",
    "x-lang": "en",
}

def post(endpoint, auth, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{BASE}/{endpoint}", data=data,
        headers={**HEADERS, "authorization": auth}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# ── Step 1: discover all hero IDs from the stats listing ─────────────────────
print("Fetching hero list...")
resp = post("2756565", "rjYdVHiPEF5/4a447YaBXuB3OsA=", {
    "pageSize": 200, "pageIndex": 1,
    "filters": [
        {"field": "bigrank",     "operator": "eq", "value": "7"},
        {"field": "match_type",  "operator": "eq", "value": 0},
    ],
    "sorts": [{"data": {"field": "main_heroid", "order": "asc"}, "type": "sequence"}],
})
hero_ids = sorted(set(
    r["data"]["main_heroid"]
    for r in resp.get("data", {}).get("records", [])
    if r.get("data", {}).get("main_heroid")
))
print(f"Found {len(hero_ids)} heroes (IDs {hero_ids[0]}–{hero_ids[-1]})")

# ── Step 2: fetch per-hero detail (skills, relation, etc.) ───────────────────
records = []
total   = len(hero_ids)

for i, hero_id in enumerate(hero_ids, 1):
    try:
        data = post("2756564", "GwW9T3dQQDDeRS4PvWViCQskno8=", {
            "pageSize": 20, "pageIndex": 1,
            "filters": [{"field": "hero_id", "operator": "eq", "value": hero_id}],
            "sorts": [], "object": [],
        })
        rec = data.get("data", {}).get("records", [])
        records.extend(rec)
        print(f"[{i:3d}/{total}] hero {hero_id} — {len(rec)} record(s)")
    except Exception as e:
        print(f"[{i:3d}/{total}] hero {hero_id} — ERROR: {e}")
    time.sleep(0.15)

with open("api_matchups.json", "w") as f:
    json.dump(records, f)

print(f"\nDone. {len(records)} records saved to api_matchups.json")
