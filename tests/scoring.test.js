const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Extracts all scoring functions from index.html into a vm context.
// HEROES is injected as a parameter so each test can control the data.
function loadFns(HEROES) {
  const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  const blocks = [...html.matchAll(/<script(?! src)>([\s\S]*?)<\/script>/g)];
  const mainJs = blocks[blocks.length - 1][1];

  // Remove the `let HEROES = {}` declaration so functions reference the
  // context-level HEROES we inject instead of a closed-over empty binding.
  const patchedJs = mainJs.replace(/let HEROES\s*=\s*\{\};/, '');

  const context = {
    HEROES,
    document: { addEventListener: () => {}, getElementById: () => null },
    window: { dataLayer: [] },
    fetch: async () => {},
    console,
  };
  vm.createContext(context);
  vm.runInContext(patchedJs, context);

  return {
    computeScore:         context.computeScore,
    heroPlaystyle:        context.heroPlaystyle,
    buildExplanation:     context.buildExplanation,
    missingRoles:         context.missingRoles,
    computeAdjustedScore: context.computeAdjustedScore,
  };
}

// ── Minimal hero fixtures ──────────────────────────────────────────────────
const LOLITA = {
  heroName: 'Lolita', heroType: 'Roam',
  winRate: 56.37, appearanceRate: 0.10, banRate: 0.05,
  heroPic: '',
  hero_compatibility_info: {
    sub_hero:      { Kagura: { winRate: 52.0, increaseWinRate: 2.72, timingCurve: {} } },
    sub_hero_last: {},
  },
  hero_counter_info: {
    sub_hero:      { Cyclops: { winRate: 51.8, increaseWinRate: 7.47, timingCurve: {} } },
    sub_hero_last: { Yve: { winRate: 54.0, increaseWinRate: -5.88, timingCurve: {} } },
  },
};

const CYCLOPS = {
  heroName: 'Cyclops', heroType: 'Mid Lane',
  winRate: 51.72, appearanceRate: 0.12, banRate: 0.02,
  heroPic: '',
  hero_compatibility_info: { sub_hero: {}, sub_hero_last: {} },
  hero_counter_info: {
    sub_hero:      {},
    sub_hero_last: { Lolita: { winRate: 56.4, increaseWinRate: -7.47, timingCurve: {} } },
  },
};

const YVE = {
  heroName: 'Yve', heroType: 'Mid Lane',
  winRate: 53.0, appearanceRate: 0.09, banRate: 0.01,
  heroPic: '',
  hero_compatibility_info: { sub_hero: {}, sub_hero_last: {} },
  hero_counter_info: {
    sub_hero:      { Lolita: { winRate: 56.4, increaseWinRate: 5.88, timingCurve: {} } },
    sub_hero_last: {},
  },
};

const HEROES = { Lolita: LOLITA, Cyclops: CYCLOPS, Yve: YVE };

// ── computeScore ──────────────────────────────────────────────────────────
test('computeScore: no allies no enemies returns base score only', () => {
  const { computeScore } = loadFns({ Lolita: LOLITA });
  const score = computeScore('Lolita', [], []);
  const expected = LOLITA.winRate + LOLITA.appearanceRate * 100;
  assert.ok(score > expected - 5 && score < expected + 35,  // role bonus for Roam (+30)
    `score ${score} out of expected range around ${expected}`);
});

test('computeScore: good counter matchup raises score above baseline', () => {
  const { computeScore } = loadFns(HEROES);
  const baseline  = computeScore('Lolita', [], []);
  const withEnemy = computeScore('Lolita', [], ['Cyclops']);
  assert.ok(withEnemy > baseline,
    `score with countered enemy (${withEnemy}) should exceed baseline (${baseline})`);
});

test('computeScore: bad matchup lowers score below baseline', () => {
  const { computeScore } = loadFns(HEROES);
  const baseline  = computeScore('Lolita', [], []);
  const withEnemy = computeScore('Lolita', [], ['Yve']);
  assert.ok(withEnemy < baseline,
    `score when countered by enemy (${withEnemy}) should be below baseline (${baseline})`);
});

test('computeScore: good matchup scores higher than bad matchup', () => {
  const { computeScore } = loadFns(HEROES);
  const good = computeScore('Lolita', [], ['Cyclops']);
  const bad  = computeScore('Lolita', [], ['Yve']);
  assert.ok(good > bad,
    `good matchup score (${good}) should exceed bad matchup score (${bad})`);
});

// ── heroPlaystyle ─────────────────────────────────────────────────────────
test('heroPlaystyle: good matchup enemy shifts label toward Aggressive', () => {
  const { heroPlaystyle } = loadFns(HEROES);
  const noEnemy   = heroPlaystyle('Lolita', []);
  const withGood  = heroPlaystyle('Lolita', ['Cyclops']);
  // noEnemy val = (56.37 - 50) * 1.5 ≈ 9.5 → already Aggressive
  // withGood adds +7.47 → even more so; at minimum it stays Aggressive
  assert.equal(withGood.label, 'Aggressive');
  assert.equal(noEnemy.label, 'Aggressive');
});

