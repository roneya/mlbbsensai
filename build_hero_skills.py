"""
Extracts hero skill/ability data from api_matchups.json into hero_skills.json.
Run after fetch_hero_matchups.py (or re-fetch by running that script first).

Output structure:
{
  "hero_skills": {
    "Miya": {
      "heroid": 1,
      "skills": [
        {
          "name": "Moon Blessing",
          "desc": "...",
          "cd_cost": "",
          "icon": "https://...",
          "tags": ["Buff"]
        },
        ...
      ]
    },
    ...
  }
}
"""

import json, re

def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "")

with open("api_matchups.json") as f:
    raw = json.load(f)

hero_skills = {}

for hero_id_str, record in raw["heroes"].items():
    if record is None:
        continue

    hero_data = record.get("data", {}).get("hero", {}).get("data", {})
    name = hero_data.get("name")
    heroid = hero_data.get("heroid")
    skill_groups = hero_data.get("heroskilllist", [])

    if not name:
        continue

    skills = []
    for group in skill_groups:
        for skill in group.get("skilllist", []):
            skills.append({
                "name": skill.get("skillname", ""),
                "desc": strip_html(skill.get("skilldesc", "")),
                "cd_cost": skill.get("skillcd&cost", ""),
                "icon": skill.get("skillicon", ""),
                "tags": [t["tagname"] for t in skill.get("skilltag", []) if "tagname" in t],
            })

    hero_skills[name] = {
        "heroid": heroid,
        "skills": skills,
    }

output = {"hero_skills": hero_skills}
with open("hero_skills.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Done. {len(hero_skills)} heroes written to hero_skills.json")

# Quick preview
for name, data in list(hero_skills.items())[:2]:
    print(f"\n{name} ({data['heroid']}) — {len(data['skills'])} skills:")
    for s in data["skills"]:
        print(f"  [{', '.join(s['tags']) or 'no tag'}] {s['name']}  {s['cd_cost']}")
