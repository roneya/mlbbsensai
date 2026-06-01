"""
Patches hero_info.json with new fields without re-running the full build:
  - relation (strong/weak/assist) + abilityStats  → API 3 (1 fast call)
  - increaseWinRate in sub_hero/sub_hero_last      → API 2 (264 calls, ~90s)

Run: python3 patch_hero_data.py
To skip the slow API 2 patch, set PATCH_INCREASE_WIN_RATE = False below.
"""

import json, requests, time

PATCH_INCREASE_WIN_RATE = True   # set False to skip the slow 264-call patch

HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://www.mobilelegends.com",
    "referer": "https://www.mobilelegends.com/",
    "user-agent": "Mozilla/5.0",
    "x-actid": "2669607", "x-appid": "2669606", "x-lang": "en"
}
BASE = "https://api.gms.moontontech.com/api/gms/source/2669606"

with open("hero_info.json", encoding="utf-8") as f:
    data = json.load(f)

hero_info = data["hero_info"]
name_to_id = {hdata["heroName"]: hid for hid, hdata in hero_info.items()}
# hero_info is already name-keyed, so id_to_name built from heroName field
id_to_name = {hdata.get("heroName", ""): hname for hname, hdata in hero_info.items()}
# Actually we need numeric id → name. Rebuild from heroName == key since they match
# name_keyed: key IS the name, heroName field also = key
# We need heroid (integer from API) → hero name string
# Get that mapping from a fresh API 3 fetch

# ── Patch 1: relation + abilityStats from API 3 ─────────────────────────────
print("Patch 1: Fetching relation + abilityStats from API 3...")
headers3 = {**HEADERS_BASE, "authorization": "CciHBEvFRqQNHGj2djxdUSja7W4="}
r3 = requests.post(f"{BASE}/2756564", headers=headers3, json={
    "pageSize": 200, "pageIndex": 1,
    "filters": [
        {"field": "<hero.data.sortid>", "operator": "hasAnyOf", "value": [1,2,3,4,5,6]},
        {"field": "<hero.data.roadsort>", "operator": "hasAnyOf", "value": [1,2,3,4,5]}
    ],
    "sorts": [{"data": {"field": "hero_id", "order": "desc"}, "type": "sequence"}]
}, timeout=30)
r3.raise_for_status()

records3 = r3.json().get("data", {}).get("records", [])

# Build heroid → name from the fetched data (hero_data.heroid → hero_data.name)
heroid_to_name = {}
for rec in records3:
    hd = rec.get("data", {}).get("hero", {}).get("data", {})
    hid = hd.get("heroid")
    # Match by heroName in our hero_info
    hname = hd.get("name", "")
    if hname in hero_info:
        heroid_to_name[hid] = hname

updated = 0
for rec in records3:
    d = rec.get("data", {})
    hero_data = d.get("hero", {}).get("data", {})
    hname = hero_data.get("name", "")
    if hname not in hero_info:
        continue

    # abilityStats
    ability_stats = [int(x) for x in hero_data.get("abilityshow", []) if str(x).isdigit()]
    if ability_stats:
        hero_info[hname]["abilityStats"] = ability_stats

    # heroClass (Tank/Fighter/Mage/etc.)
    hero_class = next((s for s in hero_data.get("sortlabel", []) if s), "")
    if hero_class:
        hero_info[hname]["heroClass"] = hero_class

    # speciality tags
    speciality = [s for s in hero_data.get("speciality", []) if s]
    if speciality:
        hero_info[hname]["speciality"] = speciality

    # relation
    relation = {}
    for key in ("strong", "weak", "assist"):
        rel = d.get("relation", {}).get(key)
        if rel:
            heroes = [heroid_to_name[hid] for hid in rel.get("target_hero_id", []) if hid in heroid_to_name]
            desc = rel.get("desc", "")
            if heroes:
                relation[key] = {"heroes": heroes, "desc": desc}
    if relation:
        hero_info[hname]["relation"] = relation

    updated += 1

print(f"  Updated {updated} heroes with relation + abilityStats")

# ── Patch 2: increaseWinRate in sub_hero/sub_hero_last from API 2 ────────────
if PATCH_INCREASE_WIN_RATE:
    print("Patch 2: Fetching increaseWinRate + timingCurve from API 2 (264 calls, ~90s)...")
    headers2 = {**HEADERS_BASE, "authorization": "bzSIpad3osbcCB/vIK+VlLmJde8="}
    max_id = max(heroid_to_name.keys()) if heroid_to_name else 132

    def fetch_counter_compat(match_type):
        field_name = "hero_counter_info" if match_type == 0 else "hero_compatibility_info"
        for hero_id in range(1, max_id + 1):
            try:
                r = requests.post(f"{BASE}/2756569", headers=headers2, json={
                    "pageSize": 20, "pageIndex": 1,
                    "filters": [
                        {"field": "match_type", "operator": "eq", "value": match_type},
                        {"field": "main_heroid", "operator": "eq", "value": str(hero_id)},
                        {"field": "bigrank", "operator": "eq", "value": 7}
                    ],
                    "sorts": []
                }, timeout=30)
                r.raise_for_status()
                records = r.json().get("data", {}).get("records", [])
                if not records:
                    continue

                d = records[0]["data"]
                hname = heroid_to_name.get(hero_id)
                if not hname or hname not in hero_info:
                    continue

                for sub_key in ("sub_hero", "sub_hero_last"):
                    existing = hero_info[hname].get(field_name, {}).get(sub_key, {})
                    for item in d.get(sub_key, []):
                        iname = heroid_to_name.get(item.get("heroid"))
                        if iname and iname in existing:
                            timing = {
                                "6_8":  round(item.get("min_win_rate6_8",  0) * 100, 2),
                                "8_10": round(item.get("min_win_rate8_10", 0) * 100, 2),
                                "10_12":round(item.get("min_win_rate10_12",0) * 100, 2),
                                "12_14":round(item.get("min_win_rate12_14",0) * 100, 2),
                                "14_16":round(item.get("min_win_rate14_16",0) * 100, 2),
                                "16_18":round(item.get("min_win_rate16_18",0) * 100, 2),
                                "18_20":round(item.get("min_win_rate18_20",0) * 100, 2),
                                "20+":  round(item.get("min_win_rate20",   0) * 100, 2),
                            }
                            if isinstance(existing[iname], dict):
                                existing[iname]["increaseWinRate"] = round(item.get("increase_win_rate", 0) * 100, 4)
                                existing[iname]["timingCurve"] = timing
                            else:
                                existing[iname] = {
                                    "winRate": existing[iname],
                                    "increaseWinRate": round(item.get("increase_win_rate", 0) * 100, 4),
                                    "timingCurve": timing
                                }

                print(f"  Hero {hero_id} ({hname}) -> {field_name}")
                time.sleep(0.2)
            except Exception as e:
                print(f"  Failed hero {hero_id}: {e}")

    fetch_counter_compat(0)
    fetch_counter_compat(1)
    print("Patch 2: Done")

# ── Save ─────────────────────────────────────────────────────────────────────
with open("hero_info.json", "w", encoding="utf-8") as f:
    json.dump({"hero_info": hero_info}, f, indent=4, ensure_ascii=False)

print(f"\nDone! hero_info.json patched.")
