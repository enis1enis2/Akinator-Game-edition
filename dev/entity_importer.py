"""
Development helper: bulk import entities from a JSON file into database.json.

Input format (JSON array):
[
  {
    "name": "Character Name",
    "category": "video game",
    "probs": {"q_fictional": 1.0, "q_human": 1.0, ...},
    "aliases": ["alias1", "alias2"],
    "notes": "Optional notes"
  },
  ...
]

Usage:
  python dev/entity_importer.py path/to/entities.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database.json"


def generate_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def import_entities(input_path: Path, dry_run: bool = False):
    with open(input_path, encoding="utf-8") as f:
        new_entities = json.load(f)

    if not isinstance(new_entities, list):
        print("Error: input file must be a JSON array")
        sys.exit(1)

    data = load_db()
    existing_ids = {e["id"] for e in data["entities"]}
    existing_names = {e["name"].lower() for e in data["entities"]}

    added = 0
    skipped = 0

    for ent in new_entities:
        name = ent.get("name", "").strip()
        if not name:
            print(f"[WARN] Skipping entity with empty name: {ent}")
            skipped += 1
            continue

        eid = generate_id(name)
        if eid in existing_ids:
            print(f"[WARN] Skipping duplicate ID: {eid}")
            skipped += 1
            continue

        if name.lower() in existing_names:
            print(f"[WARN] Skipping duplicate name: {name}")
            skipped += 1
            continue

        entity = {
            "id": eid,
            "name": name,
            "category": ent.get("category", "unknown"),
            "aliases": ent.get("aliases", []),
            "notes": ent.get("notes", ""),
            "probs": ent.get("probs", {}),
        }

        if not dry_run:
            data["entities"].append(entity)
            existing_ids.add(eid)
            existing_names.add(name.lower())

        added += 1
        print(f"  [+] {name} (id={eid})")

    if not dry_run:
        save_db(data)
        print(f"\nSaved {added} entities to {DB_PATH}")
    else:
        print(f"\nDry run: would add {added} entities")

    print(f"Skipped: {skipped}")
    return added, skipped


def main():
    if len(sys.argv) < 2:
        print("Usage: python dev/entity_importer.py <input.json> [--dry-run]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    print(f"Importing entities from: {input_path}")
    if dry_run:
        print("(dry run mode)")
    print()

    import_entities(input_path, dry_run=dry_run)


if __name__ == "__main__":
    main()
