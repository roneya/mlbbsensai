# MLBB Itemization Rules — Research Notes

Research notes driving the item-recommendation engine in `index.html`
(`recommendCounters()` / `CORE_BUILDS`). Sourced from MLBB item guides (S38/2025 meta).

---

## 1. Magic Defense — Athena's Shield vs Radiant Armor vs Oracle

All three are magic-defense, but counter **different magic threats**:

| Item | Build when | Why |
|------|-----------|-----|
| **Athena's Shield** | Enemy has **burst** magic — 1-2 high-nuke mages (Eudora, Aurora, Cyclops, Karina) | Flat 25% magic-damage reduction shield. Wins **short damage windows** — absorbs the single big combo. |
| **Radiant Armor** | Enemy has **multiple mages** OR **sustained/DoT magic** (Alice, Lylia, Zhuxin, Cecilion, Yve, Julian) | Stacking magic def (+5–8 per magic hit, up to 6). Wins **long damage windows** — ramps over 3s+ of continuous magic. |
| **Oracle** | Hero relies on **shields/HP regen** (you have heal/shield support, or hero like Esmeralda/Uranus) | +30% to received shield & HP regen + hybrid def. Defensive utility, not raw magic mitigation. |

**Rule of thumb:** 1 burst mage → Athena's. 2+ mages or DoT/poke → Radiant. Regen-based hero → Oracle.

---

## 2. Physical Defense — Antique Cuirass vs Dominance Ice vs Blade Armor

Different physical threats need different armor:

| Item | Counters | Key passive |
|------|----------|-------------|
| **Antique Cuirass** | **Skill-based** physical heroes (fighters/assassins: Chou, Paquito, Lancelot, Aulus, Yu Zhong) | Deter — enemy skill damage −6%/stack (−18% at 3 stacks). **Useless vs marksmen** (they use basic attacks). |
| **Blade Armor** | **Crit / basic-attack** marksmen (Layla, Miya, Melissa, Bruno, Clint) | Reflects physical damage + −20% crit damage. |
| **Dominance Ice** | **Attack-speed hyper-carries** (Wanwan, Karrie, Hanabi, Claude, Irithel) + **lifesteal/regen** heroes | −80% enemy attack speed in aura + Lifebane (−shield/regen). Doubles as anti-heal. |

**Rule of thumb:** physical *skill* damage → Antique Cuirass. physical *basic-attack/crit* → Blade Armor. *attack-speed/lifesteal* carry → Dominance Ice.

---

## 3. Penetration — only vs tanky frontlines

Build penetration when the enemy stacks defense (2+ tanks/durable fighters), and **match the hero's damage type**:

| Hero damage | Item |
|-------------|------|
| Physical (MM/Assassin/Fighter) | **Malefic Roar** (+30% phys pen, scales vs armor) |
| Magic (Mage) | **Divine Glaive** (+40% magic pen, scales vs magic def) / Genius Wand |

Do **not** give penetration to pure tanks/supports who deal no damage.

---

## 4. Anti-heal (Lifebane) — role-matched, build only ONE

Enemy sustain (Estes, Angela, Rafaela, Esmeralda, Uranus, Alice, lifesteal MM) → one anti-heal:

| Hero role | Anti-heal item |
|-----------|----------------|
| Tank / Support | **Dominance Ice** (defensive Lifebane) |
| Mage | **Glowing Wand** (magic Lifebane + Scorch DoT) |
| Marksman / Fighter / Assassin | **Sea Halberd** (physical Lifebane + Punish vs high-HP) |

⚠️ Lifebane is a **unique passive — does NOT stack.** Only ONE Lifebane item per hero, and the team only needs ONE source total. (Currently implemented role-aware.)

---

## 5. Anti-CC & survival — for squishy carries

| Threat | Item |
|--------|------|
| Heavy CC (3+ stuns/suppress) | **Tough Boots** (−25% CC duration), then Wind of Nature/Queen's Wings |
| Burst / dive on carry | **Wind of Nature** (phys immunity), **Winter Crown** (invulnerability), Queen's Wings (mage/fighter) |
| Enemy execute / heavy teamfight | **Immortality** (revive) — esp. tanks/supports |

---

## 6. ⚠️ Redundant items — NEVER build two that share a unique passive

