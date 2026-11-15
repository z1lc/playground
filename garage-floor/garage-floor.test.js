import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const coreMatch = html.match(/<script id="garage-core">([\s\S]*?)<\/script>/);
if (!coreMatch) throw new Error('Inline garage core was not found');
const sandbox = {};
vm.runInNewContext(coreMatch[1], sandbox);
const G = sandbox.GarageFloor;
const plain = v => JSON.parse(JSON.stringify(v));

const floor = (over = {}) => ({
  id: 'x', name: 'X', family: 'penetrating', role: 'floor',
  cost: { low: 100, high: 300, basis: 'DIY materials' }, lifespan: { low: 4, high: 6 },
  health: { score: 5 }, durability: { score: 3 }, effort: { score: 4 },
  ...over,
});

describe('data', () => {
  it('passes the built-in consistency check', () => {
    expect(plain(G.selfCheck(G.TYPES))).toEqual([]);
  });

  it('has ten floor options (incl. the baseline) and the two gym mats', () => {
    expect(G.floors(G.TYPES)).toHaveLength(10);
    expect(G.TYPES.filter(t => t.role === 'baseline').map(t => t.id)).toEqual(['bare']);
    expect(G.TYPES.filter(t => t.role === 'mat')).toHaveLength(2);
  });

  it('puts every family on the Learn tab with at least two floor types', () => {
    for (const f of G.FAMILIES) {
      expect(G.TYPES.filter(t => t.family === f.id && t.role === 'floor').length, f.id).toBeGreaterThanOrEqual(2);
    }
  });

  it('uses https sources only and no duplicate URLs within a type', () => {
    for (const t of G.TYPES) {
      const urls = t.sources.map(s => s.url);
      expect(new Set(urls).size, t.id).toBe(urls.length);
      for (const u of urls) expect(u.startsWith('https://'), u).toBe(true);
    }
  });

  it('catches broken entries in selfCheck', () => {
    const bad = [floor({ id: 'a', sources: [] }), floor({ id: 'a', role: 'nope', health: { score: 9 } })];
    const problems = plain(G.selfCheck(bad));
    expect(problems.some(p => p.includes('duplicate id'))).toBe(true);
    expect(problems.some(p => p.includes('bad role'))).toBe(true);
    expect(problems.some(p => p.includes('bad health'))).toBe(true);
    expect(problems.some(p => p.includes('no source covers health'))).toBe(true);
  });

  it('requires health details for every exposure route', () => {
    for (const t of G.TYPES) for (const k of ['cured', 'air', 'skin', 'mouth']) expect(t.health[k], t.id + ' ' + k).toBeTruthy();
    const noSkin = { ...G.TYPES[1], id: 'noskin', health: { ...G.TYPES[1].health, skin: '' } };
    expect(plain(G.selfCheck([noSkin])).some(p => p.includes('bad health'))).toBe(true);
  });
});

describe('cost math', () => {
  it('counts applications over ten years from the lifespan midpoint', () => {
    expect(G.applications(floor({ lifespan: { low: 4, high: 6 } }))).toBe(2);
    expect(G.applications(floor({ lifespan: { low: 1, high: 3 } }))).toBe(5);
    expect(G.applications(floor({ lifespan: { low: 10, high: 20 } }))).toBe(1);
    expect(G.applications(floor({ cost: { low: 0, high: 0, basis: 'n/a' }, lifespan: null }))).toBe(0);
  });

  it('multiplies the upfront midpoint by the applications', () => {
    expect(G.tenYearCost(floor())).toBe(400);
    expect(G.tenYearCost(floor({ cost: { low: 3000, high: 5000, basis: 'pro installed' }, lifespan: { low: 15, high: 20 } }))).toBe(4000);
  });

  it('buckets ten-year cost into a 1–5 score with inclusive edges', () => {
    const at = c => G.costScore(floor({ cost: { low: c, high: c, basis: 'DIY materials' }, lifespan: { low: 20, high: 20 } }));
    expect([at(0), at(500), at(501), at(1000), at(1001), at(2000), at(3500), at(3501)]).toEqual([5, 5, 4, 4, 3, 3, 2, 1]);
  });

  it('formats money and ranges', () => {
    expect(G.fmtMoney(0)).toBe('$0');
    expect(G.fmtMoney(234)).toBe('~$230');
    expect(G.fmtMoney(4321)).toBe('~$4,300');
    expect(G.fmtRange({ low: 120, high: 280 })).toBe('$120–280');
    expect(G.fmtRange({ low: 1850, high: 3100 })).toBe('$1,850–3,100');
    expect(G.fmtLife({ low: 5, high: 7 })).toBe('5–7 yrs');
    expect(G.fmtLife(null)).toBe('n/a');
  });
});

