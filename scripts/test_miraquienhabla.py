import json
import tempfile
import unittest
from pathlib import Path

from scripts.miraquienhabla import extract_entries_from_html, normalize_number, process_dataset

SAMPLE_HTML = """
<html>
  <body>
    <table>
      <tr>
        <td>+52 55 1234 5678</td>
        <td>3 reportes</td>
        <td>Extorsión telefónica</td>
      </tr>
      <tr>
        <td>5215512349999</td>
        <td>1 reporte</td>
        <td>Fraude bancario</td>
      </tr>
      <tr>
        <td>(55) 1234-5678</td>
        <td>5 reportes</td>
        <td>Extorsión</td>
      </tr>
    </table>
  </body>
</html>
"""


class MiraQuienHablaTests(unittest.TestCase):
    def test_normalize_number(self):
        self.assertEqual(normalize_number("5512345678"), "+525512345678")
        self.assertEqual(normalize_number("5215512345678"), "+525512345678")
        self.assertIsNone(normalize_number("52525668054473"))
        self.assertIsNone(normalize_number("559776782"))

    def test_extract_entries_deduplicates_and_prefers_highest_reports(self):
        extracted = sorted(extract_entries_from_html(SAMPLE_HTML), key=lambda item: item["number"])
        self.assertEqual(
            extracted,
            [
                {
                    "number": "+525512345678",
                    "reports": 5,
                    "tag": "extorsion",
                    "source": "MiraQuienHabla",
                },
                {
                    "number": "+525512349999",
                    "reports": 1,
                    "tag": "fraude",
                    "source": "MiraQuienHabla",
                },
            ],
        )

    def test_process_dataset_filters_one_report_and_cleans_existing_invalid_rows(self):
        initial_db = {
            "version": "1.1",
            "updated_at": "2026-09-24",
            "description": "Base de datos colaborativa de números de extorsión telefónica en México. Fuentes: MiraQuienHabla y reportes públicos.",
            "numbers": [
                {"number": "+525566329867", "reports": 2, "tag": "extorsion", "source": "MiraQuienHabla"},
                {"number": "+525566329867", "reports": 1, "tag": "extorsion", "source": "MiraQuienHabla"},
                {"number": "+52525668054473", "reports": 1, "tag": "extorsion", "source": "MiraQuienHabla"},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "mexico_spam_db.json"
            fuentes_path = Path(tmp_dir) / "FUENTES.md"
            db_path.write_text(json.dumps(initial_db), encoding="utf-8")
            fuentes_path.write_text("# Fuentes\n", encoding="utf-8")

            result = process_dataset(
                db_path=db_path,
                fuentes_path=fuentes_path,
                html=SAMPLE_HTML,
                min_reports=2,
                extraction_date="2026-09-24",
            )

            payload = json.loads(db_path.read_text(encoding="utf-8"))
            self.assertTrue(result["changed"])
            self.assertEqual(payload["version"], "1.2")
            self.assertEqual(len(payload["numbers"]), 2)
            self.assertEqual(payload["numbers"][0]["number"], "+525566329867")
            self.assertEqual(payload["numbers"][1]["number"], "+525512345678")
            self.assertIn("Números añadidos: +525512345678 (5 reportes)", fuentes_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
