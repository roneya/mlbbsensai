"""
Step 1 of 2 — fetch raw hero data (including skills) from the MLBB API.
Output: api_matchups.json (raw array of API records, one per hero)

When a new hero is added, update MAX_HERO_ID below, then run:
  1. python3 fetch_hero_matchups.py
  2. python3 build_hero_data.py
"""

import json, time, urllib.request

MAX_HERO_ID = 132  # ← bump this when a new hero is released

URL = "https://api.gms.moontontech.com/api/gms/source/2669606/2756564"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "authorization": "GwW9T3dQQDDeRS4PvWViCQskno8=",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://www.mobilelegends.com",
    "referer": "https://www.mobilelegends.com/",
    "user-agent": "Mozilla/5.0",
    "x-actid": "2669607",
    "x-appid": "2669606",
    "x-lang": "en",
}

records = []

for hero_id in range(1, MAX_HERO_ID + 1):
    payload = json.dumps({
        "pageSize": 20, "pageIndex": 1,
        "filters": [{"field": "hero_id", "operator": "eq", "value": hero_id}],
        "sorts": [], "object": []
    }).encode()
    try:
        req = urllib.request.Request(URL, data=payload, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        rec = data.get("data", {}).get("records", [])
        records.extend(rec)
        print(f"[{hero_id:3d}/132] {len(rec)} record(s)")
    except Exception as e:
        print(f"[{hero_id:3d}/132] ERROR: {e}")
    time.sleep(0.15)

with open("api_matchups.json", "w") as f:
    json.dump(records, f)

print(f"\nDone. {len(records)} total records saved to api_matchups.json")
