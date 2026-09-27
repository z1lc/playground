import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const coreMatch = html.match(/<script id="monitor-core">([\s\S]*?)<\/script>/);
if (!coreMatch) throw new Error('Inline monitor core was not found');
const sandbox = {};
vm.runInNewContext(coreMatch[1], sandbox);

const { MONITORS, MM_IN, DEFAULT_VISIBLE, defaultHidden, arcGeom, arcPoint, splitPart, derive, layoutColumn, selfCheck, partitionRows, physAreaMm2, panelType } = sandbox.MonitorSizes;
const derived = MONITORS.map(m => derive({ ...m }, 0, MONITORS));
const byId = Object.fromEntries(derived.map(m => [m.id, m]));

describe('data', () => {
  it('passes the built-in consistency check', () => {
    expect(selfCheck(MONITORS)).toEqual([]);
  });

  it('has unique ids, distinct colour/stroke looks, and the TV as the only reference item', () => {
    expect(new Set(MONITORS.map(m => m.id)).size).toBe(MONITORS.length);
    const dashed = MONITORS.filter(m => m.dash);
    expect(dashed.map(m => m.id).sort()).toEqual(['s3225qs-x2', 'un48ju6700']);
    expect(new Set(dashed.map(m => m.dash)).size).toBe(dashed.length);   // distinct dash patterns
    expect(MONITORS.filter(m => m.reference).map(m => m.id)).toEqual(['un48ju6700']);
    const solid = MONITORS.filter(m => !m.dash);
    expect(new Set(solid.map(m => m.color)).size).toBe(solid.length);
    // the eight validated categorical slots are all in use, plus neutral grey
    const slots = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'];
    for (const c of slots) expect(solid.some(m => m.color === c), c).toBe(true);
  });

  it('reproduces the manufacturer-stated diagonals from the active area', () => {
    for (const m of derived) {
      expect(Math.abs(m.diagCalcIn - m.diagIn) / m.diagIn).toBeLessThan(0.005);
    }
  });

  it('records the year each display first went on sale', () => {
    for (const m of MONITORS) {
      expect(Number.isInteger(m.year), m.id).toBe(true);
      expect(m.year).toBeGreaterThanOrEqual(2015);
      expect(m.year).toBeLessThanOrEqual(2026);
      expect(m.available.length, m.id).toBeGreaterThan(10);
    }
    expect(MONITORS.find(m => m.id === 'un48ju6700').year).toBe(2015);
    expect(MONITORS.find(m => m.id === 'neo-g9-57').year).toBe(2023);
    expect(MONITORS.find(m => m.id === 'aw3926qw').year).toBe(2026);
  });

  it('cites at least one source per display', () => {
    for (const m of MONITORS) {
      expect(m.sources.length).toBeGreaterThan(0);
      for (const s of m.sources) expect(s.url).toMatch(/^https:\/\//);
    }
  });
});

describe('derived values', () => {
  it('matches manufacturer-stated pixel densities', () => {
    expect(byId.u2725qe.ppi).toBeCloseTo(163, 0);
    expect(byId.u5226kw.ppi).toBeCloseTo(129, 0);
    expect(byId.u4025qw.ppi).toBeCloseTo(140, 0);
    expect(byId.aw3926qw.ppi).toBeCloseTo(143, 0);
    expect(byId['neo-g9-57'].ppi).toBeCloseTo(140, 0);
    expect(byId['45gx950a'].ppi).toBeCloseTo(125, 0);
  });

  it('reproduces the manufacturers\u2019 stated active areas as physical area', () => {
    expect(byId.u5226kw.areaIn2).toBeCloseTo(940.77, 0);   // Dell User\u2019s Guide: 940.77 in²
    expect(byId.u4025qw.areaIn2).toBeCloseTo(564.69, 0);   // Dell: 564.69 in²
    expect(byId.u2725qe.areaIn2).toBeCloseTo(310.47, 0);   // Dell: 310.47 in²
    expect(byId['neo-g9-57'].areaIn2).toBeCloseTo(847.9, 0);
    // a 47.6 in 16:9 TV has more screen surface than the 51.6 in 21:9 ultrawide
    expect(byId.un48ju6700.areaIn2).toBeGreaterThan(byId['52g930b'].areaIn2);
    // curved screens: surface area uses the unrolled (arc) width, so it exceeds the footprint
    for (const m of derived.filter(m => m.radiusMm)) expect(m.areaIn2).toBeGreaterThan(m.chordIn * m.hIn);
  });

  it('computes megapixels and aspect decimals', () => {
    expect(byId['neo-g9-57'].mp).toBeCloseTo(16.6, 1);
    expect(byId.u5226kw.aspectDec).toBeCloseTo(2.4, 6);
    expect(byId.u2725qe.aspectDec).toBeCloseTo(16 / 9, 6);
  });

  it('a flat single screen has chord = width, zero depth and no toe-in', () => {
    const flat = byId.u2725qe;
    expect(flat.radiusMm).toBeNull();
    expect(flat.chordIn).toBeCloseTo(flat.wIn, 9);
    expect(flat.sagIn).toBe(0);
    expect(flat.focalIn).toBeNull();
    expect(flat.toeInRad).toBe(0);
  });

  it('curved screens satisfy the circle identity chord²/4 + (R − sag)² = R²', () => {
    for (const m of derived.filter(m => m.radiusMm)) {
      const { chordMm, sagMm } = arcGeom(m.activeWmm, m.radiusMm);
      expect(chordMm).toBeLessThan(m.activeWmm);
      expect(sagMm).toBeGreaterThan(0);
      const lhs = (chordMm * chordMm) / 4 + (m.radiusMm - sagMm) ** 2;
      expect(lhs).toBeCloseTo(m.radiusMm * m.radiusMm, 6);
      expect(m.chordIn).toBeCloseTo(chordMm * MM_IN, 9);
      expect(m.focalIn).toBeCloseTo(m.radiusMm * MM_IN, 9);
    }
  });

  it('gets the known 1000R and 1800R geometry right', () => {
    // Neo G9 57: 1394.6 mm arc on 1000R → ≈1284 mm chord, ≈233 mm bow
    expect(byId['neo-g9-57'].chordIn * 25.4).toBeCloseTo(1284.4, 0);
    expect(byId['neo-g9-57'].sagIn * 25.4).toBeCloseTo(233.5, 0);
    // S3221QS: chord + two 8.2 mm bezels ≈ 709.2 mm chassis width (Dell manual)
    expect(byId.s3221qs.chordIn * 25.4 + 2 * 8.2).toBeCloseTo(709.2, 0);
  });

  it('models two S2725QC side by side as one flat assembly with the bezel gap', () => {
    const pair = byId['s2725qc-x2'];
    expect(pair.units).toBe(2);
    expect(pair.unitWmm).toBeCloseTo(596.74, 6);          // one screen's active width
    expect(pair.wIn * 25.4).toBeCloseTo(2 * 596.74 + 14.8, 6);
    expect(pair.diagCalcIn).toBeCloseTo(27.0, 1);          // per-screen diagonal, not the pair's
    expect(pair.ppi).toBeCloseTo(163, 0);
    expect(pair.mp).toBeCloseTo(16.6, 1);
    expect(pair.radiusMm).toBeNull();
    expect(pair.areaIn2).toBeCloseTo(2 * 310.47, 0);       // two panels, seam excluded
    // toed in so the outer edges land near the LG 52G930B's
    const lg = byId['52g930b'];
    expect(pair.toeInDeg).toBeCloseTo(17.5, 0);
    expect(pair.chordIn).toBeLessThan(pair.wIn);
    expect(Math.hypot(pair.chordIn / 2 - lg.chordIn / 2, pair.sagIn - lg.sagIn)).toBeLessThan(1);
  });

  it('models two S3225QS side by side, matching the Neo G9 57 in screen area and pixels', () => {
    const pair = byId['s3225qs-x2'], neo = byId['neo-g9-57'];
    expect(pair.units).toBe(2);
    expect(pair.unitWmm).toBeCloseTo(697.31, 6);
    expect(pair.diagCalcIn).toBeCloseTo(31.5, 1);
    expect(pair.ppi).toBeCloseTo(140, 0);                  // Dell prints the truncated 139
    expect(pair.areaIn2).toBeCloseTo(2 * 423.93, 0);       // Dell: 423.93 in² per screen
    expect(pair.areaIn2).toBeCloseTo(neo.areaIn2, 0);
    expect(pair.mp).toBe(neo.mp);
    expect(pair.activeHmm).toBeCloseTo(neo.activeHmm, 0);
    expect(pair.radiusMm).toBeNull();
    // toed in so the outer edges land near the Neo G9 57's
    expect(pair.toeInDeg).toBeCloseTo(20.2, 0);
    expect(Math.hypot(pair.chordIn / 2 - neo.chordIn / 2, pair.sagIn - neo.sagIn)).toBeLessThan(1);
    // each screen keeps its full length: seam-to-outer-edge distance equals one active width
    expect(Math.hypot(pair.chordIn / 2 - pair.gapMm / 2 / 25.4, pair.sagIn) * 25.4).toBeCloseTo(697.31, 3);
  });

  it('keeps every curved active width wider than its chord but narrower than a semicircle', () => {
    for (const m of derived.filter(m => m.radiusMm)) {
      expect(m.activeWmm).toBeLessThan(Math.PI * m.radiusMm);
      expect(m.chordIn).toBeLessThan(m.wIn);
    }
  });
});

describe('layoutColumn', () => {
  const mk = (ax, ay, id) => ({ id, ax, ay });

  it('stacks labels in anchor order with at least one pitch between them', () => {
    const items = [mk(300, 120, 'a'), mk(280, 100, 'b'), mk(320, 100, 'c'), mk(200, 400, 'd')];
    const { items: laid } = layoutColumn(items, { topPx: 6, plotBottom: 1000, lh: 30 });
    expect(laid.map(i => i.id)).toEqual(['c', 'b', 'a', 'd']);   // ties → rightmost anchor first
    for (let i = 1; i < laid.length; i++) expect(laid[i].y - laid[i - 1].y).toBeGreaterThanOrEqual(36);
    for (const it of laid) expect(it.y).toBeGreaterThanOrEqual(6);
  });

  it('lifts an overflowing stack into the slack above the plot', () => {
    const items = Array.from({ length: 9 }, (_, i) => mk(100 + i, 200 + i, String(i)));
    const { items: laid, bottom } = layoutColumn(items, { topPx: 6, plotBottom: 300, lh: 30 });
    expect(laid[0].y).toBe(6);                                       // used all the slack
    expect(bottom).toBe(6 + 8 * 36 + 30);
    expect(bottom).toBeGreaterThan(300);                             // still overflows: the SVG must grow
  });

  it('handles an empty selection', () => {
    expect(layoutColumn([], { topPx: 6, plotBottom: 100, lh: 30 })).toEqual({ items: [], bottom: 6 });
  });
});

describe('partitionRows', () => {
  it('lists enabled screens first, then disabled, each largest-first', () => {
    const { enabled, disabled } = partitionRows(MONITORS, new Set(['u2725qe', 'neo-g9-57']));
    expect(disabled.map(m => m.id)).toEqual(['neo-g9-57', 'u2725qe']);
    expect(enabled).toHaveLength(9);
    expect(enabled[0].id).toBe('un48ju6700');                // largest screen surface
    for (let i = 1; i < enabled.length; i++) expect(physAreaMm2(enabled[i - 1])).toBeGreaterThanOrEqual(physAreaMm2(enabled[i]));
    expect(enabled.map(m => m.id)).toEqual(['un48ju6700', '52g930b', 'u5226kw', 's3225qs-x2', '45gx950a', 's2725qc-x2', 'u4025qw', 'aw3926qw', 's3221qs']);
  });

  it('puts every screen in exactly one section', () => {
    const { enabled, disabled } = partitionRows(MONITORS, new Set(['s3221qs']));
    const ids = [...enabled, ...disabled].map(m => m.id).sort();
    expect(ids).toEqual(MONITORS.map(m => m.id).sort());
    expect(partitionRows(MONITORS, new Set()).disabled).toEqual([]);
    expect(partitionRows(MONITORS, new Set(MONITORS.map(m => m.id))).enabled).toEqual([]);
  });
});

describe('panelType', () => {
  it('reduces every panel description to IPS, VA or OLED', () => {
    const expected = {
      'neo-g9-57': 'VA', '52g930b': 'VA', u5226kw: 'IPS', un48ju6700: 'VA', '45gx950a': 'OLED',
      u4025qw: 'IPS', aw3926qw: 'OLED', s3221qs: 'VA', u2725qe: 'IPS', 's2725qc-x2': 'IPS', 's3225qs-x2': 'VA',
    };
    for (const m of MONITORS) expect(panelType(m), m.id).toBe(expected[m.id]);
  });
});

describe('arcPoint (split markers)', () => {
  it('walks a flat screen in a straight line', () => {
    expect(arcPoint(0.5, 600, null)).toEqual({ xMm: 0, depthMm: 0 });
    expect(arcPoint(0, 600, null)).toEqual({ xMm: -300, depthMm: 0 });
    expect(arcPoint(1 / 3, 600, null).xMm).toBeCloseTo(-100, 9);
  });

  it('lands on the arc: middle at the stand line, ends at the chord tips', () => {
    for (const m of derived.filter(m => m.radiusMm)) {
      const mid = arcPoint(0.5, m.activeWmm, m.radiusMm);
      expect(mid.xMm).toBeCloseTo(0, 9);
      expect(mid.depthMm).toBeCloseTo(0, 9);
      const { chordMm, sagMm } = arcGeom(m.activeWmm, m.radiusMm);
      const right = arcPoint(1, m.activeWmm, m.radiusMm), left = arcPoint(0, m.activeWmm, m.radiusMm);
      expect(right.xMm).toBeCloseTo(chordMm / 2, 6);
      expect(right.depthMm).toBeCloseTo(sagMm, 6);
      expect(left.xMm).toBeCloseTo(-chordMm / 2, 6);
      // every point stays on the circle of radius R centred R behind... i.e. toward the viewer from the stand line
      for (const f of [0.25, 1 / 3, 2 / 3, 0.9]) {
        const pt = arcPoint(f, m.activeWmm, m.radiusMm);
        expect(Math.hypot(pt.xMm, m.radiusMm - pt.depthMm)).toBeCloseTo(m.radiusMm, 6);
      }
    }
  });

  it('splits into equal arc lengths', () => {
    const neo = byId['neo-g9-57'];
    const a = arcPoint(1 / 3, neo.activeWmm, neo.radiusMm), b = arcPoint(2 / 3, neo.activeWmm, neo.radiusMm);
    expect(a.xMm).toBeCloseTo(-b.xMm, 9);                     // symmetric about the centre
    expect(a.depthMm).toBeCloseTo(b.depthMm, 9);
    // the angle subtended between the two thirds markers is one third of the whole arc
    const ang = 2 * Math.asin(Math.hypot(b.xMm - a.xMm, b.depthMm - a.depthMm) / 2 / neo.radiusMm);
    expect(ang).toBeCloseTo(neo.activeWmm / neo.radiusMm / 3, 9);
  });
});

describe('splitPart (front-view rows)', () => {
  it('divides width and horizontal pixels equally, keeping the height', () => {
    const u = splitPart(byId.u5226kw, 3);
    expect(u.resW).toBe(2048);
    expect(u.exact).toBe(true);
    expect(u.resH).toBe(2560);
    expect(u.wIn).toBeCloseTo(47.52 / 3, 2);
    expect(u.hIn).toBeCloseTo(19.8, 1);
    const whole = splitPart(byId.u5226kw, 1);
    expect(whole.resW).toBe(6144);
    expect(whole.wIn).toBeCloseTo(byId.u5226kw.wIn, 9);
  });

  it('flags splits that do not land on whole pixels', () => {
    expect(splitPart(byId.u4025qw, 3).exact).toBe(false);      // 5120 / 3
    expect(splitPart(byId.u4025qw, 3).resW).toBeCloseTo(1706.67, 2);
    expect(splitPart(byId['neo-g9-57'], 3).exact).toBe(true);   // 7680 / 3 = 2560
    expect(splitPart(byId['neo-g9-57'], 4).resW).toBe(1920);
    expect(splitPart(byId.u2725qe, 4).resW).toBe(960);
  });

  it('reports each part\u2019s aspect ratio as a decimal', () => {
    expect(splitPart(byId.u4025qw, 1).aspect).toBeCloseTo(2.37, 2);   // whole 21:9 panel
    expect(splitPart(byId.u4025qw, 3).aspect).toBeCloseTo(0.79, 2);   // one third of it
    expect(splitPart(byId.u2725qe, 2).aspect).toBeCloseTo(0.89, 2);   // half of 16:9
    expect(splitPart(byId['neo-g9-57'], 2).aspect).toBeCloseTo(16 / 9, 6);   // half a 32:9 is exactly 16:9
  });
});

describe('default selection', () => {
  it('starts with only the 27-inch pair and the LG 45GX950A-B visible', () => {
    expect(DEFAULT_VISIBLE.sort()).toEqual(['45gx950a', 's2725qc-x2']);
    for (const id of DEFAULT_VISIBLE) expect(MONITORS.some(m => m.id === id), id).toBe(true);
    const hidden = defaultHidden(MONITORS);
    expect(hidden).toHaveLength(MONITORS.length - 2);
    expect(hidden).not.toContain('45gx950a');
    expect(hidden).not.toContain('s2725qc-x2');
    expect(hidden).toContain('neo-g9-57');
  });
});
