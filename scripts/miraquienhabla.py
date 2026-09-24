import argparse
import json
import logging
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import requests
from bs4 import BeautifulSoup
from jsonschema import ValidationError

try:
    from scripts.schema import validate_database
except ModuleNotFoundError:  # pragma: no cover - fallback for direct script execution
    from schema import validate_database

LOGGER = logging.getLogger("miraquienhabla")
DEFAULT_URL = "https://miraquienhabla.com.mx/reportes"
SOURCE_NAME = "MiraQuienHabla"
PHONE_CANDIDATE_RE = re.compile(r"(?:\+?52(?:1)?[\s\-\(\)]*)?(?:\d[\s\-\(\)]*){10}")
BLOCKING_KEYWORDS = (
    "captcha",
    "cloudflare",
    "access denied",
    "forbidden",
    "attention required",
    "blocked",
)

class ScrapingBlockedError(RuntimeError):
    """Raised when the source site blocks automated access."""


class ExtractionError(RuntimeError):
    """Raised when data extraction cannot continue safely."""



def normalize_number(raw_value: str) -> Optional[str]:
    digits = re.sub(r"\D", "", raw_value or "")
    if len(digits) == 10:
        return f"+52{digits}"
    if len(digits) == 12 and digits.startswith("52"):
        return f"+{digits}"
    if len(digits) == 13 and digits.startswith("521"):
        return f"+52{digits[3:]}"
    return None



def infer_tag(text: str) -> str:
    lowered = text.lower()
    if "extorsi" in lowered:
        return "extorsion"
    if any(keyword in lowered for keyword in ("fraude", "estafa", "scam")):
        return "fraude"
    return "spam"



def extract_report_count(text: str) -> int:
    matches = re.findall(r"(\d+)\s*(?:reportes?|denuncias?)", text, flags=re.IGNORECASE)
    if matches:
        return max(int(match) for match in matches)
    return 1



def detect_blocking(html: str, status_code: int) -> None:
    lowered = html.lower()
    if status_code in {403, 429} or any(keyword in lowered for keyword in BLOCKING_KEYWORDS):
        raise ScrapingBlockedError(
            f"El acceso a {DEFAULT_URL} parece estar bloqueado (status={status_code})."
        )



def fetch_html(url: str, timeout: int) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"
            )
        },
    )
    detect_blocking(response.text, response.status_code)
    response.raise_for_status()
    return response.text



def iter_candidate_blocks(soup: BeautifulSoup) -> Iterable[str]:
    seen = set()
    for node in soup.find_all(string=lambda value: value and PHONE_CANDIDATE_RE.search(value)):
        element = node.parent
        selected_text = None
        while element is not None:
            text = " ".join(element.stripped_strings)
            if 10 <= len(text) <= 500 and PHONE_CANDIDATE_RE.search(text):
                selected_text = text
                if re.search(r"reportes?|denuncias?|extorsi|fraude|spam", text, flags=re.IGNORECASE):
                    break
            if len(text) > 500:
                break
            element = element.parent
        if selected_text and selected_text not in seen:
            seen.add(selected_text)
            yield selected_text



def extract_entries_from_html(html: str, source: str = SOURCE_NAME) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    extracted: dict[str, dict] = {}

    for block_text in iter_candidate_blocks(soup):
        reports = extract_report_count(block_text)
        tag = infer_tag(block_text)
        for match in PHONE_CANDIDATE_RE.finditer(block_text):
            number = normalize_number(match.group(0))
            if not number:
                continue
            candidate = {
                "number": number,
                "reports": reports,
                "tag": tag,
                "source": source,
            }
            previous = extracted.get(number)
            if previous is None or candidate["reports"] > previous["reports"]:
                extracted[number] = candidate

    return list(extracted.values())



def clean_numbers(entries: Iterable[dict], min_reports: int = 1) -> tuple[list[dict], list[dict]]:
    cleaned: list[dict] = []
    rejected: list[dict] = []
    positions: dict[str, int] = {}

    for entry in entries:
        normalized = normalize_number(entry.get("number", ""))
        reports = entry.get("reports", 1)
        tag = str(entry.get("tag", "spam")).strip() or "spam"
        source = str(entry.get("source", SOURCE_NAME)).strip() or SOURCE_NAME

        if not normalized or not isinstance(reports, int) or reports < min_reports:
            rejected.append(entry)
            continue

        cleaned_entry = {
            "number": normalized,
            "reports": reports,
            "tag": tag,
            "source": source,
        }

        index = positions.get(normalized)
        if index is None:
            positions[normalized] = len(cleaned)
            cleaned.append(cleaned_entry)
            continue

        rejected.append(entry)
        if cleaned_entry["reports"] > cleaned[index]["reports"]:
            cleaned[index]["reports"] = cleaned_entry["reports"]
        if cleaned[index]["tag"] == "spam" and cleaned_entry["tag"] != "spam":
            cleaned[index]["tag"] = cleaned_entry["tag"]

    return cleaned, rejected



