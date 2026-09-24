#!/usr/bin/env python3
import argparse
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup
from jsonschema import ValidationError, validate

PHONE_CANDIDATE_RE = re.compile(r'(?:\+?52)?(?:[\s().-]*\d){10,12}')
REPORT_RE = re.compile(r'\b(\d{1,4})\b')
VALID_TAGS = {"extorsion", "fraude", "spam"}
SOURCE_PRIORITIES = {
    "condusef": 4,
    "profeco": 4,
    "gobierno de baja california": 3,
    "gobierno de guanajuato": 3,
    "gobierno de aguascalientes": 3,
    "miraquienhabla": 2,
    "reddit": 1,
    "twitter": 1,
}
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
                    "tag": {"type": "string", "enum": sorted(VALID_TAGS)},
                    "source": {"type": "string"},
                },
                "required": ["number", "reports", "tag", "source"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["version", "updated_at", "description", "numbers"],
    "additionalProperties": False,
}


def normalize_phone(raw: object) -> Optional[str]:
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 10:
        return f"+52{digits}"
    if len(digits) == 12 and digits.startswith("52"):
        return f"+{digits}"
    return None



def normalize_tag(raw: object) -> str:
    text = str(raw or "").strip().lower()
    if "fraud" in text or "estafa" in text:
        return "fraude"
    if "spam" in text or "public" in text:
        return "spam"
    return "extorsion"



def infer_tag(text: str) -> str:
    lowered = text.lower()
    if "fraud" in lowered or "estafa" in lowered:
        return "fraude"
    if "spam" in lowered or "public" in lowered:
        return "spam"
    return "extorsion"



def source_priority(source: str) -> int:
    lowered = source.lower()
    for key, priority in SOURCE_PRIORITIES.items():
        if key in lowered:
            return priority
    return 0



def extract_report_count(text: str) -> int:
    reports = []
    for match in REPORT_RE.finditer(text):
        value = int(match.group(1))
        if 1 <= value <= 9999:
            reports.append(value)
    return min(reports) if reports else 1



def split_sources(source_list: str) -> List[str]:
    return [part.strip() for part in str(source_list).split("|") if part.strip()]



def merge_sources(*sources: str) -> str:
    merged = []
    seen = set()
    for source_list in sources:
        for item in split_sources(source_list):
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return " | ".join(merged)



def choose_tag(existing: Dict[str, object], incoming: Dict[str, object]) -> str:
    existing_score = (int(existing["reports"]), source_priority(str(existing["source"])))
    incoming_score = (int(incoming["reports"]), source_priority(str(incoming["source"])))
    return str(incoming["tag"] if incoming_score > existing_score else existing["tag"])



def clean_record(record: Dict[str, object], default_source: Optional[str] = None) -> Optional[Dict[str, object]]:
    number = normalize_phone(record.get("number"))
    if not number:
        logging.warning("Se descartó un número con formato inválido: %s", record.get("number"))
        return None

    reports = int(record.get("reports", 1) or 1)
    if reports < 1:
        reports = 1

    return {
        "number": number,
        "reports": reports,
        "tag": normalize_tag(record.get("tag")),
        "source": str(record.get("source") or default_source or "Fuente desconocida").strip(),
    }



