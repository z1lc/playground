import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const coreMatch = html.match(/<script id="layout-core">([\s\S]*?)<\/script>/);
if (!coreMatch) throw new Error('Inline layout core was not found');
const sandbox = {};
vm.runInNewContext(coreMatch[1], sandbox);
const G = sandbox.GarageLayout;
const plain = v => JSON.parse(JSON.stringify(v));

const item = (type, x, y, rot = 0, extra = {}) => ({ uid: `${type}-${x}-${y}-${rot}`, type, x, y, rot, ...extra });
const levels = res => plain(res.issues).map(i => i.level);

describe('catalog', () => {
  it('has every requested piece of equipment, both trainer options, with unique ids', () => {
    const ids = G.TYPES.map(t => t.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toEqual(['mikolo', 'rogue', 'bench', 'dumbbells', 'treadmill', 'stair', 'bag-hanging', 'bag-standing', 'sauna', 'plunge', 'yoga', 'tv', 'minisplit', 'ebikes']);
  });

  it('gives each type positive dimensions, a known group and https sources', () => {
    const groups = G.GROUPS.map(g => g.id);
    for (const t of G.TYPES) {
      expect(t.w, t.id).toBeGreaterThan(0);
      expect(t.d, t.id).toBeGreaterThan(0);
      expect(groups, t.id).toContain(t.group);
      expect(t.zoneName, t.id).toBeTruthy();
      expect(t.power, t.id).toMatch(/^[A-Z].*\.$/);
      for (const s of t.sources) expect(s.url, t.id).toMatch(/^https:\/\//);
    }
  });

  it('keeps every drawing inside its item’s outline', () => {
    for (const t of G.TYPES) {
      expect(t.art && t.art.length, t.id).toBeGreaterThan(0);
      for (const [kind, ...v] of t.art) {
        const [x0, y0, x1, y1] =
          kind === 'r' ? [v[0], v[1], v[0] + v[2], v[1] + v[3]] : kind === 'l' ? [Math.min(v[0], v[2]), Math.min(v[1], v[3]), Math.max(v[0], v[2]), Math.max(v[1], v[3])] : [v[0] - v[2], v[1] - v[2], v[0] + v[2], v[1] + v[2]];
        expect(x0 >= 0 && y0 >= 0 && x1 <= t.w + 1e-9 && y1 <= t.d + 1e-9, `${t.id} ${kind} ${v.join(',')}`).toBe(true);
      }
    }
  });

  it('gives both trainers 24" each side and 36" in front', () => {
    for (const id of ['mikolo', 'rogue']) {
      expect(plain(G.TYPES.find(t => t.id === id).clear), id).toEqual({ left: 24, right: 24, bottom: 36 });
    }
  });

  it('uses the researched dimensions', () => {
    const t = Object.fromEntries(G.TYPES.map(x => [x.id, x]));
    expect([t.sauna.w, t.sauna.d]).toEqual([84, 60]);
    expect([t.treadmill.w, t.treadmill.d]).toEqual([38.1, 69.9]);
    expect(plain(t.treadmill.clear)).toEqual({ bottom: 24 }); // like the stair climber, by choice
    expect([t.plunge.w, t.plunge.d]).toEqual([77, 31.5]);
    expect([t.mikolo.w, t.mikolo.d, t.mikolo.h]).toEqual([79.2, 69.8, 91.6]);
  });
});

describe('geometry', () => {
  it('swaps width and depth at 90° and 270°', () => {
    expect(plain(G.footprint(item('treadmill', 0, 0, 0)))).toMatchObject({ w: 38.1, d: 69.9 });
    expect(plain(G.footprint(item('treadmill', 0, 0, 90)))).toMatchObject({ w: 69.9, d: 38.1 });
    expect(plain(G.footprint(item('treadmill', 0, 0, 180)))).toMatchObject({ w: 38.1, d: 69.9 });
    expect(plain(G.footprint(item('treadmill', 0, 0, 270)))).toMatchObject({ w: 69.9, d: 38.1 });
  });

  it('turns clearance clockwise with the item', () => {
    const c = { top: 1, right: 2, bottom: 3, left: 4 };
    expect(plain(G.rotateSides(c, 0))).toEqual(c);
    expect(plain(G.rotateSides(c, 90))).toEqual({ top: 4, right: 1, bottom: 2, left: 3 });
    expect(plain(G.rotateSides(c, 180))).toEqual({ top: 3, right: 4, bottom: 1, left: 2 });
    expect(plain(G.rotateSides(c, 270))).toEqual({ top: 2, right: 3, bottom: 4, left: 1 });
  });

  it('points the use side the same way as the rotated clearance', () => {
    for (const rot of G.ROTS) {
      const sides = G.rotateSides({ bottom: 1 }, rot);
      const side = Object.keys(sides).find(k => sides[k] === 1);
      expect(G.useSide(rot), `rot ${rot}`).toBe(side);
    }
  });

  it('builds the treadmill step-off space behind the belt at every rotation', () => {
    const near = (r, e) => {
      for (const k of ['x', 'y', 'w', 'd']) expect(r[k], k).toBeCloseTo(e[k], 6);
    };
    near(G.zoneOf(item('treadmill', 100, 50, 0)), { x: 100, y: 50, w: 38.1, d: 93.9 });
    near(G.zoneOf(item('treadmill', 100, 50, 90)), { x: 76, y: 50, w: 93.9, d: 38.1 });
    near(G.zoneOf(item('treadmill', 100, 50, 180)), { x: 100, y: 26, w: 38.1, d: 93.9 });
    near(G.zoneOf(item('treadmill', 100, 50, 270)), { x: 100, y: 50, w: 93.9, d: 38.1 });
    expect(G.zoneOf(item('treadmill', 0, 0, 0))).not.toBeNull();
  });

  it('treats touching edges as not overlapping', () => {
    expect(G.overlaps({ x: 0, y: 0, w: 10, d: 10 }, { x: 10, y: 0, w: 10, d: 10 })).toBe(false);
    expect(G.overlaps({ x: 0, y: 0, w: 10, d: 10 }, { x: 9.5, y: 9.5, w: 10, d: 10 })).toBe(true);
  });

  it('rotates about the center and stays inside the room', () => {
    const r = G.rotateItem(item('treadmill', 100, 50, 0));
    const before = G.footprint(item('treadmill', 100, 50, 0));
    const after = G.footprint(r);
    expect(r.rot).toBe(90);
    expect(after.x + after.w / 2).toBeCloseTo(before.x + before.w / 2, 0);
    expect(after.y + after.d / 2).toBeCloseTo(before.y + before.d / 2, 0);
    const corner = G.footprint(G.rotateItem(item('treadmill', 0, 0, 0)));
    expect(corner.x).toBeGreaterThanOrEqual(0);
    expect(corner.y).toBeGreaterThanOrEqual(0);
    let it4 = item('sauna', 120, 80, 0);
    for (let k = 0; k < 4; k++) it4 = G.rotateItem(it4);
    expect(plain(it4)).toMatchObject({ x: 120, y: 80, rot: 0 });
  });

  it('clamps items inside the walls', () => {
    expect(plain(G.clampItem(item('bench', -20, 400)))).toMatchObject({ x: 0, y: 264 - 56 });
    expect(plain(G.clampItem(item('sauna', 999, 0, 90)))).toMatchObject({ x: 336 - 60 });
  });
});

describe('punching bags', () => {
  it('gets a round 5-foot footwork zone around its center', () => {
    const z = plain(G.zoneOf(item('bag-standing', 100, 100)));
    expect(z).toMatchObject({ round: true, cx: 114, cy: 114, r: 60, x: 54, y: 54, w: 120, d: 120 });
  });

  it('only flags what is inside the circle, not the corners of its bounding square', () => {
    const bag = item('bag-hanging', 143, 100); // center (150, 107)
    // Dumbbells tucked in the bounding square's corner; nearest point (198, 156) is ~69" from the center: clear.
    const corner = item('dumbbells', 198, 156);
    expect(G.analyze([bag, corner], { landing: { from: 0, len: 12, depth: 12 } }).issues.filter(i => i.level === 'bad')).toHaveLength(0);
    // Straight beside the bag, 40" away: in the footwork space.
    const beside = item('dumbbells', 190, 90);
    const res = G.analyze([bag, beside], { landing: { from: 0, len: 12, depth: 12 } });
    expect(res.issues.map(i => i.text)).toContain('Dumbbells is in the Heavy bag’s footwork space.');
  });

  it('warns about a hanging bag under the open garage door, not a free-standing one', () => {
    const door = { x: 96, w: 216 };
    const hang = G.analyze([item('bag-hanging', 200, 200)], { clearance: false, door });
    expect(hang.issues.map(i => i.text)).toEqual(['Heavy bag hangs from the ceiling, but the open garage door covers the ceiling there.']);
    expect(G.analyze([item('bag-standing', 200, 200)], { clearance: false, door }).issues).toHaveLength(0);
  });

  it('does not turn, since a round bag looks the same at every angle', () => {
    const b = item('bag-standing', 50, 60);
    expect(plain(G.rotateItem(b))).toEqual(plain(b));
  });

  it('settles for amber over red when nothing is fully clear', () => {
    // After a free-standing bag takes the open middle, a hanging bag's 10' circle fits nowhere
    // cleanly; it must not land on top of other equipment.
    const one = G.placeNew('bag-standing', G.DEFAULT_ITEMS, {}, 'a');
    const items = G.DEFAULT_ITEMS.concat([one]);
    const two = G.placeNew('bag-hanging', items, {}, 'b');
    const res = G.analyze(items.concat([two]), {});
    expect(res.item.b).not.toBe('bad');
    expect(res.zone.b).not.toBe('bad');
  });

  it('can be added to the default layout without conflicts', () => {
    for (const type of ['bag-hanging', 'bag-standing', 'yoga']) {
      const add = G.placeNew(type, G.DEFAULT_ITEMS, {}, 'new');
      expect(G.analyze(G.DEFAULT_ITEMS.concat([add]), {}).issues, type).toHaveLength(0);
    }
  });
});

describe('moveItem', () => {
  it('rounds to the inch away from anything to snap to', () => {
    const m = G.moveItem(item('bench', 0, 0), 150.4, 120.6, [], { clearance: false });
    expect(plain(m)).toMatchObject({ x: 150, y: 121 });
  });

  it('snaps to a wall within 3 inches', () => {
    const m = G.moveItem(item('bench', 0, 0), 2, 100, [], { clearance: false });
    expect(m.x).toBe(0);
    const r = G.moveItem(item('bench', 0, 0), 336 - 26 - 2.6, 100, [], { clearance: false });
    expect(r.x).toBe(336 - 26);
  });

  it('snaps flush against another item and to the edge of its clearance zone', () => {
    const sauna = item('sauna', 200, 0);
    const flush = G.moveItem(item('bench', 0, 0), 200 - 26 - 2, 100, [sauna], { clearance: false });
    expect(flush.x).toBe(174);
    // Sauna door zone ends at y = 84; a bench dragged to y = 86 snaps onto that edge.
    const z = G.moveItem(item('bench', 0, 0), 220, 86, [sauna], { clearance: true });
    expect(z.y).toBe(84);
  });

  it('snaps its own clearance zone to a wall', () => {
    // Treadmill step-off space is 24" behind; at y = 168 it ends 2.1" short of the garage door wall.
    const m = G.moveItem(item('treadmill', 0, 0), 150, 168, [], { clearance: true });
    expect(m.y + 69.9 + 24).toBeCloseTo(264, 5);
  });

  it('never leaves the room', () => {
    const m = G.moveItem(item('sauna', 0, 0), 500, -50, [], {});
    expect(plain(m)).toMatchObject({ x: 336 - 84, y: 0 });
  });
});

describe('analyze', () => {
  it('finds no issues in the default layout', () => {
    expect(plain(G.analyze(G.DEFAULT_ITEMS, {}).issues)).toEqual([]);
  });

  it('places one of each piece, with the Mikolo as the trainer, all inside the room', () => {
    expect(G.DEFAULT_ITEMS.map(i => i.type).sort()).toEqual(['bench', 'dumbbells', 'mikolo', 'plunge', 'sauna', 'stair', 'treadmill']);
    for (const it of G.DEFAULT_ITEMS) expect(plain(G.clampItem(it)), it.uid).toEqual(plain(it));
  });

  it('flags overlapping footprints as bad on both items', () => {
    const a = item('bench', 100, 100), b = item('dumbbells', 110, 110);
    const res = G.analyze([a, b], { clearance: false });
    expect(levels(res)).toEqual(['bad']);
    expect(res.issues[0].text).toBe('Bench and Dumbbells overlap.');
    expect(plain(res.item)).toEqual({ [a.uid]: 'bad', [b.uid]: 'bad' });
  });

  it('flags an item inside another item’s clearance zone', () => {
    const tm = item('treadmill', 100, 0), bench = item('bench', 110, 80);
    const res = G.analyze([tm, bench], {});
    expect(res.issues.map(i => i.text)).toContain('Bench is in the Treadmill’s step-off space.');
    expect(res.item[bench.uid]).toBe('bad');
    expect(res.zone[tm.uid]).toBe('bad');
    expect(G.analyze([tm, bench], { clearance: false }).issues).toHaveLength(0);
  });

  it('does not double-report a zone hit when the footprints already overlap', () => {
    const res = G.analyze([item('treadmill', 100, 0), item('bench', 100, 0)], {});
    expect(res.issues.filter(i => i.level === 'bad')).toHaveLength(1);
  });

  it('lets clearance zones overlap each other', () => {
    // Treadmill step-off space (x 100–138.1, y 69.9–93.9) and a sideways bench whose 24" side
    // strip (y 76–100) reaches into it: the spaces overlap, but neither touches the other's equipment.
    const res = G.analyze([item('treadmill', 100, 0), item('bench', 40, 100, 90)], { landing: { from: 0, len: 12, depth: 12 } });
    expect(res.issues).toHaveLength(0);
  });

  it('flags anything on the landing and steps, or at the foot of the steps', () => {
    // Default landing: 42" out from the left wall, y 140–212; clear floor at its foot, y 104–140.
    expect(plain(G.landingRects())).toEqual({ box: { x: 0, y: 140, w: 42, d: 72 }, foot: { x: 0, y: 104, w: 42, d: 36 }, run: 30 });
    const on = G.analyze([item('dumbbells', 10, 180)], { clearance: false });
    expect(on.issues.map(i => i.text)).toEqual(['Dumbbells is on the landing and steps.']);
    const foot = G.analyze([item('dumbbells', 10, 110)], { clearance: false });
    expect(foot.issues.map(i => i.text)).toEqual(['Dumbbells blocks the bottom of the steps.']);
    expect(G.analyze([item('dumbbells', 42, 180)], { clearance: false }).issues).toHaveLength(0);
  });

  it('warns when a clearance zone runs into the landing', () => {
    // Turned so the belt runs toward the left wall: its step-off space reaches the landing.
    const res = G.analyze([item('treadmill', 60, 150, 90)], {});
    expect(plain(res.issues)).toEqual([{ level: 'warn', uid: 'treadmill-60-150-90', text: 'Treadmill’s step-off space runs into the landing and steps.' }]);
    expect(res.zone['treadmill-60-150-90']).toBe('warn');
  });

  it('moves the landing with its settings', () => {
    const l = { from: 0, len: 48, depth: 30 };
    expect(plain(G.landingRects(l).box)).toEqual({ x: 0, y: 216, w: 30, d: 48 });
    expect(G.analyze([item('dumbbells', 10, 180)], { clearance: false, landing: l }).issues.map(i => i.text)).toEqual([
      'Dumbbells blocks the bottom of the steps.',
    ]);
    // A landing pushed against the back wall leaves no foot zone rather than one outside the room.
    expect(plain(G.landingRects({ from: 200, len: 64, depth: 40 }).foot)).toEqual({ x: 0, y: 0, w: 40, d: 0 });
  });

  it('defaults the garage door to an 18-foot opening ending 2 feet from the right wall', () => {
    expect(G.ROOM.w - G.DEFAULT_DOOR.x - G.DEFAULT_DOOR.w).toBe(24);
    expect(G.DEFAULT_DOOR.w).toBe(216);
    expect(G.DEFAULT_LANDING.from).toBe(52);
  });

  it('warns when a clearance zone runs past a wall, naming the wall and distance', () => {
    const res = G.analyze([item('treadmill', 100, 180)], {});
    expect(levels(res)).toEqual(['warn']);
    expect(res.issues[0].text).toBe('Treadmill’s step-off space runs 10″ past the garage door wall.');
    const corner = G.analyze([item('bench', 0, 0)], {});
    expect(corner.issues[0].text).toBe('Bench’s side clearance runs 2′ past the left wall and 1′ past the back wall.');
  });

  it('warns about tall items under the open garage door only', () => {
    const door = { x: 72, w: 192 };
    const tall = G.analyze([item('mikolo', 120, 190)], { clearance: false, door });
    expect(plain(tall.issues)).toEqual([{ level: 'warn', uid: 'mikolo-120-190-0', text: 'Mikolo trainer (7′ 8″ tall) is under the open garage door, which hangs about 7′ up.' }]);
    expect(G.analyze([item('treadmill', 120, 190)], { clearance: false, door }).issues).toHaveLength(0);
    expect(G.analyze([item('mikolo', 50, 190)], { clearance: false, door: { x: 200, w: 120 } }).issues).toHaveLength(0);
  });

  it('lists bad issues before warnings', () => {
    const res = G.analyze([item('treadmill', 100, 150), item('bench', 0, 110, 90)], {});
    expect(levels(res)[0]).toBe('bad');
    expect(levels(res)).toContain('warn');
  });
});

describe('electrical panel', () => {
  const panelIssues = (items, panel) => plain(G.analyze(items, { panel }).issues).filter(i => /electrical panel/.test(i.text));

  it('defaults to the 20-foot mark on the back wall and stays on it', () => {
    expect(plain(G.defaultState().panel)).toEqual({ x: 240 });
    expect(plain(G.normPanel(undefined))).toEqual({ x: 240 });
    expect(plain(G.normPanel({ x: 100.4 }))).toEqual({ x: 100 });
    expect(G.normPanel({ x: -50 }).x).toBe(8);
    expect(G.normPanel({ x: 9999 }).x).toBe(G.ROOM.w - 8);
  });

  it('keeps 30" wide and 36" deep clear in front of the panel, centered when nothing is near', () => {
    const { box, space } = plain(G.panelRects({ x: 240 }, []));
    expect(box).toEqual({ x: 232.75, y: 0, w: 14.5, d: 4 });
    expect(space).toEqual({ x: 225, y: 0, w: 30, d: 40 });
  });

  it('slides the clear space sideways, keeping the panel in it, before calling anything a conflict', () => {
    const bench = item('bench', 204, 0); // ends at 230, 5" into the centered space
    expect(G.panelRects({ x: 240 }, [bench]).space.x).toBe(230);
    expect(panelIssues([bench], { x: 240 })).toEqual([]);
  });

  it('flags equipment that leaves no 30" gap in front of the panel', () => {
    const stair = item('stair', 226, 0);
    const res = G.analyze([stair], { panel: { x: 240 } });
    expect(plain(res.issues)).toEqual([
      { level: 'bad', uid: stair.uid, text: 'Stair climber blocks the electrical panel, which needs 2′ 6″ wide × 3′ deep of clear floor in front of it.' },
    ]);
    expect(res.item[stair.uid]).toBe('bad');
    // With no clear spot, only what is truly in the way is blamed: a sauna starting at 252"
    // would be clear of the space if the stair weren't there.
    const sauna = item('sauna', 252, 0);
    expect(panelIssues([item('stair', 222, 0), sauna], { x: 240 }).map(i => i.uid)).toEqual(['stair-222-0-0']);
    // Moving the panel in the settings moves the rule with it.
    expect(panelIssues([stair], { x: 100 })).toEqual([]);
  });

  it('leaves wall-mounted items out of the floor space, and ignores anything past it', () => {
    expect(G.panelRects({ x: 240 }, [item('tv', 218, 0)]).space.x).toBe(225);
    expect(panelIssues([item('bench', 220, 40)], { x: 240 })).toEqual([]);
  });

  it('uses the default spot for layouts saved before the panel existed', () => {
    const old = JSON.stringify({ v: 1, gv: G.GARAGE_VERSION, items: [], clearance: true, door: G.DEFAULT_DOOR, landing: G.DEFAULT_LANDING, mat: 100 });
    expect(plain(G.parse(old).panel)).toEqual({ x: 240 });
  });
});

describe('electrician view', () => {
  const base = () => G.defaultState();
  const withSplit = (elec = {}) => {
    const s = base();
    return { ...s, items: s.items.concat([G.placeNew('minisplit', s.items, {}, 'ms')]), elec: { ...G.ELEC_DEFAULT, ...elec } };
  };

  it('lists one new circuit per powered item on the plan, and the breaker spaces they take', () => {
    const c = G.circuits(base());
    expect(c.rows.map(r => [r.n, r.type, r.volts, r.amps, r.poles])).toEqual([
      [1, 'sauna', 240, 30, 2], [2, 'plunge', 120, 20, 1], [3, 'treadmill', 120, 20, 1],
    ]);
    expect(c.spaces).toBe(4);
    expect(plain(c.shared)).toEqual(['Stair climber']);
    expect(G.circuits({ ...base(), items: [item('bench', 100, 100)] }).rows).toEqual([]);
  });

  it('follows the sauna and mini-split choices', () => {
    const c = G.circuits(withSplit({ sauna: 'ir', split: '24k' }));
    expect(c.rows.map(r => `${r.type} ${r.volts}V ${r.amps}A ${r.gfci}`)).toEqual([
      'sauna 240V 20A yes', 'minisplit 240V 25A no', 'plunge 120V 20A yes', 'treadmill 120V 20A yes',
    ]);
    expect(c.spaces).toBe(6);
    expect(G.circuits(withSplit({ split: '12k' })).spaces).toBe(5);
    expect(G.circuits(withSplit({ sauna: 'trad8' })).rows[0]).toMatchObject({ amps: 40, gfci: 'ask' });
  });

  it('falls back to the default choices for anything unknown', () => {
    expect(plain(G.normElec({ sauna: 'wood', split: '18k', install: 42 }))).toEqual({ sauna: 'trad6', split: '18k', install: 'pro' });
    expect(plain(G.parse(JSON.stringify({ v: 1, items: [] })))).toMatchObject({ elec: { sauna: 'trad6', split: '18k', install: 'pro' }, tab: 'layout' });
  });

  it('puts the treadmill outlet at its console and the mini-split power at its outdoor unit', () => {
    const c = G.circuits(withSplit());
    expect(plain(c.rows.find(r => r.type === 'treadmill').point)).toEqual({ x: 81, y: 0, wall: 'top' });
    expect(plain(c.rows.find(r => r.type === 'minisplit').point)).toEqual({ x: 84, y: 0, wall: 'top', outside: { x: 84, y: -30 } });
  });

  it('keeps the plunge outlet on a wall at least 6 feet from the tub, never in the door opening', () => {
    const s = base();
    for (const p of G.PRESETS) {
      const pt = G.circuits({ ...s, items: p.items }).rows.find(r => r.type === 'plunge').point;
      const f = G.footprint(p.items.find(i => i.type === 'plunge'));
      const d = Math.hypot(Math.max(f.x - pt.x, 0, pt.x - f.x - f.w), Math.max(f.y - pt.y, 0, pt.y - f.y - f.d));
      expect(d, p.id).toBeGreaterThanOrEqual(72);
      expect(pt.x === 0 || pt.x === G.ROOM.w || pt.y === 0 || pt.y === G.ROOM.d, p.id).toBe(true);
      expect(pt.y === G.ROOM.d && pt.x > s.door.x && pt.x < s.door.x + s.door.w, p.id).toBe(false);
    }
  });

  it('estimates wire runs from the panel in 5-foot steps', () => {
    expect(G.runLength({ x: 294, y: 0 }, { x: 240 })).toBe(20); // 4.5' + 10' up and down, +10%
    expect(G.runLength({ x: 336, y: 234 }, { x: 240 })).toBe(45);
    expect(G.runLength({ x: 336, y: 132, outside: { x: 366, y: 132 } }, { x: 240 })).toBe(40);
  });

  it('splits the electrician into a fixed part per visit and an incremental part per circuit', () => {
    const est = G.costEstimate(base());
    const of = g => plain(est.lines.filter(l => l.group === g));
    expect(of('fixed').map(l => [l.label, l.low, l.high])).toEqual([
      ['Service call and setup', 75, 200], ['Panel work and load calculation', 50, 300], ['Electrical permit', 95, 250],
    ]);
    expect(plain(est.fixed)).toEqual([220, 750]);
    // Sauna: 3–4 h at $50–$150, 20 ft of 10/2 at $2.74–$2.97, GFCI breaker $85–$200 plus box $5–$20.
    expect(of('circuit')[0]).toMatchObject({
      n: 1, label: 'Circuit 1: Sauna (240 V, 30 A)', low: 295, high: 880,
      detail: '3–4 h labor · ~20 ft of 10/2 · 2-pole GFCI breaker (likely required), box, connector and breaker lock',
    });
    const sum = (ls, k) => ls.reduce((s, l) => s + l[k], 0);
    expect(plain(est.incremental)).toEqual([sum(of('circuit'), 'low'), sum(of('circuit'), 'high')]);
    expect(plain(est.electric)).toEqual([est.fixed[0] + est.incremental[0], est.fixed[1] + est.incremental[1]]);
    expect(plain(est.total)).toEqual([sum(est.lines, 'low'), sum(est.lines, 'high')]);
    expect(plain(est.hvac)).toEqual([0, 0]);
  });

  it('adds only incremental cost for another circuit, and prices the mini-split by install', () => {
    const est = G.costEstimate(base());
    const pro = G.costEstimate(withSplit()), diy = G.costEstimate(withSplit({ install: 'diy' }));
    expect(plain(pro.fixed)).toEqual(plain(est.fixed));
    expect(pro.incremental[0]).toBeGreaterThan(est.incremental[0]);
    expect(pro.lines.filter(l => l.group === 'hvac').map(l => l.label)).toEqual(['18,000 BTU unit, installed by an HVAC pro', 'Mechanical permit']);
    expect(pro.hvac[0]).toBeGreaterThan(diy.hvac[0]);
    expect(G.costEstimate(withSplit({ sauna: 'ir' })).lines[3].detail).toMatch(/2-pole GFCI breaker, 6-20 receptacle/);
    expect(est.contingencies.length).toBe(2);
    expect(plain(G.costEstimate({ ...base(), items: [] }).total)).toEqual([0, 0]);
  });
});

describe('costs tab', () => {
  const base = () => G.defaultState();
  const total = ls => [ls.reduce((s, l) => s + l.low, 0), ls.reduce((s, l) => s + l.high, 0)];

  it('prices every piece from a source, the sauna per choice', () => {
    for (const t of G.TYPES) {
      if (t.id === 'minisplit') continue; // priced by the Electrician tab
      const p = G.PRICES[t.id];
      expect(p, t.id).toBeTruthy();
      for (const q of p.byChoice ? Object.values(p.byChoice) : [p]) {
        expect(q.low, t.id).toBeGreaterThan(0);
        expect(q.high, t.id).toBeGreaterThanOrEqual(q.low);
        expect(q.url, t.id).toMatch(/^https:\/\//);
        expect(q.note, t.id).toMatch(/^[A-Z0-9$]/);
        expect(q.note, t.id).not.toMatch(/PENDING/);
      }
    }
    expect(Object.keys(G.PRICES.sauna.byChoice)).toEqual(Object.keys(G.ELEC_CHOICES.sauna));
  });

  it('counts only what is on the plan, in catalog order, and adds it up', () => {
    const s = base();
    const sum = G.costSummary(s);
    expect(sum.groups.map(g => g.id)).toEqual(['strength', 'cardio', 'recovery', 'floor', 'install']);
    expect(sum.groups.flatMap(g => g.lines.map(l => l.type))).toEqual(['mikolo', 'bench', 'dumbbells', 'treadmill', 'stair', 'sauna', 'plunge', 'mats', 'electrician']);
    for (const g of sum.groups) expect(plain(g.subtotal), g.id).toEqual(total(g.lines));
    const all = sum.groups.flatMap(g => g.lines);
    expect(plain(sum.total)).toEqual(total(all));
    expect(plain(sum.total)).toEqual([0, 1].map(k => sum.equipment[k] + sum.floor[k] + sum.install[k]));
    const elec = all.find(l => l.type === 'electrician');
    expect([elec.low, elec.high]).toEqual(plain(G.costEstimate(s).electric));
    const mats = all.find(l => l.type === 'mats');
    expect(mats.label).toBe(`Gym mats, about ${Math.round(G.matArea(s.mat, s.landing))} sq ft`);
  });

  it('adds the mini-split and the TV mount only when they are placed', () => {
    const s = base();
    const items = s.items.concat([G.placeNew('minisplit', s.items, {}, 'ms'), G.placeNew('tv', s.items, {}, 'tv')]);
    const sum = G.costSummary({ ...s, items });
    const types = sum.groups.flatMap(g => g.lines.map(l => l.type));
    expect(types.filter(t => ['tv', 'tv-mount', 'hvac'].includes(t))).toEqual(['tv', 'tv-mount', 'hvac', 'hvac']);
    const hvac = G.costEstimate({ ...s, items }).hvac;
    const lines = sum.groups.find(g => g.id === 'install').lines.filter(l => l.type === 'hvac');
    expect(total(lines)).toEqual(plain(hvac));
    expect(G.costSummary({ ...s, items: [], mat: G.ROOM.w }).total).toEqual([0, 0]);
  });

  it('prices the sauna by the Electrician tab choice', () => {
    const price = sauna => G.costSummary({ ...base(), elec: { ...G.ELEC_DEFAULT, sauna } }).groups.flatMap(g => g.lines).find(l => l.type === 'sauna');
    expect(price('ir')).toMatchObject({ low: G.PRICES.sauna.byChoice.ir.low, high: G.PRICES.sauna.byChoice.ir.high });
    expect(price('trad6')).toMatchObject({ low: G.PRICES.sauna.byChoice.trad6.low });
  });

  it('lists pieces left off the plan for comparison, the mini-split at its chosen size', () => {
    const off = G.costSummary(base()).notOnPlan;
    expect(off.map(l => l.type)).toEqual(['rogue', 'bag-hanging', 'bag-standing', 'yoga', 'tv', 'minisplit', 'ebikes']);
    expect(off.find(l => l.type === 'minisplit')).toMatchObject({ low: G.COSTS.unit.pro['18k'][0], high: G.COSTS.unit.pro['18k'][1] });
  });

  it('remembers the Costs tab, and falls back to Layout for anything else', () => {
    expect(G.parse(G.serialize({ ...base(), tab: 'costs' })).tab).toBe('costs');
    expect(G.parse(G.serialize({ ...base(), tab: 'nope' })).tab).toBe('layout');
  });
});

describe('placeNew', () => {
  it('adds a second trainer to the default layout without collisions', () => {
    // With 24" side space it no longer fits cleanly; the best spot is only short on room.
    const add = G.placeNew('rogue', G.DEFAULT_ITEMS, {}, 'new');
    const res = G.analyze(G.DEFAULT_ITEMS.concat([add]), {});
    expect(res.issues.filter(i => i.level === 'bad')).toHaveLength(0);
  });

  it('falls back to the center when nothing fits', () => {
    const saunas = [];
    for (let y = 0; y + 60 <= 264; y += 60) for (let x = 0; x + 84 <= 336; x += 84) saunas.push(item('sauna', x, y));
    const add = G.placeNew('sauna', saunas, { clearance: false }, 'new');
    expect(plain(add)).toMatchObject({ x: (336 - 84) / 2, y: (264 - 60) / 2, rot: 0 });
  });
});

describe('storage', () => {
  it('round-trips state, including size overrides and door settings', () => {
    const state = {
      items: [item('bench', 10, 20, 90, { w: 24, d: 50 }), item('sauna', 200, 0)],
      clearance: false,
      door: { x: 60, w: 216 },
      landing: { from: 50, len: 80, depth: 40 },
      panel: { x: 180 },
      mat: 120,
      elec: { sauna: 'ir', split: '24k', install: 'diy' },
      tab: 'elec',
      overlay: { on: true, x: 30, y: 40, rot: 90, flip: false },
    };
    const back = G.parse(G.serialize(state));
    expect(plain(back)).toEqual(plain(state));
  });

  it('rejects unusable input', () => {
    expect(G.parse(null)).toBeNull();
    expect(G.parse('not json')).toBeNull();
    expect(G.parse('{"v":2,"items":[]}')).toBeNull();
    expect(G.parse('{"v":1}')).toBeNull();
  });

  it('drops bad items, fixes bad values and keeps the rest', () => {
    const raw = JSON.stringify({
      v: 1,
      gv: G.GARAGE_VERSION,
      items: [
        { uid: 'a', type: 'bench', x: 10, y: 10, rot: 0 },
        { uid: 'b', type: 'hot-tub', x: 10, y: 10, rot: 0 },
        { uid: 'c', type: 'bench', x: 'x', y: 10, rot: 0 },
        { uid: 'd', type: 'bench', x: 10, y: 10, rot: 45 },
        { uid: 'a', type: 'sauna', x: 9999, y: 10, rot: 0, w: 2 },
      ],
      door: { x: 500, w: 1000 },
      landing: { from: 'x', len: 9999, depth: 2 },
    });
    const s = plain(G.parse(raw));
    expect(s.items.map(i => i.type)).toEqual(['bench', 'sauna']);
    expect(s.items[1].uid).not.toBe('a');
    expect(s.items[1].x).toBe(336 - 84);
    expect(s.items[1].w).toBeUndefined();
    expect(s.door).toEqual({ x: 0, w: 336 });
    expect(s.landing).toEqual({ from: 52, len: 212, depth: 12 });
    expect(s.clearance).toBe(true);
  });

  it('keeps the equipment but takes the new garage defaults from a layout saved by an older version', () => {
    // What the first version saved: a centered 16' door and no landing.
    const old = JSON.stringify({ v: 1, items: [item('bench', 10, 20)], clearance: true, door: { x: 72, w: 192 } });
    const s = plain(G.parse(old));
    expect(s.items).toHaveLength(1);
    expect(s.door).toEqual(plain(G.DEFAULT_DOOR));
    expect(s.landing).toEqual(plain(G.DEFAULT_LANDING));
  });

  it('keeps only the first of each equipment type from storage', () => {
    const raw = JSON.stringify({ v: 1, gv: G.GARAGE_VERSION, items: [item('bench', 10, 20), item('bench', 200, 20), item('sauna', 200, 100)] });
    expect(plain(G.parse(raw)).items.map(i => [i.type, i.x])).toEqual([['bench', 10], ['sauna', 200]]);
  });

  it('has at most one of each type in the default layout', () => {
    const types = G.DEFAULT_ITEMS.map(i => i.type);
    expect(new Set(types).size).toBe(types.length);
  });

  it('starts from a fresh copy of the default layout', () => {
    const a = G.defaultState();
    a.items[0].x = 999;
    expect(G.defaultState().items[0].x).toBe(G.DEFAULT_ITEMS[0].x);
  });
});

describe('starting layouts', () => {
  const must = ['bench', 'dumbbells', 'treadmill', 'stair', 'sauna', 'plunge'];

  it('each has one trainer and every must-have, at most one of each, inside the room', () => {
    for (const p of G.PRESETS) {
      const types = p.items.map(i => i.type);
      expect(new Set(types).size, p.id).toBe(types.length);
      for (const m of must) expect(types, `${p.id} ${m}`).toContain(m);
      expect(types.filter(x => x === 'mikolo' || x === 'rogue'), p.id).toHaveLength(1);
      for (const it of p.items) expect(plain(G.clampItem(it)), `${p.id} ${it.type}`).toEqual(plain(it));
      expect(G.normMat(p.mat), p.id).toBe(p.mat);
    }
  });

  it('each fits the default garage with no issues at all', () => {
    for (const p of G.PRESETS) expect(plain(G.analyze(p.items, {}).issues), p.id).toEqual([]);
  });

  it('starts from the first one', () => {
    expect(plain(G.DEFAULT_ITEMS)).toEqual(plain(G.PRESETS[0].items));
    expect(G.DEFAULT_MAT).toBe(G.PRESETS[0].mat);
    expect(G.matchesPreset(G.defaultState(), G.PRESETS[0].id)).toBe(true);
  });

  it('swaps equipment and mat edge but keeps the garage', () => {
    const before = { ...G.defaultState(), door: { x: 50, w: 200 }, landing: { from: 40, len: 60, depth: 40 }, clearance: false };
    const after = G.applyPreset(before, 'wet-corner');
    expect(plain(after.door)).toEqual({ x: 50, w: 200 });
    expect(plain(after.landing)).toEqual({ from: 40, len: 60, depth: 40 });
    expect(after.clearance).toBe(false);
    expect(after.mat).toBe(230);
    expect(G.matchesPreset(after, 'wet-corner')).toBe(true);
    expect(G.matchesPreset(after, 'back-wall')).toBe(false);
    // A copy: editing the plan doesn't change the preset.
    after.items[0].x += 10;
    expect(G.matchesPreset(after, 'wet-corner')).toBe(false);
    expect(G.matchesPreset(G.applyPreset(before, 'wet-corner'), 'wet-corner')).toBe(true);
  });
});

describe('wall-mounted TV', () => {
  const tv = (x, y, rot = 0) => ({ uid: 'tv', type: 'tv', x, y, rot });

  it('snaps to the nearest wall and faces into the room', () => {
    expect(plain(G.onWall(tv(0, 0), 100, 5))).toMatchObject({ x: 78, y: 0, rot: 0 });
    expect(plain(G.onWall(tv(0, 0), 330, 120))).toMatchObject({ x: 333, y: 98, rot: 90 });
    expect(plain(G.onWall(tv(0, 0), 150, 260))).toMatchObject({ x: 128, y: 261, rot: 180 });
    expect(plain(G.onWall(tv(0, 0), 2, 50))).toMatchObject({ x: 0, y: 28, rot: 270 });
  });

  it('slides along a wall when dragged and does not turn', () => {
    expect(plain(G.moveItem(tv(78, 0), 100, 40, [], {}))).toMatchObject({ x: 100, y: 0, rot: 0 });
    expect(plain(G.rotateItem(tv(78, 0)))).toEqual(plain(tv(78, 0)));
  });

  it('hangs above floor equipment without conflicts, and adds no floor area', () => {
    const items = [item('treadmill', 62, 0), tv(59, 0)];
    expect(G.analyze(items, {}).issues).toHaveLength(0);
    expect(G.coverage([tv(59, 0)])).toBe(0);
  });

  it('cannot hang over the garage door opening', () => {
    const res = G.analyze([tv(150, 261, 180)], {});
    expect(res.issues.map(i => i.text)).toEqual(['TV can’t hang over the garage door opening.']);
    expect(G.analyze([tv(20, 261, 180)], {}).issues).toHaveLength(0);
  });

  it('goes on the wall in front of the treadmill when added', () => {
    expect(plain(G.placeNew('tv', [item('treadmill', 62, 0)], {}, 'tv'))).toMatchObject({ x: 59, y: 0, rot: 0 });
    expect(plain(G.placeNew('tv', [], {}, 'tv'))).toMatchObject({ x: 146, y: 0, rot: 0 });
  });

  it('is put back on a wall when loaded from storage', () => {
    const raw = JSON.stringify({ v: 1, gv: G.GARAGE_VERSION, items: [tv(100, 100, 0)] });
    expect(plain(G.parse(raw)).items[0]).toMatchObject({ x: 100, y: 0, rot: 0 });
  });

  it('cannot hang above the electrical panel', () => {
    expect(plain(G.analyze([tv(220, 0)], {}).issues)).toEqual([
      { level: 'bad', uid: 'tv', text: 'TV can’t hang above the electrical panel; code keeps that wall clear.' },
    ]);
    expect(G.analyze([tv(220, 0)], { panel: { x: 100 } }).issues).toHaveLength(0);
  });
});

describe('mini-split', () => {
  const split = (x, y, rot) => ({ uid: 'ms', type: 'minisplit', x, y, rot });

  it('goes on the back wall when added, clear of the panel and tall gear in every starting layout', () => {
    for (const p of G.PRESETS) {
      const ms = G.placeNew('minisplit', p.items, {}, 'ms');
      expect(plain(ms), p.id).toEqual(split(64, 0, 0));
      expect(plain(G.analyze(p.items.concat([ms]), {}).issues), p.id).toEqual([]);
    }
  });

  it('keeps 4 feet of air in front of it, on whichever wall it hangs', () => {
    expect(plain(G.airflowZone(split(326, 112, 90)))).toEqual({ x: 278, y: 112, w: 48, d: 40 });
    expect(plain(G.airflowZone(split(50, 0, 0)))).toEqual({ x: 50, y: 10, w: 40, d: 48 });
    expect(G.airflowZone(item('tv', 50, 0))).toBeNull();
  });

  it('warns on the side walls, which back onto the house and another building', () => {
    expect(plain(G.analyze([split(326, 112, 90)], {}).issues)).toEqual([
      { level: 'warn', uid: 'ms', text: 'Mini-split is on the right wall, which backs onto another building, so its refrigerant lines and drain can’t go straight outside. Put it on the back wall.' },
    ]);
    expect(plain(G.analyze([split(0, 112, 270)], {}).issues)[0].text).toMatch(/left wall, which backs onto the house/);
    expect(G.analyze([split(20, 254, 180)], {}).issues).toHaveLength(0); // beside the garage door is fine
    expect(G.analyze([item('tv', 0, 100, 270)], {}).issues).toHaveLength(0); // the TV can go anywhere
  });

  it('warns when something tall stands in its airflow, but not short gear', () => {
    const ms = split(150, 0, 0);
    const trainer = item('mikolo', 125, 0);
    const res = G.analyze([trainer, ms], {});
    expect(plain(res.issues)).toEqual([
      { level: 'warn', uid: trainer.uid, text: 'Mikolo trainer (7′ 8″ tall) stands right in front of the Mini-split and would block its airflow.' },
    ]);
    expect(res.item.ms).toBe('warn');
    expect(res.zone.ms).toBe('warn');
    expect(G.analyze([item('plunge', 140, 20), ms], {}).issues).toHaveLength(0);
  });

  it('cannot hang above the panel and warns when it shares wall with the TV', () => {
    const texts = plain(G.analyze([split(225, 0, 0), item('tv', 200, 0)], {}).issues).map(i => i.text);
    expect(texts).toEqual([
      'Mini-split can’t hang above the electrical panel; code keeps that wall clear.',
      'TV can’t hang above the electrical panel; code keeps that wall clear.',
      'Mini-split and TV share a stretch of the back wall; one has to go well above the other.',
    ]);
  });
});

describe('e-bikes', () => {
  const bikes = (x, y, rot = 0) => ({ uid: 'eb', type: 'ebikes', x, y, rot });

  it('are one 4′ × 7′ piece for both bikes, with no floor reserved around it', () => {
    const t = G.TYPES.find(t => t.id === 'ebikes');
    expect([t.w, t.d]).toEqual([84, 48]);
    expect(G.zoneOf(bikes(100, 100))).toBeNull();
    expect(G.analyze([bikes(100, 100), item('treadmill', 184, 100)], {}).issues).toHaveLength(0); // flush against the treadmill's side
  });

  it('park by the garage door, clear of the steps, in every starting layout', () => {
    for (const p of G.PRESETS) {
      const b = G.placeNew('ebikes', p.items, {}, 'eb');
      expect(b.y + G.footprint(b).d, p.id).toBe(G.ROOM.d);
      expect(plain(G.analyze(p.items.concat([b]), {}).issues), p.id).toEqual([]);
    }
  });

  it('warns when they park by the steps to the house door', () => {
    const box = G.landingRects().box;
    expect(plain(G.analyze([bikes(0, box.y + box.d + 2, 180)], {}).issues)).toEqual([
      { level: 'warn', uid: 'eb', text: 'E-bikes parked within 3′ of the steps to the house door: Specialized says not to charge or store an e-bike by an exit door, since a battery fire there would block the way out.' },
    ]);
    expect(G.analyze([bikes(box.w + G.EXIT_CLEAR, G.ROOM.d - 48, 180)], {}).issues).toHaveLength(0);
  });

  it('share an existing outlet and count both bikes in the costs', () => {
    const s = G.defaultState();
    const st = { ...s, items: s.items.concat([G.placeNew('ebikes', s.items, {}, 'eb')]) };
    const c = G.circuits(st);
    expect(c.rows.map(r => r.type)).toEqual(['sauna', 'plunge', 'treadmill']);
    expect(plain(c.shared)).toEqual(['Stair climber', 'e-bike chargers']);
    const other = G.costSummary(st).groups.find(g => g.id === 'other');
    expect(plain(other.lines.map(l => [l.type, l.low, l.high]))).toEqual([['ebikes', 5600, 8200]]);
    expect(G.listJoin(['a', 'b', 'c'])).toBe('a, b and c');
  });
});

describe('current garage overlay', () => {
  const area = pts => Math.abs(pts.reduce((s, [x, y], k) => {
    const [nx, ny] = pts[(k + 1) % pts.length];
    return s + x * ny - nx * y;
  }, 0)) / 2;

  it('is 117″ × 221″, 2′ wider for half its length, and starts hidden in the back-left corner', () => {
    expect(plain(G.defaultState().overlay)).toEqual({ on: false, x: 0, y: 0, rot: 0, flip: false });
    const pts = plain(G.overlayPoints({ on: true }));
    expect(pts).toEqual([[0, 0], [141, 0], [141, 110.5], [117, 110.5], [117, 221], [0, 221]]);
    expect(area(pts)).toBe(117 * 221 + 24 * 110.5);
  });

  it('turns about its center and flips, keeping the same shape', () => {
    const turned = G.turnOverlay({ on: true, x: 100, y: 20 });
    expect(plain(turned)).toEqual({ on: true, x: 60, y: 60, rot: 90, flip: false });
    expect(plain(G.overlayBox(turned))).toEqual({ x: 60, y: 60, w: 221, d: 141 });
    expect(plain(G.overlayPoints({ on: true, flip: true }))).toEqual([[141, 0], [0, 0], [0, 110.5], [24, 110.5], [24, 221], [141, 221]]);
    for (const rot of G.ROTS) for (const flip of [false, true]) expect(area(plain(G.overlayPoints({ on: true, rot, flip }))), `${rot} ${flip}`).toBe(117 * 221 + 24 * 110.5);
  });

  it('stays inside the room and survives storage', () => {
    expect(plain(G.normOverlay({ on: true, x: 999, y: -5, rot: 45 }))).toEqual({ on: true, x: 195, y: 0, rot: 0, flip: false });
    expect(plain(G.normOverlay(null))).toEqual(plain(G.DEFAULT_OVERLAY));
    const overlay = { on: true, x: 40, y: 12, rot: 270, flip: true };
    expect(plain(G.parse(G.serialize({ ...G.defaultState(), overlay })).overlay)).toEqual(overlay);
  });
});

describe('saved layouts', () => {
  const now = Date.UTC(2026, 10, 13, 15, 30);

  it('snapshots the equipment and mat edge, not the garage, under a unique name', () => {
    const state = { ...G.defaultState(), door: { x: 50, w: 200 }, mat: 120 };
    const a = G.snapshot(state, '  Recovery corner  ', [], now);
    expect(a).toMatchObject({ name: 'Recovery corner', mat: 120, savedAt: '2026-11-13T15:30:00.000Z' });
    expect(a.door).toBeUndefined();
    expect(plain(a.items)).toEqual(plain(state.items));
    state.items[0].x = 999; // a copy, not a reference
    expect(a.items[0].x).not.toBe(999);
    expect(G.snapshot(state, 'Recovery corner', [a], now + 1).name).toBe('Recovery corner (2)');
    expect(G.snapshot(state, '', [a], now + 2).name).toBe('Layout 2');
  });

  it('round-trips through storage and matches the plan it came from', () => {
    const state = G.applyPreset(G.defaultState(), 'steps-nook');
    const list = [G.snapshot(state, 'Nook', [], now)];
    const back = G.parseSaved(G.serializeSaved(list));
    expect(plain(back)).toEqual(plain(list));
    expect(G.sameLayout(state, back[0])).toBe(true);
    expect(G.sameLayout(G.defaultState(), back[0])).toBe(false);
    const loaded = G.applyLayout({ ...G.defaultState(), door: { x: 50, w: 200 } }, back[0]);
    expect(plain(loaded.door)).toEqual({ x: 50, w: 200 });
    expect(G.sameLayout(loaded, back[0])).toBe(true);
  });

  it('counts a resized piece as a different layout', () => {
    const state = G.defaultState();
    const l = G.snapshot(state, 'A', [], now);
    state.items[0] = { ...state.items[0], w: 30 };
    expect(G.sameLayout(state, l)).toBe(false);
  });

  it('skips unreadable entries and cleans the rest', () => {
    expect(plain(G.parseSaved('nope'))).toEqual([]);
    expect(plain(G.parseSaved('{"v":2,"layouts":[]}'))).toEqual([]);
    const raw = JSON.stringify({
      v: 1,
      layouts: [
        null,
        { id: 'a', name: 'x'.repeat(80), items: [item('bench', 10, 20), item('bench', 50, 20), { uid: 'tv', type: 'tv', x: 100, y: 100, rot: 0 }], mat: 9999 },
        { id: 'a', items: [], savedAt: 'not a date' },
      ],
    });
    const out = plain(G.parseSaved(raw));
    expect(out).toHaveLength(2);
    expect(out[0].name).toHaveLength(60);
    expect(out[0].items.map(i => i.type)).toEqual(['bench', 'tv']);
    expect(out[0].items[1]).toMatchObject({ y: 0, rot: 0 }); // back on a wall
    expect(out[0].mat).toBe(336);
    expect(out[1]).toMatchObject({ name: 'Layout 3', savedAt: null });
    expect(out[1].id).not.toBe('a');
  });
});

describe('gym mats', () => {
  it('start 100" from the left wall by default and stay inside the room', () => {
    expect(G.defaultState().mat).toBe(G.DEFAULT_MAT);
    expect(G.normMat(-5)).toBe(0);
    expect(G.normMat(400)).toBe(336);
    expect(G.normMat('x')).toBe(G.DEFAULT_MAT);
    expect(plain(G.parse(JSON.stringify({ v: 1, items: [] }))).mat).toBe(G.DEFAULT_MAT);
  });

  it('snaps the edge to walls and equipment edges within 3 inches', () => {
    const bench = item('bench', 150, 100); // x 150–176
    expect(G.snapMat(148.4, [bench])).toBe(150);
    expect(G.snapMat(178, [bench])).toBe(176);
    expect(G.snapMat(160, [bench])).toBe(160);
    expect(G.snapMat(2, [])).toBe(0);
    expect(G.snapMat(44, [])).toBe(42); // the landing's outer edge
  });

  it('measures mat area without the landing', () => {
    expect(G.matArea(336)).toBe(0);
    expect(G.matArea(100)).toBeCloseTo((236 * 264) / 144, 6);
    // Mats from the left wall: the 42" × 72" landing isn't matted.
    expect(G.matArea(0)).toBeCloseTo((336 * 264 - 42 * 72) / 144, 6);
  });
});

describe('formatting', () => {
  it('formats lengths in feet and inches', () => {
    expect(G.fmtLen(0)).toBe('0″');
    expect(G.fmtLen(8.4)).toBe('8″');
    expect(G.fmtLen(12)).toBe('1′');
    expect(G.fmtLen(79)).toBe('6′ 7″');
    expect(G.fmtLen(192)).toBe('16′');
  });
});
