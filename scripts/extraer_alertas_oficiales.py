#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrae números telefónicos asociados a extorsión/fraude desde fuentes
oficiales y públicas de acceso abierto:

  1. bc       — Gobierno de Baja California, "Teléfonos más denunciados"
                https://seguridadbc.gob.mx/ExtorsionTelefonica/index.php
  2. condusef — CONDUSEF: portal de números sospechosos y comunicados de
                prensa (incluye PDFs recientes).
  3. gobmx    — Artículos/alertas de Profeco, SSPC (Policía Cibernética)
                y CONDUSEF publicados en gob.mx.

Cada fuente es *best-effort*: si una falla se registra el error y se
continúa con las demás. Los números nuevos se fusionan en
`mexico_spam_db.json` (sin duplicados) y el resultado se valida contra
el esquema de OpenCallShield.

Filtros anti falsos positivos:
  - Solo se aceptan números con 10 dígitos nacionales (o +52 + 10).
  - Se excluyen líneas 01-800 / 900 (números de atención oficial).
  - Se excluyen números con todos los dígitos iguales (ruido).
  - El número debe aparecer cerca de palabras clave de contexto
    (extorsión, fraude, llamada, teléfono, denuncia, etc.).

Uso:
    python3 scripts/extraer_alertas_oficiales.py [--fuentes bc condusef gobmx]
