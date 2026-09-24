from jsonschema import validate

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


def validate_database(payload: dict) -> None:
    validate(instance=payload, schema=SCHEMA)
