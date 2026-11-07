/**
 * Headless checks for valuation-curves.  `node verify.mjs`
 *
 * Four things worth proving without a browser:
 *   1. data.json is internally consistent (parallel arrays, monotone time, sane money)
 *   2. the blob inlined into index.html is byte-identical to data.json -- this is what
 *      catches editing the page by hand and forgetting to rebuild
 *   3. the derived numbers can be re-derived: every GDP-adjusted figure is recomputed
 *      from the shipped GDP table rather than trusted
 *   4. the htm templates actually render, with React stubbed out
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { writeFileSync, unlinkSync } from 'node:fs';

const HERE = dirname(fileURLToPath(import.meta.url));
let pass = 0;
const failures = [];
const warnings = [];

function check(name, cond, detail = '') {
  if (cond) pass++;
  else failures.push(`${name}${detail ? ` — ${detail}` : ''}`);
}
const warn = (msg) => warnings.push(msg);

const data = JSON.parse(readFileSync(join(HERE, 'data.json'), 'utf8'));
const htmlText = readFileSync(join(HERE, 'index.html'), 'utf8');

// ── 1. data integrity ───────────────────────────────────────────────────────
console.log('\n1. data.json integrity');

check('has companies', Array.isArray(data.companies) && data.companies.length > 0);
check('has meta.palette', data.meta?.palette?.light?.length === 8 && data.meta?.palette?.dark?.length === 8);
check('has meta.dashes', Array.isArray(data.meta?.dashes) && data.meta.dashes.length === 5);
check('has GDP table', Object.keys(data.meta?.gdp || {}).length > 100);

const slugs = new Set();
const identities = new Set();
for (const c of data.companies) {
  const n = c.t.length;
  check(`${c.slug}: unique slug`, !slugs.has(c.slug));
  slugs.add(c.slug);

  const id = `${c.colorSlot}/${c.dashSlot}`;
  check(`${c.slug}: unique (colorSlot, dashSlot)`, !identities.has(id), id);
  identities.add(id);

  for (const key of ['vNom', 'vGdp', 'kind', 'quality', 'dates']) {
    check(`${c.slug}: ${key} length matches t`, c[key].length === n, `${c[key].length} vs ${n}`);
  }
  check(`${c.slug}: has points`, n > 0);

  let mono = true;
  for (let i = 1; i < n; i++) if (c.t[i] < c.t[i - 1]) mono = false;
  check(`${c.slug}: t is monotonic`, mono);
  check(`${c.slug}: t starts at or after 0`, n === 0 || c.t[0] >= 0);

  // A thousandfold units slip is the classic failure here and is entirely
  // invisible on a log axis without an explicit bound.
  let inRange = true, bad = null;
  for (let i = 0; i < n; i++) {
    if (!(c.vNom[i] >= 1e5 && c.vNom[i] <= 1e13)) { inRange = false; bad = `${c.dates[i]} = ${c.vNom[i]}`; }
  }
  check(`${c.slug}: values within $100K..$10T`, inRange, bad);

  check(`${c.slug}: ipoIndex in range`, c.ipoIndex == null || (c.ipoIndex >= 0 && c.ipoIndex < n));
  // A public company may legitimately lack an IPO marker — Microsoft listed in 1986
  // and no free source publishes its market cap before 1996 — but only if the series
  // genuinely starts long after the listing. A marker missing for any other reason,
  // or one placed far from the IPO date, is a bug.
  if (c.status === 'public' && c.ipoDate) {
    const ipo = Date.parse(c.ipoDate);
    const firstPublic = c.dates[c.kind.indexOf(1)];
    const gapDays = (Date.parse(firstPublic) - ipo) / 86400000;
    if (c.ipoIndex == null) {
      check(`${c.slug}: no IPO marker only because the series starts late`, gapDays > 400,
        `first public point is ${Math.round(gapDays)} days after the IPO`);
    } else {
      const markerGap = (Date.parse(c.dates[c.ipoIndex]) - ipo) / 86400000;
      check(`${c.slug}: IPO marker sits near the IPO date`, markerGap >= 0 && markerGap <= 400,
        `marker is ${Math.round(markerGap)} days from the IPO`);
    }
  }
  check(`${c.slug}: private line ends on a funding round`, c.status !== 'private' || c.kind[n - 1] === 0);
  check(`${c.slug}: dates are ISO`, c.dates.every((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)));
  check(`${c.slug}: quality is 0 or 1`, c.quality.every((q) => q === 0 || q === 1));
  check(`${c.slug}: kind is 0 or 1`, c.kind.every((k) => k === 0 || k === 1));
  check(`${c.slug}: has at least one source`, (c.sources || []).length > 0);
  check(`${c.slug}: sources are https`, (c.sources || []).every((s) => s.url.startsWith('https://')));

  // Every label/amount key must point at a real private event, or the tooltip
  // would attribute a round to a quarterly market-cap reading.
  for (const key of ['labels', 'amounts', 'leads', 'basis', 'method']) {
    const stray = Object.keys(c[key] || {}).filter((k) => c.kind[Number(k)] !== 0);
    check(`${c.slug}: ${key} keys point at private events`, stray.length === 0, stray.join(','));
  }
}

// ── 2. source ↔ inlined parity ──────────────────────────────────────────────
console.log('2. index.html parity');

const m = htmlText.match(/\/\/ DATA_START\n\s*const DATA = (.*?);\n\s*\/\/ DATA_END/s);
check('DATA_START/DATA_END sentinels present with a blob', !!m);
if (m) {
  const inlined = JSON.parse(m[1]);
  check('inlined payload equals data.json', JSON.stringify(inlined) === JSON.stringify(data),
    'index.html is stale — re-run `uv run build_data.py`');
  // A single "</script>" inside any article title would close the tag and blank
  // the page, so the escape is load-bearing rather than decorative.
  check('inlined blob contains no raw "<"', !m[1].includes('<'));
}

// ── 3. re-derive the derived numbers ────────────────────────────────────────
console.log('3. recomputation');

const gdp = data.meta.gdp;
const gdpBase = data.meta.gdpBase;
const gdpQuarters = Object.keys(gdp).sort();
check('GDP base is the latest quarter in the table', gdpBase === gdpQuarters[gdpQuarters.length - 1]);
check('GDP quarters are contiguous',
  gdpQuarters.every((q, i) => i === 0 || (Date.parse(q) - Date.parse(gdpQuarters[i - 1])) / 864e5 < 93));

// The quarter a date falls in, capped at the latest release -- the same rule the
// build uses, written independently.
const quarterOf = (iso) => {
  const [y, m] = iso.split('-').map(Number);
  const q = `${y}-${String(Math.floor((m - 1) / 3) * 3 + 1).padStart(2, '0')}-01`;
  return q > gdpBase ? gdpBase : q;
};

for (const c of data.companies) {
  let worst = 0, at = null;
  for (let i = 0; i < c.t.length; i++) {
    const q = quarterOf(c.dates[i]);
    if (!gdp[q]) { warn(`${c.slug}: no GDP for ${q}`); continue; }
    const expect = Math.round(c.vNom[i] * gdp[gdpBase] / gdp[q]);
    const err = Math.abs(c.vGdp[i] - expect) / Math.max(expect, 1);
    if (err > worst) { worst = err; at = `${c.dates[i]}: ${c.vGdp[i]} vs ${expect}`; }
  }
  check(`${c.slug}: vGdp recomputes from the GDP table`, worst < 1e-6, at);

  // Scaling to the latest quarter only ever scales a past figure up, as long as the
  // latest quarter is the largest economy on record -- true unless a recession is
  // under way, in which case this check is the place that should notice.
  const mults = c.vNom.map((v, i) => c.vGdp[i] / v);
  check(`${c.slug}: GDP-adjusted never below nominal`, mults.every((x) => x >= 1 - 1e-9),
    `min ${Math.min(...mults).toFixed(4)}`);

  if (c.latest) {
    const n = c.t.length;
    check(`${c.slug}: latest matches the final point`,
      c.latest.vNom === c.vNom[n - 1] && Math.abs(c.latest.t - c.t[n - 1]) < 1e-9);
    check(`${c.slug}: ageYears matches the final point`, Math.abs(c.ageYears - c.t[n - 1]) < 1e-9);
  }
}

// Independent reimplementation of the log-tick generator: the axis must never
// emit a tick outside the domain it was asked for.
function logTicks(yMin, yMax) {
  const decades = Math.log10(yMax) - Math.log10(yMin);
  const mant = decades >= 4 ? [1] : decades >= 2 ? [1, 3] : [1, 2, 5];
  const out = [];
  for (let k = Math.floor(Math.log10(yMin)); k <= Math.ceil(Math.log10(yMax)); k++) {
    for (const mm of mant) {
      const v = mm * 10 ** k;
      if (v >= yMin * 0.999 && v <= yMax * 1.001) out.push(v);
    }
  }
  return out;
}
for (const [lo, hi] of [[1e6, 5e12], [1e9, 2e10], [4.5e9, 1.6e10], [1e5, 1e13]]) {
  const t = logTicks(lo, hi);
  check(`logTicks(${lo}, ${hi}) is non-empty`, t.length > 0);
  check(`logTicks(${lo}, ${hi}) stays inside the domain`, t.every((v) => v >= lo * 0.999 && v <= hi * 1.001));
}

// ── 4. structural wiring ────────────────────────────────────────────────────
console.log('4. page wiring');

for (const [name, needle] of [
  ['react pinned to 18.2.0', 'https://esm.sh/react@18.2.0'],
  ['htm pinned to 3.1.1', 'https://esm.sh/htm@3.1.1'],
  ['localStorage key', "STORAGE_KEY = 'valuation-curves-v1'"],
  ['localStorage is wrapped in try/catch', 'catch (e)'],
  ['dark mode block', '@media (prefers-color-scheme: dark)'],
  ['back link', 'class="back-link"'],
  ['methodology section', 'How this was built'],
  ['no external stylesheet', '<link rel="stylesheet"'],
]) {
  const found = htmlText.includes(needle);
  check(name, name.startsWith('no ') ? !found : found);
}
for (const hex of [...data.meta.palette.light, ...data.meta.palette.dark]) {
  check(`palette colour ${hex} reaches the page`, htmlText.includes(hex));
}

// The module must at least parse. A stray backtick inside an htm template is
// otherwise a blank page discovered only in a browser.
const mod = htmlText.match(/<script type="module">([\s\S]*?)<\/script>/);
check('module script found', !!mod);
if (mod) {
  const tmp = join(HERE, '.verify-tmp.mjs');
  try {
    writeFileSync(tmp, mod[1]);
    execFileSync(process.execPath, ['--check', tmp], { stdio: 'pipe' });
    check('module parses under node --check', true);
  } catch (e) {
    check('module parses under node --check', false, String(e.stderr || e.message).slice(0, 300));
  } finally {
    try { unlinkSync(tmp); } catch { /* already gone */ }
  }
}

