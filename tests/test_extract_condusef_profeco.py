import tempfile
import unittest
from pathlib import Path

from scripts.extract_condusef_profeco import (
    extract_entries_from_text,
    merge_numbers,
    normalize_phone_number,
    update_sources_log,
    validate_database,
)


class ExtractCondusefProfecoTests(unittest.TestCase):
    def test_normalize_phone_number_variants(self):
        self.assertEqual(normalize_phone_number("55 1234 5678"), "+525512345678")
        self.assertEqual(normalize_phone_number("+52 (55) 1234-5678"), "+525512345678")
        self.assertEqual(normalize_phone_number("5215512345678"), "+525512345678")
        self.assertIsNone(normalize_phone_number("555123456"))

    def test_extract_entries_aggregates_reports_and_tag(self):
        text = (
            "Reporte de extorsión desde el 55 1234 5678. "
            "Otro reporte de fraude menciona al +52 55 1234 5678 nuevamente."
        )

        entries = extract_entries_from_text(text, "CONDUSEF")

        self.assertEqual(entries, [{
            "number": "+525512345678",
            "reports": 2,
            "tag": "extorsion",
            "source": "CONDUSEF",
        }])

    def test_merge_numbers_deduplicates_and_discards_invalid_entries(self):
        existing = [
            {"number": "+525512345678", "reports": 1, "tag": "spam", "source": "MiraQuienHabla"},
            {"number": "+525512345678", "reports": 4, "tag": "fraude", "source": "MiraQuienHabla"},
            {"number": "+52559776782", "reports": 2, "tag": "extorsion", "source": "MiraQuienHabla"},
        ]
        new = [
            {"number": "+52 55 1111 2222", "reports": 3, "tag": "extorsion", "source": "CONDUSEF"},
            {"number": "+525512345678", "reports": 2, "tag": "extorsion", "source": "Profeco"},
        ]

        merged, added = merge_numbers(existing, new)

        self.assertEqual(merged, [
            {
                "number": "+525512345678",
                "reports": 4,
                "tag": "extorsion",
                "source": "MiraQuienHabla, Profeco",
            },
            {
                "number": "+525511112222",
                "reports": 3,
                "tag": "extorsion",
                "source": "CONDUSEF",
            },
        ])
        self.assertEqual(added, [{
            "number": "+525511112222",
            "reports": 3,
            "tag": "extorsion",
            "source": "CONDUSEF",
        }])

    def test_update_sources_log_replaces_marker_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "FUENTES.md"
            path.write_text(
                "# Fuentes\n\n## Registro automatizado CONDUSEF y Profeco\n"
                "<!-- condusef-profeco-log:start -->\n"
                "texto viejo\n"
                "<!-- condusef-profeco-log:end -->\n",
                encoding="utf-8",
            )

            update_sources_log(
                path,
                "2026-09-24",
                [{"number": "+525511112222", "reports": 2, "tag": "fraude", "source": "CONDUSEF"}],
                ["Profeco: acceso fallido"],
            )

            content = path.read_text(encoding="utf-8")
            self.assertIn("2026-09-24 - CONDUSEF y Profeco", content)
            self.assertIn("`+525511112222`", content)
            self.assertIn("Profeco: acceso fallido", content)
            self.assertNotIn("texto viejo", content)

    def test_validate_database_accepts_expected_payload(self):
        validate_database(
            {
                "version": "1.2",
                "updated_at": "2026-09-24",
                "description": "Base de datos",
                "numbers": [
                    {
                        "number": "+525511112222",
                        "reports": 1,
                        "tag": "spam",
                        "source": "Profeco",
                    }
                ],
            }
        )


if __name__ == "__main__":
    unittest.main()