def merge_numbers(existing_numbers: list[dict], extracted_numbers: list[dict], min_reports: int = 2) -> tuple[list[dict], list[dict], list[dict]]:
    cleaned_existing, rejected_existing = clean_numbers(existing_numbers, min_reports=1)
    cleaned_extracted, _ = clean_numbers(extracted_numbers, min_reports=min_reports)

    merged = deepcopy(cleaned_existing)
    positions = {entry["number"]: index for index, entry in enumerate(merged)}
    added_numbers: list[dict] = []

    for entry in cleaned_extracted:
        index = positions.get(entry["number"])
        if index is None:
            positions[entry["number"]] = len(merged)
            merged.append(entry)
            added_numbers.append(entry)
            continue

        current = merged[index]
        if entry["reports"] > current["reports"]:
            current["reports"] = entry["reports"]
        if current["tag"] == "spam" and entry["tag"] != "spam":
            current["tag"] = entry["tag"]

    return merged, added_numbers, rejected_existing



def bump_version(version: str) -> str:
    parts = version.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return version
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)



def build_description(description: str) -> str:
    if SOURCE_NAME.lower() in description.lower():
        return description
    if description.endswith("."):
        return f"{description[:-1]}, {SOURCE_NAME}, y reportes públicos."
    return f"{description} Fuentes: {SOURCE_NAME}."



def append_fuentes_log(path: Path, extraction_date: str, added_numbers: list[dict], rejected_existing: list[dict]) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    section_header = "## Registro de Extracciones Automatizadas"
    if section_header not in current:
        current = current.rstrip() + f"\n\n---\n\n{section_header}\n"

    lines = [f"\n### {extraction_date} — {SOURCE_NAME}"]
    if added_numbers:
        lines.append(f"- Fuente: {SOURCE_NAME}")
        lines.append(
            "- Números añadidos: "
            + ", ".join(f"{entry['number']} ({entry['reports']} reportes)" for entry in added_numbers)
        )
    else:
        lines.append(f"- Fuente: {SOURCE_NAME}")
        lines.append("- Números añadidos: ninguno")
    if rejected_existing:
        lines.append(
            f"- Limpieza de integridad: se descartaron {len(rejected_existing)} registro(s) inválido(s) o duplicado(s) de la base existente."
        )

    updated = current.rstrip() + "\n" + "\n".join(lines) + "\n"
    path.write_text(updated, encoding="utf-8")



def process_dataset(
    db_path: Path,
    fuentes_path: Path,
    html: str,
    min_reports: int = 2,
    extraction_date: Optional[str] = None,
    update_fuentes: bool = True,
) -> dict:
    extraction_date = extraction_date or date.today().isoformat()
    data = json.loads(db_path.read_text(encoding="utf-8"))
    extracted_numbers = extract_entries_from_html(html)
    if not extracted_numbers:
        raise ExtractionError("No se pudieron extraer números de la página; revisa si cambió el HTML.")

    merged_numbers, added_numbers, rejected_existing = merge_numbers(
        data.get("numbers", []),
        extracted_numbers,
        min_reports=min_reports,
    )

    changed = merged_numbers != data.get("numbers", []) or bool(added_numbers) or bool(rejected_existing)
    updated_payload = {
        "version": bump_version(data.get("version", "1.0")) if changed else data.get("version", "1.0"),
        "updated_at": extraction_date if changed else data.get("updated_at", extraction_date),
        "description": build_description(data.get("description", "")),
        "numbers": merged_numbers,
    }

    validate_database(updated_payload)
    db_path.write_text(json.dumps(updated_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if update_fuentes and changed:
        append_fuentes_log(fuentes_path, extraction_date, added_numbers, rejected_existing)

    LOGGER.info(
        "Extracción completada: %s candidatos, %s añadidos, %s descartados del histórico.",
        len(extracted_numbers),
        len(added_numbers),
        len(rejected_existing),
    )
    return {
        "extracted": extracted_numbers,
        "added": added_numbers,
        "rejected_existing": rejected_existing,
        "changed": changed,
        "payload": updated_payload,
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrae números de MiraQuienHabla y actualiza mexico_spam_db.json")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--db-path", default="mexico_spam_db.json")
    parser.add_argument("--fuentes-path", default="FUENTES.md")
    parser.add_argument("--html-file", help="Archivo HTML local para pruebas o depuración")
    parser.add_argument("--min-reports", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--no-update-fuentes", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s: %(message)s")

    try:
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
        else:
            html = fetch_html(args.url, timeout=args.timeout)

        process_dataset(
            db_path=Path(args.db_path),
            fuentes_path=Path(args.fuentes_path),
            html=html,
            min_reports=args.min_reports,
            extraction_date=args.date,
            update_fuentes=not args.no_update_fuentes,
        )
        return 0
    except ScrapingBlockedError as error:
        LOGGER.error("Acceso bloqueado o protegido por CAPTCHA: %s", error)
    except (requests.RequestException, ExtractionError, ValidationError, json.JSONDecodeError) as error:
        LOGGER.error("No fue posible actualizar la base de datos: %s", error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
