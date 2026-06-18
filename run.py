"""
MLBB Draft Tool — hero data pipeline.

Usage:
  python3 run.py          # fetch all APIs + build hero_info.json
  python3 run.py fetch    # fetch only (saves raw JSON cache files)
  python3 run.py build    # build only (reads cache, writes hero_info.json)

Raw cache files (gitignored):
  raw_stats.json    — win/ban/appearance rates  (1 API call)
  raw_details.json  — hero types, relations, ability stats, story  (1 API call)
  raw_skills.json   — per-hero skills  (1 call per hero)
  raw_counters.json — counter + compatibility win rates  (2 calls per hero)
"""

import json, re, sys, time
import urllib.request

# ── Config ────────────────────────────────────────────────────────────────────

BASE = "https://api.gms.moontontech.com/api/gms/source/2669606"
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

AUTH = {
    "stats":    "rjYdVHiPEF5/4a447YaBXuB3OsA=",
    "details":  "GwW9T3dQQDDeRS4PvWViCQskno8=",
    "types":    "CciHBEvFRqQNHGj2djxdUSja7W4=",
    "counters": "bzSIpad3osbcCB/vIK+VlLmJde8=",
}

DELAY = 0.15  # seconds between per-hero calls

# ── HTTP helper ───────────────────────────────────────────────────────────────

def post(endpoint, auth_key, payload):
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{BASE}/{endpoint}", data=body,
        headers={**HEADERS, "authorization": AUTH[auth_key]}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "")

# ── FETCH — saves raw API responses as JSON cache ─────────────────────────────

def fetch():
    # 1. Stats (win/ban/appearance rates) — also used to discover hero IDs
    print("Fetching stats...")
    stats = post("2756565", "stats", {
        "pageSize": 1000, "pageIndex": 1,
        "filters": [
            {"field": "bigrank",    "operator": "eq", "value": "7"},
            {"field": "match_type", "operator": "eq", "value": 0},
        ],
        "sorts": [{"data": {"field": "main_heroid", "order": "asc"}, "type": "sequence"}],
    })
    with open("raw_stats.json", "w") as f:
        json.dump(stats, f)
    ids_from_stats = set(
        r["data"]["main_heroid"]
        for r in stats.get("data", {}).get("records", [])
        if r.get("data", {}).get("main_heroid")
    )

    # 2. Hero detail bulk (types, names, pics, relations, ability stats, story)
    print("Fetching hero details...")
    details = post("2756564", "types", {
        "pageSize": 1000, "pageIndex": 1,
        "filters": [
            {"field": "<hero.data.sortid>",  "operator": "hasAnyOf", "value": [1,2,3,4,5,6]},
            {"field": "<hero.data.roadsort>", "operator": "hasAnyOf", "value": [1,2,3,4,5]},
        ],
        "sorts": [{"data": {"field": "hero_id", "order": "asc"}, "type": "sequence"}],
    })
    with open("raw_details.json", "w") as f:
        json.dump(details, f)
    ids_from_details = set(
        r["data"]["hero_id"]
        for r in details.get("data", {}).get("records", [])
        if r.get("data", {}).get("hero_id")
    )

    # Merge IDs — details API catches newly released heroes missing from stats
    hero_ids = sorted(ids_from_stats | ids_from_details)
    new_ids  = ids_from_details - ids_from_stats
    if new_ids:
        print(f"  Note: hero IDs {sorted(new_ids)} are new (no stats data yet)")
    print(f"Found {len(hero_ids)} heroes (IDs {hero_ids[0]}–{hero_ids[-1]})")

    # 3. Per-hero skills
    print("Fetching per-hero skills...")
    skills_records = []
    for i, hero_id in enumerate(hero_ids, 1):
        try:
            resp = post("2756564", "details", {
                "pageSize": 20, "pageIndex": 1,
                "filters": [{"field": "hero_id", "operator": "eq", "value": hero_id}],
                "sorts": [], "object": [],
            })
            recs = resp.get("data", {}).get("records", [])
            skills_records.extend(recs)
            print(f"  [{i:3d}/{len(hero_ids)}] hero {hero_id} — {len(recs)} record(s)")
        except Exception as e:
            print(f"  [{i:3d}/{len(hero_ids)}] hero {hero_id} — ERROR: {e}")
        time.sleep(DELAY)
    with open("raw_skills.json", "w") as f:
        json.dump(skills_records, f)

    # 4. Per-hero counters + compatibility
    print("Fetching counters and compatibility...")
    counters = {}
    total = len(hero_ids)
    for match_type in (0, 1):
        label = "counters" if match_type == 0 else "compat"
        print(f"  match_type={match_type} ({label})...")
        for i, hero_id in enumerate(hero_ids, 1):
            try:
                resp = post("2756569", "counters", {
                    "pageSize": 20, "pageIndex": 1,
                    "filters": [
                        {"field": "match_type",  "operator": "eq", "value": match_type},
                        {"field": "main_heroid", "operator": "eq", "value": str(hero_id)},
                        {"field": "bigrank",     "operator": "eq", "value": 7},
                    ],
                    "sorts": [],
                })
                recs = resp.get("data", {}).get("records", [])
                if recs:
                    counters.setdefault(str(hero_id), {})[label] = recs[0]["data"]
                print(f"    [{i:3d}/{total}] hero {hero_id} — {'ok' if recs else 'no data'}")
            except Exception as e:
                print(f"    [{i:3d}/{total}] hero {hero_id} — ERROR: {e}")
            time.sleep(DELAY)
        # Save after each match_type so progress isn't lost if it crashes
        with open("raw_counters.json", "w") as f:
            json.dump(counters, f)
        print(f"  Saved {label} data.")

    print("\nFetch complete. Raw files saved.")

