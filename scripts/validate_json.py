import json
import sys
from pathlib import Path

from jsonschema import ValidationError, validate


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


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("mexico_spam_db.json")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    try:
        validate(instance=data, schema=SCHEMA)
    except ValidationError as error:
        print(f"❌ Error de validación: {error.message}")
        return 1

    print("✅ El JSON cumple con el formato esperado para OpenCallShield.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