"""

import argparse
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

DB_PATH = Path(__file__).resolve().parent.parent / "mexico_spam_db.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
        "spam-mexico-extractor/1.0"
    )
}
TIMEOUT = 20
VENTANA = 150  # caracteres de contexto alrededor de cada número

KEYWORDS = re.compile(
    r"extorsi|fraude|enga[nñ]o|estaf|llamad|tel[eé]fon|celular|"
    r"denunci|report|vishing|suplantaci",
    re.IGNORECASE,
)

# Secuencia de dígitos con separadores opcionales (espacios, guiones, puntos).
CANDIDATO_RE = re.compile(r"\+?\d[\d\s\-.()]{7,16}\d"
)

# Prefijos nacionales que NUNCA se marcan como spam (líneas oficiales).
EXCLUIR_PREFIJOS = ("800", "900")

# ---------------------------------------------------------------- Utilidades

def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def html_a_texto(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser").get_text(" ")
    except ImportError:
        return re.sub(r"<[^>]+>", " ", html)


def normalizar(candidato: str):
    """Convierte un candidato en +52XXXXXXXXXX o None si no es válido."""
    digitos = re.sub(r"\D", "", candidato)
    if len(digitos) == 12 and digitos.startswith("52"):
        nacional = digitos[2:]
    elif len(digitos) == 10:
        nacional = digitos
    else:
        return None
    if nacional[0] not in "2345678":
        return None
    if nacional.startswith(EXCLUIR_PREFIJOS):
        return None
    if len(set(nacional)) == 1:
        return None
    return "+52" + nacional


def extraer_numeros(texto: str):
    """Devuelve el conjunto de números válidos con contexto de fraude."""
    encontrados = set()
    for m in CANDIDATO_RE.finditer(texto):
        ini, fin = max(0, m.start() - VENTANA), min(len(texto), m.end() + VENTANA)
        if not KEYWORDS.search(texto[ini:fin]):
            continue
        numero = normalizar(m.group())
        if numero:
            encontrados.add(numero)
    return encontrados

# ------------------------------------------------------------------ Fuentes

URL_BC = "https://seguridadbc.gob.mx/ExtorsionTelefonica/index.php"

def fuente_bc():
    """Teléfonos más denunciados en Baja California (página dedicada)."""
    texto = html_a_texto(fetch(URL_BC))
    return {n: "Gobierno de Baja California" for n in extraer_numeros(texto)}


URLS_CONDUSEF = [
    "https://www.condusef.gob.mx/?p=contenido&idc=2828&idcat=1",
    "https://www.condusef.gob.mx/documentos/prensa/",
]

def _pdfs_en(html: str, base_url: str):
    from urllib.parse import urljoin
    enlaces = re.findall(r'href=["\']([^"\']+\.pdf)["\']', html, re.IGNORECASE)
    return [urljoin(base_url, h) for h in enlaces]

def _texto_de_pdf(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    from PyPDF2 import PdfReader
    lector = PdfReader(io.BytesIO(r.content))
    return "\n".join((p.extract_text() or "") for p in lector.pages)

def fuente_condusef():
    """Portal de números sospechosos y comunicados de CONDUSEF (con PDFs)."""
    resultados = {}
    for url in URLS_CONDUSEF:
        html = fetch(url)
        for n in extraer_numeros(html_a_texto(html)):
            resultados.setdefault(n, "CONDUSEF")
        for pdf_url in _pdfs_en(html, url)[:10]:
            try:
                for n in extraer_numeros(_texto_de_pdf(pdf_url)):
                    resultados.setdefault(n, "CONDUSEF")
            except Exception as e:
                print(f"  ⚠️ PDF omitido ({pdf_url}): {e}")
    return resultados


URLS_GOBMX = [
    "https://www.gob.mx/profeco/es/articulos",
    "https://www.gob.mx/sspc/es/articulos",
    "https://www.gob.mx/condusef/es/articulos",
]

def fuente_gobmx():
    """Artículos y alertas de Profeco / SSPC / CONDUSEF en gob.mx."""
    resultados = {}
    for url in URLS_GOBMX:
        texto = html_a_texto(fetch(url))
        for n in extraer_numeros(texto):
            resultados.setdefault(n, "Alertas gob.mx (Profeco/SSPC)")
    return resultados

# ---------------------------------------------------------------- Principal

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
                    "number": {"type": "string", "pattern": r
"^\+52\d{10}$"},
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


def validar(data: dict) -> None:
    try:
        from jsonschema import validate as schema_validate, ValidationError
    except ImportError:
        print("ℹ️ jsonschema no disponible; se omite la validación.")
        return
    try:
        schema_validate(instance=data, schema=SCHEMA)
        print("✅ JSON válido según el esquema de OpenCallShield.")
    except ValidationError as e:
        print(f"❌ JSON inválido: {e.message}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fuentes", nargs="*", default=["bc", "condusef", "gobmx"],
        choices=["bc", "condusef", "gobmx"],
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ No se encontró {DB_PATH}")
        sys.exit(1)

    with open(DB_PATH, encoding="utf-8") as f:
        data = json.load(f)

    extractores = {
        "bc": fuente_bc,
        "condusef": fuente_condusef,
        "gobmx": fuente_gobmx,
    }
    nuevos = {}
    for clave in args.fuentes:
        try:
            hallazgos = extractores[clave]()
            print(f"✅ [{clave}] {len(hallazgos)} números detectados.")
            for numero, fuente in hallazgos.items():
                nuevos.setdefault(numero, fuente)
        except Exception as e:
            print(f"⚠️ [{clave}] Falló la extracción: {e}")

    existentes = {e["number"] for e in data.get("numbers", [])}
    por_agregar = [
        {"number": n, "reports": 1, "tag": "extorsion", "source": f}
        for n, f in sorted(nuevos.items())
        if n not in existentes
    ]

    if por_agregar:
      
  data["numbers"].extend(por_agregar)
        try:
            version = float(data.get("version", "1.0"))
        except (TypeError, ValueError):
            version = 1.0
        data["version"] = str(round(version + 0.1, 1))
        data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data["description"] = (
            "Base de datos colaborativa de números de extorsión telefónica en México. "
            "Fuentes: MiraQuienHabla, CONDUSEF, Profeco, gobiernos estatales y "
            "alertas oficiales públicas."
        )
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"➕ {len(por_agregar)} números nuevos agregados:")
        for e in por_agregar:
            print(f"   - {e['number']} ({e['source']})")
    else:
        print("ℹ️ Sin números nuevos que agregar.")

    validar(data)


if __name__ == "__main__":
    main()