# ── BUILD — reads cache, produces hero_info.json ──────────────────────────────

def build():
    print("Building hero_info.json...")

    # ── Load raw cache ──
    with open("raw_stats.json")    as f: raw_stats    = json.load(f)
    with open("raw_details.json")  as f: raw_details  = json.load(f)
    with open("raw_skills.json")   as f: raw_skills   = json.load(f)
    with open("raw_counters.json") as f: raw_counters = json.load(f)

    # ── Step 1: base stats (win/ban/appearance rates) ──
    hero_info = {}  # keyed by numeric string hero_id
    for record in raw_stats.get("data", {}).get("records", []):
        d    = record.get("data", {})
        hid  = str(d.get("main_heroid"))
        hero = d.get("main_hero", {}).get("data", {})
        hero_info[hid] = {
            "heroName":       hero.get("name", ""),
            "heroPic":        hero.get("head", ""),
            "appearanceRate": round(d.get("main_hero_appearance_rate", 0) * 100, 4),
            "banRate":        round(d.get("main_hero_ban_rate",        0) * 100, 4),
            "winRate":        round(d.get("main_hero_win_rate",        0) * 100, 4),
        }

    # ── Step 2: hero types, relations, ability stats, story ──
    # Build heroid → name map for relation target resolution
    heroid_to_name = {}
    for record in raw_details.get("data", {}).get("records", []):
        hd = record.get("data", {}).get("hero", {}).get("data", {})
        heroid_to_name[hd.get("heroid")] = hd.get("name", "")

    for record in raw_details.get("data", {}).get("records", []):
        d         = record.get("data", {})
        hid       = str(d.get("hero_id"))
        hero_data = d.get("hero", {}).get("data", {})
        hname     = hero_data.get("name", "")

        # Add to hero_info if missing (newly released hero with no stats yet)
        if hid not in hero_info:
            hero_info[hid] = {
                "heroName": hname, "heroPic": hero_data.get("head", ""),
                "appearanceRate": 0, "banRate": 0, "winRate": 0,
            }

        lane = ""
        for road in hero_data.get("roadsort", []):
            if isinstance(road, dict):
                lane = road.get("data", {}).get("road_sort_title", "")
                if lane: break

        ability_stats = [int(x) for x in hero_data.get("abilityshow", []) if str(x).isdigit()]
        hero_class    = next((s for s in hero_data.get("sortlabel", []) if s), "")
        speciality    = [s for s in hero_data.get("speciality", []) if s]
        story         = hero_data.get("story", "")

        relation = {}
        for key in ("strong", "weak", "assist"):
            rel = d.get("relation", {}).get(key)
            if rel:
                heroes = [heroid_to_name[hid2] for hid2 in rel.get("target_hero_id", []) if hid2 in heroid_to_name]
                desc   = rel.get("desc", "")
                if heroes:
                    relation[key] = {"heroes": heroes, "desc": desc}

        entry = hero_info[hid]
        entry["heroType"] = lane
        if hero_class:   entry["heroClass"]   = hero_class
        if speciality:   entry["speciality"]  = speciality
        if ability_stats:entry["abilityStats"] = ability_stats
        if relation:     entry["relation"]    = relation
        entry["difficulty"] = int(hero_data.get("difficulty") or 0)
        if story:        entry["story"] = story

    print(f"  {len(hero_info)} heroes with types + relations")

    # ── Step 3: skills ──
    skills_added = 0
    for record in raw_skills:
        hd       = record.get("data", {}).get("hero", {}).get("data", {})
        hid      = str(hd.get("heroid", ""))
        skill_groups = hd.get("heroskilllist", [])
        skills = []
        for group in skill_groups:
            for sk in group.get("skilllist", []):
                skills.append({
                    "name":    sk.get("skillname", ""),
                    "desc":    strip_html(sk.get("skilldesc", "")),
                    "cd_cost": sk.get("skillcd&cost", ""),
                    "tags":    [t["tagname"] for t in sk.get("skilltag", []) if "tagname" in t],
                })
        if hid in hero_info and skills:
            hero_info[hid]["skills"] = skills
            skills_added += 1
    print(f"  {skills_added} heroes with skills")

    # ── Step 4: counters + compatibility ──
    # Build name → id mapping for rekey
    name_to_id = {v.get("heroName", ""): k for k, v in hero_info.items()}
    id_to_name = {k: v.get("heroName", "") for k, v in hero_info.items()}

    def parse_sub(items):
        return {
            str(item["heroid"]): {
                "winRate":        round(item.get("hero_win_rate",     0) * 100, 4),
                "increaseWinRate":round(item.get("increase_win_rate", 0) * 100, 4),
                "timingCurve": {
                    "6_8":  round(item.get("min_win_rate6_8",   0) * 100, 2),
                    "8_10": round(item.get("min_win_rate8_10",  0) * 100, 2),
                    "10_12":round(item.get("min_win_rate10_12", 0) * 100, 2),
                    "12_14":round(item.get("min_win_rate12_14", 0) * 100, 2),
                    "14_16":round(item.get("min_win_rate14_16", 0) * 100, 2),
                    "16_18":round(item.get("min_win_rate16_18", 0) * 100, 2),
                    "18_20":round(item.get("min_win_rate18_20", 0) * 100, 2),
                    "20+":  round(item.get("min_win_rate20",    0) * 100, 2),
                }
            }
            for item in items if "heroid" in item
        }

    counters_added = 0
    for hid, data in raw_counters.items():
        if hid not in hero_info:
            hero_info[hid] = {}
        for label, field in (("counters", "hero_counter_info"), ("compat", "hero_compatibility_info")):
            if label in data:
                hero_info[hid][field] = {
                    "sub_hero":      parse_sub(data[label].get("sub_hero",      [])),
                    "sub_hero_last": parse_sub(data[label].get("sub_hero_last", [])),
                }
        counters_added += 1
    print(f"  {counters_added} heroes with counter/compat data")

    # ── Step 5: rekey by name, resolve numeric IDs in counter sub-lists ──
    named = {}
    for hid, hdata in hero_info.items():
        name = id_to_name.get(hid) or hdata.get("heroName", "")
        if not name:
            continue
        entry = dict(hdata)
        for field in ("hero_counter_info", "hero_compatibility_info"):
            if field in entry:
                for sub in ("sub_hero", "sub_hero_last"):
                    if sub in entry[field]:
                        entry[field][sub] = {
                            id_to_name[k]: v
                            for k, v in entry[field][sub].items()
                            if k in id_to_name
                        }
        named[name] = entry

    with open("hero_info.json", "w", encoding="utf-8") as f:
        json.dump({"hero_info": named}, f, indent=4, ensure_ascii=False)

    print(f"\nDone! hero_info.json written with {len(named)} heroes.")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "fetch":
        fetch()
    elif cmd == "build":
        build()
    else:
        fetch()
        print()
        build()
