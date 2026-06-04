import json
import re
import requests
import time

def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "")

HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://www.mobilelegends.com",
    "referer": "https://www.mobilelegends.com/",
    "user-agent": "Mozilla/5.0",
    "x-actid": "2669607",
    "x-appid": "2669606",
    "x-lang": "en"
}

BASE = "https://api.gms.moontontech.com/api/gms/source/2669606"


# ── Step 1: Fetch hero stats (listing.py) ────────────────────────────────────

def fetch_hero_stats():
    headers = {**HEADERS_BASE, "authorization": "rjYdVHiPEF5/4a447YaBXuB3OsA="}
    payload = {
        "pageSize": 200,
        "pageIndex": 1,
        "filters": [
            {"field": "bigrank", "operator": "eq", "value": "7"},
            {"field": "match_type", "operator": "eq", "value": 0}
        ],
        "sorts": [
            {"data": {"field": "main_hero_win_rate", "order": "desc"}, "type": "sequence"},
            {"data": {"field": "main_heroid", "order": "desc"}, "type": "sequence"}
        ]
    }

    response = requests.post(f"{BASE}/2756565", headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    records = response.json().get("data", {}).get("records", [])
    records = sorted(records, key=lambda r: r.get("data", {}).get("main_heroid", 0), reverse=True)

    hero_info = {}
    for record in records:
        data = record.get("data", {})
        hero_id = str(data.get("main_heroid"))
        hero = data.get("main_hero", {}).get("data", {})
        hero_info[hero_id] = {
            "heroName": hero.get("name", ""),
            "heroPic": hero.get("head", ""),
            "appearanceRate": round(data.get("main_hero_appearance_rate", 0) * 100, 4),
            "banRate": round(data.get("main_hero_ban_rate", 0) * 100, 4),
            "winRate": round(data.get("main_hero_win_rate", 0) * 100, 4)
        }

    print(f"Step 1: Fetched stats for {len(hero_info)} heroes")
    return hero_info, max(int(k) for k in hero_info)


# ── Step 2: Add hero type / lane (hero_type.py) ───────────────────────────────

def add_hero_types(hero_info):
    headers = {**HEADERS_BASE, "authorization": "CciHBEvFRqQNHGj2djxdUSja7W4="}
    payload = {
        "pageSize": 200,
        "pageIndex": 1,
        "filters": [
            {"field": "<hero.data.sortid>", "operator": "hasAnyOf", "value": [1, 2, 3, 4, 5, 6]},
            {"field": "<hero.data.roadsort>", "operator": "hasAnyOf", "value": [1, 2, 3, 4, 5]}
        ],
        "sorts": [{"data": {"field": "hero_id", "order": "desc"}, "type": "sequence"}]
    }

    response = requests.post(f"{BASE}/2756564", headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    records = response.json().get("data", {}).get("records", [])
    id_to_name = {hid: hdata["heroName"] for hid, hdata in hero_info.items() if hdata.get("heroName")}
    updated = 0

    for record in records:
        data = record.get("data", {})
        hero_id = str(data.get("hero_id"))
        hero_data = data.get("hero", {}).get("data", {})

        # Lane / role
        hero_type = ""
        for road in hero_data.get("roadsort", []):
            if isinstance(road, dict):
                hero_type = road.get("data", {}).get("road_sort_title", "")
                if hero_type:
                    break

        # Ability stats [offense, defense, utility, difficulty]
        ability_stats = [int(x) for x in hero_data.get("abilityshow", []) if str(x).isdigit()]

        # Curated relation: strong (counters), weak (countered by), assist (synergy)
        relation = {}
        for key in ("strong", "weak", "assist"):
            rel = data.get("relation", {}).get(key)
            if rel:
                heroes = [id_to_name[str(hid)] for hid in rel.get("target_hero_id", []) if str(hid) in id_to_name]
                desc = rel.get("desc", "")
                if heroes:
                    relation[key] = {"heroes": heroes, "desc": desc}

        if hero_id in hero_info:
            hero_info[hero_id]["heroType"] = hero_type
            hero_class = next((s for s in hero_data.get("sortlabel", []) if s), "")
            if hero_class:
                hero_info[hero_id]["heroClass"] = hero_class
            speciality = [s for s in hero_data.get("speciality", []) if s]
            if speciality:
                hero_info[hero_id]["speciality"] = speciality
            if ability_stats:
                hero_info[hero_id]["abilityStats"] = ability_stats
            if relation:
                hero_info[hero_id]["relation"] = relation
            hero_info[hero_id]["difficulty"] = int(hero_data.get("difficulty") or 0)
            story = hero_data.get("story", "")
            if story:
                hero_info[hero_id]["story"] = story
            updated += 1

    # ── Merge skill data from api_matchups.json (per-hero fetch has heroskilllist) ──
    try:
        with open("api_matchups.json") as f:
            matchup_records = json.load(f)
        id_to_name = {hid: hdata["heroName"] for hid, hdata in hero_info.items() if hdata.get("heroName")}
        skills_added = 0
        for record in matchup_records:
            hd = record.get("data", {}).get("hero", {}).get("data", {})
            hero_id = str(hd.get("heroid", ""))
            skill_groups = hd.get("heroskilllist", [])
            skills = []
            for group in skill_groups:
                for sk in group.get("skilllist", []):
                    skills.append({
                        "name": sk.get("skillname", ""),
                        "desc": strip_html(sk.get("skilldesc", "")),
                        "cd_cost": sk.get("skillcd&cost", ""),
                        "tags": [t["tagname"] for t in sk.get("skilltag", []) if "tagname" in t],
                    })
            if hero_id in hero_info and skills:
                hero_info[hero_id]["skills"] = skills
                skills_added += 1
        print(f"Step 2b: Merged skills for {skills_added} heroes from api_matchups.json")
    except FileNotFoundError:
        print("Step 2b: api_matchups.json not found — run fetch_hero_matchups.py first to get skill data")

    print(f"Step 2: Added hero types, ability stats, and relations for {updated} heroes")
    return hero_info


# ── Step 3: Add counter & compatibility info (processHeroes.py) ───────────────

def add_counter_and_compatibility(hero_info, max_hero_id):
    headers = {**HEADERS_BASE, "authorization": "bzSIpad3osbcCB/vIK+VlLmJde8="}

    def fetch_for_match_type(match_type):
        field_name = "hero_counter_info" if match_type == 0 else "hero_compatibility_info"
        for hero_id in range(1, max_hero_id + 1):
            payload = {
                "pageSize": 20,
                "pageIndex": 1,
                "filters": [
                    {"field": "match_type", "operator": "eq", "value": match_type},
                    {"field": "main_heroid", "operator": "eq", "value": str(hero_id)},
                    {"field": "bigrank", "operator": "eq", "value": 7}
                ],
                "sorts": []
            }
            try:
                response = requests.post(f"{BASE}/2756569", headers=headers, json=payload, timeout=30)
                response.raise_for_status()

                records = response.json().get("data", {}).get("records", [])
                if not records:
                    print(f"  No data for hero {hero_id}, match_type={match_type}")
                    continue

                data = records[0]["data"]

                def parse_sub(items):
                    return {
                        str(item["heroid"]): {
                            "winRate": round(item.get("hero_win_rate", 0) * 100, 4),
                            "increaseWinRate": round(item.get("increase_win_rate", 0) * 100, 4),
                            "timingCurve": {
                                "6_8":  round(item.get("min_win_rate6_8",  0) * 100, 2),
                                "8_10": round(item.get("min_win_rate8_10", 0) * 100, 2),
                                "10_12":round(item.get("min_win_rate10_12",0) * 100, 2),
                                "12_14":round(item.get("min_win_rate12_14",0) * 100, 2),
                                "14_16":round(item.get("min_win_rate14_16",0) * 100, 2),
                                "16_18":round(item.get("min_win_rate16_18",0) * 100, 2),
                                "18_20":round(item.get("min_win_rate18_20",0) * 100, 2),
                                "20+":  round(item.get("min_win_rate20",   0) * 100, 2),
                            }
                        }
                        for item in items if "heroid" in item
                    }

                sub_hero      = parse_sub(data.get("sub_hero", []))
                sub_hero_last = parse_sub(data.get("sub_hero_last", []))

                hero_key = str(hero_id)
                if hero_key not in hero_info:
                    hero_info[hero_key] = {}
                hero_info[hero_key][field_name] = {"sub_hero": sub_hero, "sub_hero_last": sub_hero_last}

                print(f"  Hero {hero_id} -> {field_name}")
                time.sleep(0.2)

            except Exception as e:
                print(f"  Failed hero {hero_id}: {e}")

    print("Step 3a: Fetching counter info (match_type=0)...")
    fetch_for_match_type(0)
    print("Step 3b: Fetching compatibility info (match_type=1)...")
    fetch_for_match_type(1)
    print("Step 3: Done")
    return hero_info


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    hero_info, max_hero_id = fetch_hero_stats()
    hero_info = add_hero_types(hero_info)
    hero_info = add_counter_and_compatibility(hero_info, max_hero_id)

    # Rekey everything by hero name instead of numeric ID
    id_to_name = {hid: hdata["heroName"] for hid, hdata in hero_info.items() if hdata.get("heroName")}

    named = {}
    for hid, hdata in hero_info.items():
        name = id_to_name.get(hid)
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

    print(f"\nDone! hero_info.json written with {len(named)} heroes (keyed by name).")
