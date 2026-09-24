import json
import sys
from pathlib import Path

from jsonschema import ValidationError

try:
    from scripts.schema import validate_database
except ModuleNotFoundError:  # pragma: no cover - fallback for direct script execution
    from schema import validate_database


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "mexico_spam_db.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_database(payload)
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo: {path}")
        return 1
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"❌ Error de validación: {error}")
        return 1

    print("✅ El JSON cumple con el formato esperado para OpenCallShield.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
