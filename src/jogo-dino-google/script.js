const DinoEngine = (() => {
  'use strict';

  const TICK_HZ = 200;                 // 1 tick = 0,005 s, igual ao jogo original
  const W = 900, GROUND = 15;
  const CACTI = [[32, 33], [23, 46], [15, 33], [49, 33], [73, 47]];   // [largura, altura]
  const BIRD_W = 42, BIRD_H = 36, SPIKE_W = 810, SPIKE_H = 31, SPIKE_Y = 10;
  const DECISION = 4;                  // o agente decide a cada 4 ticks
  const DEATH = -100;                  // recompensa ao morrer
  const TTC_STEP = 8, TTC_N = 29, NCLASS = 9, NV = 23;
  const MAX_KEY = TTC_N * NCLASS * NV * 2;
  const FORMAT = 'dino-qlearning';

  const hit = (x1, y1, w1, h1, x2, y2, w2, h2) =>
    !(x1 + w1 <= x2 || x1 >= x2 + w2 || y1 + h1 <= y2 || y1 >= y2 + h2);
  const dw = d => d.estado === 1 ? 55 : d.estado === 4 ? 39 : 40;
  const dh = d => d.estado === 1 ? 25 : d.estado === 4 ? 37 : 43;
  const r4 = v => Math.round(v * 10000) / 10000;

  function obsClass(o) {
    if (o.type < 5) return o.type;                 // cactos
    if (o.type === 5) return o.y < 35 ? 5 : (o.y < 53 ? 6 : 7);   // pássaro: baixo (pular), médio (abaixar), alto (nada)
    return 8;                                      // espinhos
  }

  class Sim {
    constructor(o = {}) {
      this.alpha = o.alpha ?? 0.15;
      this.gamma = o.gamma ?? 0.95;
      this.epsilon = o.epsilon ?? 0.15;
      this.epsilonMin = o.epsilonMin ?? 0.02;
      this.epsilonDecay = o.epsilonDecay ?? 0.98;
      this.planeMode = !!o.planeMode;
      this.learn = o.learn !== false;
      this.numDinos = o.numDinos ?? 30;
      this.capDistance = o.capDistance ?? 0;       // 0 = sem limite de distância por episódio
      this.playerMode = false;
      this.playerJumpQueued = false;
      this.playerDuck = false;
      this.q = new Map();                          // estado -> [q0, q1, q2, q3, visitas]
      this.episode = 0;
      this.bestEver = 0;
      this.history = [];                           // { best, avg } por episódio
      this.totalSteps = 0;
      this.newEpisode();
    }

    /* ---------- episódio ---------- */
    newEpisode() {
      this.V = -3;
      this.dist = 0;
      this.tick = 0;
      this.obstacles = [];
      this.nextId = 0;
      this.spikeCount = 0;
      this.ended = false;
      this.playerJumpQueued = false;
      this.playerDuck = false;
      this.spawn(true);
      while (this.obstacles[this.obstacles.length - 1].x < W + 800) this.spawn(false);
      this.dinos = [];
      for (let i = 0; i < this.numDinos; i++) {
        this.dinos.push({
          id: i, x: 100 + Math.random() * 80, y: GROUND, vy: 0, estado: 0,
          cool: 0, desl: 0, alive: true, dist: 0,
          ps: -1, pa: 0, acc: 0, action: 0
        });
      }
      this.alive = this.dinos.length;
    }

    spawn(first) {
      const last = this.obstacles[this.obstacles.length - 1];
      const x = last ? last.x + last.w + 500 + (Math.random() * 200 - 100) : 650;
      let type;
      if (!first && this.planeMode && this.spikeCount >= 10) { type = 6; this.spikeCount = 0; }
      else {
        type = Math.floor(Math.random() * (first ? 5 : 6));
        if (this.planeMode) this.spikeCount++;
      }
      let w, h, y = GROUND;
      if (type < 5) { w = CACTI[type][0]; h = CACTI[type][1]; }
      else if (type === 5) { w = BIRD_W; h = BIRD_H; y = 20 + Math.floor(Math.random() * 65); }
      else { w = SPIKE_W; h = SPIKE_H; y = SPIKE_Y; }
      this.obstacles.push({ id: this.nextId++, x, y, w, h, type });
    }

    nextObstacle(d) {
      const left = d.x + 7;
      for (const o of this.obstacles) if (o.x + o.w > left) return o;
      return this.obstacles[this.obstacles.length - 1];
    }

    /* ---------- estado discretizado ---------- */
    stateKey(d) {
      const o = this.nextObstacle(d);
      const dist = o.x - (d.x + 33);
      let b = 0;                                   // 0 = obstáculo já sobre o dinossauro
      if (dist >= 0) b = 1 + Math.min(TTC_N - 2, Math.floor(dist / (-this.V) / TTC_STEP));
      let vs;
      if (d.estado === 4) vs = 1;
      else if (d.estado === 1) vs = 2;
      else if (d.estado === 0) vs = 0;
      else vs = 3 + Math.min(9, Math.floor((d.y - GROUND) / 12)) * 2 + (d.vy > 0 ? 1 : 0);
      const ready = (this.planeMode && d.cool <= 0) ? 1 : 0;
      return ((b * NCLASS + obsClass(o)) * NV + vs) * 2 + ready;
    }

    /* ---------- Q-learning ---------- */
    row(s) {
      let r = this.q.get(s);
      if (!r) { r = new Float32Array(5); this.q.set(s, r); }
      return r;
    }

    update(s, a, reward, s2, terminal) {
      const nA = this.planeMode ? 4 : 3;
      const r = this.row(s);
      let target = reward;
      if (!terminal) {
        const q2 = this.q.get(s2);
        if (q2) {
          let m = q2[0];
          for (let i = 1; i < nA; i++) if (q2[i] > m) m = q2[i];
          target += this.gamma * m;
        }
      }
      r[a] += this.alpha * (target - r[a]);
      r[4] += 1;
    }

    epsFor(d) {
      if (!this.learn) return 0;
      const n = this.dinos.length;
      if (n === 1) return this.epsilon;
      if (d.id === 0) return 0;                    // dinossauro 0 só explora o que já sabe
      return this.epsilon * (0.5 + d.id / (n - 1));
    }

    pick(s, d) {
      const nA = this.planeMode ? 4 : 3;
      const eps = this.epsFor(d);
      if (eps > 0 && Math.random() < eps) {
        const wts = nA === 4 ? [0.5, 0.22, 0.22, 0.06] : [0.5, 0.25, 0.25];
        let u = Math.random();
        for (let i = 0; i < nA; i++) { u -= wts[i]; if (u <= 0) return i; }
        return 0;
      }
      const q = this.q.get(s);
      if (!q) return 0;
      let best = 0;
      for (let i = 1; i < nA; i++) if (q[i] > q[best] + 1e-6) best = i;
      return best;
    }

    decide(d) {
      const s = this.stateKey(d);
      if (this.learn && d.ps !== -1) this.update(d.ps, d.pa, d.acc, s, false);
      d.ps = s; d.pa = this.pick(s, d); d.acc = 0; d.action = d.pa;
    }

    die(d) {
      d.alive = false;
      d.dist = this.dist;
      this.alive--;
      if (this.learn && d.ps !== -1) {
        this.update(d.ps, d.pa, d.acc + DEATH, 0, true);
        d.ps = -1;
      }
    }

    /* ---------- física (portada do original) ---------- */
    applyAction(d, a) {
      const sp = -this.V;
      const pular = a === 1, abaixar = a === 2, aviao = a === 3 && this.planeMode;
      if (d.estado !== 4) {
        if (d.estado !== 2) d.estado = 0;
        if (abaixar && d.estado !== 2) d.estado = 1;
        if (abaixar && d.estado === 2) { if (d.vy > 0) d.vy = 0; d.y -= 2; }
        if (pular && d.estado !== 2) { d.estado = 2; d.y += 1; d.vy += 4.0; }
        if (aviao && d.cool <= 0) {
          d.estado = 4; d.y += 1;
          if (d.vy <= 0.5 && d.y < 25) d.vy += 4.0;
          d.cool = 4000;
        }
      } else if (d.desl >= 820) { d.desl = 0; d.estado = 2; }
      else d.desl += sp;
      d.cool -= sp;
    }

    step() {
      const V = this.V;
      for (const o of this.obstacles) o.x += V;
      while (this.obstacles.length && this.obstacles[0].x + this.obstacles[0].w < -30) this.obstacles.shift();
      while (this.obstacles[this.obstacles.length - 1].x < W + 800) this.spawn(false);

      const decide = this.tick % DECISION === 0;
      for (const d of this.dinos) {
        if (!d.alive) { d.x += V; continue; }

        if (d.y > GROUND) {                                      // gravidade
          if (d.estado !== 4) d.vy -= 0.08;
          else if (d.vy <= 0) d.vy = 0; else d.vy -= 0.08;
          d.y += d.vy;
        } else { d.vy = 0; d.y = GROUND; if (d.estado === 2) d.estado = 0; }

        const o = this.nextObstacle(d);                          // colisão
        if (hit(d.x + 7, d.y + 5, dw(d) - 14, dh(d) - 10, o.x, o.y, o.w, o.h)) { this.die(d); continue; }

        if (this.learn) d.acc += (d.estado === 0 || d.estado === 1 ? 1 : 0.6) / DECISION;

        if (this.playerMode && d.id === 0) {
          // No modo manual, o jogador controla o primeiro dinossauro.
          if (this.playerJumpQueued && d.y <= GROUND + 0.001) {
            d.action = 1;
            this.playerJumpQueued = false;
          } else {
            d.action = this.playerDuck ? 2 : 0;
          }
        } else if (decide) {
          this.decide(d);
        }

        this.applyAction(d, d.action);
      }

      if (Math.abs(this.V) < 8) this.V -= 0.0005;
      this.dist += -V;
      this.tick++;
      this.totalSteps++;
      if (this.alive === 0 || (this.capDistance > 0 && this.dist > this.capDistance)) this.endEpisode();
    }

    run(n) { for (let i = 0; i < n; i++) this.step(); }

    endEpisode() {
      let sum = 0;
      for (const d of this.dinos) { if (d.alive) d.dist = this.dist; sum += d.dist; }
      const best = Math.max(...this.dinos.map(d => d.dist));
      this.history.push({ best: Math.round(best), avg: Math.round(sum / this.dinos.length) });
      if (this.history.length > 2000) this.history.splice(0, this.history.length - 2000);
      this.bestEver = Math.max(this.bestEver, best);
      this.episode++;
      if (this.learn) this.epsilon = Math.max(this.epsilonMin, this.epsilon * this.epsilonDecay);
      this.newEpisode();
    }

    /* ---------- exportação e importação ---------- */
    exportData() {
      const qtable = {};
      for (const [k, v] of this.q) {
        if (v[0] === 0 && v[1] === 0 && v[2] === 0 && v[3] === 0) continue;
        qtable[k] = [r4(v[0]), r4(v[1]), r4(v[2]), r4(v[3]), v[4]];
      }
      return {
        app: FORMAT, version: 1, savedAt: new Date().toISOString(),
        config: {
          alpha: this.alpha, gamma: this.gamma, epsilon: r4(this.epsilon),
          epsilonMin: this.epsilonMin, epsilonDecay: this.epsilonDecay,
          planeMode: this.planeMode, numDinos: this.numDinos, capDistance: this.capDistance
        },
        stats: {
          episode: this.episode, bestEver: Math.round(this.bestEver),
          totalSteps: this.totalSteps, history: this.history.slice(-1000)
        },
        qtable
      };
    }

    importData(obj, mode) {
      if (!obj || obj.app !== FORMAT || typeof obj.qtable !== 'object' || obj.qtable === null)
        throw new Error('Este arquivo não é um aprendizado do Dino Q-Learning.');
      if (obj.version !== 1) throw new Error('Versão do arquivo não suportada: ' + obj.version);
      const incoming = new Map();
      for (const [k, v] of Object.entries(obj.qtable)) {
        const key = Number(k);
        if (!Number.isInteger(key) || key < 0 || key >= MAX_KEY || !Array.isArray(v) || v.length < 4 ||
            !v.slice(0, 5).every(x => Number.isFinite(x)))
          throw new Error('Tabela Q inválida (entrada "' + k + '").');
        const row = new Float32Array(5);
        for (let i = 0; i < 4; i++) row[i] = v[i];
        row[4] = Number.isFinite(v[4]) ? Math.max(1, v[4]) : 1;
        incoming.set(key, row);
      }
      let overlap = 0;
      if (mode === 'merge') {
        for (const [k, inc] of incoming) {
          const cur = this.q.get(k);
          if (!cur) { this.q.set(k, inc); continue; }
          overlap++;
          const n1 = Math.max(1, cur[4]), n2 = inc[4], t = n1 + n2;
          for (let i = 0; i < 4; i++) cur[i] = (cur[i] * n1 + inc[i] * n2) / t;
          cur[4] = t;
        }
        this.bestEver = Math.max(this.bestEver, Number(obj.stats?.bestEver) || 0);
      } else {
        this.q = incoming;
        const c = obj.config || {}, s = obj.stats || {};
        const num = (v, d) => Number.isFinite(v) ? v : d;
        this.alpha = num(c.alpha, this.alpha); this.gamma = num(c.gamma, this.gamma);
        this.epsilon = num(c.epsilon, this.epsilon); this.epsilonMin = num(c.epsilonMin, this.epsilonMin);
        this.epsilonDecay = num(c.epsilonDecay, this.epsilonDecay);
        this.planeMode = !!c.planeMode;
        this.capDistance = num(c.capDistance, this.capDistance);
        this.episode = num(s.episode, 0); this.bestEver = num(s.bestEver, 0);
        this.totalSteps = num(s.totalSteps, 0);
        this.history = Array.isArray(s.history)
          ? s.history.filter(h => h && Number.isFinite(h.best) && Number.isFinite(h.avg)).slice(-2000) : [];
      }
      this.newEpisode();
      return { states: incoming.size, overlap };
    }

    reset() {
      this.q = new Map(); this.episode = 0; this.bestEver = 0; this.history = []; this.totalSteps = 0;
      this.newEpisode();
    }
  }

  return { Sim, TICK_HZ, W, GROUND, DECISION };
})();
if (typeof module !== 'undefined') module.exports = DinoEngine;

