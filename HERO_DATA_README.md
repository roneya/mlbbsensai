# Hero Data Structure Documentation

## hero_info.json Structure

### Counter Information (`hero_counter_info`)

```json
"hero_counter_info": {
    "sub_hero": {
        "88": 54.1095,
        "132": 53.6604
    },
    "sub_hero_last": {
        "70": 53.8076,
        "33": 51.8045
    }
}
```

**`sub_hero`**: Heroes that COUNTER this hero
- If enemy picks hero 109, these heroes (88, 132, etc.) counter hero 109
- Use this to recommend counter picks
- Higher winrate = stronger counter

**`sub_hero_last`**: Heroes that this hero is COUNTERED BY
- These heroes counter the selected hero (you perform poorly against them)
- Use this to avoid bad matchups

### Compatibility Information (`hero_compatibility_info`)

```json
"hero_compatibility_info": {
    "sub_hero": {
        "121": 53.7804,
        "101": 53.7535
    },
    "sub_hero_last": {
        "121": 53.3918,
        "48": 52.3432
    }
}
```

**`sub_hero`**: Heroes that work WELL with this hero in same team
- Good synergy / high winrate together
- Use for pair recommendations

**`sub_hero_last`**: Heroes that work POORLY with this hero in same team
- Bad synergy / low winrate together
- Avoid pairing these heroes

### Other Fields

- `heroName`: Hero display name
- `heroPic`: Hero image URL
- `heroType`: Role (Roam, Mid, Gold, EXP, Jungle)
- `winRate`: Overall win percentage
- `banRate`: How often banned
- `appearanceRate`: Pick rate / popularity