// ── 5. render smoke test, React stubbed ─────────────────────────────────────
console.log('5. render smoke test');

const htmSrc = await fetch('https://unpkg.com/htm@3.1.1/dist/htm.module.js')
  .then((r) => (r.ok ? r.text() : null))
  .catch(() => null);

if (!htmSrc) {
  warn('could not fetch htm from esm.sh — render smoke test skipped (offline?)');
} else {
  // Run the page as a real module: the fetched htm, a recording React, and a
  // scripted browser. Anything less does not exercise the templates -- a stray
  // backtick inside one is otherwise a blank page found only in a browser.
  const tmpHtm = join(HERE, '.verify-htm.mjs');
  const tmpReact = join(HERE, '.verify-react.mjs');
  const tmpDom = join(HERE, '.verify-dom.mjs');
  const tmpApp = join(HERE, '.verify-app.mjs');

  const reactStub = `
    export const useState = (init) => [typeof init === 'function' ? init() : init, () => {}];
    export const useEffect = () => {};
    export const useMemo = (fn) => fn();
    export const useRef = () => ({ current: { getBoundingClientRect: () => ({ left: 0, width: 1000 }) } });
    export const useCallback = (fn) => fn;
    export const createElement = (type, props, ...children) =>
      ({ type, props: props || {}, children: children.flat(Infinity) });
    export default { useState, useEffect, useMemo, useRef, useCallback, createElement };
  `;

  const appSrc = mod[1]
    .replace(/import React[^;]*from 'react';/, "import React, { useState, useEffect, useMemo, useRef, useCallback } from './.verify-react.mjs';")
    .replace(/import \{ createRoot \}[^;]*;/, "import { createRoot } from './.verify-dom.mjs';")
    .replace(/import htm from 'htm';/, "import htm from './.verify-htm.mjs';")
    .replace(/createRoot\(document[\s\S]*?\);\s*$/m, '')
    + '\nexport { App, DATA, fmtUsd, logTicks, domainFor, valueAt, loadState };\n';

  writeFileSync(tmpHtm, htmSrc);
  writeFileSync(tmpReact, reactStub);
  writeFileSync(tmpDom, 'export const createRoot = () => ({ render: () => {} });');
  writeFileSync(tmpApp, appSrc);

  // Walk the tree, calling function components so the whole page is exercised
  // rather than just its outermost element.
  function walk(node, out) {
    if (node == null || typeof node !== 'object') return;
    if (Array.isArray(node)) { for (const n of node) walk(n, out); return; }
    const { type, props, children } = node;
    if (typeof type === 'function') {
      out.components.push(type.name);
      walk(type({ ...props, children }), out);
      return;
    }
    if (typeof type === 'string') {
      const cls = props?.class || props?.className || '';
      out.tags.push(type);
      for (const c of String(cls).split(/\s+/)) if (c) out.classes.push(c);
    }
    walk(children, out);
    if (props?.children) walk(props.children, out);
  }

  try {
    const scenarios = [
      ['defaults', null, ''],
      ['corrupt localStorage', '{{{not json', ''],
      ['empty selection', JSON.stringify({ selected: [] }), ''],
      ['unknown slug in storage', JSON.stringify({ selected: ['nope', data.companies[0].slug] }), ''],
      ['all companies', JSON.stringify({ selected: data.companies.map((c) => c.slug) }), ''],
      ['nominal via URL', null, '?gdp=0'],
      ['age sort', JSON.stringify({ sort: 'age' }), ''],
      // Window chosen to straddle the company's real span, so this exercises zoom
      // rather than the empty-window branch.
      ['zoom window via URL', null, `?c=${data.companies[0].slug}&x=0-${Math.ceil(data.companies[0].ageYears)}`],
      ['zoom window with no data in range', null, `?c=${data.companies[0].slug}&x=0-0.5`],
    ];

    for (const [label, store, search] of scenarios) {
      globalThis.localStorage = { getItem: () => store, setItem: () => {} };
      globalThis.location = { search, pathname: '/valuation-curves/' };
      globalThis.history = { replaceState: () => {} };
      globalThis.matchMedia = () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} });
      globalThis.document = { getElementById: () => ({}) };

      // A fresh query string each time, because ESM caches a module by URL.
      const url = pathToFileURL(tmpApp).href + '?s=' + encodeURIComponent(label);
      try {
        const m2 = await import(url);
        const out = { tags: [], classes: [], components: [] };
        walk(m2.App(), out);
        const expected = m2.loadState().selected.length;
        const lines = out.classes.filter((c) => c === 'line').length;
        check(`renders: ${label}`, out.tags.length > 0);
        if (label === 'zoom window with no data in range') {
          check(`renders: ${label} — draws no line`, lines === 0, `${lines} paths`);
          check(`renders: ${label} — offers a way out`, out.classes.includes('empty') && out.classes.includes('ghost'));
        } else {
          check(`renders: ${label} — one line per selected company`, lines === expected, `${lines} paths vs ${expected} selected`);
        }
        if (label === 'defaults') {
          check('renders: methodology present', out.components.includes('Methodology'));
          check('renders: sidebar lists every company',
            out.classes.filter((c) => c === 'row-btn').length === data.companies.length);
          const diamonds = out.classes.filter((c) => c === 'ipo-glyph').length;
          check('renders: an IPO glyph per public company shown',
            diamonds === data.companies.filter((c) => m2.loadState().selected.includes(c.slug) && c.ipoIndex != null).length,
            `${diamonds} diamonds`);
        }
      } catch (e) {
        check(`renders: ${label}`, false, String(e.message).slice(0, 220));
      }
    }
  } finally {
    for (const f of [tmpHtm, tmpReact, tmpDom, tmpApp]) { try { unlinkSync(f); } catch { /* already gone */ } }
  }
}