(() => {
  if (typeof document === 'undefined') return;
  const { Sim, TICK_HZ, W, GROUND } = DinoEngine;
  const H = 300, GL = 250;                         // altura do canvas e linha do chão
  const SPEEDS = [0.25, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 'max'];
  const PALETTE = ['#e4572e', '#2e86ab', '#3bb273', '#f2a541', '#7768ae', '#d1507a', '#1b998b', '#8d6a43'];
  const INK = '#535353';
  const $ = id => document.getElementById(id);

  const sim = new Sim({ numDinos: 30 });
  let speedIdx = 4, paused = false, drawOn = true, acc = 0, lastTs = performance.now(), lastEpisode = -1, lastStats = 0;

  /* ---------- canvas ---------- */
  const game = $('game'), chart = $('chart');
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  game.width = W * dpr; game.height = H * dpr;
  chart.width = W * dpr; chart.height = 170 * dpr;
  const g = game.getContext('2d'), ch = chart.getContext('2d');

  function drawDino(d, color, alpha, champion) {
    const w = d.estado === 1 ? 55 : d.estado === 4 ? 39 : 40;
    const h = d.estado === 1 ? 25 : d.estado === 4 ? 37 : 43;
    const left = Math.round(d.x), bottom = GL - Math.round(d.y - GROUND), top = bottom - h;
    const R = (x, y, ww, hh) => g.fillRect(left + x, top + y, ww, hh);
    const step = ((sim.tick / 12) | 0) % 2;
    g.globalAlpha = alpha;
    g.fillStyle = color;
    if (d.estado === 1 && d.alive) {                               // agachado
      R(0, 4, 8, 6); R(0, 6, 36, 14); R(34, 0, 21, 13);
      R(8, 20, 6, step ? 5 : 3); R(24, 20, 6, step ? 3 : 5);
      g.fillStyle = '#fff'; R(46, 3, 4, 4);
    } else if (d.estado === 4 && d.alive) {                        // voando de avião
      R(20, 0, 16, 12); R(6, 8, 22, 14);
      g.fillStyle = '#2b2b2b';
      g.beginPath(); g.moveTo(left, top + 26); g.lineTo(left + 39, top + 26); g.lineTo(left + 33, top + 33); g.lineTo(left + 6, top + 33); g.fill();
      g.beginPath(); g.moveTo(left, top + 18); g.lineTo(left + 9, top + 26); g.lineTo(left, top + 26); g.fill();
      R(37, 19 + ((sim.tick / 2) & 1) * 7, 2, 10);
      g.fillStyle = '#fff'; R(30, 3, 4, 4);
    } else {                                                       // em pé, pulando ou morto
      R(16, 0, 24, 15); R(8, 14, 22, 18); R(0, 16, 9, 9); R(3, 24, 7, 5); R(30, 22, 7, 3);
      const air = d.estado === 2 || !d.alive;
      R(10, 32, 6, air ? 11 : (step ? 11 : 6)); R(22, 32, 6, air ? 11 : (step ? 6 : 11));
      g.fillStyle = '#fff';
      if (d.alive) { R(30, 3, 4, 4); }
      else { g.strokeStyle = '#fff'; g.lineWidth = 1.5; g.beginPath();
        g.moveTo(left + 29, top + 2); g.lineTo(left + 35, top + 8); g.moveTo(left + 35, top + 2); g.lineTo(left + 29, top + 8); g.stroke(); }
    }
    if (champion && d.alive) {
      g.globalAlpha = 1; g.strokeStyle = '#111'; g.lineWidth = 2;
      g.strokeRect(left - 3, top - 3, w + 6, h + 6);
    }
    g.globalAlpha = 1;
  }

  function drawObstacle(o) {
    const left = Math.round(o.x), bottom = GL - Math.round(o.y - GROUND), top = bottom - o.h;
    g.fillStyle = INK;
    if (o.type < 5) {
      const trunks = o.w >= 49 ? 2 : 1, tw = Math.max(7, Math.round(o.w / (trunks === 2 ? 4.5 : 2.6)));
      for (let t = 0; t < trunks; t++) {
        const cx = left + (o.w / (trunks * 2)) * (2 * t + 1) - tw / 2;
        const th = t === 1 ? o.h * 0.8 : o.h;
        g.fillRect(cx, bottom - th, tw, th);
        if (o.w > 20) { g.fillRect(cx - 6, bottom - th * 0.6, 6, 4); g.fillRect(cx - 6, bottom - th * 0.6 - 8, 4, 12);
                        g.fillRect(cx + tw, bottom - th * 0.45, 6, 4); g.fillRect(cx + tw + 2, bottom - th * 0.45 - 8, 4, 12); }
      }
    } else if (o.type === 5) {                                     // pássaro
      const up = ((sim.dist / 60) | 0) % 2 === 0;
      g.fillRect(left + 6, top + 14, 28, 10); g.fillRect(left + 32, top + 12, 10, 6); g.fillRect(left, top + 16, 8, 4);
      g.beginPath();
      if (up) { g.moveTo(left + 12, top + 14); g.lineTo(left + 26, top + 14); g.lineTo(left + 20, top); }
      else { g.moveTo(left + 12, top + 24); g.lineTo(left + 26, top + 24); g.lineTo(left + 20, top + 36); }
      g.fill();
    } else {                                                       // espinhos
      for (let x = 0; x < o.w; x += 18) {
        const sx = left + x;
        if (sx > W || sx + 18 < 0) continue;
        g.beginPath(); g.moveTo(sx, bottom); g.lineTo(sx + 9, top); g.lineTo(sx + 18, bottom); g.fill();
      }
    }
  }

  function draw() {
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = '#f7f7f7'; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 3; i++) {                                  // nuvens
      const cx = (((i * 340 + 120 - sim.dist * 0.08) % (W + 120)) + W + 120) % (W + 120) - 60;
      g.fillStyle = '#e2e2e2'; g.fillRect(cx, 60 + i * 28, 46, 10); g.fillRect(cx + 10, 54 + i * 28, 24, 6);
    }
    g.fillStyle = INK; g.fillRect(0, GL + 1, W, 2);
    g.fillStyle = '#b5b5b5';
    for (let i = 0; i < 34; i++) {
      const x = (((i * 79 - sim.dist) % W) + W) % W;
      g.fillRect(x, GL + 8 + (i % 3) * 6, 5 + (i % 4) * 4, 2);
    }
    for (const o of sim.obstacles) if (o.x < W && o.x + o.w > 0) drawObstacle(o);
    for (const d of sim.dinos) if (!d.alive && d.x > -60) drawDino(d, PALETTE[d.id % 8], 0.22, false);
    for (const d of sim.dinos) if (d.alive && d.id !== 0) drawDino(d, PALETTE[d.id % 8], 0.6, false);
    const champ = sim.dinos[0];
    if (champ) drawDino(champ, PALETTE[0], champ.alive ? 1 : 0.3, true);
  }

  function drawChart() {
    const cw = W, chh = 170, c = ch;
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.fillStyle = '#fff'; c.fillRect(0, 0, cw, chh);
    const hist = sim.history.slice(-300), padL = 72, padR = 14, padT = 26, padB = 22;
    c.font = '12px system-ui, sans-serif'; c.textBaseline = 'middle';
    c.fillStyle = '#5d6673'; c.textAlign = 'left';
    c.fillText('Distância por episódio', padL, 11);
    c.fillStyle = '#1f4fd8'; c.fillRect(padL + 150, 7, 14, 3); c.fillStyle = '#5d6673'; c.fillText('melhor', padL + 170, 11);
    c.fillStyle = '#9aa3af'; c.fillRect(padL + 226, 7, 14, 3); c.fillStyle = '#5d6673'; c.fillText('média', padL + 246, 11);
    if (hist.length < 2) { c.fillStyle = '#9aa3af'; c.textAlign = 'center'; c.fillText('O gráfico aparece depois de 2 episódios.', cw / 2, chh / 2); return; }
    const max = Math.max(1, ...hist.map(h => h.best)), pw = cw - padL - padR, ph = chh - padT - padB;
    c.strokeStyle = '#e4e7ec'; c.lineWidth = 1; c.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
      const y = padT + ph * i / 4; c.beginPath(); c.moveTo(padL, y); c.lineTo(cw - padR, y); c.stroke();
      c.fillStyle = '#5d6673'; c.fillText(Math.round(max * (1 - i / 4)).toLocaleString('pt-BR'), padL - 6, y);
    }
    const line = (key, color, wd) => {
      c.strokeStyle = color; c.lineWidth = wd; c.beginPath();
      hist.forEach((h, i) => { const x = padL + pw * i / (hist.length - 1), y = padT + ph * (1 - h[key] / max); i ? c.lineTo(x, y) : c.moveTo(x, y); });
      c.stroke();
    };
    line('avg', '#9aa3af', 1.5); line('best', '#1f4fd8', 2);
    c.fillStyle = '#5d6673'; c.textAlign = 'center';
    const first = sim.episode - hist.length + 1;
    c.fillText('episódio ' + first, padL + 30, chh - 8); c.fillText('episódio ' + sim.episode, cw - padR - 40, chh - 8);
  }

  /* ---------- painel ---------- */
  const fmt = n => Math.round(n).toLocaleString('pt-BR');
  function updateStats() {
    $('sEp').textContent = fmt(sim.episode + 1);
    $('sAlive').textContent = sim.alive + '/' + sim.dinos.length;
    $('sDist').textContent = fmt(sim.dist);
    $('sBest').textContent = fmt(Math.max(sim.bestEver, sim.dist));
    $('sStates').textContent = fmt(sim.q.size);
    const totalDistance = sim.dinos.reduce((sum, d) => sum + (d.alive ? sim.dist : d.dist), 0);
    $('sAvg').textContent = fmt(sim.dinos.length ? totalDistance / sim.dinos.length : 0);
    $('sEps').textContent = sim.learn ? sim.epsilon.toFixed(3) : '0';
    const f = $('pEps'); if (document.activeElement !== f) f.value = sim.epsilon.toFixed(3);
  }
  function syncInputs() {
    $('nDinos').value = sim.numDinos; $('pAlpha').value = sim.alpha; $('pGamma').value = sim.gamma;
    $('pEps').value = sim.epsilon.toFixed(3); $('pEpsMin').value = sim.epsilonMin; $('pDecay').value = sim.epsilonDecay;
    $('pCap').value = sim.capDistance; $('chkLearn').checked = sim.learn; $('chkPlane').checked = sim.planeMode;
  }
  function setStatus(msg, err) { const s = $('status'); s.textContent = msg; s.className = err ? 'err' : ''; }
  function setSpeed(i) {
    speedIdx = Math.max(0, Math.min(SPEEDS.length - 1, i));
    $('speed').value = speedIdx;
    $('speedVal').textContent = SPEEDS[speedIdx] === 'max' ? 'Máx' : '×' + SPEEDS[speedIdx];
    acc = 0;
  }
  function setPaused(p) { paused = p; $('btnPause').textContent = p ? 'Continuar' : 'Pausar'; }

  /* ---------- exportação Excel com gráfico incorporado ---------- */
  const excelXmlEscape = value => String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;');

  const excelColumn = n => {
    let out = '';
    while (n > 0) { const r = (n - 1) % 26; out = String.fromCharCode(65 + r) + out; n = Math.floor((n - 1) / 26); }
    return out;
  };

  function excelCellText(ref, value, style = 0) {
    return `<c r="${ref}" t="inlineStr" s="${style}"><is><t xml:space="preserve">${excelXmlEscape(value)}</t></is></c>`;
  }
  function excelCellNumber(ref, value, style = 4) {
    const n = Number.isFinite(Number(value)) ? Number(value) : 0;
    return `<c r="${ref}" s="${style}"><v>${n}</v></c>`;
  }

  // ZIP sem compressão: o formato XLSX continua sendo um pacote ZIP válido e não depende de bibliotecas externas.
  const excelCrcTable = (() => {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      table[n] = c >>> 0;
    }
    return table;
  })();

  function excelCrc32(bytes) {
    let crc = 0xFFFFFFFF;
    for (let i = 0; i < bytes.length; i++) crc = excelCrcTable[(crc ^ bytes[i]) & 0xFF] ^ (crc >>> 8);
    return (crc ^ 0xFFFFFFFF) >>> 0;
  }

  function excelZip(files) {
    const encoder = new TextEncoder();
    const localParts = [], centralParts = [];
    const now = new Date();
    const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | Math.floor(now.getSeconds() / 2);
    const dosDate = ((Math.max(1980, now.getFullYear()) - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
    let offset = 0;

    const header = size => new Uint8Array(size);
    const set16 = (view, at, value) => view.setUint16(at, value, true);
    const set32 = (view, at, value) => view.setUint32(at, value >>> 0, true);

    for (const [path, content] of Object.entries(files)) {
      const name = encoder.encode(path);
      const data = encoder.encode(content);
      const crc = excelCrc32(data);
      const local = header(30), lv = new DataView(local.buffer);
      set32(lv, 0, 0x04034b50); set16(lv, 4, 20); set16(lv, 6, 0x0800);
      set16(lv, 8, 0); set16(lv, 10, dosTime); set16(lv, 12, dosDate);
      set32(lv, 14, crc); set32(lv, 18, data.length); set32(lv, 22, data.length);
      set16(lv, 26, name.length); set16(lv, 28, 0);
      localParts.push(local, name, data);

      const central = header(46), cv = new DataView(central.buffer);
      set32(cv, 0, 0x02014b50); set16(cv, 4, 20); set16(cv, 6, 20);
      set16(cv, 8, 0x0800); set16(cv, 10, 0); set16(cv, 12, dosTime); set16(cv, 14, dosDate);
      set32(cv, 16, crc); set32(cv, 20, data.length); set32(cv, 24, data.length);
      set16(cv, 28, name.length); set16(cv, 30, 0); set16(cv, 32, 0);
      set16(cv, 34, 0); set16(cv, 36, 0); set32(cv, 38, 0); set32(cv, 42, offset);
      centralParts.push(central, name);
      offset += local.length + name.length + data.length;
    }

    const centralSize = centralParts.reduce((sum, part) => sum + part.length, 0);
    const end = header(22), ev = new DataView(end.buffer);
    set32(ev, 0, 0x06054b50); set16(ev, 4, 0); set16(ev, 6, 0);
    set16(ev, 8, Object.keys(files).length); set16(ev, 10, Object.keys(files).length);
    set32(ev, 12, centralSize); set32(ev, 16, offset); set16(ev, 20, 0);

    return new Blob([...localParts, ...centralParts, end], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
  }

  function buildExcelReport() {
    const history = sim.history.map((item, index) => ({
      episode: Math.max(1, sim.episode - sim.history.length + index + 1),
      best: Number(item.best) || 0,
      avg: Number(item.avg) || 0,
      status: 'Concluído'
    }));

    // Inclui um retrato do episódio atual para permitir exportação antes do fim da partida.
    const distances = sim.dinos.map(d => d.alive ? sim.dist : d.dist);
    const currentBest = distances.length ? Math.max(...distances) : 0;
    const currentAverage = distances.length
      ? distances.reduce((sum, value) => sum + value, 0) / distances.length : 0;
    history.push({
      episode: sim.episode + 1,
      best: currentBest,
      avg: currentAverage,
      status: 'Em andamento'
    });

    const firstDataRow = 8;
    const lastDataRow = firstDataRow + history.length - 1;
    const averageOfAverages = history.length
      ? history.reduce((sum, row) => sum + row.avg, 0) / history.length : 0;
    const maxDistance = history.reduce((max, row) => Math.max(max, row.best), 0);
    const modeName = sim.playerMode ? 'Jogador' : 'Inteligência artificial';

    const rows = [];
    rows.push(`<row r="1" ht="32" customHeight="1">${excelCellText('A1', 'Dino Q-Learning — Relatório de desempenho', 1)}</row>`);
    rows.push(`<row r="2" ht="22" customHeight="1">${excelCellText('A2', 'Histórico por episódio | Gerado em ' + new Date().toLocaleString('pt-BR'), 2)}</row>`);
    rows.push(`<row r="4">${excelCellText('A4', 'Episódios concluídos', 5)}${excelCellNumber('B4', sim.history.length, 6)}${excelCellText('C4', 'Recorde geral', 5)}${excelCellNumber('D4', Math.max(Number(sim.bestEver) || 0, maxDistance), 6)}</row>`);
    rows.push(`<row r="5">${excelCellText('A5', 'Média das médias', 5)}${excelCellNumber('B5', averageOfAverages, 6)}${excelCellText('C5', 'Modo exportado', 5)}${excelCellText('D5', modeName, 7)}</row>`);
    rows.push(`<row r="7" ht="28" customHeight="1">${excelCellText('A7', 'Episódio', 3)}${excelCellText('B7', 'Melhor distância', 3)}${excelCellText('C7', 'Distância média', 3)}${excelCellText('D7', 'Status', 3)}</row>`);

    history.forEach((item, index) => {
      const row = firstDataRow + index;
      rows.push(`<row r="${row}">${excelCellText('A' + row, 'Episódio ' + item.episode, 0)}${excelCellNumber('B' + row, item.best)}${excelCellNumber('C' + row, item.avg)}${excelCellText('D' + row, item.status, 0)}</row>`);
    });

    const chartSeries = (index, titleCell, title, column, color) => {
      const points = history.map((item, i) => `<c:pt idx="${i}"><c:v>${excelXmlEscape(item[column])}</c:v></c:pt>`).join('');
      const categoryPoints = history.map((item, i) => `<c:pt idx="${i}"><c:v>${excelXmlEscape('Episódio ' + item.episode)}</c:v></c:pt>`).join('');
      return `<c:ser>
        <c:idx val="${index}"/><c:order val="${index}"/>
        <c:tx><c:strRef><c:f>'Desempenho'!$${titleCell}$7</c:f><c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>${excelXmlEscape(title)}</c:v></c:pt></c:strCache></c:strRef></c:tx>
        <c:spPr><a:ln w="28575"><a:solidFill><a:srgbClr val="${color}"/></a:solidFill><a:prstDash val="solid"/></a:ln></c:spPr>
        <c:marker><c:symbol val="circle"/><c:size val="5"/><c:spPr><a:solidFill><a:srgbClr val="${color}"/></a:solidFill></c:spPr></c:marker>
        <c:cat><c:strRef><c:f>'Desempenho'!$A$${firstDataRow}:$A$${lastDataRow}</c:f><c:strCache><c:ptCount val="${history.length}"/>${categoryPoints}</c:strCache></c:strRef></c:cat>
        <c:val><c:numRef><c:f>'Desempenho'!$${column === 'best' ? 'B' : 'C'}$${firstDataRow}:$${column === 'best' ? 'B' : 'C'}$${lastDataRow}</c:f><c:numCache><c:formatCode>0.00</c:formatCode><c:ptCount val="${history.length}"/>${points}</c:numCache></c:numRef></c:val>
        <c:smooth val="0"/>
      </c:ser>`;
    };

    const skipLabels = Math.max(1, Math.ceil(history.length / 18));
    const chartXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
        <c:date1904 val="0"/><c:lang val="pt-BR"/><c:roundedCorners val="1"/>
        <c:chart>
          <c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr lang="pt-BR" sz="1500" b="1"/></a:pPr><a:r><a:rPr lang="pt-BR" sz="1500" b="1"/><a:t>Evolução do desempenho por episódio</a:t></a:r><a:endParaRPr lang="pt-BR"/></a:p></c:rich></c:tx><c:overlay val="0"/></c:title>
          <c:autoTitleDeleted val="0"/><c:plotArea><c:layout/><c:lineChart><c:grouping val="standard"/><c:varyColors val="0"/>
            ${chartSeries(0, 'B', 'Melhor distância', 'best', '1F4FD8')}
            ${chartSeries(1, 'C', 'Distância média', 'avg', '8993A4')}
            <c:dropLines/><c:hiLowLines/><c:upDownBars/><c:marker val="1"/><c:smooth val="0"/><c:axId val="123456"/><c:axId val="123457"/>
          </c:lineChart>
          <c:catAx><c:axId val="123456"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="b"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/><c:crossAx val="123457"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/><c:tickLblSkip val="${skipLabels}"/></c:catAx>
          <c:valAx><c:axId val="123457"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="l"/><c:majorGridlines><c:spPr><a:ln w="9525"><a:solidFill><a:srgbClr val="D9E1F2"/></a:solidFill></a:ln></c:spPr></c:majorGridlines><c:numFmt formatCode="#,##0" sourceLinked="1"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/><c:crossAx val="123456"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx>
          </c:plotArea><c:legend><c:legendPos val="b"/><c:overlay val="0"/></c:legend><c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/><c:showDLblsOverMax val="0"/>
        </c:chart><c:printSettings><c:headerFooter/><c:pageMargins b="0.75" l="0.7" r="0.7" t="0.75" header="0.3" footer="0.3"/><c:pageSetup/></c:printSettings>
      </c:chartSpace>`;

    const sheetRows = rows.join('');
    const sheetXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <dimension ref="A1:D${lastDataRow}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="7" topLeftCell="A8" activePane="bottomLeft" state="frozen"/><selection pane="bottomLeft" activeCell="A8" sqref="A8"/></sheetView></sheetViews>
        <sheetFormatPr defaultRowHeight="18"/><cols><col min="1" max="1" width="25" customWidth="1"/><col min="2" max="3" width="22" customWidth="1"/><col min="4" max="4" width="18" customWidth="1"/></cols>
        <sheetData>${sheetRows}</sheetData><autoFilter ref="A7:D${lastDataRow}"/><mergeCells count="2"><mergeCell ref="A1:D1"/><mergeCell ref="A2:D2"/></mergeCells><drawing r:id="rId1"/>
      </worksheet>`;

    const stylesXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts>
        <fonts count="5"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="18"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><sz val="10"/><i/><color rgb="FF5D6673"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FF1F2937"/><name val="Calibri"/></font></fonts>
        <fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F3B70"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4FD8"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEAF0FF"/><bgColor indexed="64"/></patternFill></fill></fills>
        <borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left/><right/><top/><bottom style="thin"><color rgb="FFD9E1F2"/></bottom><diagonal/></border></borders>
        <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
        <cellXfs count="8"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="4" fillId="4" borderId="1" xfId="0"/><xf numFmtId="164" fontId="4" fillId="4" borderId="1" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0"/></cellXfs>
        <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
      </styleSheet>`;

    const workbookXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><fileVersion appName="xl"/><workbookPr/><bookViews><workbookView/></bookViews><sheets><sheet name="Desempenho" sheetId="1" r:id="rId1"/></sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>`;
    const drawingXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><xdr:twoCellAnchor editAs="oneCell"><xdr:from><xdr:col>5</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>2</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from><xdr:to><xdr:col>14</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>22</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to><xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="Gráfico de desempenho"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr><xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rId1"/></a:graphicData></a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>`;

    return {
      '[Content_Types].xml': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/><Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>`,
      '_rels/.rels': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>`,
      'docProps/core.xml': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Dino Q-Learning — Relatório de desempenho</dc:title><dc:creator>Dino Q-Learning</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${new Date().toISOString()}</dcterms:created></cp:coreProperties>`,
      'docProps/app.xml': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Dino Q-Learning</Application><HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs><TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Desempenho</vt:lpstr></vt:vector></TitlesOfParts></Properties>`,
      'xl/workbook.xml': workbookXml,
      'xl/_rels/workbook.xml.rels': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
      'xl/styles.xml': stylesXml,
      'xl/worksheets/sheet1.xml': sheetXml,
      'xl/worksheets/_rels/sheet1.xml.rels': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/></Relationships>`,
      'xl/drawings/drawing1.xml': drawingXml,
      'xl/drawings/_rels/drawing1.xml.rels': `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/></Relationships>`,
      'xl/charts/chart1.xml': chartXml
    };
  }

  function exportExcelReport() {
    try {
      const file = excelZip(buildExcelReport());
      const url = URL.createObjectURL(file);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dino-qlearning_desempenho_' + new Date().toISOString().slice(0, 10) + '.xlsx';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1500);
      setStatus('Relatório Excel exportado com dados e gráfico de melhor distância x média.');
    } catch (err) {
      console.error('Falha ao exportar Excel:', err);
      setStatus('Não foi possível gerar o Excel: ' + (err.message || 'erro inesperado.'), true);
    }
  }

  const numInput = (id, key, lo, hi) => $(id).addEventListener('input', e => {
    const v = parseFloat(e.target.value);
    if (Number.isFinite(v)) sim[key] = Math.min(hi, Math.max(lo, v));
  });
  numInput('pAlpha', 'alpha', 0.001, 1); numInput('pGamma', 'gamma', 0, 0.999);
  numInput('pEps', 'epsilon', 0, 1); numInput('pEpsMin', 'epsilonMin', 0, 1); numInput('pDecay', 'epsilonDecay', 0.5, 1);
  $('pCap').addEventListener('input', e => {
    const v = parseFloat(e.target.value);
    if (Number.isFinite(v)) sim.capDistance = Math.max(0, v);
  });
  $('nDinos').addEventListener('input', e => {
    const v = parseInt(e.target.value, 10);
    if (Number.isFinite(v)) sim.numDinos = Math.min(300, Math.max(1, v));
  });
  $('speed').addEventListener('input', e => setSpeed(+e.target.value));
  $('btnPause').addEventListener('click', () => setPaused(!paused));
  $('btnNew').addEventListener('click', () => { sim.newEpisode(); setStatus('Novo episódio iniciado.'); });
  $('chkDraw').addEventListener('change', e => { drawOn = e.target.checked; if (!drawOn) { g.setTransform(dpr, 0, 0, dpr, 0, 0); g.fillStyle = '#f7f7f7'; g.fillRect(0, 0, W, H); g.fillStyle = '#5d6673'; g.font = '15px system-ui'; g.textAlign = 'center'; g.fillText('Desenho desligado: o treino roda mais rápido.', W / 2, H / 2); } });
  $('chkLearn').addEventListener('change', e => { sim.learn = e.target.checked; });
  $('chkPlane').addEventListener('change', e => { sim.planeMode = e.target.checked; sim.newEpisode(); setStatus(sim.planeMode ? 'Modo avião ligado: espinhos longos exigem voar.' : 'Modo avião desligado.'); });

  /* ---------- exportar / importar ---------- */
  $('btnExport').addEventListener('click', () => {
    const data = sim.exportData();
    const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'dino-qlearning_ep' + sim.episode + '_rec' + Math.round(sim.bestEver) + '.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    setStatus('Exportado: ' + fmt(Object.keys(data.qtable).length) + ' estados, ' + fmt(sim.episode) + ' episódios.');
  });
  $('btnExportExcel').addEventListener('click', exportExcelReport);
  $('btnImport').addEventListener('click', () => $('fileIn').click());
  $('fileIn').addEventListener('change', e => {
    const file = e.target.files[0]; e.target.value = '';
    if (!file) return;
    const mode = document.querySelector('input[name=impMode]:checked').value;
    const rd = new FileReader();
    rd.onload = () => {
      try {
        const res = sim.importData(JSON.parse(rd.result), mode);
        syncInputs(); lastEpisode = -1;
        setStatus(mode === 'merge'
          ? 'Mesclado: ' + fmt(res.states) + ' estados do arquivo (' + fmt(res.overlap) + ' em comum).'
          : 'Importado: ' + fmt(res.states) + ' estados.');
      } catch (err) { setStatus(err.message || 'Não foi possível ler o arquivo.', true); }
    };
    rd.onerror = () => setStatus('Não foi possível ler o arquivo.', true);
    rd.readAsText(file);
  });
  $('btnReset').addEventListener('click', () => {
    if (confirm('Apagar toda a tabela Q e o histórico? Exporte antes se quiser guardar.')) { sim.reset(); lastEpisode = -1; syncInputs(); setStatus('Aprendizado zerado.'); }
  });

  window.addEventListener('keydown', e => {
    const t = e.target.tagName;
    if (t === 'INPUT' || t === 'SELECT' || t === 'TEXTAREA' || e.ctrlKey || e.metaKey || e.altKey) return;

    if (sim.playerMode) {
      if (e.code === 'Space' || e.key === 'ArrowUp') {
        if (!e.repeat) sim.playerJumpQueued = true;
        e.preventDefault();
      } else if (e.key === 'ArrowDown') {
        sim.playerDuck = true;
        e.preventDefault();
      } else if (e.key === 'Escape') {
        setPaused(!paused);
      }
      return;
    }

    if (e.key === 'ArrowUp') { setSpeed(speedIdx + 1); e.preventDefault(); }
    else if (e.key === 'ArrowDown') { setSpeed(speedIdx - 1); e.preventDefault(); }
    else if (e.key === ' ') { if (t !== 'BUTTON') { setPaused(!paused); e.preventDefault(); } }
    else if (e.key === 'd' || e.key === 'D') { $('chkDraw').click(); }
  });

  window.addEventListener('keyup', e => {
    if (sim.playerMode && e.key === 'ArrowDown') {
      sim.playerDuck = false;
      e.preventDefault();
    }
  });

  /* ---------- modo de jogo ---------- */
  let savedAIConfig = null;

  function setGameMode(mode) {
    if (mode === 'player') {
      if (!sim.playerMode) {
        savedAIConfig = {
          numDinos: sim.numDinos,
          learn: sim.learn,
          planeMode: sim.planeMode
        };
      }
      sim.playerMode = true;
      sim.numDinos = 1;
      sim.learn = false;
      sim.planeMode = false;
      $('nDinos').disabled = true;
      $('chkLearn').checked = false;
      $('chkLearn').disabled = true;
      $('chkPlane').checked = false;
      $('chkPlane').disabled = true;
      $('playerControls').hidden = false;
      setStatus('Modo jogador ativado. Use Espaço/↑ para pular e ↓ para abaixar.');
    } else {
      sim.playerMode = false;
      if (savedAIConfig) {
        sim.numDinos = savedAIConfig.numDinos;
        sim.learn = savedAIConfig.learn;
        sim.planeMode = savedAIConfig.planeMode;
      }
      savedAIConfig = null;
      $('nDinos').disabled = false;
      $('chkLearn').disabled = false;
      $('chkPlane').disabled = false;
      $('playerControls').hidden = true;
      setStatus('Modo IA ativado. Os dinossauros voltaram a treinar.');
    }
    sim.newEpisode();
    syncInputs();
    $('mode').value = mode;
    $('speedHint').textContent = mode === 'player'
      ? 'Teclado: Espaço/↑ pula, ↓ abaixa e Esc pausa. Também dá para usar os botões acima.'
      : 'Teclas: ↑ e ↓ mudam a velocidade, espaço pausa, D liga/desliga o desenho.';
    $('chkLearn').disabled = mode === 'player';
    $('chkPlane').disabled = mode === 'player';
    $('nDinos').disabled = mode === 'player';
    lastEpisode = -1;
  }

  $('mode').addEventListener('change', e => setGameMode(e.target.value));
  $('btnJump').addEventListener('click', () => { if (sim.playerMode) sim.playerJumpQueued = true; });

  const duckButton = $('btnDuck');
  const startDuck = e => {
    if (!sim.playerMode) return;
    sim.playerDuck = true;
    if (e && e.cancelable) e.preventDefault();
  };
  const stopDuck = e => {
    sim.playerDuck = false;
    if (e && e.cancelable) e.preventDefault();
  };
  duckButton.addEventListener('pointerdown', startDuck);
  duckButton.addEventListener('pointerup', stopDuck);
  duckButton.addEventListener('pointerleave', stopDuck);
  duckButton.addEventListener('pointercancel', stopDuck);
  duckButton.addEventListener('lostpointercapture', stopDuck);

  /* ---------- laço principal ---------- */
  function frame(ts) {
    requestAnimationFrame(frame);
    const dt = Math.min(100, ts - lastTs); lastTs = ts;
    if (!paused) {
      const t0 = performance.now(), sp = SPEEDS[speedIdx];
      if (sp === 'max') {
        const budget = drawOn ? 16 : 30;
        while (performance.now() - t0 < budget) sim.run(100);
      } else {
        acc += dt / 1000 * TICK_HZ * sp;
        let n = Math.floor(acc); acc -= n;
        while (n > 0) {
          const k = Math.min(n, 100); sim.run(k); n -= k;
          if (performance.now() - t0 > 20) { acc = 0; break; }
        }
      }
    }
    if (drawOn) draw();
    if (sim.episode !== lastEpisode) { lastEpisode = sim.episode; drawChart(); }
    if (ts - lastStats > 120) { lastStats = ts; updateStats(); }
  }

  syncInputs(); setSpeed(speedIdx); updateStats(); drawChart();
  requestAnimationFrame(frame);
})();
