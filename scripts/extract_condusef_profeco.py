from __future__ import annotations

import json
import logging
import re
from collections import OrderedDict
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from jsonschema import ValidationError, validate

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "mexico_spam_db.json"
SOURCES_DOC_PATH = ROOT / "FUENTES.md"
PHONE_PATTERN = re.compile(r"(?:\+?52[\s().-]*)?(?:\d[\s().-]*){10,12}")
LOG_START = "<!-- condusef-profeco-log:start -->"
LOG_END = "<!-- condusef-profeco-log:end -->"
TAG_PRIORITY = {"extorsion": 3, "fraude": 2, "spam": 1}
JSON_SCHEMA = {
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
SOURCES = (
    {
        "name": "CONDUSEF",
        "url": "https://www.condusef.gob.mx/?p=contenido&idc=2828&idcat=1",
    },
    {
        "name": "Profeco",
        "url": "https://repep.profeco.gob.mx/Denunciar.jsp",
    },
)
DESCRIPTION = (
    "Base de datos colaborativa de números de extorsión telefónica en México. "
    "Fuentes: MiraQuienHabla, CONDUSEF, Profeco y otros reportes públicos verificados."
)

logger = logging.getLogger("extract_condusef_profeco")


def normalize_phone_number(raw_number: str) -> str | None:
    digits = re.sub(r"\D", "", raw_number)
    if digits.startswith("521") and len(digits) == 13:
        digits = f"52{digits[3:]}"
    elif len(digits) == 10:
        digits = f"52{digits}"
    if len(digits) == 12 and digits.startswith("52"):
        return f"+{digits}"
    return None


def choose_tag(*tags: str) -> str:
    cleaned_tags = [tag.strip().lower() for tag in tags if tag and tag.strip()]
    if not cleaned_tags:
        return "spam"
    return max(cleaned_tags, key=lambda tag: TAG_PRIORITY.get(tag, 0))


def infer_tag(context: str) -> str:
    text = context.lower()
    if any(keyword in text for keyword in ("extorsi", "secuestro", "amenaza")):
        return "extorsion"
    if any(keyword in text for keyword in ("fraude", "estafa", "banco", "phishing")):
        return "fraude"
    return "spam"


def combine_sources(existing_source: str, new_source: str) -> str:
    sources = []
    for value in (existing_source, new_source):
        for source in value.split(","):
            source = source.strip()
            if source and source not in sources:
                sources.append(source)
    return ", ".join(sources)


def merge_record(existing: dict, incoming: dict) -> dict:
    return {
        "number": existing["number"],
        "reports": max(int(existing["reports"]), int(incoming["reports"])),
        "tag": choose_tag(existing.get("tag", "spam"), incoming.get("tag", "spam")),
        "source": combine_sources(existing.get("source", ""), incoming.get("source", "")),
    }


def sanitize_numbers(numbers: Iterable[dict]) -> list[dict]:
    sanitized: OrderedDict[str, dict] = OrderedDict()
    for entry in numbers:
        normalized = normalize_phone_number(str(entry.get("number", "")))
        if not normalized:
            logger.warning("Número descartado por formato inválido: %s", entry.get("number", ""))
            continue
        cleaned = {
            "number": normalized,
            "reports": max(int(entry.get("reports", 1)), 1),
            "tag": choose_tag(str(entry.get("tag", "spam"))),
            "source": str(entry.get("source", "desconocido")).strip() or "desconocido",
        }
        if normalized in sanitized:
            sanitized[normalized] = merge_record(sanitized[normalized], cleaned)
        else:
            sanitized[normalized] = cleaned
    return list(sanitized.values())


def extract_entries_from_text(text: str, source: str) -> list[dict]:
    extracted: OrderedDict[str, dict] = OrderedDict()
    for match in PHONE_PATTERN.finditer(text):
        normalized = normalize_phone_number(match.group())
        if not normalized:
            continue
        context = text[max(0, match.start() - 80): match.end() + 80]
        record = {
            "number": normalized,
            "reports": 1,
            "tag": infer_tag(context),
            "source": source,
        }
        if normalized in extracted:
            current = extracted[normalized]
            current["reports"] += 1
            current["tag"] = choose_tag(current["tag"], record["tag"])
        else:
            extracted[normalized] = record
    return list(extracted.values())


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def discover_pdf_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if ".pdf" not in href.lower():
            continue
        absolute_url = urljoin(base_url, href)
        if absolute_url not in urls:
            urls.append(absolute_url)
    return urls


def fetch_response(session: requests.Session, url: str) -> requests.Response | None:
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        logger.warning("No se pudo acceder a %s: %s", url, exc)
        return None


def extract_source_numbers(session: requests.Session, name: str, url: str) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    response = fetch_response(session, url)
    if response is None:
        return [], [f"{name}: no fue posible acceder a {url}"]

    extracted = extract_entries_from_text(response.text, name)
    for pdf_url in discover_pdf_links(response.text, url):
        pdf_response = fetch_response(session, pdf_url)
        if pdf_response is None:
            errors.append(f"{name}: no fue posible descargar el PDF {pdf_url}")
            continue
        try:
            pdf_text = extract_pdf_text(pdf_response.content)
        except Exception as exc:
            logger.warning("No se pudo leer el PDF %s: %s", pdf_url, exc)
            errors.append(f"{name}: no fue posible leer el PDF {pdf_url}")
            continue
        extracted.extend(extract_entries_from_text(pdf_text, name))

    return sanitize_numbers(extracted), errors


def merge_numbers(existing_numbers: Iterable[dict], new_numbers: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    merged: OrderedDict[str, dict] = OrderedDict(
        (entry["number"], entry) for entry in sanitize_numbers(existing_numbers)
    )
    added: list[dict] = []
    for entry in sanitize_numbers(new_numbers):
        number = entry["number"]
        if number in merged:
            merged[number] = merge_record(merged[number], entry)
            continue
        merged[number] = entry
        added.append(entry)
    return list(merged.values()), added


def bump_version(version: str) -> str:
    parts = [int(part) for part in version.split(".") if part.isdigit()]
    if not parts:
        return "1.0"
    if len(parts) == 1:
        return f"{parts[0] + 1}.0"
    head = parts[:-1]
    tail = parts[-1] + 1
    return ".".join(str(part) for part in [*head, tail])


def validate_database(payload: dict) -> None:
    validate(instance=payload, schema=JSON_SCHEMA)


def load_database(path: Path = DB_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def format_database(payload: dict) -> str:
    lines = [
        "{",
        f'  "version": {json.dumps(payload["version"], ensure_ascii=False)},',
        f'  "updated_at": {json.dumps(payload["updated_at"], ensure_ascii=False)},',
        f'  "description": {json.dumps(payload["description"], ensure_ascii=False)},',
        '  "numbers": [',
    ]
    entries = payload.get("numbers", [])
    for index, entry in enumerate(entries):
        suffix = "," if index < len(entries) - 1 else ""
        lines.append(f"    {json.dumps(entry, ensure_ascii=False)}{suffix}")
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


def save_database(payload: dict, path: Path = DB_PATH) -> None:
    path.write_text(format_database(payload), encoding="utf-8")


def update_sources_log(
    path: Path,
    extracted_at: str,
    added_numbers: list[dict],
    errors: list[str],
) -> None:
    content = path.read_text(encoding="utf-8")
    numbers_block = [f"### {extracted_at} - CONDUSEF y Profeco"]
    if added_numbers:
        numbers_block.append("- Números añadidos:")
        for entry in added_numbers:
            numbers_block.append(
                f"  - `{entry['number']}` · reportes={entry['reports']} · etiqueta={entry['tag']} · fuente={entry['source']}"
            )
    else:
        numbers_block.append("- Números añadidos: ninguno")
    if errors:
        numbers_block.append("- Incidencias:")
        for error in errors:
            numbers_block.append(f"  - {error}")
    else:
        numbers_block.append("- Incidencias: ninguna")
    replacement = f"{LOG_START}\n" + "\n".join(numbers_block) + f"\n{LOG_END}"
    if LOG_START in content and LOG_END in content:
        updated = re.sub(
            rf"{re.escape(LOG_START)}.*?{re.escape(LOG_END)}",
            replacement,
            content,
            flags=re.DOTALL,
        )
    else:
        updated = content.rstrip() + (
            "\n\n## Registro automatizado CONDUSEF y Profeco\n"
            f"{replacement}\n"
        )
    path.write_text(updated, encoding="utf-8")


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; spam_mexico/1.0; +https://github.com/xolotlsoft/spam_mexico)"
            )
        }
    )
    return session


