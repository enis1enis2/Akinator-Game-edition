#!/usr/bin/env python3
"""
Build a GitHub Pages-compatible static site from the current database.
Output: docs/index.html (self-contained, no build step required).
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "database.json"
OUT_PATH = HERE / "docs" / "index.html"

data = json.loads(DB_PATH.read_text(encoding="utf-8"))
questions = data["questions"]
entities = data["entities"]

QUESTIONS_JSON = json.dumps(questions, ensure_ascii=False)
ENTITIES_JSON = json.dumps(entities, ensure_ascii=False)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Guessly — 20 Questions Engine</title>
<style>
  :root {{
    --bg: #0d0d0d;
    --fg: #00ff66;
    --muted: #00802b;
    --accent: #00cc55;
    --card: #111111;
    --border: #1f1f1f;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--fg);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  }}
  .wrap {{
    max-width: 860px;
    margin: 0 auto;
    padding: 24px;
  }}
  header {{
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px;
    margin-bottom: 18px;
    background: linear-gradient(180deg, rgba(0,255,102,0.06), rgba(0,255,102,0));
  }}
  header h1 {{
    margin: 0 0 6px 0;
    font-size: 22px;
    letter-spacing: 2px;
  }}
  header p {{ margin: 0; opacity: .75; font-size: 13px; }}
  .card {{
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px;
    margin-bottom: 14px;
    background: var(--card);
  }}
  .meta {{ opacity: .8; font-size: 12px; margin-bottom: 10px; }}
  .btn {{
    background: transparent;
    color: var(--fg);
    border: 1px solid var(--fg);
    padding: 10px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-family: inherit;
    margin: 6px 6px 0 0;
    transition: transform .05s ease, background .15s ease;
  }}
  .btn:hover {{ background: rgba(0,255,102,0.12); }}
  .btn:active {{ transform: translateY(1px); }}
  .btn.secondary {{
    border-color: var(--muted);
    color: var(--muted);
  }}
  .question {{ font-size: 16px; line-height: 1.5; }}
  .guess {{ font-size: 18px; }}
  .confidence {{ opacity: .85; font-size: 13px; }}
  .bar-bg {{
    background: #1f1f1f;
    height: 10px;
    border-radius: 5px;
    overflow: hidden;
    margin-top: 8px;
  }}
  .bar-fill {{
    background: var(--fg);
    height: 100%;
    width: 0%;
    transition: width .25s ease;
  }}
  .candidates {{ margin-top: 12px; }}
  .candidate {{ margin-bottom: 8px; }}
  .candidate-name {{ font-size: 12px; opacity: .9; }}
  input[type="text"] {{
    width: 100%;
    background: #0a0a0a;
    color: var(--fg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px;
    font-family: inherit;
    margin-top: 8px;
  }}
  .hidden {{ display: none; }}
  .stats {{ display:flex; gap: 18px; flex-wrap: wrap; }}
  .stat {{ min-width: 100px; }}
  .stat-value {{ font-size: 22px; }}
  .stat-label {{ font-size: 11px; opacity: .75; text-transform: uppercase; letter-spacing: 1px; }}
  footer {{
    margin-top: 22px;
    opacity: .5;
    font-size: 12px;
    text-align: center;
  }}
  a {{ color: var(--fg); opacity: .8; text-decoration: none; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>GUESSLY</h1>
      <p>Entropy-based 20-questions engine — static build</p>
    </header>

    <div class="card">
      <div class="stats">
        <div class="stat">
          <div class="stat-value" id="stat-entities">-</div>
          <div class="stat-label">Entities</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="stat-questions">-</div>
          <div class="stat-label">Questions</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="stat-asked">0</div>
          <div class="stat-label">Asked</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="stat-learned">0</div>
          <div class="stat-label">Learned</div>
        </div>
      </div>
      <div style="margin-top:14px;">
        <button class="btn" id="start-btn" onclick="startGame()">Start New Game</button>
        <button class="btn secondary" onclick="showAbout()">About</button>
        <button class="btn secondary" onclick="exportDB()">Export DB</button>
        <button class="btn secondary" onclick="document.getElementById('file-input').click()">Import DB</button>
        <input type="file" id="file-input" class="hidden" accept="application/json" onchange="importDB(event)">
      </div>
    </div>

    <div class="card" id="game-box">
      <div class="meta" id="status">Click "Start New Game" to begin.</div>
      <div id="main-area"></div>
      <div class="candidates hidden" id="candidates-box">
        <div class="meta">Live candidates</div>
        <div id="candidates"></div>
      </div>
    </div>

    <footer>
      Built for GitHub Pages · No server required · Data stored locally in your browser
    </footer>
  </div>

<script>
  const QUESTIONS = {QUESTIONS_JSON};
  const SEED_ENTITIES = {ENTITIES_JSON};
  const STORAGE_KEY = 'guessly_db_v1';

  const ANSWER_WEIGHTS = {{
    yes: 1.0,
    probably: 0.75,
    dont_know: null,
    probably_not: 0.25,
    no: 0.0,
  }};
  const DEFAULT_CONFIDENCE_THRESHOLD = 0.62;
  const DEFAULT_MAX_QUESTIONS = 25;
  const MIN_QUESTIONS_BEFORE_GUESS = 6;

  let entities = {{}};
  let questions = {{}};
  let engine = null;
  let learnedCount = 0;

  function loadSavedDB() {{
    try {{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return SEED_ENTITIES.slice();
      const saved = JSON.parse(raw);
      if (!Array.isArray(saved)) return SEED_ENTITIES.slice();
      const ids = new Set(saved.map(e => e.id));
      const merged = saved.slice();
      for (const e of SEED_ENTITIES) {{
        if (!ids.has(e.id)) merged.push(e);
      }}
      return merged;
    }} catch (e) {{
      return SEED_ENTITIES.slice();
    }}
  }}

  function saveDB(list) {{
    try {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    }} catch (e) {{}}
  }}

  function init() {{
    const list = loadSavedDB();
    learnedCount = list.filter(e => e.category === 'crowdsourced').length;
    QUESTIONS.forEach(q => questions[q.id] = q);
    list.forEach(e => entities[e.id] = e);
    document.getElementById('stat-entities').textContent = list.length;
    document.getElementById('stat-questions').textContent = QUESTIONS.length;
    document.getElementById('stat-learned').textContent = learnedCount;
  }}

  class GuesslyEngine {{
    constructor(entities, questions) {{
      this.entities = entities;
      this.questions = questions;
      this.reset();
    }}
    reset() {{
      const ids = Object.keys(this.entities);
      this.belief = {{}};
      ids.forEach(id => this.belief[id] = 1.0 / ids.length);
      this.asked = [];
      this.history = [];
      this.eliminated = new Set();
      this.updateStats();
    }}
    updateStats() {{
      document.getElementById('stat-asked').textContent = this.asked.length;
    }}
    _entropyScore(qid) {{
      let yesMass = 0;
      let totalMass = 0;
      for (const [eid, p] of Object.entries(this.belief)) {{
        if (this.eliminated.has(eid)) continue;
        const entProb = this.entities[eid].probs[qid];
        if (entProb == null) continue;
        yesMass += p * entProb;
        totalMass += p;
      }}
      if (totalMass <= 0) return -1;
      const fractionYes = yesMass / totalMass;
      return 0.5 - Math.abs(0.5 - fractionYes);
    }}
    nextQuestion() {{
      const candidates = Object.keys(this.questions).filter(qid => !this.asked.includes(qid));
      if (!candidates.length) return null;
      const scored = candidates.slice().sort((a, b) => this._entropyScore(b) - this._entropyScore(a));
      const topN = scored.slice(0, 5);
      const topScores = topN.map(q => this._entropyScore(q));
      const best = Math.max(...topScores);
      const nearBest = topN.filter((q, i) => topScores[i] >= best - 0.02);
      const chosen = nearBest[Math.floor(Math.random() * nearBest.length)];
      return this.questions[chosen];
    }}
    answer(questionId, answer) {{
      if (!ANSWER_WEIGHTS.hasOwnProperty(answer)) throw new Error('Invalid answer: ' + answer);
      this.asked.push(questionId);
      this.history.push([questionId, answer]);
      const weight = ANSWER_WEIGHTS[answer];
      if (weight === null) {{ this.updateStats(); return; }}
      const updated = {{}};
      let total = 0;
      for (const [eid, p] of Object.entries(this.belief)) {{
        if (this.eliminated.has(eid)) {{ updated[eid] = 0; continue; }}
        const entProb = this.entities[eid].probs[questionId];
        const effective = entProb == null ? 0.5 : entProb;
        const likelihood = 1.0 - Math.abs(effective - weight);
        const clamped = Math.max(likelihood, 0.02);
        updated[eid] = p * clamped;
        total += updated[eid];
      }}
      if (total <= 0) {{ this.updateStats(); return; }}
      for (const eid of Object.keys(updated)) {{
        this.belief[eid] = updated[eid] / total;
      }}
      this.updateStats();
    }}
    eliminate(entityId) {{
      this.eliminated.add(entityId);
      this.belief[entityId] = 0;
      const total = Object.values(this.belief).reduce((a, b) => a + b, 0);
      if (total > 0) {{
        for (const eid of Object.keys(this.belief)) this.belief[eid] /= total;
      }}
      this.updateStats();
    }}
    topCandidates(n) {{
      return Object.entries(this.belief)
        .filter(([eid]) => eid in this.entities && !this.eliminated.has(eid))
        .sort((a, b) => b[1] - a[1])
        .slice(0, n)
        .map(([eid, prob]) => [this.entities[eid], prob]);
    }}
    shouldGuess() {{
      if (this.asked.length < MIN_QUESTIONS_BEFORE_GUESS) return false;
      const top = this.topCandidates(1);
      if (!top.length) return false;
      return top[0][1] >= DEFAULT_CONFIDENCE_THRESHOLD;
    }}
    isExhausted() {{
      return this.asked.length >= DEFAULT_MAX_QUESTIONS ||
        !Object.keys(this.questions).some(qid => !this.asked.includes(qid));
    }}
  }}

  function el(tag, cls, html) {{
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }}

  function setStatus(msg) {{
    document.getElementById('status').textContent = msg;
  }}

  function renderCandidates() {{
    const box = document.getElementById('candidates-box');
    const container = document.getElementById('candidates');
    const top = engine.topCandidates(5);
    if (!top.length) {{ box.classList.add('hidden'); return; }}
    box.classList.remove('hidden');
    container.innerHTML = '';
    top.forEach(([entity, prob]) => {{
      const pct = (prob * 100).toFixed(1);
      const row = el('div', 'candidate', `
        <div class="candidate-name">${{entity.name}} · ${{pct}}%</div>
        <div class="bar-bg"><div class="bar-fill" style="width:${{pct}}%"></div></div>
      `);
      container.appendChild(row);
    }});
  }}

  function showQuestion(q) {{
    const area = document.getElementById('main-area');
    area.innerHTML = '';
    const qEl = el('div', 'question', q.text);
    area.appendChild(qEl);
    const row = el('div', '');
    [
      ['yes','Yes'], ['probably','Probably'], ['dont_know',"Don't Know"],
      ['probably_not','Probably Not'], ['no','No']
    ].forEach(([key, label]) => {{
      const b = el('button', 'btn', label);
      b.onclick = () => submitAnswer(key);
      row.appendChild(b);
    }});
    area.appendChild(row);
    renderCandidates();
  }}

  function showGuess(entity, confidence) {{
    const area = document.getElementById('main-area');
    area.innerHTML = '';
    const g = el('div', 'guess', `Is your character: <u>${{entity.name}}</u>?`);
    const c = el('div', 'confidence', `Confidence: ${{(confidence * 100).toFixed(1)}}%`);
    const row = el('div', '');
    const y = el('button', 'btn', 'Yes, correct!');
    y.onclick = () => resolveGuess(true);
    const n = el('button', 'btn', 'No, wrong');
    n.onclick = () => resolveGuess(false);
    row.appendChild(y);
    row.appendChild(n);
    area.appendChild(g);
    area.appendChild(c);
    area.appendChild(row);
    renderCandidates();
  }}

  function showGiveUp(bestEntity, confidence) {{
    const area = document.getElementById('main-area');
    area.innerHTML = '';
    const msg = el('div', '', `I give up! Best guess: <b>${{bestEntity.name}}</b> (${{(confidence*100).toFixed(1)}}%)`);
    const label = el('div', '', 'Who was your character?');
    const input = el('input', '');
    input.placeholder = 'Enter name, e.g. Master Chief';
    const row = el('div', '');
    const b = el('button', 'btn', 'Teach Engine');
    b.onclick = () => {{
      const name = input.value.trim();
      if (!name) return;
      submitFeedback(name);
    }};
    row.appendChild(b);
    area.appendChild(msg);
    area.appendChild(label);
    area.appendChild(input);
    area.appendChild(row);
    renderCandidates();
  }}

  function showAbout() {{
    const area = document.getElementById('main-area');
    area.innerHTML = `
      <div class="guess">Guessly — Static Build</div>
      <p style="opacity:.85; line-height:1.6;">
        This is a GitHub Pages-compatible static build of the Guessly engine.
        It runs entirely in your browser using the same entropy-based question selection
        and Bayesian-style belief updates as the Python/Flask version.
        Learned entities are persisted in your browser's localStorage.
      </p>
      <p style="opacity:.85;">
        Entities: ${{Object.keys(entities).length}} · Questions: ${{Object.keys(questions).length}}
      </p>
    `;
    setStatus('About');
  }}

  function startGame() {{
    engine = new GuesslyEngine(entities, questions);
    engine.reset();
    setStatus('Playing...');
    nextStep();
  }}

  function submitAnswer(answer) {{
    if (!engine) return;
    engine.answer(currentQuestionId, answer);
    nextStep();
  }}

  function resolveGuess(correct) {{
    if (correct) {{
      document.getElementById('main-area').innerHTML = '<div class="guess">System victory! Candidate confirmed.</div><button class="btn" onclick="startGame()">Play Again</button>';
      setStatus('Correct guess');
    }} else {{
      if (!engine) return;
      engine.eliminate(engine.topCandidates(1)[0][0].id);
      if (engine.shouldGuess()) {{
        const [e, p] = engine.topCandidates(1)[0];
        showGuess(e, p);
      }} else if (engine.isExhausted()) {{
        const [e, p] = engine.topCandidates(1)[0];
        showGiveUp(e, p);
      }} else {{
        nextStep();
      }}
    }}
  }}

  function submitFeedback(name) {{
    const id = name.toLowerCase().replace(/\\s+/g, '_');
    if (entities[id]) {{
      const target = entities[id];
    }} else {{
      entities[id] = {{ id, name, category: 'crowdsourced', probs: {{}}, aliases: [] }};
    }}
    const target = entities[id];
    for (const [qid, ans] of engine.history) {{
      if (ans === 'yes' || ans === 'probably') {{
        target.probs[qid] = Math.min(1.0, (target.probs[qid] || 0.5) + 0.2);
      }} else if (ans === 'no' || ans === 'probably_not') {{
        target.probs[qid] = Math.max(0.0, (target.probs[qid] || 0.5) - 0.2);
      }}
    }}
    const list = Object.values(entities);
    saveDB(list);
    learnedCount = list.filter(e => e.category === 'crowdsourced').length;
    document.getElementById('stat-learned').textContent = learnedCount;
    document.getElementById('main-area').innerHTML = `<div class="guess">Learned '${{name}}'. Saved locally.</div><button class="btn" onclick="startGame()">Play Again</button>`;
    setStatus('Learned new entity');
  }}

  function nextStep() {{
    if (!engine) return;
    if (engine.shouldGuess()) {{
      const [e, p] = engine.topCandidates(1)[0];
      showGuess(e, p);
      setStatus('Guess');
      return;
    }}
    if (engine.isExhausted()) {{
      const [e, p] = engine.topCandidates(1)[0];
      showGiveUp(e, p);
      setStatus('Gave up');
      return;
    }}
    const q = engine.nextQuestion();
    if (q) {{
      currentQuestionId = q.id;
      showQuestion(q);
      setStatus('Question');
    }} else {{
      const [e, p] = engine.topCandidates(1)[0];
      showGiveUp(e, p);
      setStatus('Gave up');
    }}
  }}

  function exportDB() {{
    const list = Object.values(entities);
    const blob = new Blob([JSON.stringify({{questions: QUESTIONS, entities: list}}, null, 2)], {{type: 'application/json'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'database.json';
    a.click();
    URL.revokeObjectURL(url);
  }}

  function importDB(event) {{
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {{
      try {{
        const data = JSON.parse(e.target.result);
        if (!data.questions || !Array.isArray(data.entities)) throw new Error('Invalid format');
        data.questions.forEach(q => questions[q.id] = q);
        data.entities.forEach(en => entities[en.id] = en);
        saveDB(data.entities);
        document.getElementById('stat-entities').textContent = data.entities.length;
        document.getElementById('stat-questions').textContent = data.questions.length;
        setStatus('Imported database');
        alert('Database imported successfully.');
      }} catch (err) {{
        alert('Import failed: ' + err.message);
      }}
    }};
    reader.readAsText(file);
  }}

  let currentQuestionId = null;

  init();
</script>
</body>
</html>
"""

OUT_PATH.write_text(HTML, encoding="utf-8")
print(f"Wrote static site to {OUT_PATH}")
print(f"Size: {OUT_PATH.stat().st_size / 1024:.1f} KB")
