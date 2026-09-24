import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from scripts.extraer_reddit_twitter import (
    collect_reddit_records,
    collect_twitter_records,
    extract_numbers,
    merge_candidate_records,
    merge_into_database,
    update_sources_log,
    validate_dataset,
)


class ExtraerRedditTwitterTests(unittest.TestCase):
    def test_extract_numbers_returns_unique_mexican_numbers(self):
        text = (
            "Reporte con +525511112233 repetido +525511112233 "
            "y un número inválido +52551111."
        )

        numbers = extract_numbers(text)

        self.assertEqual(numbers, ["+525511112233"])

    def test_merge_candidate_records_combines_sources_and_reports(self):
        merged = merge_candidate_records(
            [
                {
                    "number": "+525511112233",
                    "reports": 1,
                    "tag": "spam",
                    "source": "Reddit",
                },
                {
                    "number": "+525511112233",
                    "reports": 2,
                    "tag": "extorsion",
                    "source": "Twitter",
                },
            ]
        )

        self.assertEqual(
            merged,
            [
                {
                    "number": "+525511112233",
                    "reports": 3,
                    "tag": "extorsion",
                    "source": "Reddit, Twitter",
                }
            ],
        )

    def test_merge_into_database_adds_only_new_numbers_and_updates_metadata(self):
        data = {
            "version": "1.1",
            "updated_at": "2026-09-24",
            "description": "Base de datos colaborativa.",
            "numbers": [
                {
                    "number": "+525500000001",
                    "reports": 1,
                    "tag": "extorsion",
                    "source": "MiraQuienHabla",
                },
                {
                    "number": "+525500000001",
                    "reports": 3,
                    "tag": "fraude",
                    "source": "Twitter",
                }
            ],
        }

        added_records = merge_into_database(
            data,
            [
                {
                    "number": "+525500000001",
                    "reports": 1,
                    "tag": "spam",
                    "source": "Reddit",
                },
                {
                    "number": "+525500000002",
                    "reports": 2,
                    "tag": "fraude",
                    "source": "Twitter",
                },
            ],
        )

        self.assertEqual(len(added_records), 1)
        self.assertEqual(added_records[0]["number"], "+525500000002")
        self.assertEqual(data["version"], "1.2")
        self.assertIn("Reddit", data["description"])
        self.assertIn("Twitter", data["description"])
        self.assertEqual(len(data["numbers"]), 2)
        self.assertEqual(data["numbers"][0]["reports"], 3)
        self.assertEqual(data["numbers"][0]["source"], "MiraQuienHabla, Twitter")

    def test_validate_dataset_rejects_invalid_numbers(self):
        data = {
            "version": "1.1",
            "updated_at": "2026-09-24",
            "description": "Base de datos colaborativa.",
            "numbers": [
                {
                    "number": "+52559776782",
                    "reports": 1,
                    "tag": "extorsion",
                    "source": "MiraQuienHabla",
                }
            ],
        }

        with self.assertRaises(ValidationError):
            validate_dataset(data)

    def test_update_sources_log_appends_new_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "FUENTES.md"
            path.write_text("# Fuentes\n", encoding="utf-8")

            update_sources_log(
                path,
                [
                    {
                        "number": "+525511112233",
                        "reports": 1,
                        "tag": "fraude",
                        "source": "Twitter",
                    }
                ],
                "2026-09-24",
            )

            content = path.read_text(encoding="utf-8")

        self.assertIn("## Registro de Extracciones Automatizadas", content)
        self.assertIn("### 2026-09-24", content)
        self.assertIn("+525511112233", content)

    def test_collect_reddit_records_filters_by_upvotes(self):
        class FakeSubmission:
            def __init__(self, title, selftext, score):
                self.title = title
                self.selftext = selftext
                self.score = score

        class FakeSubreddit:
            def search(self, *_args, **_kwargs):
                return [
                    FakeSubmission("extorsión telefónica +525511112233", "", 6),
                    FakeSubmission("extorsión telefónica +525522223344", "", 5),
                ]

        class FakeRedditClient:
            def subreddit(self, _name):
                return FakeSubreddit()

        records = collect_reddit_records(FakeRedditClient())

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["number"], "+525511112233")
        self.assertEqual(records[0]["source"], "Reddit")

    def test_collect_twitter_records_filters_by_likes(self):
        class FakeTweet:
            def __init__(self, text, like_count):
                self.text = text
                self.public_metrics = {"like_count": like_count}

        class FakeResponse:
            def __init__(self, data):
                self.data = data

        class FakeTwitterClient:
            def search_recent_tweets(self, **_kwargs):
                return FakeResponse(
                    [
                        FakeTweet("fraude México +525511112233", 11),
                        FakeTweet("fraude México +525522223344", 10),
                    ]
                )

        records = collect_twitter_records(FakeTwitterClient())

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["number"], "+525511112233")
        self.assertEqual(records[0]["source"], "Twitter")


if __name__ == "__main__":
    unittest.main()