def merge_records(records: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    merged: Dict[str, Dict[str, object]] = {}
    for record in records:
        cleaned = clean_record(record)
        if not cleaned:
            continue
        current = merged.get(cleaned["number"])
        if current is None:
            merged[cleaned["number"]] = cleaned
            continue
        selected_tag = choose_tag(current, cleaned)
        current_sources = set(split_sources(str(current["source"])))
        incoming_sources = set(split_sources(str(cleaned["source"])))
        same_source = bool(current_sources & incoming_sources)
        merged_reports = max(int(current["reports"]), int(cleaned["reports"])) if same_source else int(current["reports"]) + int(cleaned["reports"])
        merged[cleaned["number"]] = {
            "number": cleaned["number"],
            "reports": merged_reports,
            "tag": selected_tag,
            "source": merge_sources(str(current["source"]), str(cleaned["source"])),
        }
    return sorted(merged.values(), key=lambda item: (-int(item["reports"]), item["number"]))



def extract_baja_california(session: requests.Session, min_reports: int, timeout: int) -> List[Dict[str, object]]:
    url = "https://seguridadbc.gob.mx/ExtorsionTelefonica"
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.warning("No fue posible consultar Baja California: %s", exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    collected: List[Dict[str, object]] = []
    seen_numbers = set()

    for element in soup.select("tr, li, article, p, div"):
        text = element.get_text(" ", strip=True)
        if not text:
            continue
        matches = PHONE_CANDIDATE_RE.findall(text)
        if not matches:
            continue
        reports = extract_report_count(text)
        if reports < min_reports:
            continue
        tag = infer_tag(text)
        for match in matches:
            number = normalize_phone(match)
            if not number or number in seen_numbers:
                continue
            seen_numbers.add(number)
            collected.append(
                {
                    "number": number,
                    "reports": reports,
                    "tag": tag,
                    "source": "Gobierno de Baja California",
                }
            )
    logging.info("Baja California: %s números candidatos extraídos.", len(collected))
    return collected



def load_manual_records(path: Path, source: str, min_reports: int) -> List[Dict[str, object]]:
    if not path.exists():
        logging.warning("No se encontró el archivo de consulta manual para %s: %s", source, path)
        return []

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    raw_records = payload.get("numbers", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_records, list):
        raise ValueError(f"El archivo manual de {source} debe contener una lista o una clave 'numbers'.")

    records = []
    for item in raw_records:
        if not isinstance(item, dict):
            continue
        cleaned = clean_record(item, default_source=source)
        if cleaned and int(cleaned["reports"]) >= min_reports:
            cleaned["source"] = source
            records.append(cleaned)
    logging.info("%s: %s números cargados desde consulta manual.", source, len(records))
    return records



def bump_version(version: str) -> str:
    parts = version.split(".")
    if all(part.isdigit() for part in parts):
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    return version



def build_description() -> str:
    return (
        "Base de datos colaborativa de números de extorsión telefónica en México. "
        "Fuentes: MiraQuienHabla, CONDUSEF, Profeco, Gobiernos Estatales, Reddit, Twitter, y reportes públicos."
    )



def validate_dataset(data: Dict[str, object]) -> None:
    validate(instance=data, schema=SCHEMA)
    numbers = [item["number"] for item in data["numbers"]]
    duplicates = [number for number, count in Counter(numbers).items() if count > 1]
    if duplicates:
        raise ValidationError(f"Números duplicados detectados: {', '.join(sorted(duplicates))}")



def update_database(
    db_path: Path,
    output_path: Path,
    guanajuato_manual: Path,
    aguascalientes_manual: Path,
    min_reports: int,
    timeout: int,
) -> Dict[str, object]:
    with db_path.open(encoding="utf-8") as handle:
        current_data = json.load(handle)

    current_numbers = merge_records(current_data.get("numbers", []))

    session = requests.Session()
    session.headers.update({"User-Agent": "spam_mexico-state-gov-agent/1.0"})

    incoming_numbers = []
    incoming_numbers.extend(extract_baja_california(session, min_reports=min_reports, timeout=timeout))
    incoming_numbers.extend(load_manual_records(guanajuato_manual, "Gobierno de Guanajuato", min_reports=min_reports))
    incoming_numbers.extend(load_manual_records(aguascalientes_manual, "Gobierno de Aguascalientes", min_reports=min_reports))

    merged_numbers = merge_records([*current_numbers, *incoming_numbers])
    desired_description = build_description()
    has_changes = current_data.get("numbers", []) != merged_numbers or str(current_data.get("description", "")) != desired_description
    updated_data = {
        "version": bump_version(str(current_data.get("version", "1.0"))) if has_changes else str(current_data.get("version", "1.0")),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d") if has_changes else str(current_data.get("updated_at", "")),
        "description": desired_description if has_changes else str(current_data.get("description", desired_description)),
        "numbers": merged_numbers,
    }
    validate_dataset(updated_data)

    if has_changes or output_path != db_path:
        output_path.write_text(json.dumps(updated_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logging.info("Base actualizada en %s con %s números únicos.", output_path, len(merged_numbers))
    else:
        logging.info("Sin cambios efectivos en la base; no se escribió ningún archivo.")
    return updated_data



def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Extrae y valida números desde gobiernos estatales.")
    parser.add_argument("--db-path", type=Path, default=repo_root / "mexico_spam_db.json")
    parser.add_argument("--output-path", type=Path, default=repo_root / "mexico_spam_db.json")
    parser.add_argument(
        "--guanajuato-manual",
        type=Path,
        default=repo_root / "data" / "manual" / "guanajuato.json",
    )
    parser.add_argument(
        "--aguascalientes-manual",
        type=Path,
        default=repo_root / "data" / "manual" / "aguascalientes.json",
    )
    parser.add_argument("--min-reports", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO), format="%(levelname)s: %(message)s")
    try:
        update_database(
            db_path=args.db_path,
            output_path=args.output_path,
            guanajuato_manual=args.guanajuato_manual,
            aguascalientes_manual=args.aguascalientes_manual,
            min_reports=args.min_reports,
            timeout=args.timeout,
        )
    except ValidationError as exc:
        logging.error("La base resultante no es válida: %s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - safety net for workflow visibility
        logging.exception("Falló la actualización de gobiernos estatales: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