describe('scoring', () => {
  it('scores a perfect option 100 and returns 0 when every weight is 0', () => {
    const perfect = floor({ health: { score: 5 }, durability: { score: 5 }, effort: { score: 5 }, cost: { low: 0, high: 0, basis: 'n/a' } });
    expect(G.matchScore(perfect, { health: 5, durability: 3, cost: 3, effort: 1 })).toBe(100);
    expect(G.matchScore(perfect, { health: 0, durability: 0, cost: 0, effort: 0 })).toBe(0);
  });

  it('weights criteria proportionally', () => {
    const t = floor({ health: { score: 5 }, durability: { score: 1 }, effort: { score: 1 }, cost: { low: 9000, high: 9000, basis: 'pro installed' }, lifespan: { low: 20, high: 20 } });
    expect(G.matchScore(t, { health: 1, durability: 0, cost: 0, effort: 0 })).toBe(100);
    expect(G.matchScore(t, { health: 1, durability: 1, cost: 0, effort: 0 })).toBe(60);
  });

  it('ranks only floors, highest match first, ties broken by health', () => {
    const ranked = G.rank(G.TYPES, G.DEFAULT_WEIGHTS);
    expect(ranked).toHaveLength(10);
    expect(ranked.every(r => r.type.role !== 'mat')).toBe(true);
    for (let i = 1; i < ranked.length; i++) {
      const a = ranked[i - 1], b = ranked[i];
      expect(a.score > b.score || (a.score === b.score && a.type.health.score >= b.type.health.score)).toBe(true);
    }
  });

  it('assigns health tiers from the health score', () => {
    expect(G.healthTier(floor({ health: { score: 5 } })).id).toBe('inert');
    expect(G.healthTier(floor({ health: { score: 4 } })).id).toBe('minor');
    expect(G.healthTier(floor({ health: { score: 3 } })).id).toBe('concern');
    expect(G.healthTier(floor({ health: { score: 2 } })).id).toBe('concern');
  });

  it('defines presets over every criterion, with Health first equal to the defaults', () => {
    for (const p of G.PRESETS) {
      for (const c of G.CRITERIA) expect(Number.isInteger(p.weights[c.key]), p.id + c.key).toBe(true);
    }
    expect(G.sameWeights(G.PRESETS.find(p => p.id === 'health').weights, G.DEFAULT_WEIGHTS)).toBe(true);
  });
});

