// Headless verification for the Living Wage tool.
// Run: node verify.mjs
// Chrome MCP can't drive a live browser in this environment, so we verify
// everything reachable without one: data integrity, source<->inlined parity,
// the exact selection+summation logic the UI runs, structural wiring, JS syntax,
// and a real htm render smoke test with React/Recharts stubbed out.

import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';

const DIR = path.dirname(fileURLToPath(import.meta.url));
const SCRATCH = process.env.SCRATCH_DIR || tmpdir();

let failures = 0;
let warnings = 0;
async function check(name, fn) {
  try {
    await fn();
    console.log('  ✓', name);
  } catch (e) {
    failures++;
    console.error('  ✗', name, '\n     ' + String(e.message).split('\n').join('\n     '));
  }
}
function warn(name, msg) {
  warnings++;
  console.log('  ! SKIP', name, '—', msg);
}

const CATS = ['Food', 'Child Care', 'Medical', 'Housing', 'Transportation', 'Civic', 'Internet & Mobile', 'Other'];
const UI_HOUSEHOLDS = ['2 Adults (1 Working)', '2 Adults (Both Working)'];
const PALETTE = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834'];

const data = JSON.parse(readFileSync(path.join(DIR, 'data.json'), 'utf8'));
const methodFile = JSON.parse(readFileSync(path.join(DIR, 'methodology.json'), 'utf8'));
const htmlSrc = readFileSync(path.join(DIR, 'index.html'), 'utf8');
const jsonMatch = htmlSrc.match(/<script type="application\/json" id="lw-data">([\s\S]*?)<\/script>/);
const inlined = JSON.parse(jsonMatch[1]);
const methodMatch = htmlSrc.match(/<script type="application\/json" id="lw-method">([\s\S]*?)<\/script>/);
const inlinedMethod = JSON.parse(methodMatch[1]);

// household is always 2 adults; the slider chooses how many work.
// getColumn returns the RAW MIT row (used for data-integrity + parity checks).
function getColumn(dataset, location, workingAdults, children) {
  const hh = workingAdults === 1 ? '2 Adults (1 Working)' : '2 Adults (Both Working)';
  return dataset.locations[location].households[hh][String(children)];
}

// The UI adjusts two categories from MIT's raw figures; mirror both here.
// Food: scaled from Low-Cost up to the USDA Liberal level.
const FOOD_RATIO = { 0: 1.545, 1: 1.533, 2: 1.527, 3: 1.516 };
const liberalFood = (children, rawFood) => Math.round(rawFood * FOOD_RATIO[children]);
// Medical: adds a flat dental + vision estimate per adult and per child.
const MEDICAL_DV = { adult: 700, child: 450 };
const dvAddon = (children) => 2 * MEDICAL_DV.adult + children * MEDICAL_DV.child;
// Atlanta Housing: median SAFMR of ZIPs 30306 & 30307 (HUD FY2026), bedrooms = children + 1.
const ATLANTA_SAFMR = {
  '30306': { 0: 2060, 1: 2150, 2: 2360, 3: 2830, 4: 3380 },
  '30307': { 0: 2030, 1: 2130, 2: 2330, 3: 2790, 4: 3340 },
};
const atlantaHousing = (children) =>
  Math.round(((ATLANTA_SAFMR['30306'][children + 1] + ATLANTA_SAFMR['30307'][children + 1]) / 2) * 12);
// A 9th slice: two adults maxing a 401(k), flat regardless of the slider or city.
const RETIREMENT = 'Retirement (401k)';
const RETIREMENT_ANNUAL = 49000;
const PIE_CATS = [...CATS, RETIREMENT];
function uiColumn(dataset, location, workingAdults, children) {
  const row = getColumn(dataset, location, workingAdults, children);
  const out = { ...row, Food: liberalFood(children, row.Food), Medical: row.Medical + dvAddon(children) };
  if (location === 'Atlanta') out.Housing = atlantaHousing(children);
  out[RETIREMENT] = RETIREMENT_ANNUAL;
  return out;
}

