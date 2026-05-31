const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadDetectGamePhase(HEROES) {
  const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  const match = html.match(/function detectGamePhase\(allies, enemies\) {[\s\S]*?\n}/);
  if (!match) throw new Error('detectGamePhase block not found');

  const source = `${match[0]}\nthis.detectGamePhase = detectGamePhase;`;
  const context = { HEROES, console };
  vm.createContext(context);
  vm.runInContext(source, context);
  return context.detectGamePhase;
}

test('ignores sub_hero counter-pick windows when classifying enemy phase', () => {
  const detectGamePhase = loadDetectGamePhase({
    Alpha: {
      hero_counter_info: {
        sub_hero: {
          Counter1: { min_win_rate18_20: 0.58, min_win_rate20: 0.57, min_win_rate10_12: 0.56 }
        },
        sub_hero_last: {}
      }
    },
    Beta: {
      hero_counter_info: {
        sub_hero: {
          Counter2: { min_win_rate18_20: 0.59, min_win_rate20: 0.58, min_win_rate10_12: 0.55 }
        },
        sub_hero_last: {}
      }
    }
  });

  assert.equal(detectGamePhase([], ['Alpha', 'Beta']), 'balanced');
});

test('uses sub_hero_last windows to detect early-game enemy bullies', () => {
  const detectGamePhase = loadDetectGamePhase({
    Alpha: {
      hero_counter_info: {
        sub_hero: {},
        sub_hero_last: {
          Target1: { min_win_rate10_12: 0.44, min_win_rate20: 0.49 }
        }
      }
    },
    Beta: {
      hero_counter_info: {
        sub_hero: {},
        sub_hero_last: {
          Target2: { min_win_rate10_12: 0.45, min_win_rate20: 0.50 }
        }
      }
    }
  });

  assert.equal(detectGamePhase([], ['Alpha', 'Beta']), 'late');
});

test('uses 18-20 and 20+ windows from sub_hero_last to detect scaling enemies', () => {
  const detectGamePhase = loadDetectGamePhase({
    Alpha: {
      hero_counter_info: {
        sub_hero: {},
        sub_hero_last: {
          Target1: { min_win_rate18_20: 0.47 }
        }
      }
    },
    Beta: {
      hero_counter_info: {
        sub_hero: {},
        sub_hero_last: {
          Target2: { min_win_rate20: 0.47 }
        }
      }
    }
  });

  assert.equal(detectGamePhase([], ['Alpha', 'Beta']), 'early');
});
