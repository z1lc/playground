import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const coreMatch = html.match(/<script id="effort-core">([\s\S]*?)<\/script>/);
if (!coreMatch) throw new Error('Inline effort core was not found');
const sandbox = {};
vm.runInNewContext(coreMatch[1], sandbox);
const K = sandbox.KidEffort;
const plain = v => JSON.parse(JSON.stringify(v));
const clone = v => JSON.parse(JSON.stringify(v));

const DUES = ['2027-01-15', '2026-06-20', '2026-07-31', '2026-08-01', '2026-08-20', '2026-09-01', '2026-09-02', '2027-09-09', '2026-12-31', '2028-02-29'];
const forDue = due => K.stagesFor(K.prekPlan(due));

describe('data', () => {
  it('passes the built-in consistency check for the base data and every kind of due date', () => {
    expect(plain(K.selfCheck(K.STAGES, K.LANES))).toEqual([]);
    for (const due of DUES) expect(plain(K.selfCheck(forDue(due), K.LANES)), due).toEqual([]);
  });

  it('has nine stages from birth to Pre-K and ten lanes of nine cells', () => {
    expect(K.STAGES).toHaveLength(9);
    expect(K.STAGES[0].startMo).toBe(0);
    expect(forDue('2026-06-20').at(-1).endMo).toBeCloseTo(49.4, 1);
    expect(K.LANES).toHaveLength(10);
    for (const l of K.LANES) expect(l.cells, l.id).toHaveLength(9);
  });

  it('peaks in the 18–24 month stage and is lightest at Pre-K', () => {
    const scores = K.STAGES.map(s => s.score);
    expect(K.STAGES[scores.indexOf(Math.max(...scores))].id).toBe('m18');
    expect(Math.min(...scores)).toBe(K.STAGES.at(-1).score);
  });

  it('states the Georgia Pre-K age cutoff on the last stage for every due date', () => {
    for (const due of DUES) expect(forDue(due).at(-1).summary, due).toMatch(/September 1/);
  });

  it('catches broken entries in selfCheck', () => {
    const stages = clone(K.STAGES);
    const lanes = clone(K.LANES);
    stages[1].id = stages[0].id;
    stages[3].startMo += 1;
    stages[2].score = 11;
    lanes[0].cells[0].level = 7;
    lanes[1].cells[2].detail = 'Only one sentence here.';
    lanes[2].cells.pop();
    lanes[3].id = lanes[4].id;
    const problems = plain(K.selfCheck(stages, lanes));
    expect(problems.some(p => p.includes('duplicate id') && p.startsWith('stage'))).toBe(true);
    expect(problems.some(p => p.includes('gap'))).toBe(true);
    expect(problems.some(p => p.includes('bad score'))).toBe(true);
    expect(problems.some(p => p.includes('bad level'))).toBe(true);
    expect(problems.some(p => p.includes('needs 2–3'))).toBe(true);
    expect(problems.some(p => p.includes('needs 9 cells'))).toBe(true);
    expect(problems.some(p => p.includes('duplicate id') && p.startsWith('lane'))).toBe(true);
  });
});

describe('sentenceCount', () => {
  it('counts sentence ends but not decimals or mid-sentence numbers', () => {
    expect(K.sentenceCount('One. Two! Three?')).toBe(3);
    expect(K.sentenceCount('About 2.5 years. Then 4 by September 1.')).toBe(2);
    expect(K.sentenceCount('No full stop')).toBe(0);
  });
});