console.log('\n1. data.json integrity');
await check('categories are the 8 expected expense rows', () => {
  assert.deepEqual(data.categories, CATS);
});
await check('5 locations present', () => {
  assert.deepEqual(Object.keys(data.locations), ['Atlanta', 'Asheville', 'San Francisco', 'New York', 'Huntsville']);
});
await check('every combo has 8 positive-integer categories that sum to afterTax', () => {
  let combos = 0;
  for (const [loc, lv] of Object.entries(data.locations)) {
    for (const hh of Object.keys(lv.households)) {
      for (const ch of ['0', '1', '2', '3']) {
        const row = lv.households[hh][ch];
        assert.ok(row, `${loc}/${hh}/${ch} missing`);
        for (const c of CATS) {
          assert.equal(typeof row[c], 'number', `${loc}/${hh}/${ch}/${c} not a number`);
          assert.ok(Number.isInteger(row[c]) && row[c] >= 0, `${loc}/${hh}/${ch}/${c} not a non-negative int`);
        }
        const sum = CATS.reduce((s, c) => s + row[c], 0);
        assert.ok(Math.abs(sum - row.afterTax) <= 3, `${loc}/${hh}/${ch}: sum ${sum} != afterTax ${row.afterTax}`);
        combos++;
      }
    }
  }
  assert.equal(combos, 60, `expected 60 combos, saw ${combos}`);
});

console.log('\n2. inlined-vs-source parity (the shipped data equals data.json)');
await check('inlined 2-adult households match data.json exactly', () => {
  for (const loc of Object.keys(data.locations)) {
    for (const hh of UI_HOUSEHOLDS) {
      assert.deepEqual(
        inlined.locations[loc].households[hh],
        data.locations[loc].households[hh],
        `${loc}/${hh} inlined copy drifted from data.json`,
      );
    }
  }
});

console.log('\n2b. methodology content + inlined parity');
await check('methodology covers the 8 expense categories plus Retirement (401k)', () => {
  assert.deepEqual(Object.keys(methodFile.categories).sort(), [...PIE_CATS].sort());
});
await check('inlined lw-method matches methodology.json exactly', () => {
  assert.deepEqual(inlinedMethod, methodFile.categories, 'inlined methodology drifted from methodology.json');
});
await check('every category has a BLUF, a <=200-word methodology, and 1-5 short pros/cons', () => {
  for (const c of PIE_CATS) {
    const m = inlinedMethod[c];
    assert.ok(m, `${c} missing from methodology`);
    assert.equal(typeof m.bluf, 'string', `${c} bluf not a string`);
    const bluf = m.bluf.trim();
    assert.ok(bluf.length > 0 && bluf.length <= 300, `${c} bluf length ${bluf.length} out of range`);
    assert.ok(bluf.endsWith('.'), `${c} bluf should end with a period`);
    const words = m.methodology.trim().split(/\s+/).length;
    assert.ok(words > 20 && words <= 200, `${c} methodology is ${words} words (must be 21-200)`);
    for (const key of ['pros', 'cons']) {
      assert.ok(Array.isArray(m[key]), `${c} ${key} not an array`);
      assert.ok(m[key].length >= 1 && m[key].length <= 5, `${c} ${key} has ${m[key].length} items (need 1-5)`);
      for (const b of m[key]) {
        assert.equal(typeof b, 'string', `${c} ${key} bullet not a string`);
        const t = b.trim();
        assert.ok(t.length > 0 && t.length <= 70, `${c} ${key} bullet length ${t.length}: "${b}"`);
      }
    }
  }
});