describe('data backs the written takeaways', () => {
  const byId = Object.fromEntries(G.TYPES.map(t => [t.id, t]));
  const pen = G.TYPES.filter(t => t.family === 'penetrating');

  it('ranks the penetrating sealers top three at the default weights', () => {
    const top3 = G.rank(G.TYPES, G.DEFAULT_WEIGHTS).slice(0, 3).map(r => r.type.family);
    expect(top3).toEqual(['penetrating', 'penetrating', 'penetrating']);
  });

  it('keeps every penetrating sealer under $750 over ten years, with the combo most protective', () => {
    for (const t of pen) expect(G.tenYearCost(t), t.id).toBeLessThan(750);
    expect(Math.max(...pen.map(t => t.durability.protection))).toBe(byId.combo.durability.protection);
  });

  it('makes acrylic and DIY epoxy cost more over ten years than any penetrating sealer, with less protection', () => {
    const maxPen = Math.max(...pen.map(G.tenYearCost));
    const minPenProt = Math.min(...pen.map(t => t.durability.protection));
    for (const id of ['acrylic', 'epoxy-kit']) {
      expect(G.tenYearCost(byId[id]), id).toBeGreaterThan(maxPen);
      expect(byId[id].durability.protection, id).toBeLessThan(minPenProt);
    }
  });

  it('gives polyaspartic the top protection and a $3,000–5,500 range', () => {
    const floors = G.floors(G.TYPES);
    expect(Math.max(...floors.map(t => t.durability.protection))).toBe(byId.polyaspartic.durability.protection);
    expect(byId.polyaspartic.cost.low).toBeGreaterThanOrEqual(3000);
    expect(byId.polyaspartic.cost.high).toBeLessThanOrEqual(5600);
  });

  it('has PVC as the only floor scored 2 on health', () => {
    expect(G.floors(G.TYPES).filter(t => t.health.score <= 2).map(t => t.id)).toEqual(['pvc-tiles']);
  });

  it('places map labels only for real floor ids and modes', () => {
    const ids = new Set(G.floors(G.TYPES).map(t => t.id));
    for (const [id, modes] of Object.entries(G.MAP_LABELS)) {
      expect(ids.has(id), id).toBe(true);
      for (const m of Object.keys(modes)) expect(G.MAP_MODES.includes(m), m).toBe(true);
    }
  });
});