describe('due date → Pre-K', () => {
  it('starts Pre-K the same year for a birthday on or before September 1', () => {
    const june = plain(K.prekPlan('2026-06-20'));
    expect(june).toMatchObject({ madeCutoff: true, startYear: 2030, waitDays: 42, ageAtStart: { years: 4, months: 1 } });
    expect(june.prekMo).toBeCloseTo(49.4, 1);
    expect(plain(K.prekPlan('2026-09-01'))).toMatchObject({ madeCutoff: true, startYear: 2030, daysPastCutoff: 0 });
  });

  it('waits a year for a birthday after September 1', () => {
    const sept9 = plain(K.prekPlan('2027-09-09'));
    expect(sept9).toMatchObject({ madeCutoff: false, startYear: 2032, daysPastCutoff: 8, ageAtStart: { years: 4, months: 10 } });
    expect(sept9.prekMo).toBeCloseTo(58.7, 1);
    expect(plain(K.prekPlan('2026-09-02'))).toMatchObject({ madeCutoff: false, startYear: 2031, daysPastCutoff: 1 });
  });

  it('has no wait at 4 for an August birthday, and the 3-year stage ends at Pre-K', () => {
    const aug = K.prekPlan('2026-08-20');
    expect(aug.waitDays).toBeLessThan(0);
    expect(plain(aug.ageAtStart)).toEqual({ years: 3, months: 11 });
    const st = forDue('2026-08-20');
    expect(st.find(s => s.id === 'y3').endMo).toBeCloseTo(aug.prekMo, 6);
    expect(st.at(-1).endMo).toBe(st.at(-1).startMo);
    expect(st.at(-1).summary).toMatch(/no wait/);
  });

  it('keeps the earlier stages fixed and makes the wait the last stage', () => {
    const st = forDue('2027-09-09');
    expect(st.slice(0, 7).map(s => [s.startMo, s.endMo])).toEqual(K.STAGES.slice(0, 7).map(s => [s.startMo, s.endMo]));
    expect(st.find(s => s.id === 'y3').endMo).toBe(48);
    expect(st.at(-1).startMo).toBe(48);
    expect(K.STAGES.at(-1).endMo).toBe(54); // base data untouched
  });

  it('writes a one-sentence summary and warns only near the cutoff', () => {
    for (const due of DUES) expect(K.sentenceCount(K.prekSummary(K.prekPlan(due))), due).toBe(1);
    expect(K.prekNote(K.prekPlan('2027-09-09')).warn).toMatch(/8 days early.*2031/);
    expect(K.prekNote(K.prekPlan('2026-08-25')).warn).toMatch(/8 days late.*2031/);
    expect(K.prekNote(K.prekPlan('2026-06-20')).warn).toBeNull();
    expect(K.prekNote(K.prekPlan('2026-12-31')).warn).toBeNull();
  });

  it('rejects malformed or impossible dates', () => {
    for (const bad of ['', '2026-02-30', '2026-13-01', '26-06-20', 'June 20', null]) expect(K.prekPlan(bad), String(bad)).toBeNull();
    expect(K.parseISO('2028-02-29')).not.toBeNull();
  });

  it('defaults to the next June 20', () => {
    expect(K.defaultDue('2026-11-16')).toBe('2027-06-20');
    expect(K.defaultDue('2027-06-20')).toBe('2027-06-20');
    expect(K.defaultDue('2027-06-21')).toBe('2028-06-20');
    expect(K.defaultDue('2027-03-01')).toBe('2027-06-20');
  });

  it('formats dates for the due-date link', () => {
    expect(K.formatDate('2027-06-20')).toBe('June 20, 2027');
    expect(K.formatDate('nope')).toBe('');
  });
});

describe('stripLayout', () => {
  const layout = plain(K.stripLayout(forDue('2026-06-20')));

  it('fills the strip exactly with increasing left edges', () => {
    const total = layout.reduce((s, b) => s + b.widthPct, 0);
    expect(total).toBeCloseTo(100, 6);
    for (let i = 1; i < layout.length; i++) expect(layout[i].leftPct).toBeGreaterThan(layout[i - 1].leftPct);
  });

  it('makes widths proportional to stage length and heights to score', () => {
    const iNewborn = K.STAGES.findIndex(s => s.id === 'm0');
    const iWalker = K.STAGES.findIndex(s => s.id === 'm12');
    expect(layout[iWalker].widthPct).toBeCloseTo(layout[iNewborn].widthPct * 2, 6);
    K.STAGES.forEach((s, i) => expect(layout[i].heightPct).toBe(s.score * 10));
  });

  it('gives a zero-width last bar when there is no wait at 4', () => {
    const l = plain(K.stripLayout(forDue('2026-08-20')));
    expect(l.at(-1).widthPct).toBe(0);
    expect(l.reduce((s, b) => s + b.widthPct, 0)).toBeCloseTo(100, 6);
  });
});

describe('stageFromScroll', () => {
  it('rounds to the nearest panel and clamps to the ends', () => {
    expect(K.stageFromScroll(0, 360, 9)).toBe(0);
    expect(K.stageFromScroll(170, 360, 9)).toBe(0);
    expect(K.stageFromScroll(190, 360, 9)).toBe(1);
    expect(K.stageFromScroll(360 * 4, 360, 9)).toBe(4);
    expect(K.stageFromScroll(99999, 360, 9)).toBe(8);
    expect(K.stageFromScroll(-50, 360, 9)).toBe(0);
  });

  it('falls back to the first stage when the carousel has no width', () => {
    expect(K.stageFromScroll(500, 0, 9)).toBe(0);
    expect(K.stageFromScroll(500, NaN, 9)).toBe(0);
  });
});

describe('loadState', () => {
  const T = '2026-11-16';
  const def = { stage: 0, due: null };   // null = not set yet, use defaultDue(today)

  it('returns the default for missing or broken input', () => {
    expect(plain(K.loadState(null, T))).toEqual(def);
    expect(plain(K.loadState('not json', T))).toEqual(def);
    expect(plain(K.loadState('"str"', T))).toEqual(def);
    expect(plain(K.loadState('{}', T))).toEqual(def);
  });

  it('keeps a valid stage and rejects out-of-range or non-integer ones', () => {
    expect(plain(K.loadState('{"stage":5}', T))).toEqual({ ...def, stage: 5 });
    expect(plain(K.loadState('{"stage":9}', T))).toEqual(def);
    expect(plain(K.loadState('{"stage":-1}', T))).toEqual(def);
    expect(plain(K.loadState('{"stage":2.5}', T))).toEqual(def);
  });

  it('keeps a valid due date and replaces a bad one', () => {
    expect(plain(K.loadState('{"stage":2,"due":"2026-06-20"}', T))).toEqual({ stage: 2, due: '2026-06-20' });
    expect(plain(K.loadState('{"stage":2,"due":"2026-02-30"}', T))).toEqual({ stage: 2, due: def.due });
  });
});