console.log('\n3. selection + summation logic the UI runs (all 40 UI combos)');
await check('getColumn maps the working-adults slider to the right MIT column', () => {
  const row1 = getColumn(inlined, 'Atlanta', 1, 2);
  const row2 = getColumn(inlined, 'Atlanta', 2, 2);
  assert.equal(row1, inlined.locations.Atlanta.households['2 Adults (1 Working)']['2']);
  assert.equal(row2, inlined.locations.Atlanta.households['2 Adults (Both Working)']['2']);
});
await check('UI pie total = MIT afterTax shifted by each category adjustment, every UI combo', () => {
  // Raw sum ≈ afterTax (MIT rounding). The UI shifts Food (Liberal), Medical
  // (+dental/vision), and — for Atlanta — Housing (ZIP SAFMR). Assert the total
  // equals afterTax plus exactly those per-category deltas.
  for (const loc of Object.keys(inlined.locations)) {
    for (const adults of [1, 2]) {
      for (const kids of [0, 1, 2, 3]) {
        const raw = getColumn(inlined, loc, adults, kids);
        const ui = uiColumn(inlined, loc, adults, kids);
        const total = PIE_CATS.reduce((s, c) => s + ui[c], 0);
        const expected = raw.afterTax + (ui.Food - raw.Food) + (ui.Medical - raw.Medical) + (ui.Housing - raw.Housing) + RETIREMENT_ANNUAL;
        assert.ok(Math.abs(total - expected) <= 3, `${loc}/${adults}working/${kids}kids: UI total ${total} vs expected ${expected}`);
      }
    }
  }
});
await check('spot-checks match values read from the live MIT site', () => {
  assert.equal(getColumn(inlined, 'Atlanta', 2, 2).afterTax, 101106);
  assert.equal(getColumn(inlined, 'Atlanta', 2, 2).Housing, 22822);
  assert.equal(getColumn(inlined, 'San Francisco', 2, 3).afterTax, 198988);
  assert.equal(getColumn(inlined, 'New York', 1, 0).afterTax, 82577);
  assert.equal(getColumn(inlined, 'Huntsville', 1, 2).afterTax, 74997);
});

console.log('\n4. structural wiring in index.html');
await check('import map pins react 18.2.0 and recharts 2.12.7', () => {
  assert.match(htmlSrc, /react@18\.2\.0/);
  assert.match(htmlSrc, /recharts@2\.12\.7/);
  assert.match(htmlSrc, /htm@3\.1\.1/);
});
await check('pie chart is wired with a click handler', () => {
  for (const s of ['PieChart', 'Pie', 'Cell', 'Tooltip', 'ResponsiveContainer', 'onClick']) {
    assert.ok(htmlSrc.includes(s), `missing ${s}`);
  }
});
await check('localStorage persistence is present', () => {
  assert.ok(htmlSrc.includes("STORAGE_KEY = 'living-wage-v1'"));
  assert.ok(htmlSrc.includes('localStorage.setItem'));
  assert.ok(htmlSrc.includes('localStorage.getItem'));
});
await check('Food is wired to the USDA Liberal ratio and detail copy reflects it', () => {
  assert.ok(htmlSrc.includes('FOOD_LIBERAL_RATIO'), 'FOOD_LIBERAL_RATIO missing from index.html');
  assert.ok(/Liberal/.test(inlinedMethod.Food.bluf + inlinedMethod.Food.methodology), 'Food detail does not mention Liberal');
});
await check('Medical is wired to the dental+vision add-on and detail copy reflects it', () => {
  assert.ok(htmlSrc.includes('MEDICAL_DENTAL_VISION'), 'MEDICAL_DENTAL_VISION missing from index.html');
  assert.ok(/dental/i.test(inlinedMethod.Medical.bluf + inlinedMethod.Medical.methodology), 'Medical detail does not mention dental');
  assert.ok(!inlinedMethod.Medical.cons.some((c) => /excludes dental/i.test(c)), 'stale "excludes dental" con still present');
});
await check('Atlanta housing is wired to the ZIP SAFMR (30306 & 30307) table', () => {
  assert.ok(htmlSrc.includes('ATLANTA_SAFMR_2026'), 'ATLANTA_SAFMR_2026 missing from index.html');
  assert.ok(htmlSrc.includes('30306') && htmlSrc.includes('30307'), 'SAFMR ZIP codes missing');
});
await check('Retirement 401(k) slice is wired in as a 9th category', () => {
  assert.ok(htmlSrc.includes('RETIREMENT_ANNUAL') && htmlSrc.includes('49000'), 'RETIREMENT_ANNUAL missing');
  assert.ok(htmlSrc.includes('PIE_CATEGORIES'), 'PIE_CATEGORIES (9-slice list) missing');
  assert.ok(htmlSrc.includes('#5b6472'), 'Retirement slate color missing');
  assert.ok(/401\(k\)/.test(inlinedMethod['Retirement (401k)'].methodology), 'Retirement methodology missing 401(k)');
});
await check('all 8 validated palette hues are used', () => {
  for (const hex of PALETTE) assert.ok(htmlSrc.includes(hex), `missing ${hex}`);
});

