/* A interface exibe dados do núcleo Python; não usa resultados fixos. */
'use strict';
const $ = id => document.getElementById(id);
const initialRows = ['S.....', '.##.#.', '....#.', '.##...', '...##.', '.#...G'];
const actionCodes = ['C', 'D', 'B', 'E'];
const actionNames = ['Cima', 'Direita', 'Baixo', 'Esquerda'];
const fields = ['episodes', 'alpha', 'gamma', 'epsilon_start', 'epsilon_end', 'step_reward', 'seed'];
let rows = [...initialRows], result = null, selected = [0, 0], editing = false;
let busy = false, timer = null, activeRun = null, frame = 0, paused = false;
let agent = [0, 0], visited = new Set();
const fmt = (value, digits = 1) => value === null ? 'Sem sucesso' : Number(value).toLocaleString('pt-BR', {maximumFractionDigits: digits});
const key = pos => pos.join(',');
const same = (a, b) => key(a) === key(b);
function message(text, error = false) { $('status').textContent = text; $('status').classList.toggle('error', error); }
function qValues(pos) { return result?.q_table.find(entry => same(entry.state, pos))?.values; }
function renderBoard() {
  const board = $('board'); board.replaceChildren();
  board.style.gridTemplateColumns = `repeat(${rows[0].length}, 1fr)`;
  rows.forEach((row, r) => [...row].forEach((symbol, c) => {
    const cell = document.createElement('button');
    const pos = [r, c];
    cell.type = 'button'; cell.className = 'cell';
    if (symbol === '#') cell.classList.add('wall');
    if (symbol === 'S') { cell.classList.add('start'); cell.textContent = 'I'; }
    if (symbol === 'G') { cell.classList.add('goal'); cell.textContent = 'F'; }
    if (visited.has(key(pos))) cell.classList.add('visited');
    if (same(selected, pos)) cell.classList.add('selected');
    if (same(agent, pos)) cell.classList.add('agent');
    const q = qValues(pos);
    if ($('policy').checked && q && symbol === '.') {
      const best = Math.max(...q);
      cell.textContent = q.flatMap((v, i) => Math.abs(v - best) < 1e-10 ? [actionCodes[i]] : []).join('/');
      cell.style.fontSize = '11px';
    }
    const kind = symbol === '#' ? 'parede' : symbol === 'S' ? 'início' : symbol === 'G' ? 'saída' : 'casa livre';
    cell.setAttribute('aria-label', `Linha ${r + 1}, coluna ${c + 1}: ${kind}${same(agent, pos) ? ', agente' : ''}`);
    cell.setAttribute('aria-pressed', String(same(selected, pos)));
    cell.disabled = busy;
    cell.addEventListener('click', () => {
      if (editing) {
        if ('SG'.includes(symbol)) { message('Início e saída são fixos.'); return; }
        rows[r] = rows[r].slice(0, c) + (symbol === '#' ? '.' : '#') + rows[r].slice(c + 1);
        selected = [0, 0]; invalidate('Mapa alterado.');
      } else if (symbol !== '#') { selected = pos; renderBoard(); renderQ(); }
    });
    board.append(cell);
  }));
}
function renderQ() {
  $('selected-state').textContent = `Linha ${selected[0] + 1}, coluna ${selected[1] + 1}`;
  const values = qValues(selected);
  const isGoal = rows[selected[0]][selected[1]] === 'G';
  $('q-values').replaceChildren();
  actionNames.forEach((name, i) => {
    const box = document.createElement('div'); box.className = 'q-value';
    if (values && !isGoal && Math.abs(values[i] - Math.max(...values)) < 1e-10) box.classList.add('best');
    const label = document.createElement('span'); label.textContent = name;
    const value = document.createElement('strong'); value.textContent = values ? fmt(values[i], 2) : '—';
    box.append(label, value); $('q-values').append(box);
  });
  $('q-note').textContent = values && isGoal ? 'Estado terminal.' : '';
}
function stopAnimation() {
  clearTimeout(timer); timer = null; activeRun = null; frame = 0; paused = false;
  $('pause').disabled = true; $('pause').textContent = 'Pausar';
}
function invalidate(text) {
  stopAnimation(); result = null; agent = [0, 0]; visited = new Set();
  $('model-state').textContent = 'Não treinado';
  ['play-trained', 'play-random', 'download', 'policy'].forEach(id => $(id).disabled = true);
  $('policy').checked = false;
  ['random', 'trained'].forEach(method => ['success', 'steps', 'collisions'].forEach(metric => $(`${method}-${metric}`).textContent = '—'));
  $('chart').innerHTML = '<p class="muted">Sem dados.</p>';
  $('takeaway').textContent = '';
  $('evaluation-note').textContent = 'Avaliação: 200 episódios por agente.';
  $('run-status').textContent = '';
  message(text); renderBoard(); renderQ();
}
function renderChart(history) {
  const blocks = [];
  for (let i = 0; i < history.length; i += 50) {
    const block = history.slice(i, i + 50);
    blocks.push({episode: block.at(-1).episode, value: block.filter(e => e.success).length / block.length * 100});
  }
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 530 185'); svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Taxa de sucesso durante o treinamento em blocos de até cinquenta episódios.');
  const title = document.createElementNS(ns, 'title'); title.textContent = blocks.map(b => `Até episódio ${b.episode}: ${fmt(b.value)}%`).join('; '); svg.append(title);
  const add = (tag, attrs, text) => { const el = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v)); if (text !== undefined) el.textContent = text; svg.append(el); return el; };
  [0, 50, 100].forEach(v => { const y = 158 - v * 1.35; add('line', {x1: 35, y1: y, x2: 518, y2: y, stroke: '#d4d8dd', 'stroke-dasharray': '3 5'}); add('text', {x: 0, y: y + 4, fill: '#626b76', 'font-size': 10}, `${v}%`); });
  const coords = blocks.map((b, i) => [blocks.length === 1 ? 277 : 38 + i / (blocks.length - 1) * 477, 158 - b.value * 1.35]);
  if (coords.length > 1) {
    add('polyline', {points: coords.map(p => p.join(',')).join(' '), fill: 'none', stroke: '#365f88', 'stroke-width': 2, 'stroke-linejoin': 'round'});
  }
  coords.forEach(([x, y], i) => { const dot = add('circle', {cx: x, cy: y, r: 3, fill: '#365f88'}); const tip = document.createElementNS(ns, 'title'); tip.textContent = `Até episódio ${blocks[i].episode}: ${fmt(blocks[i].value)}%`; dot.append(tip); });
  add('text', {x: 35, y: 180, fill: '#626b76', 'font-size': 10}, String(blocks[0].episode));
  if (blocks.length > 1) add('text', {x: 515, y: 180, fill: '#626b76', 'font-size': 10, 'text-anchor': 'end'}, String(history.length));
  $('chart').replaceChildren(svg);
}
function showResult() {
  ['random', 'trained'].forEach(method => {
    const m = result[method];
    $(`${method}-success`).textContent = `${fmt(m.success_rate * 100)}%`;
    $(`${method}-steps`).textContent = fmt(m.mean_steps_success);
    $(`${method}-collisions`).textContent = fmt(m.mean_collisions);
  });
  const distance = result.shortest_path;
  $('takeaway').textContent = distance === null ? 'Mapa sem caminho até a saída.' : `Menor caminho: ${distance} passos.`;
  $('evaluation-note').textContent = `Avaliação: ${result.evaluation.episodes} episódios por agente | Limite: ${result.config.max_steps} passos`;
  $('model-state').textContent = 'Treinado';
  ['play-trained', 'play-random', 'download', 'policy'].forEach(id => $(id).disabled = false);
  $('run-status').textContent = '';
  renderChart(result.history); renderQ(); renderBoard();
}
function lockControls(locked) {
  fields.forEach(id => $(id).disabled = locked);
  $('train').disabled = locked; $('edit').disabled = locked; $('reset').disabled = locked;
}
$('settings').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return;
  invalidate('Treinando...');
  editing = false;
  $('edit').setAttribute('aria-pressed', 'false'); $('edit').textContent = 'Editar paredes'; $('map-hint').textContent = '';
  const data = Object.fromEntries(fields.map(id => [id, Number($(id).value)]));
  data.rows = [...rows];
  busy = true; lockControls(true); renderBoard();
  $('train').textContent = 'Treinando...'; $('model-state').textContent = 'Treinando';
  try {
    const response = await fetch('/api/train', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || 'Não foi possível executar o treinamento.');
    result = body;
    message(`${result.config.episodes.toLocaleString('pt-BR')} episódios concluídos.`);
  } catch (error) {
    $('model-state').textContent = 'Erro no treino';
    message(error.message, true);
  } finally {
    busy = false; lockControls(false); $('train').textContent = 'Treinar';
    if (result) showResult(); else renderBoard();
  }
});
fields.forEach(id => $(id).addEventListener('input', () => { if (!busy) invalidate('Parâmetros alterados.'); }));
function play(which) {
  if (!result || busy) return;
  stopAnimation(); visited = new Set();
  activeRun = {run: result[`${which}_run`], label: which === 'trained' ? 'Q-learning' : 'Aleatório'};
  agent = [...activeRun.run.path[0]]; frame = 0; $('pause').disabled = false;
  renderBoard(); tick();
}
function tick() {
  if (!activeRun || paused) return;
  const {run, label} = activeRun;
  agent = [...run.path[frame]]; visited.add(key(agent)); renderBoard();
  $('run-status').textContent = `${label} | Passo ${frame} de ${run.steps}`;
  if (frame === run.path.length - 1) {
    $('run-status').textContent = `${label} | ${run.success ? 'Saída alcançada' : 'Limite atingido'} | ${run.steps} passos | ${run.collisions} colisões | Retorno ${fmt(run.return)}`;
    $('pause').disabled = true; activeRun = null; timer = null; return;
  }
  frame++; timer = setTimeout(tick, 650 - Number($('speed').value) * 58);
}
$('play-trained').addEventListener('click', () => play('trained'));
$('play-random').addEventListener('click', () => play('random'));
$('pause').addEventListener('click', () => {
  if (!activeRun) return;
  paused = !paused; clearTimeout(timer);
  $('pause').textContent = paused ? 'Continuar' : 'Pausar';
  if (!paused) tick();
});
$('policy').addEventListener('change', renderBoard);
$('edit').addEventListener('click', () => {
  editing = !editing; stopAnimation();
  $('edit').setAttribute('aria-pressed', String(editing));
  $('edit').textContent = editing ? 'Concluir edição' : 'Editar paredes';
  $('map-hint').textContent = editing ? 'Editando paredes.' : '';
});
$('reset').addEventListener('click', () => { rows = [...initialRows]; selected = [0, 0]; invalidate('Mapa restaurado.'); });
$('download').addEventListener('click', () => {
  if (!result) return;
  const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
  anchor.href = url; anchor.download = `lb007-semente-${result.seed}.json`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
renderBoard(); renderQ();
