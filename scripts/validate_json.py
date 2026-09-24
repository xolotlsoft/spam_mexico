#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from jsonschema import ValidationError, validate


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "mexico_spam_db.json"
PHONE_PATTERN = re.compile(r"^\+52\d{10}$")

SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "updated_at": {"type": "string"},
        "description": {"type": "string"},
        "numbers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "string", "pattern": r"^\+52\d{10}$"},
                    "reports": {"type": "integer", "minimum": 1},
                    "tag": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["number", "reports", "tag", "source"],
            },
        },
    },
    "required": ["version", "updated_at", "description", "numbers"],
}


def main() -> None:
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))

    validate(instance=data, schema=SCHEMA)

    try:
        datetime.strptime(data["updated_at"], "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("updated_at debe usar el formato YYYY-MM-DD") from exc

    numbers = [entry["number"] for entry in data["numbers"]]
    invalid = [number for number in numbers if not PHONE_PATTERN.fullmatch(number)]
    if invalid:
        raise ValidationError(f"Números con formato inválido: {', '.join(invalid)}")

    duplicates = [number for number, count in Counter(numbers).items() if count > 1]
    if duplicates:
        raise ValidationError(f"Números duplicados: {', '.join(sorted(duplicates))}")

    print(f"✅ JSON válido. Registros: {len(numbers)}")


if __name__ == "__main__":
    main()