describe('gym mats', () => {
  const mats = G.MAT_PRODUCTS;
  const byId = Object.fromEntries(mats.map(p => [p.id, p]));
  const mat = (over = {}) => ({
    id: 'm', name: 'M', maker: 'Maker', summary: 's', material: 'm', format: 'f', gym: 'g', garage: 'g', madeIn: 'x',
    construction: 'solid', tire: 'none', tireText: 'None', grade: 'C', gradeWhy: 'why',
    price: { perSqft: 5, note: 'n' }, docs: [], contaminantTests: [], flags: [],
    buy: [{ label: 'Shop', url: 'https://example.com' }],
    sources: [{ label: 'S', url: 'https://example.com/s', covers: ['material', 'price'] }],
    ...over,
  });

  it('passes the built-in consistency check', () => {
    expect(plain(G.matSelfCheck(mats, G.LABELS))).toEqual([]);
  });

  it('catches broken entries and grades the paperwork does not support', () => {
    const bad = [
      mat({ id: 'a', grade: 'A' }),
      mat({ id: 'a', construction: 'foam', tire: 'lots' }),
      mat({ id: 'b', grade: 'C', docs: [{ kind: 'emissions', label: 'cert', status: 'verified', url: 'https://x.org' }] }),
      mat({ id: 'c', grade: 'B', sources: [] }),
    ];
    const problems = plain(G.matSelfCheck(bad, [{ id: 'l', kind: 'test', routes: { air: 'huge', skin: 'high', mouth: 'high' }, name: 'L', tests: 't', misses: 'm', source: { label: 's', url: 'https://x.org' } }]));
    expect(problems.some(p => p.includes('duplicate id'))).toBe(true);
    expect(problems.some(p => p.includes('grade A needs a verified ingredient list'))).toBe(true);
    expect(problems.some(p => p.includes('bad construction'))).toBe(true);
    expect(problems.some(p => p.includes('bad tire'))).toBe(true);
    expect(problems.some(p => p.includes('grade C with a verified document'))).toBe(true);
    expect(problems.some(p => p.includes('grade B needs'))).toBe(true);
    expect(problems.some(p => p.includes('[mat c] no source covers price'))).toBe(true);
    expect(problems.some(p => p.includes('[label l] incomplete'))).toBe(true);
  });

  it('prices the matted area from the per-square-foot price', () => {
    expect(G.MAT_AREA.sqft).toBe(308);
    expect(G.matCost(mat({ price: { perSqft: 2.5, note: 'n' } }))).toBe(770);
    expect(G.matCost(byId.triumph)).toBe(6314);
  });

  it('sorts best-for-kids by tire content, then proof grade, then price', () => {
    const ids = G.sortMats(mats, 'kids', false).map(p => p.id);
    expect(ids[0]).toBe('triumph');
    expect(ids).toHaveLength(mats.length);
    const order = G.TIRE_ORDER;
    const rows = G.sortMats(mats, 'kids', false);
    for (let i = 1; i < rows.length; i++) {
      expect(order.indexOf(rows[i - 1].tire)).toBeLessThanOrEqual(order.indexOf(rows[i].tire));
    }
    expect(rows[rows.length - 1].tire).toBe('unknown');
  });

  it('sorts by price ascending and hides mostly-tire products on request', () => {
    const prices = G.sortMats(mats, 'price', false).map(p => p.price.perSqft);
    expect(prices).toEqual([...prices].sort((a, b) => a - b));
    const shown = G.sortMats(mats, 'kids', true);
    expect(shown.some(p => p.tire === 'most')).toBe(false);
    expect(shown.length).toBe(mats.filter(p => p.tire !== 'most').length);
    expect(mats.length).toBe(13);
  });

  it('resolves the three picks from the data', () => {
    expect(G.MAT_PICKS.map(pk => G.pickFor(pk.rule).id)).toEqual(['triumph', 'pavigym', 'ecore-fit']);
    expect(mats.filter(p => p.grade === 'A').map(p => p.id)).toEqual(['triumph']);
    expect(G.pickFor('nope')).toBe(null);
  });

  it('has no product publishing contaminant tests, which the callout states', () => {
    for (const p of mats) expect(p.contaminantTests, p.id).toEqual([]);
  });

  it('rates labels per exposure route, with only lab tests rated high', () => {
    const by = Object.fromEntries(G.LABELS.map(l => [l.id, l.routes]));
    for (const l of G.LABELS) {
      for (const r of ['air', 'skin', 'mouth']) if (l.routes[r] === 'high') expect(l.kind, l.id + ' ' + r).toBe('test');
    }
    expect(plain(by.floorscore)).toEqual({ air: 'some', skin: 'none', mouth: 'none' });
    expect(by.greenguard.air).toBe('some');
    expect(by['reach-pah'].skin).toBe('high');
    expect(by['reach-pah'].air).toBe('none');
    for (const g of G.LABEL_GROUPS) expect(G.LABELS.some(l => l.kind === g.kind), g.kind).toBe(true);
  });

  it('groups supplier questions by route and keeps the old essentials', () => {
    const groups = new Set(G.MAT_QUESTIONS.map(q => q.group));
    expect([...groups]).toEqual(G.Q_GROUPS.map(g => g.id));
    const text = G.MAT_QUESTIONS.map(q => q.q).join(' ');
    for (const word of ['PAHs', 'EN 71-3', 'EN 71-12', 'TVOC', 'biocide', 'natural rubber']) expect(text, word).toContain(word);
  });

  it('sources every exposure tip or marks it as our own reasoning', () => {
    expect(G.EXPOSURE_TIPS.map(g => g.route)).toEqual(['air', 'skin', 'mouth']);
    for (const g of G.EXPOSURE_TIPS) for (const t of g.tips) expect(t.source === null || t.source.url.startsWith('https://'), t.text).toBe(true);
  });

  it('reports per-route evidence from the documents', () => {
    const ev = id => plain(G.routeEvidence(byId[id]));
    expect(ev('triumph')).toEqual({ air: 'verified', skin: 'none', mouth: 'none' });
    expect(ev('pavigym').air).toBe('unconfirmed');
    expect(ev('aktivlok').air).toBe('self');
    expect(ev('fitlock').air).toBe('not-found');
    expect(ev('lesol').air).toBe('none');
    for (const p of mats) {
      const e = G.routeEvidence(p);
      expect([e.skin, e.mouth], p.id).toEqual(['none', 'none']);
    }
    expect(mats.filter(p => G.routeEvidence(p).air === 'verified').map(p => p.id)).toEqual(['triumph', 'hero', 'ecore-fit', 'survivor']);
  });

  it('breaks kids-sort ties on air evidence: verified before self-declared', () => {
    const order = G.sortMats(mats, 'kids', false).map(p => p.id);
    expect(order.indexOf('ecore-fit')).toBeLessThan(order.indexOf('aktivlok'));
    expect(order.indexOf('survivor')).toBeLessThan(order.indexOf('aktivlok'));
    expect(order.indexOf('survivor')).toBeLessThan(order.indexOf('aktivpro'));
  });

  it('tags every product concern with a route', () => {
    for (const p of mats) for (const f of p.flags) expect(f.routes.every(r => ['air', 'skin', 'mouth', 'other'].includes(r)), p.id).toBe(true);
    expect(byId.triumph.flags.some(f => f.routes.includes('skin'))).toBe(true);
    expect(byId.survivor.flags.some(f => f.routes.includes('skin'))).toBe(true);
  });

  it('lists every construction type with at least one product in the table', () => {
    for (const c of G.CONSTRUCTIONS) expect(mats.some(p => p.construction === c.id), c.id).toBe(true);
  });
});

