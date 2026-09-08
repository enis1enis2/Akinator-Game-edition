"""
Guessly Interactive Web CLI & API Server
Run: python app.py
Access via browser at http://localhost:5000
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from flask import Flask, jsonify, request, render_template
from engine import GuesslyEngine, load_database, save_database, Entity, Question, VALID_ANSWERS

DB_PATH = Path(__file__).parent / "database.json"

app = Flask(__name__)

# Global state / single-session storage
entities, questions = load_database(DB_PATH)
engine = GuesslyEngine(entities, questions)

@app.route("/")
def index():
    return render_template("index.html")

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
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)