def run() -> int:
    payload = load_database()
    current_numbers = payload.get("numbers", [])
    existing_clean = sanitize_numbers(current_numbers)

    session = build_session()
    extracted_numbers: list[dict] = []
    errors: list[str] = []
    for source in SOURCES:
        source_numbers, source_errors = extract_source_numbers(session, source["name"], source["url"])
        extracted_numbers.extend(source_numbers)
        errors.extend(source_errors)

    merged_numbers, added_numbers = merge_numbers(existing_clean, extracted_numbers)
    payload["numbers"] = merged_numbers
    database_changed = current_numbers != merged_numbers or payload.get("description") != DESCRIPTION
    if database_changed:
        payload["version"] = bump_version(str(payload.get("version", "1.0")))
        payload["updated_at"] = date.today().isoformat()
    payload["description"] = DESCRIPTION

    validate_database(payload)
    save_database(payload)
    update_sources_log(SOURCES_DOC_PATH, payload["updated_at"], added_numbers, errors)

    logger.info("Números existentes normalizados: %s -> %s", len(current_numbers), len(existing_clean))
    logger.info("Números nuevos agregados: %s", len(added_numbers))
    if errors:
        logger.warning("La extracción terminó con incidencias: %s", "; ".join(errors))
    return len(added_numbers)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        added_count = run()
    except ValidationError as exc:
        logger.error("El JSON generado no cumple con el schema: %s", exc.message)
        raise SystemExit(1) from exc
    except Exception as exc:
        logger.exception("Fallo inesperado durante la extracción: %s", exc)
        raise SystemExit(1) from exc
    logger.info("Proceso completado. Nuevos números agregados: %s", added_count)