describe('persisted state', () => {
  it('includes the mats tab', () => {
    expect(G.TABS).toEqual(['learn', 'map', 'compare', 'mats']);
    expect(G.loadState(JSON.stringify({ tab: 'mats' })).tab).toBe('mats');
  });

  it('keeps valid mat settings and drops invalid ones', () => {
    const ok = G.loadState(JSON.stringify({ matSort: 'price', matHideTire: true, matExpandedId: 'pavigym' }));
    expect([ok.matSort, ok.matHideTire, ok.matExpandedId]).toEqual(['price', true, 'pavigym']);
    const bad = G.loadState(JSON.stringify({ matSort: 'odor', matHideTire: 'yes', matExpandedId: 'silane' }));
    expect([bad.matSort, bad.matHideTire, bad.matExpandedId]).toEqual(['kids', false, null]);
  });

  it('falls back to defaults for empty or broken storage', () => {
    expect(plain(G.loadState(null))).toEqual(plain(G.defaultState()));
    expect(plain(G.loadState('{not json'))).toEqual(plain(G.defaultState()));
    expect(plain(G.loadState('42'))).toEqual(plain(G.defaultState()));
  });

  it('keeps valid fields and drops invalid ones', () => {
    const id = G.floors(G.TYPES)[1].id;
    const s = G.loadState(JSON.stringify({
      tab: 'map', weights: { health: 2, durability: 9, cost: 'x', effort: 0 },
      matsOn: false, expandedId: id, mapY: 'lifespan', mapSelectedId: 'nope',
    }));
    expect(s.tab).toBe('map');
    expect(plain(s.weights)).toEqual({ health: 2, durability: 3, cost: 3, effort: 0 });
    expect(s.matsOn).toBe(false);
    expect(s.expandedId).toBe(id);
    expect(s.mapY).toBe('lifespan');
    expect(s.mapSelectedId).toBe(null);
  });

  it('never restores a mat as the expanded or selected option', () => {
    const mat = G.TYPES.find(t => t.role === 'mat').id;
    const s = G.loadState(JSON.stringify({ expandedId: mat, mapSelectedId: mat }));
    expect(s.expandedId).toBe(null);
    expect(s.mapSelectedId).toBe(null);
  });
});
