"""
Guessly Interactive Web CLI & API Server
Run: python app.py
Access via browser at http://localhost:5000
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string
from engine import GuesslyEngine, load_database, save_database, Entity, Question, VALID_ANSWERS

DB_PATH = Path(__file__).parent / "database.json"

app = Flask(__name__)

# Global state / single-session storage
entities, questions = load_database(DB_PATH)
engine = GuesslyEngine(entities, questions)

# HTML/JS Front-End Template for Web CLI Interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Guessly Engine - Web CLI</title>
    <style>
        body { font-family: monospace; background: #121212; color: #00ff66; padding: 20px; max-width: 800px; margin: auto; }
        .card { border: 1px solid #00ff66; padding: 20px; margin-top: 20px; border-radius: 5px; }
        button { background: #222; color: #00ff66; border: 1px solid #00ff66; padding: 10px 15px; margin: 5px; cursor: pointer; }
        button:hover { background: #00ff66; color: #121212; }
        input { background: #121212; color: #00ff66; border: 1px solid #00ff66; padding: 8px; width: 80%; }
        .bar-bg { background: #333; height: 12px; width: 100%; border-radius: 6px; overflow: hidden; }
        .bar-fill { background: #00ff66; height: 100%; width: 0%; transition: width 0.3s; }
    </style>
</head>
<body>
    <h1>> GUESSLY_DECISION_ENGINE v1.0</h1>
    <hr>

    <div id="game-box" class="card">
        <p id="status">Click "Start New Game" to begin.</p>
        <button onclick="startGame()">Start New Game</button>
    </div>

    <div id="stats-box" class="card" style="display:none;">
        <h3>Live Entropy & Probabilities</h3>
        <div id="top-candidates"></div>
    </div>

    <script>
        let currentQuestionId = null;

        async function startGame() {
            let res = await fetch('/api/reset', { method: 'POST' });
            let data = await res.json();
            document.getElementById('stats-box').style.display = 'block';
            nextStep(data);
        }

        async function submitAnswer(answer) {
            let res = await fetch('/api/answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_id: currentQuestionId, answer: answer })
            });
            let data = await res.json();
            nextStep(data);
        }

        async function resolveGuess(correct) {
            if (correct) {
                document.getElementById('game-box').innerHTML = '<h2>System Victory! Candidate confirmed.</h2><button onclick="startGame()">Play Again</button>';
            } else {
                let res = await fetch('/api/eliminate', { method: 'POST' });
                let data = await res.json();
                if (data.status === 'guess') {
                    showGuess(data.guess, data.confidence);
                } else if (data.status === 'question') {
                    showQuestion(data.question);
                } else {
                    showFeedbackForm();
                }
            }
        }

        function nextStep(data) {
            updateStats(data.top_candidates);
            if (data.status === 'guess') {
                showGuess(data.guess, data.confidence);
            } else if (data.status === 'question') {
                showQuestion(data.question);
            } else {
                showFeedbackForm();
            }
        }

        function showQuestion(q) {
            currentQuestionId = q.id;
            document.getElementById('game-box').innerHTML = `
                <h3>${q.text}</h3>
                <button onclick="submitAnswer('yes')">Yes</button>
                <button onclick="submitAnswer('probably')">Probably</button>
                <button onclick="submitAnswer('dont_know')">Don't Know</button>
                <button onclick="submitAnswer('probably_not')">Probably Not</button>
                <button onclick="submitAnswer('no')">No</button>
            `;
        }

        function showGuess(guess, confidence) {
            document.getElementById('game-box').innerHTML = `
                <h3>Is your character: <u>${guess.name}</u>?</h3>
                <p>Confidence: ${(confidence * 100).toFixed(1)}%</p>
                <button onclick="resolveGuess(true)">Yes, That's Correct!</button>
                <button onclick="resolveGuess(false)">No, Wrong Guess</button>
            `;
        }

        function showFeedbackForm() {
            document.getElementById('game-box').innerHTML = `
                <h3>I give up! Who was your character?</h3>
                <p>Help teach the engine by entering the character name below:</p>
                <input type="text" id="char-name" placeholder="e.g. Master Chief">
                <br><br>
                <button onclick="submitFeedback()">Teach Engine</button>
            `;
        }

        async function submitFeedback() {
            let name = document.getElementById('char-name').value.trim();
            if (!name) return;
            let res = await fetch('/api/learn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            });
            let data = await res.json();
            document.getElementById('game-box').innerHTML = `<p>${data.message}</p><button onclick="startGame()">Play Again</button>`;
        }

        function updateStats(candidates) {
            let html = '';
            candidates.forEach(c => {
                let pct = (c.probability * 100).toFixed(1);
                html += `<div>${c.name}: ${pct}%<div class="bar-bg"><div class="bar-fill" style="width:${pct}%"></div></div></div>`;
            });
            document.getElementById('top-candidates').innerHTML = html;
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/reset", methods=["POST"])
def api_reset():
    engine.reset()
    return get_engine_state()

@app.route("/api/answer", methods=["POST"])
def api_answer():
    data = request.json or {}
    engine.answer(data["question_id"], data["answer"])
    return get_engine_state()

@app.route("/api/eliminate", methods=["POST"])
def api_eliminate():
    top = engine.top_candidates(1)
    if top:
        engine.eliminate(top[0][0].id)
    return get_engine_state()

@app.route("/api/learn", methods=["POST"])
def api_learn():
    """Reinforcement step: Updates or creates an entity based on user feedback."""
    data = request.json or {}
    char_name = data.get("name", "").strip()
    if not char_name:
        return jsonify({"error": "Invalid name"}), 400

    entity_id = char_name.lower().replace(" ", "_")
    
    # Check if entity exists or needs creation
    if entity_id in engine.entities:
        target = engine.entities[entity_id]
    else:
        target = Entity(
            id=entity_id,
            name=char_name,
            category="crowdsourced",
            probs={}
        )
        engine.entities[entity_id] = target

    # Update probabilities based on current session's answered questions
    for qid, ans in engine.history:
        if ans in ("yes", "probably"):
            target.probs[qid] = min(1.0, target.probs.get(qid, 0.5) + 0.2)
        elif ans in ("no", "probably_not"):
            target.probs[qid] = max(0.0, target.probs.get(qid, 0.5) - 0.2)

    # Persist updated engine database to storage
    save_database(DB_PATH, list(engine.entities.values()), engine.questions)
    
    return jsonify({"message": f"Successfully learned/updated parameters for '{char_name}'!"})

def get_engine_state():
    top = engine.top_candidates(3)
    top_data = [{"id": e.id, "name": e.name, "probability": p} for e, p in top]
    
    if engine.should_guess():
        best_entity, confidence = top[0]
        return jsonify({
            "status": "guess",
            "guess": {"id": best_entity.id, "name": best_entity.name},
            "confidence": confidence,
            "top_candidates": top_data
        })
    
    q = engine.next_question()
    if q and not engine.is_exhausted():
        return jsonify({
            "status": "question",
            "question": {"id": q.id, "text": q.text},
            "top_candidates": top_data
        })
    
    return jsonify({
        "status": "give_up",
        "top_candidates": top_data
    })

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)