console.log('\n5. module JS syntax (node --check)');
const modMatch = htmlSrc.match(/<script type="module">([\s\S]*?)<\/script>/);
const moduleSrc = modMatch[1];
await check('module parses as valid ES module', () => {
  const tmp = path.join(SCRATCH, 'lw-module-check.mjs');
  writeFileSync(tmp, moduleSrc);
  const r = spawnSync(process.execPath, ['--check', tmp], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr || 'node --check failed');
});

console.log('\n6. htm render smoke test (React/Recharts stubbed)');
let htmMod = null;
try {
  const res = await fetch('https://unpkg.com/htm@3.1.1/dist/htm.module.js');
  if (res.ok) {
    const tmp = path.join(SCRATCH, 'htm.module.mjs');
    writeFileSync(tmp, await res.text());
    htmMod = (await import(pathToFileURL(tmp).href)).default;
  }
} catch (e) {
  /* offline */
}

if (!htmMod) {
  warn('render smoke test', 'could not fetch htm (offline?); logic + syntax still verified above');
} else {
  // Build a stubbed runtime: createElement records a lightweight tree; hooks are
  // inert; Recharts components are opaque markers. This exercises every htm
  // template in App (and its .map bodies) so tag-balance / undefined-var /
  // runtime errors surface without a browser or a real DOM.
  const Cell = { $$: 'Cell' };
  const stubs = { PieChart: { $$: 'PieChart' }, Pie: { $$: 'Pie' }, Cell, Tooltip: { $$: 'Tooltip' }, ResponsiveContainer: { $$: 'ResponsiveContainer' } };
  let cellCount = 0;
  const createElement = (type, props, ...children) => {
    if (type === Cell) cellCount++;
    return { type, props: props || {}, children: children.flat(Infinity) };
  };
  const React = { createElement, default: {} };
  const useMemo = (fn) => fn();
  const useState = (init) => [init, () => {}];
  const useEffect = () => {};
  const useRef = (init) => ({ current: init });
  const createRoot = () => ({ render: () => {} });

  let scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":null}';
  const localStorage = { getItem: () => scenario, setItem: () => {} };
  const document = {
    getElementById: (id) =>
      id === 'lw-data' ? { textContent: jsonMatch[1] }
        : id === 'lw-method' ? { textContent: methodMatch[1] }
          : { textContent: '' },
  };

  const factorySrc =
    moduleSrc
      .replace(/import React[^\n]*\n/, '')
      .replace(/import \{ createRoot \}[^\n]*\n/, '')
      .replace(/import \{ PieChart[^\n]*\n/, '')
      .replace(/import htm[^\n]*\n/, '') +
    '\n;return { App, getColumn, CATEGORIES };';
  const factory = new Function(
    'React', 'useMemo', 'useState', 'useEffect', 'useRef', 'createRoot',
    'PieChart', 'Pie', 'Cell', 'Tooltip', 'ResponsiveContainer',
    'htm', 'document', 'localStorage',
    factorySrc,
  );

  const usdfmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  // The UI rounds annual figures to the nearest $100 for display.
  const round100 = (v) => Math.round(v / 100) * 100;
  // Sum the UI column across all 9 slices (incl. Retirement), matching the donut.
  const expectedTotal = (loc, adults, kids) =>
    usdfmt.format(round100(PIE_CATS.reduce((s, c) => s + uiColumn(inlined, loc, adults, kids)[c], 0)));

  const collect = (node, out) => {
    if (node == null || node === false || node === true) return;
    if (typeof node === 'string' || typeof node === 'number') { out.push(String(node)); return; }
    if (Array.isArray(node)) { node.forEach((n) => collect(n, out)); return; }
    if (node.children) collect(node.children, out);
  };

  let app;
  await check('module evaluates and exposes App', () => {
    app = factory(React, useMemo, useState, useEffect, useRef, createRoot,
      stubs.PieChart, stubs.Pie, stubs.Cell, stubs.Tooltip, stubs.ResponsiveContainer,
      htmMod, document, localStorage);
    assert.equal(typeof app.App, 'function');
  });

  await check('App renders default (Atlanta / both working / 2 kids) with correct total & labels', () => {
    cellCount = 0;
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":null}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    assert.ok(text.includes(expectedTotal('Atlanta', 2, 2)), 'annual total not rendered');
    for (const c of CATS) assert.ok(text.includes(c), `legend missing ${c}`);
    assert.equal(cellCount, 9, `expected 9 pie cells, got ${cellCount}`);
    assert.ok(text.includes('Fulton County, GA'), 'household note missing location');
  });

  await check('App renders a selected slice (Housing) with figures, BLUF, methodology & pros/cons', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":"Housing"}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    // Atlanta Housing is the ZIP SAFMR (3BR) = 33720 -> $33,700 for display.
    assert.ok(text.includes(usdfmt.format(round100(atlantaHousing(2)))), 'rounded Housing annual not rendered');
    assert.ok(text.includes('Methodology'), 'methodology heading missing');
    assert.ok(text.includes('Pros') && text.includes('Cons'), 'pros/cons headers missing');
    assert.ok(text.includes(inlinedMethod.Housing.bluf), 'Housing BLUF not rendered');
    assert.ok(text.includes(inlinedMethod.Housing.pros[0]), 'first Housing pro not rendered');
    assert.ok(text.includes(inlinedMethod.Housing.cons[0]), 'first Housing con not rendered');
  });

  await check('Food slice shows the USDA Liberal figure, not MIT Low-Cost', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":"Food"}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    const lib = liberalFood(2, getColumn(inlined, 'Atlanta', 2, 2).Food); // 15148 -> 23131
    assert.ok(text.includes(usdfmt.format(round100(lib))), `Liberal Food ${usdfmt.format(round100(lib))} not rendered`);
    assert.ok(!text.includes(usdfmt.format(round100(15148))), 'stale Low-Cost Food $15,100 still present');
    assert.ok(text.includes(inlinedMethod.Food.bluf), 'Food BLUF (Liberal) not rendered');
  });

  await check('Medical slice includes the dental + vision add-on', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":"Medical"}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    const med = getColumn(inlined, 'Atlanta', 2, 2).Medical + dvAddon(2); // 9600 + 2300 = 11900
    assert.ok(text.includes(usdfmt.format(round100(med))), `Medical + D&V ${usdfmt.format(round100(med))} not rendered`);
    assert.ok(!text.includes(usdfmt.format(round100(9600))), 'stale MIT-only Medical $9,600 still present');
    assert.ok(text.includes(inlinedMethod.Medical.bluf), 'Medical BLUF (dental+vision) not rendered');
  });

  await check('Atlanta Housing uses the ZIP SAFMR median (bedrooms = children + 1)', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":"Housing"}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    const h = atlantaHousing(2); // 2 kids -> 3BR -> median(2830,2790)=2810 * 12 = 33720
    assert.ok(text.includes(usdfmt.format(round100(h))), `Atlanta SAFMR housing ${usdfmt.format(round100(h))} not rendered`);
    assert.ok(!text.includes(usdfmt.format(round100(22822))), 'stale MIT county Housing $22,800 still present');
    assert.ok(text.includes('30306') && text.includes('30307'), 'Atlanta housing detail note (ZIP codes) missing');
  });

  await check('Retirement (401k) slice shows the flat $49,000 savings figure', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":"Retirement (401k)"}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    assert.ok(text.includes(usdfmt.format(round100(RETIREMENT_ANNUAL))), 'Retirement $49,000 not rendered');
    assert.ok(text.includes(inlinedMethod['Retirement (401k)'].bluf), 'Retirement BLUF not rendered');
  });

  await check('empty state prompts to select a slice when nothing is selected', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":null}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    assert.ok(text.includes('Select a slice to see how MIT calculates it'), 'empty-state prompt missing');
  });

  await check('legend is sorted by value desc with "Other" pinned last', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":null}';
    const out = [];
    collect(app.App(), out);
    const text = out.join('');
    // Atlanta / both working / 2 kids, all adjustments — Retirement 49000 > Housing
    // (ZIP SAFMR) 33720 > Food (Liberal) 23131 > Child Care 21916 > Transportation
    // 13843 > Medical (+D&V) 11900 > Civic 6547 > Internet & Mobile 2428; Other last.
    const order = ['Retirement (401k)', 'Housing', 'Food', 'Child Care', 'Transportation', 'Medical', 'Civic', 'Internet & Mobile', 'Other'];
    let last = -1;
    for (const name of order) {
      const at = text.indexOf(name);
      assert.ok(at > last, `legend order wrong: ${name} not after previous entry`);
      last = at;
    }
  });

  await check('App renders another city/household without error (SF / 1 working / 3 kids)', () => {
    scenario = '{"location":"San Francisco","workingAdults":1,"children":3,"selected":null}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    assert.ok(text.includes(expectedTotal('San Francisco', 1, 3)), 'SF total not rendered');
  });

  const usdDeltaFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0, signDisplay: 'exceptZero' });
  await check('a non-Atlanta city shows a signed $ delta vs Atlanta in the legend', () => {
    scenario = '{"location":"San Francisco","workingAdults":2,"children":2,"selected":null}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    // Deltas compare UI columns: SF Housing 39908 vs Atlanta ZIP-SAFMR Housing 33720
    // => +$6,200 (nearest $100, positive = pricier than the Atlanta baseline).
    const d = round100(uiColumn(inlined, 'San Francisco', 2, 2).Housing - uiColumn(inlined, 'Atlanta', 2, 2).Housing);
    assert.ok(text.includes(usdDeltaFmt.format(d)), `expected Housing delta ${usdDeltaFmt.format(d)} not rendered`);
    // Asheville-style cheaper category would be negative; here at least one "-$" should show too.
    assert.ok(/\+\$/.test(text), 'no positive delta rendered for a pricier city');
  });
  await check('Atlanta (the baseline) renders no signed deltas', () => {
    scenario = '{"location":"Atlanta","workingAdults":2,"children":2,"selected":null}';
    const out = [];
    collect(app.App(), out);
    const text = out.join(' ');
    assert.ok(!text.includes('+$') && !text.includes('-$'), 'unexpected signed delta on baseline Atlanta');
  });
}

console.log(`\n${failures === 0 ? '✓ ALL CHECKS PASSED' : '✗ ' + failures + ' CHECK(S) FAILED'}` + (warnings ? ` (${warnings} skipped)` : ''));
process.exit(failures === 0 ? 0 : 1);