test('heroPlaystyle: bad matchup enemy shifts label toward Safe', () => {
  const { heroPlaystyle } = loadFns({ ...HEROES,
    // Use a hero with neutral base WR so enemy matchup is decisive
    Neutral: {
      heroName: 'Neutral', heroType: 'Gold Lane',
      winRate: 50, appearanceRate: 0, banRate: 0, heroPic: '',
      hero_compatibility_info: { sub_hero: {}, sub_hero_last: {} },
      hero_counter_info: {
        sub_hero:      {},
        sub_hero_last: { Yve: { winRate: 54.0, increaseWinRate: -8.0, timingCurve: {} } },
      },
    },
  });
  const style = heroPlaystyle('Neutral', ['Yve']);
  assert.equal(style.label, 'Safe');
});

// ── buildExplanation ──────────────────────────────────────────────────────
test('buildExplanation: produces Counters note when hero beats an enemy', () => {
  const { buildExplanation } = loadFns(HEROES);
  const notes = buildExplanation('Lolita', [], ['Cyclops']);
  const countersNote = notes.find(n => n.t.includes('Counters Cyclops'));
  assert.ok(countersNote, `expected a "Counters Cyclops" note, got: ${JSON.stringify(notes)}`);
  assert.ok(countersNote.pos, 'Counters note should be positive');
});

test('buildExplanation: produces Countered-by note when enemy beats hero', () => {
  const { buildExplanation } = loadFns(HEROES);
  const notes = buildExplanation('Lolita', [], ['Yve']);
  const counteredNote = notes.find(n => n.t.includes('Countered by Yve'));
  assert.ok(counteredNote, `expected a "Countered by Yve" note, got: ${JSON.stringify(notes)}`);
  assert.ok(!counteredNote.pos, 'Countered-by note should be negative');
});

test('buildExplanation: fills role note appears when role is missing from allies', () => {
  const { buildExplanation } = loadFns(HEROES);
  // No Roam ally — Lolita fills the role
  const notes = buildExplanation('Lolita', [], []);
  const roleNote = notes.find(n => n.t.includes('Fills'));
  assert.ok(roleNote, `expected a role fill note, got: ${JSON.stringify(notes)}`);
  assert.ok(roleNote.pos, 'role fill note should be positive');
});

test('buildExplanation: role overlap note appears when role already in allies', () => {
  const { buildExplanation } = loadFns({ ...HEROES,
    OtherRoam: {
      heroName: 'OtherRoam', heroType: 'Roam',
      winRate: 50, appearanceRate: 0, banRate: 0, heroPic: '',
      hero_compatibility_info: { sub_hero: {}, sub_hero_last: {} },
      hero_counter_info: { sub_hero: {}, sub_hero_last: {} },
    },
  });
  const notes = buildExplanation('Lolita', ['OtherRoam'], []);
  const overlapNote = notes.find(n => n.t.includes('Overlaps'));
  assert.ok(overlapNote, `expected an overlap note, got: ${JSON.stringify(notes)}`);
  assert.ok(!overlapNote.pos, 'role overlap note should be negative');
});

// ── missingRoles ──────────────────────────────────────────────────────────
test('missingRoles: returns all 5 roles when allies is empty', () => {
  const { missingRoles } = loadFns(HEROES);
  const missing = missingRoles([]);
  assert.deepEqual(
    [...missing].sort(),
    ['Exp Lane', 'Gold Lane', 'Jungle', 'Mid Lane', 'Roam']
  );
});

test('missingRoles: Roam absent from result when a Roam ally is present', () => {
  const { missingRoles } = loadFns(HEROES);
  const missing = missingRoles(['Lolita']); // Lolita heroType='Roam'
  assert.ok(!missing.includes('Roam'), `Roam should be filled: ${missing}`);
  assert.equal(missing.length, 4);
});

test('missingRoles: returns empty array when all 5 roles are filled', () => {
  const FULL = {
    ...HEROES,
    G: { heroName:'G', heroType:'Gold Lane', winRate:50, appearanceRate:0, banRate:0, heroPic:'',
         hero_compatibility_info:{sub_hero:{},sub_hero_last:{}},
         hero_counter_info:{sub_hero:{},sub_hero_last:{}} },
    E: { heroName:'E', heroType:'Exp Lane', winRate:50, appearanceRate:0, banRate:0, heroPic:'',
         hero_compatibility_info:{sub_hero:{},sub_hero_last:{}},
         hero_counter_info:{sub_hero:{},sub_hero_last:{}} },
    J: { heroName:'J', heroType:'Jungle', winRate:50, appearanceRate:0, banRate:0, heroPic:'',
         hero_compatibility_info:{sub_hero:{},sub_hero_last:{}},
         hero_counter_info:{sub_hero:{},sub_hero_last:{}} },
  };
  const { missingRoles } = loadFns(FULL);
  // Lolita=Roam, Cyclops=Mid Lane, G=Gold Lane, E=Exp Lane, J=Jungle
  assert.equal(missingRoles(['Lolita','Cyclops','G','E','J']).length, 0);
});