// ── 6. palette ──────────────────────────────────────────────────────────────
// The page claims two specific things about colour, and both are checkable:
// that the default companies are mutually distinguishable in both modes,
// and that hue alone does NOT carry identity for every company — which is why every
// line also gets a dash pattern and an always-on name label.
console.log('6. palette');

const hex2rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const luminance = (h) => { const [r, g, b] = hex2rgb(h).map(toLinear); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const contrast = (a, b) => { const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

function toLab(h) {
  const [r, g, b] = hex2rgb(h).map(toLinear);
  const X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047;
  const Y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
}
const deltaE = (a, b) => Math.hypot(...toLab(a).map((v, i) => v - toLab(b)[i]));

// Machado et al. deuteranopia at full severity, applied in linear RGB.
function deuter(h) {
  const [r, g, b] = hex2rgb(h).map(toLinear);
  const m = [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]];
  const out = m.map(([a1, a2, a3]) => Math.min(1, Math.max(0, a1 * r + a2 * g + a3 * b)));
  const back = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);
  return '#' + out.map((c) => Math.round(back(c) * 255).toString(16).padStart(2, '0')).join('');
}

const SURFACE = { light: '#fcfcfb', dark: '#1a1a19' };
for (const mode of ['light', 'dark']) {
  const pal = data.meta.palette[mode];

  // The defaults are the page's headline claim — these must hold.
  const defaultSlots = data.meta.defaults
    .map((s) => data.companies.find((c) => c.slug === s))
    .filter(Boolean)
    .map((c) => pal[c.colorSlot]);
  for (let i = 0; i < defaultSlots.length; i++) {
    for (let j = i + 1; j < defaultSlots.length; j++) {
      const [a, b] = [defaultSlots[i], defaultSlots[j]];
      check(`${mode}: defaults ${a} vs ${b} separated for normal vision`, deltaE(a, b) >= 15, `ΔE ${deltaE(a, b).toFixed(1)}`);
      check(`${mode}: defaults ${a} vs ${b} separated under deuteranopia`,
        deltaE(deuter(a), deuter(b)) >= 8, `ΔE ${deltaE(deuter(a), deuter(b)).toFixed(1)}`);
    }
  }

  // The full palette is expected to fail this; record how badly, so the tradeoff
  // stays visible rather than being quietly forgotten.
  let worstPair = Infinity, worstAt = '';
  for (let i = 0; i < pal.length; i++) {
    for (let j = i + 1; j < pal.length; j++) {
      const d = deltaE(deuter(pal[i]), deuter(pal[j]));
      if (d < worstPair) { worstPair = d; worstAt = `${pal[i]} vs ${pal[j]}`; }
    }
  }
  if (worstPair < 8) {
    warn(`${mode}: closest pair across all 8 hues is ΔE ${worstPair.toFixed(1)} under deuteranopia (${worstAt}) `
      + `— expected; dash patterns and end labels carry identity`);
  }

  const lowContrast = pal.filter((h) => contrast(h, SURFACE[mode]) < 3);
  if (lowContrast.length) {
    warn(`${mode}: ${lowContrast.length} hue(s) under 3:1 against the surface (${lowContrast.join(', ')}) `
      + `— relief is the always-on direct labels, which must never become optional`);
  }
  check(`${mode}: every hue is a valid 6-digit hex`, pal.every((h) => /^#[0-9a-f]{6}$/i.test(h)));
}

// ── report ──────────────────────────────────────────────────────────────────
console.log('');
for (const w of warnings) console.log(`  WARN  ${w}`);
for (const f of failures) console.log(`  FAIL  ${f}`);
console.log(`\n${pass} passed, ${failures.length} failed, ${warnings.length} warning(s)`);
process.exit(failures.length ? 1 : 0);