Confirmed from our `items.json` passive text. Building two = **wasted gold** (passive doesn't stack):

| Shared passive | Items (pick ONE) |
|----------------|------------------|
| **Lifebane** (anti-heal) | Dominance Ice · Glowing Wand · Sea Halberd |
| **Armor Buster** (phys pen) | Malefic Roar · Malefic Gun |
| **Fortress Shield** (hybrid def stack) | Black Ice Shield · Dominance Ice |
| **Burning Soul** (HP% magic dmg) | Cursed Helmet · Molten Essence |
| **Deter** (skill dmg reduction) | Antique Cuirass · Dreadnaught Armor |
| **Gift** (HP/mana restore) | Clock of Destiny · Elegant Gem |
| **Impulse** (atk-speed stack) | Corrosion Scythe · Feather of Heaven · Swift Crossbow |
| **Lifeline** (low-HP shield) | Magic Blade · Rose Gold Meteor |

> Note: Dominance Ice carries BOTH Lifebane and Fortress Shield — so it conflicts with both anti-heal items AND Black Ice Shield. Treat it as the tank's all-in-one anti-carry/anti-heal pick.

---

## 7. Good synergies (build-together)

| Combo | Why |
|-------|-----|
| Clock of Destiny + Lightning Truncheon | Mana-scaling mage burst (Resonate triggers > 600 mana) |
| Holy Crystal + Divine Glaive | Multiplies magic power then ignores magic def |
| Endless Battle + Blade of Despair + Hunter Strike | Phys attack + pen + True damage proc (skill→basic weave fighters/MM) |
| Berserker's Fury + Windtalker | Crit chance + crit damage scaling for MM |
| Demon Hunter Sword + Haas' Claws | %HP on-hit shred + attack-speed/lifesteal vs tanks |

⚠️ **Endless Battle** only works on heroes that weave **skill → basic attack** (fighters, some MM). Bad on pure-burst mages who don't auto-attack.

---

## 8. Stat glossary (in `items.json` → `glossary`)

Plain-language definitions of every stat, used by:
- **items.html** — "📖 Stats Guide" toggle panel + hover tooltips on modal attributes
- **index.html** — hover tooltips on recommended build chips (stats + passive)

Key mechanics captured: CDR cap 40% (45% w/ Enchanted Talisman), flat pen applies
before %, Lifesteal = basic attacks only, Spell Vamp = skills only (AoE 25%),
crit = 2x default.

---

## Engine TODO (refinements from this research)

- [x] Anti-heal role-aware (Dominance Ice / Glowing Wand / Sea Halberd)
- [x] Stat glossary added to items.json + surfaced in both pages
- [ ] Split magic defense: Athena's (1 burst mage) vs Radiant Armor (2+ mages / DoT)
- [ ] Split physical defense: Antique Cuirass (skill heroes) vs Blade Armor (basic-attack/crit MM) vs Dominance Ice (attack-speed carry)
- [ ] Add redundant-passive guard so two same-passive items never both appear in a build
- [ ] Add Radiant Armor, Oracle, Queen's Wings, Demon Hunter Sword to relevant pools

---

## Sources
- [Synn — Radiant Armor vs Athena's Shield](https://synnmlbb.com/blog/radiant-armor-vs-athenas-shield-which-is-better)
- [vpesports — Athena's vs Radiant: when to buy](https://vpesports.com/athenas-shield-vs-radiant-armor-what-is-the-difference-and-when-to-buy-these-items)
- [mlbbcentral — Dominance Ice / Antique Cuirass / Blade Armor / Twilight](https://mlbbcentral.com/mlbb-physical-damage-diff/)
- [mlbbcentral — Antique Cuirass vs skill fighters](https://mlbbcentral.com/mlbb-item-antique-cuirass/)
- [mlbbcentral — Blade Armor guide](https://mlbbcentral.com/mlbb-item-blade-armor/)
- [ONE Esports — Blade Armor or Antique Cuirass](https://www.oneesports.gg/mobile-legends/blade-armor-antique-cuirass-mlbb/)
- [boosteria — MLBB Itemization Basics](https://boosteria.org/guides/mlbb-itemization-basics)
- [BitTopup — Item Build Guide 2025 S38](https://bittopup.com/article/Mobile-Legends-Item-Build-Guide-2025-Master-S38-Meta)
- [Fandom Wiki — Endless Battle](https://mobile-legends.fandom.com/wiki/Endless_Battle)
