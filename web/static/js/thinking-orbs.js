/**
 * Thinking Orbs Engine — Agent Plus Edition
 * Direct 2D Canvas implementation based on Jakub Antalik's specifications.
 * Zero external dependencies. 60 FPS smooth rendering.
 * 
 * 9 Autonomous Agent States:
 * - working: Particles on tilted orbits
 * - searching: Scan meridian sweeps a dotted globe
 * - solving: Bands scramble and click back into alignment
 * - listening: A waveform rolls through rings
 * - connecting: A constellation wires itself with pulse packets
 * - weaving: Three strands plait around the sphere
 * - composing: An undulating sash of multi-bands
 * - breathing: A ring slowly morphing and pulsing
 * - shaping: Dotted outline morphs: circle -> triangle -> square
 */

(function (global) {
  'use strict';

  // --- Core Math Primitives ---
  function lerp(a, b, f) { return a + (b - a) * f; }
  function frac(x) { return x - Math.floor(x); }
  function hashD(a, b) {
    const h = Math.sin(a * 12.9898 + b * 78.233) * 43758.5453;
    return h - Math.floor(h);
  }
  function vnoise(x, y) {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    let fx = x - xi;
    let fy = y - yi;
    fx = fx * fx * (3 - 2 * fx);
    fy = fy * fy * (3 - 2 * fy);
    const a = hashD(xi, yi);
    const b = hashD(xi + 1, yi);
    const c = hashD(xi, yi + 1);
    const d = hashD(xi + 1, yi + 1);
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
  }
  function fibDir(i, n) {
    const golden = Math.PI * (3 - Math.sqrt(5));
    const y = 1 - (2 * (i + 0.5)) / n;
    const rad = Math.sqrt(Math.max(0, 1 - y * y));
    const a = i * golden;
    return [rad * Math.cos(a), y, rad * Math.sin(a)];
  }
  function angleDelta(a, b) {
    return Math.atan2(Math.sin(a - b), Math.cos(a - b));
  }
  function makeProj(yaw, tilt, cx, cy, scale) {
    const st = Math.sin(tilt);
    const ct = Math.cos(tilt);
    const sy = Math.sin(yaw);
    const cyw = Math.cos(yaw);
    return function (x, y, z) {
      const x1 = x * cyw + z * sy;
      const z1 = -x * sy + z * cyw;
      const y1 = y * ct - z1 * st;
      const z2 = y * st + z1 * ct;
      return [cx + x1 * scale, cy - y1 * scale, z2];
    };
  }
  function radiusScale(size, pow) {
    return Math.pow(size / 300, pow);
  }
  function finalizeFrame(dots, lines, rMin) {
    rMin = rMin || 0.3;
    const visible = [];
    for (let i = 0; i < dots.length; i++) {
      const d = dots[i];
      if ((d.a !== undefined ? d.a : 1) < 0.02) continue;
      d.r = Math.max(rMin, d.r);
      visible.push(d);
    }
    visible.sort(function (a, b) { return a.z - b.z; });
    const visLines = (lines || []).filter(function (l) { return (l.a !== undefined ? l.a : 1) >= 0.02; });
    return { dots: visible, lines: visLines };
  }

  // --- Profiles & Presets ---
  const BASE_PROFILES = {
    globe: { latRings: 17, lonDensity: 44, rBase: 0.6, rDepth: 1.7, rBoost: 1.0, inkFar: 0.62, inkSpan: 0.54, rsPow: 0.6, rMin: 0.3 },
    orbits: { orbitN: 12, ghostN: 40, ghostR: 0.9, ghostA: 0.5, particles: 3, partR: 1.2, partRDepth: 1.6, rsPow: 0.6, rMin: 0.3 },
    rubik: { latRings: 15, lonDensity: 40, moveCount: 14, rBase: 0.6, rDepth: 1.7, rActive: 0.3, inkFar: 0.62, inkSpan: 0.54, rsPow: 0.6, rMin: 0.3 },
    wave: { rings: 15, lonDensity: 40, rBase: 0.6, rDepth: 1.7, rsPow: 0.6, rMin: 0.3 },
    web: { nodeN: 30, thr: 0.72, signals: 5, nodeR: 1.4, nodeRDepth: 1.8, lineW: 0.8, rsPow: 0.6, rMin: 0.3 },
    braid: { strandN: 52, turns: 3.0, ghostN: 150, rBase: 1.2, rDepth: 1.8, rsPow: 0.6, rMin: 0.3 },
    ribbon: { lanes: 5, segs: 88, ghostN: 150, rBase: 1.1, rDepth: 1.7, rsPow: 0.6, rMin: 0.3 },
    ring: { lanes: 5, segs: 88, ghostN: 0, faceOn: 1, rBase: 1.1, rDepth: 1.7, rsPow: 0.6, rMin: 0.3 },
    morph: { rDot: 0.021, iconD: 1, rMin: 0.25 }
  };

  const PRESETS = {
    orbits: { 64: { speed: 1.885, count: 1, size: 1 }, 20: { speed: 3.9, count: 0.238, size: 2.4 } },
    globe: { 64: { speed: 2.015, count: 0.42, size: 1.15, extra: { scanMul: 4.08, dimBase: 0.45 } }, 20: { speed: 2.665, count: 0.105, size: 1.75, extra: { scanMul: 4.335, dimBase: 0.45 } } },
    rubik: { 64: { speed: 1.82, count: 0.35, size: 1.05 }, 20: { speed: 1.95, count: 0.088, size: 1.9 } },
    wave: { 64: { speed: 4.388, count: 0.341, size: 1 }, 20: { speed: 3.998, count: 0.105, size: 1.6 } },
    web: { 64: { speed: 3.315, count: 1.35, size: 0.95 }, 20: { speed: 6.63, count: 0.25, size: 1.52 } },
    braid: { 64: { speed: 1.625, count: 0.5, size: 1 }, 20: { speed: 2.75, count: 0.1125, size: 1.36 } },
    ribbon: { 64: { speed: 2.34, count: 0.25, size: 0.85, extra: { spin: 0, bandMul: 3.9, wobMul: 1 } }, 20: { speed: 3.12, count: 0.051, size: 1.073, extra: { spin: 0, bandMul: 4.94, wobMul: 1 } } },
    ring: { 64: { speed: 3.24, count: 0.25, size: 0.956, extra: { spin: 0, bandMul: 3.627, wobMul: 0.368 } }, 20: { speed: 3.78, count: 0.028, size: 1.622, extra: { spin: 0, bandMul: 3.968, wobMul: 0.565 } } },
    morph: { 64: { speed: 2.405, count: 0.702, size: 0.395, extra: { spread: 1.45 } }, 20: { speed: 2.08, count: 0.53, size: 1.011, extra: { spread: 1.45 } } }
  };

  const STATE_TO_MODE = {
    working: 'orbits',
    searching: 'globe',
    solving: 'rubik',
    listening: 'wave',
    connecting: 'web',
    weaving: 'braid',
    composing: 'ribbon',
    breathing: 'ring',
    shaping: 'morph'
  };

  function scaleCounts(opts, scale) {
    const out = Object.assign({}, opts);
    const rt = Math.sqrt(scale);
    const pairs = [['latRings', 'lonDensity'], ['rings', 'lonDensity'], ['lanes', 'segs']];
    for (let p = 0; p < pairs.length; p++) {
      const a = pairs[p][0], b = pairs[p][1];
      if (out[a] != null && out[b] != null) {
        out[a] = Math.max(2, Math.round(out[a] * rt));
        out[b] = Math.max(2, Math.round(out[b] * rt));
      }
    }
    const single = ['orbitN', 'ghostN', 'nodeN', 'strandN', 'signals'];
    for (let s = 0; s < single.length; s++) {
      const k = single[s];
      if (out[k] != null && out[k] !== 0) out[k] = Math.max(1, Math.round(out[k] * scale));
    }
    if (out.iconD != null) out.iconD = Math.max(0.02, out.iconD * scale);
    return out;
  }

  function scaleRadii(opts, scale) {
    const out = Object.assign({}, opts);
    const radKeys = ['rBase', 'rDepth', 'rActive', 'rDot', 'ghostR', 'partR', 'partRDepth', 'nodeR', 'nodeRDepth'];
    for (let i = 0; i < radKeys.length; i++) {
      const k = radKeys[i];
      if (out[k] != null) out[k] = out[k] * scale;
    }
    out.rSizeMul = (out.rSizeMul || 1) * scale;
    return out;
  }

  function resolvePreset(state, size) {
    const mode = STATE_TO_MODE[state] || 'orbits';
    const presetBucket = size <= 32 ? 20 : 64;
    const preset = PRESETS[mode][presetBucket] || PRESETS[mode][64];
    let opts = Object.assign({}, BASE_PROFILES[mode]);
    if (preset.count !== 1) opts = scaleCounts(opts, preset.count);
    if (preset.size !== 1) opts = scaleRadii(opts, preset.size);
    if (preset.extra) Object.assign(opts, preset.extra);
    return { mode: mode, speed: preset.speed, opts: opts };
  }

  // --- Mode Frames Implementations ---

  // 1. Orbits (working)
  function frameOrbits(size, t, o) {
    const cx = size / 2, cy = size / 2;
    const R = (size / 2) * 0.82;
    const pt = makeProj(t * 0.12, 0.3, cx, cy, 1);
    const rs = radiusScale(size, o.rsPow || 0.6);
    const dots = [];
    const orbitN = o.orbitN || 12;
    const ghostN = o.ghostN || 40;
    const particles = o.particles || 3;

    for (let orb = 0; orb < orbitN; orb++) {
      const h1 = hashD(orb, 1.7);
      const h2 = hashD(orb, 5.2);
      const h3 = hashD(orb, 8.9);
      const ro = R * (0.45 + 0.52 * h1);
      const th = h1 * 2 * Math.PI;
      const phi = Math.acos(2 * h2 - 1);
      const nx = Math.sin(phi) * Math.cos(th);
      const ny = Math.cos(phi);
      const nz = Math.sin(phi) * Math.sin(th);
      let ux = -ny, uy = nx, uz = 0;
      const ul = Math.max(1e-6, Math.sqrt(ux * ux + uy * uy));
      ux /= ul; uy /= ul;
      const vx = ny * uz - nz * uy;
      const vy = nz * ux - nx * uz;
      const vz = nx * uy - ny * ux;
      const speed = (0.25 + 0.55 * h3) * (h3 > 0.5 ? 1 : -1);

      for (let k = 0; k < ghostN; k++) {
        const a = (k / ghostN) * 2 * Math.PI;
        const p = pt(
          (ux * Math.cos(a) + vx * Math.sin(a)) * ro,
          (uy * Math.cos(a) + vy * Math.sin(a)) * ro,
          (uz * Math.cos(a) + vz * Math.sin(a)) * ro
        );
        const depth = (p[2] / ro + 1) / 2;
        dots.push({ x: p[0], y: p[1], z: p[2], r: (o.ghostR || 0.9) * rs, white: 0.72, a: (o.ghostA || 0.5) * (0.4 + 0.6 * depth) });
      }

      for (let m = 0; m < particles; m++) {
        const a = t * speed + (m / particles) * 2 * Math.PI + h2 * 6;
        const p = pt(
          (ux * Math.cos(a) + vx * Math.sin(a)) * ro,
          (uy * Math.cos(a) + vy * Math.sin(a)) * ro,
          (uz * Math.cos(a) + vz * Math.sin(a)) * ro
        );
        const depth = (p[2] / ro + 1) / 2;
        dots.push({ x: p[0], y: p[1], z: p[2], r: ((o.partR || 1.2) + (o.partRDepth || 1.6) * depth) * rs, white: 0.3 - 0.22 * depth });
      }
    }
    return finalizeFrame(dots, [], o.rMin);
  }

  // 2. Globe (searching)
  function frameGlobe(size, t, o) {
    const spin = 0.5;
    const cx = size / 2, cy = size / 2;
    const radius = (size / 2) * 0.82;
    const tilt = 0.4 + 0.06 * Math.sin(t * 0.35);
    const pt = makeProj(t * spin, tilt, cx, cy, radius);
    const scan = t * (spin + (1.7 - spin) * (o.scanMul || 1));
    const rs = radiusScale(size, o.rsPow || 0.6);
    const dimBase = o.dimBase || 1;
    const dots = [];
    const latRings = o.latRings || 17;
    const lonDensity = o.lonDensity || 44;

    for (let li = 0; li <= latRings; li++) {
      const lat = -Math.PI / 2 + (li / latRings) * Math.PI;
      const cosLat = Math.cos(lat);
      const sinLat = Math.sin(lat);
      const lonCount = Math.max(1, Math.round(Math.abs(cosLat) * lonDensity));
      for (let lj = 0; lj < lonCount; lj++) {
        const lon = (lj / lonCount) * 2 * Math.PI;
        const p = pt(cosLat * Math.cos(lon), sinLat, cosLat * Math.sin(lon));
        const depth = (p[2] + 1) / 2;
        const d = angleDelta(lon + t * spin, scan);
        const boost = Math.exp(-(d * d) / 0.18) * Math.max(0, p[2]);
        dots.push({
          x: p[0], y: p[1], z: p[2],
          r: ((o.rBase || 0.6) + (o.rDepth || 1.7) * depth + (o.rBoost || 1) * boost) * rs,
          white: (o.inkFar || 0.62) - (o.inkSpan || 0.54) * depth,
          a: dimBase + (1 - dimBase) * Math.min(1, boost)
        });
      }
    }
    return finalizeFrame(dots, [], o.rMin);
  }

  // 3. Rubik (solving)
  function makeMoves(count) {
    const moves = [];
    for (let i = 0; i < count; i++) {
      const axis = Math.min(2, Math.floor(hashD(i, 2.3) * 3));
      const lo = -1.0 + 0.5 * Math.min(3, Math.floor(hashD(i, 5.9) * 4));
      const dir = hashD(i, 7.7) < 0.5 ? 1 : -1;
      moves.push({ axis: axis, lo: lo, hi: lo + 0.5, ang: (dir * Math.PI) / 2 });
    }
    return moves;
  }
  function solveCycle(time, count, slotDur, rest) {
    const cyc = 2 * count * slotDur + rest;
    const tc = time % cyc;
    const amount = new Array(count).fill(0);
    let active = -1;
    if (tc < 2 * count * slotDur) {
      const slot = Math.floor(tc / slotDur);
      const p = (tc - slot * slotDur) / slotDur;
      const cl = Math.min(1, p / 0.7);
      const ep = 1 - Math.pow(1 - cl, 3);
      if (slot < count) {
        for (let i = 0; i < slot; i++) amount[i] = 1;
        amount[slot] = ep;
        active = slot;
      } else {
        const u = 2 * count - 1 - slot;
        for (let i = 0; i < u; i++) amount[i] = 1;
        amount[u] = 1 - ep;
        active = u;
      }
    }
    return { amount: amount, active: active };
  }
  function applyMoves(pt3, moves, sc) {
    let x = pt3[0], y = pt3[1], z = pt3[2];
    let inActive = false;
    for (let i = 0; i < moves.length; i++) {
      if (sc.amount[i] <= 0) continue;
      const mv = moves[i];
      const coord = mv.axis === 0 ? x : mv.axis === 1 ? y : z;
      if (coord < mv.lo || coord >= mv.hi) continue;
      if (i === sc.active) inActive = true;
      const a = mv.ang * sc.amount[i];
      const ca = Math.cos(a), sa = Math.sin(a);
      if (mv.axis === 0) { const y2 = y * ca - z * sa; z = y * sa + z * ca; y = y2; }
      else if (mv.axis === 1) { const x2 = x * ca + z * sa; z = -x * sa + z * ca; x = x2; }
      else { const x2 = x * ca - y * sa; y = x * sa + y * ca; x = x2; }
    }
    return [x, y, z, inActive];
  }
  function frameRubik(size, t, o) {
    const cx = size / 2, cy = size / 2;
    const R = (size / 2) * 0.82;
    const pt = makeProj(t * 0.55, 0.35 + 0.1 * Math.sin(t * 0.9), cx, cy, R);
    const rs = radiusScale(size, o.rsPow || 0.6);
    const moveCount = o.moveCount || 14;
    const moves = makeMoves(moveCount);
    const sc = solveCycle(t, moveCount, 0.42, 1.2);
    const dots = [];
    const latRings = o.latRings || 15;
    const lonDensity = o.lonDensity || 40;

    for (let li = 0; li <= latRings; li++) {
      const lat = -Math.PI / 2 + (li / latRings) * Math.PI;
      const cosLat = Math.cos(lat);
      const sinLat = Math.sin(lat);
      const lonCount = Math.max(1, Math.round(Math.abs(cosLat) * lonDensity));
      for (let lj = 0; lj < lonCount; lj++) {
        const lon = (lj / lonCount) * 2 * Math.PI;
        const res = applyMoves([cosLat * Math.cos(lon), sinLat, cosLat * Math.sin(lon)], moves, sc);
        const p = pt(res[0], res[1], res[2]);
        const inActive = res[3];
        const depth = (p[2] + 1) / 2;
        dots.push({
          x: p[0], y: p[1], z: p[2],
          r: ((o.rBase || 0.6) + (o.rDepth || 1.7) * depth + (inActive ? (o.rActive || 0.3) : 0)) * rs,
          white: (o.inkFar || 0.62) - (o.inkSpan || 0.54) * depth - (inActive ? 0.14 : 0)
        });
      }
    }
    return finalizeFrame(dots, [], o.rMin);
  }

  // 4. Wave (listening)
  function frameWave(size, t, o) {
    const cx = size / 2, cy = size / 2;
    const R = (size / 2) * 0.874;
    const pt = makeProj(t * 0.18, 0.38, cx, cy, 1);
    const rs = radiusScale(size, o.rsPow || 0.6);
    const dots = [];
    const rings = o.rings || 15;
    const lonDensity = o.lonDensity || 40;

    for (let ri = 0; ri <= rings; ri++) {
      const lat = -Math.PI / 2 + (ri / rings) * Math.PI;
      const cosLat = Math.cos(lat);
      const sinLat = Math.sin(lat);
      const w = 0.62 * Math.sin(t * 2.1 - ri * 0.52) + 0.38 * Math.sin(t * 1.27 + ri * 0.83);
      const rr = R * (0.88 + 0.105 * w);
      const lonCount = Math.max(1, Math.round(Math.abs(cosLat) * lonDensity));
      for (let lj = 0; lj < lonCount; lj++) {
        const lon = (lj / lonCount) * 2 * Math.PI;
        const p = pt(cosLat * Math.cos(lon) * rr, sinLat * rr, cosLat * Math.sin(lon) * rr);
        const depth = (p[2] / R + 1) / 2;
        const crest = Math.max(0, w);
        dots.push({
          x: p[0], y: p[1], z: p[2],
          r: ((o.rBase || 0.6) + (o.rDepth || 1.7) * depth) * (1 + 0.4 * crest) * rs,
          white: 0.66 - 0.56 * depth - 0.1 * crest
        });
      }
    }
    return finalizeFrame(dots, [], o.rMin);
  }

  // 5. Ribbon (composing & breathing)
  function frameRibbon(size, t, o) {
    const cx = size / 2, cy = size / 2;
    const R = (size / 2) * 0.78;
    const spin = o.spin !== undefined ? o.spin : 1;
    const camTilt = 0.3;
    const pt = makeProj(t * 0.1 * spin, camTilt, cx, cy, 1);
    const rs = radiusScale(size, o.rsPow || 0.6);
    const dots = [];
    const ghostN = o.ghostN !== undefined ? o.ghostN : 150;

    for (let i = 0; i < ghostN; i++) {
      const d = fibDir(i, ghostN);
      const p = pt(d[0] * R, d[1] * R, d[2] * R);
      const depth = (p[2] / R + 1) / 2;
      dots.push({ x: p[0], y: p[1], z: p[2], r: 0.8 * rs, white: 0.78, a: 0.1 + 0.22 * depth });
    }

    const ya = t * 0.24 * spin;
    const ta = o.faceOn ? -camTilt : 0.55 + 0.3 * Math.sin(t * 0.18) * spin;
    const ux = Math.cos(ya), uy = 0, uz = Math.sin(ya);
    const vx = -uz * Math.sin(ta), vy = Math.cos(ta), vz = ux * Math.sin(ta);
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;

    const wobAmp = 0.23 * (o.wobMul || 1);
    const baseR = o.faceOn ? R / (1 + 0.85 * wobAmp) : R;
    const baseLanes = o.lanes || 5;
    const segs = o.segs || 88;
    const lanes = Math.max(1, Math.round(baseLanes * (o.bandMul || 1)));

    for (let w = 0; w < lanes; w++) {
      const laneOff = (w - (lanes - 1) / 2) * 0.075;
      const edge = Math.abs(w - (lanes - 1) / 2) / Math.max(1, (lanes - 1) / 2);
      for (let k = 0; k < segs; k++) {
        const a = (k / segs) * 2 * Math.PI;
        const wob = (0.16 * Math.sin(a * 3 - t * 1.7 + w * 0.22) + 0.07 * Math.sin(a * 5 + t * 1.1)) * (o.wobMul || 1);
        const radial = o.faceOn ? 1 + wob : 1;
        const off = o.faceOn ? laneOff : laneOff + wob;
        const x = ux * Math.cos(a) + vx * Math.sin(a) + nx * off;
        const y = uy * Math.cos(a) + vy * Math.sin(a) + ny * off;
        const z = uz * Math.cos(a) + vz * Math.sin(a) + nz * off;
        const l = Math.sqrt(x * x + y * y + z * z);
        const rr = baseR * radial;
        const p = pt((x / l) * rr, (y / l) * rr, (z / l) * rr);
        const depth = (p[2] / R + 1) / 2;
        dots.push({
          x: p[0], y: p[1], z: p[2],
          r: ((o.rBase || 1.1) + (o.rDepth || 1.7) * depth) * (1 - 0.25 * edge) * rs,
          white: 0.52 - 0.44 * depth + 0.18 * edge,
          a: 0.4 + 0.6 * depth
        });
      }
    }
    return finalizeFrame(dots, [], o.rMin);
  }

  // 6. Web (connecting)
  function frameWeb(size, t, o) {
    const cx = size / 2, cy = size / 2;
    const R = (size / 2) * 0.8 * (o.spread || 1);
    const pt = makeProj(t * 0.12, 0.32, cx, cy, R);
    const rs = radiusScale(size, o.rsPow || 0.6);
    const nodeN = o.nodeN || 30;
    const thr = o.thr || 0.72;
    const nodeR = o.nodeR || 1.4;
    const nodeRDepth = o.nodeRDepth || 1.8;
    const nodes = [];

    for (let i = 0; i < nodeN; i++) {
      const d = fibDir(i, nodeN);
      const x = d[0] + 0.3 * (vnoise(i * 0.31 + 9, t * 0.24) - 0.5) * 2;
      const y = d[1] + 0.3 * (vnoise(i * 0.53 + 27, t * 0.21) - 0.5) * 2;
      const z = d[2] + 0.3 * (vnoise(i * 0.77 + 55, t * 0.27) - 0.5) * 2;
      const l = Math.sqrt(x * x + y * y + z * z);
      nodes.push([x / l, y / l, z / l]);
    }

    const lines = [];
    const dots = [];

    for (let i = 0; i < nodeN; i++) {
      for (let j = i + 1; j < nodeN; j++) {
        const dx = nodes[i][0] - nodes[j][0];
        const dy = nodes[i][1] - nodes[j][1];
        const dz = nodes[i][2] - nodes[j][2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist >= thr) continue;
        const p1 = pt(nodes[i][0], nodes[i][1], nodes[i][2]);
        const p2 = pt(nodes[j][0], nodes[j][1], nodes[j][2]);
        const depth = ((p1[2] + p2[2]) / 2 + 1) / 2;
        lines.push({
          x1: p1[0], y1: p1[1], x2: p2[0], y2: p2[1],
          white: 0.42,
          a: (1 - dist / thr) * (0.3 + 0.55 * depth),
          w: Math.max(0.6, (o.lineW || 0.8) * rs)
        });
      }
    }

    for (let i = 0; i < nodeN; i++) {
      const p = pt(nodes[i][0], nodes[i][1], nodes[i][2]);
      const depth = (p[2] + 1) / 2;
      const pulse = 1 + 0.25 * Math.sin(t * 1.4 + i * 2.7);
      dots.push({
        x: p[0], y: p[1], z: p[2],
        r: (nodeR + nodeRDepth * depth) * pulse * rs,
        white: 0.55 - 0.45 * depth
      });
    }

    const signals = o.signals || 5;
    for (let s = 0; s < signals; s++) {
      const seg = Math.floor(t * 0.55 + s * 7.31);
      const a = Math.floor(hashD(seg, s * 3.1 + 1.7) * nodeN);
      const b = Math.floor(hashD(seg, s * 5.7 + 4.2) * nodeN);
      if (a === b) continue;
      const f = frac(t * 0.55 + s * 7.31);
      const x = lerp(nodes[a][0], nodes[b][0], f);
      const y = lerp(nodes[a][1], nodes[b][1], f);
      const z = lerp(nodes[a][2], nodes[b][2], f);
      const l = Math.max(1e-6, Math.sqrt(x * x + y * y + z * z));
      const p = pt(x / l, y / l, z / l);
      const depth = (p[2] + 1) / 2;
      dots.push({
        x: p[0], y: p[1], z: p[2],
        r: (nodeR * 1.5 + nodeRDepth * depth) * rs,
        white: 0.05,
        a: 0.5 + 0.5 * depth
      });
    }
    return finalizeFrame(dots, lines, o.rMin);
  }

  // 7. Braid (weaving)
  function frameBraid(size, t, o) {
    const cx = size / 2, cy = size / 2;
    const R = (size / 2) * 0.76;
    const pt = makeProj(t * 0.4, 0.3, cx, cy, 1);
    const rs = radiusScale(size, o.rsPow || 0.6);
    const dots = [];
    const ghostN = o.ghostN || 150;

    for (let i = 0; i < ghostN; i++) {
      const d = fibDir(i, ghostN);
      const p = pt(d[0] * R, d[1] * R, d[2] * R);
      const depth = (p[2] / R + 1) / 2;
      dots.push({ x: p[0], y: p[1], z: p[2], r: 0.8 * rs, white: 0.78, a: 0.1 + 0.22 * depth });
    }

    const strandN = o.strandN || 52;
    const turns = o.turns || 3;
    for (let s = 0; s < 3; s++) {
      const phase = (s / 3) * 2 * Math.PI;
      for (let i = 0; i < strandN; i++) {
        const u = (frac(i / strandN + t * 0.045) * 2 - 1) * 0.96;
        const surf = Math.sqrt(Math.max(0, 1 - u * u));
        const endFade = Math.min(1, (1 - Math.abs(u)) / 0.1);
        const a = u * Math.PI * turns + phase;
        const weave = 1 + 0.075 * Math.sin(u * Math.PI * turns * 2 + phase * 2 + t * 0.8);
        const rr = surf * R * weave;
        const p = pt(Math.cos(a) * rr, u * R * weave, Math.sin(a) * rr);
        const depth = (p[2] / R + 1) / 2;
        dots.push({
          x: p[0], y: p[1], z: p[2],
          r: ((o.rBase || 1.2) + (o.rDepth || 1.8) * depth) * rs,
          white: 0.55 - 0.45 * depth,
          a: endFade * (0.45 + 0.55 * depth)
        });
      }
    }
    return finalizeFrame(dots, [], o.rMin);
  }

  // 8. Morph (shaping)
  function smoothE(x) { return x * x * (3 - 2 * x); }
  function polyPath(verts) {
    const V = verts.length;
    const L = [];
    let total = 0;
    for (let i = 0; i < V; i++) {
      const a = verts[i], b = verts[(i + 1) % V];
      const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      L.push(l);
      total += l;
    }
    return function (f) {
      let target = f * total;
      let i = 0;
      while (target > L[i] && i < V - 1) {
        target -= L[i];
        i++;
      }
      const a = verts[i], b = verts[(i + 1) % V];
      const ff = L[i] ? Math.min(1, target / L[i]) : 0;
      return [a[0] + (b[0] - a[0]) * ff, a[1] + (b[1] - a[1]) * ff];
    };
  }
  const CIRCLE_PATH = function (f) {
    const a = -Math.PI / 2 + f * 2 * Math.PI;
    return [Math.cos(a) * 0.24, Math.sin(a) * 0.24];
  };
  const TRIANGLE_PATH = polyPath([[0.0, -0.26], [0.24, 0.16], [-0.24, 0.16]]);
  const SQUARE_PATH = polyPath([[0, -0.2], [0.2, -0.2], [0.2, 0.2], [-0.2, 0.2], [-0.2, -0.2]]);
  const CYCLE_PATHS = [CIRCLE_PATH, TRIANGLE_PATH, SQUARE_PATH];

  function frameMorph(size, t, o) {
    const HOLD = 1.4, MORPH = 0.9, SEG = HOLD + MORPH;
    const K = CYCLE_PATHS.length;
    const tc = t % (SEG * K);
    const k = Math.floor(tc / SEG);
    const local = tc - k * SEG;
    const m = local > HOLD ? smoothE((local - HOLD) / MORPH) : 0;
    const sprd = o.spread || 1;
    const pA = CYCLE_PATHS[k];
    const pB = CYCLE_PATHS[(k + 1) % K];
    const M = 160;
    const pts = [];
    for (let i = 0; i < M; i++) {
      const f = i / M;
      const a = pA(f), b = pB(f);
      pts.push([(a[0] + (b[0] - a[0]) * m) * sprd, (a[1] + (b[1] - a[1]) * m) * sprd]);
    }
    const L = [];
    let total = 0;
    for (let i = 0; i < M; i++) {
      const a = pts[i], b = pts[(i + 1) % M];
      const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      L.push(l); total += l;
    }
    const n = Math.max(6, Math.round(34 * (o.iconD || 1)));
    const re = (o.rDot || 0.021) * 1.35 * sprd;
    const pulse = 1 + 0.02 * Math.sin(local * 3.1);
    const dots = [];
    const c2 = size / 2;
    let seg = 0, acc = 0;
    for (let k2 = 0; k2 < n; k2++) {
      const target = (k2 / n) * total;
      while (acc + L[seg] < target && seg < M - 1) {
        acc += L[seg];
        seg++;
      }
      const a = pts[seg], b = pts[(seg + 1) % M];
      const f = L[seg] ? Math.min(1, (target - acc) / L[seg]) : 0;
      const x = (a[0] + (b[0] - a[0]) * f) * pulse;
      const y = (a[1] + (b[1] - a[1]) * f) * pulse;
      dots.push({
        x: c2 + x * size,
        y: c2 + y * size,
        z: 0,
        r: Math.max(0.35, re * size),
        white: 0.1
      });
    }
    return finalizeFrame(dots, [], o.rMin);
  }

  const MODE_FRAMES = {
    orbits: frameOrbits,
    globe: frameGlobe,
    rubik: frameRubik,
    wave: frameWave,
    web: frameWeb,
    braid: frameBraid,
    ribbon: frameRibbon,
    ring: frameRibbon,
    morph: frameMorph
  };

  // --- 2D Canvas Painting ---
  function paint(ctx, dots, dark) {
    for (let i = 0; i < dots.length; i++) {
      const d = dots[i];
      const alpha = d.a !== undefined ? d.a : 1;
      const w = Math.min(1, Math.max(0, d.white));
      const g = Math.round((dark ? 1 - w : w) * 255);
      ctx.fillStyle = `rgba(${g},${g},${g},${alpha})`;
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function paintLines(ctx, lines, dark) {
    for (let i = 0; i < lines.length; i++) {
      const l = lines[i];
      const alpha = l.a !== undefined ? l.a : 1;
      const w = Math.min(1, Math.max(0, l.white));
      const g = Math.round((dark ? 1 - w : w) * 255);
      ctx.strokeStyle = `rgba(${g},${g},${g},${alpha})`;
      ctx.lineWidth = l.w;
      ctx.beginPath();
      ctx.moveTo(l.x1, l.y1);
      ctx.lineTo(l.x2, l.y2);
      ctx.stroke();
    }
  }

  function paintFrame(ctx, frame, dark) {
    if (frame.lines && frame.lines.length) paintLines(ctx, frame.lines, dark);
    paint(ctx, frame.dots, dark);
  }

  // --- Public API & Mounting Controller ---
  const ThinkingOrbs = {
    /**
     * Mounts an active 60fps Thinking Orb onto an element.
     * @param {HTMLElement|string} target - Container element or CSS selector or canvas
     * @param {Object} options
     * @param {string} [options.state='breathing'] - 'working'|'searching'|'solving'|'listening'|'connecting'|'weaving'|'composing'|'breathing'|'shaping'
     * @param {number} [options.size=20] - 20 or 64 px
     * @param {string} [options.theme='auto'] - 'auto' | 'dark' | 'light'
     * @param {number} [options.speed=1] - Speed multiplier
     * @param {string} [options.label] - Accessible aria-label
     * @returns {Object} Controller with { setState(state), destroy(), canvas }
     */
    mount: function (target, options) {
      options = options || {};
      const container = typeof target === 'string' ? document.querySelector(target) : target;
      if (!container) return null;

      let canvas = container.tagName === 'CANVAS' ? container : container.querySelector('canvas');
      if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.style.display = 'block';
        container.appendChild(canvas);
      }

      let state = options.state || 'breathing';
      let size = options.size || (container.clientWidth > 40 ? 64 : 20);
      let speedMul = options.speed || 1;
      let themeMode = options.theme || 'auto';
      let animId = null;
      let isDestroyed = false;

      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', options.label || `Agent Status: ${state}`);

      const ctx = canvas.getContext('2d');
      if (!ctx) return null;

      let currentResolved = resolvePreset(state, size);

      function updateCanvasMetrics() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = size * dpr;
        canvas.height = size * dpr;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';
      }
      updateCanvasMetrics();

      function isDarkTheme() {
        if (themeMode === 'dark') return true;
        if (themeMode === 'light') return false;
        return document.documentElement.classList.contains('dark') || 
               document.body.classList.contains('dark') ||
               (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
      }

      const startPerf = performance.now();

      function renderLoop(now) {
        if (isDestroyed) return;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const elapsedSec = ((now - startPerf) / 1000) * currentResolved.speed * speedMul;
        const dark = isDarkTheme();

        ctx.save();
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, size, size);

        const frameFn = MODE_FRAMES[currentResolved.mode];
        if (frameFn) {
          const frame = frameFn(size, elapsedSec, currentResolved.opts);
          paintFrame(ctx, frame, dark);
        }
        ctx.restore();

        animId = requestAnimationFrame(renderLoop);
      }

      animId = requestAnimationFrame(renderLoop);

      return {
        canvas: canvas,
        getState: function () { return state; },
        setState: function (newState) {
          if (state === newState) return;
          state = newState;
          canvas.setAttribute('aria-label', `Agent Status: ${state}`);
          currentResolved = resolvePreset(state, size);
        },
        setSize: function (newSize) {
          if (size === newSize) return;
          size = newSize;
          updateCanvasMetrics();
          currentResolved = resolvePreset(state, size);
        },
        setTheme: function (newTheme) {
          themeMode = newTheme;
        },
        destroy: function () {
          isDestroyed = true;
          if (animId) cancelAnimationFrame(animId);
        }
      };
    }
  };

  // Export globally
  global.ThinkingOrbs = ThinkingOrbs;
})(typeof window !== 'undefined' ? window : this);
