#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import praw
import tweepy


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "mexico_spam_db.json"
FUENTES_PATH = ROOT / "FUENTES.md"
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?52[\s\-()]*)?(?:\d[\s\-()]*){10}(?!\d)")
VALID_NUMBER_PATTERN = re.compile(r"^\+52\d{10}$")
REDDIT_QUERIES = ("extorsión telefónica", "fraude México", "número sospechoso")
TWITTER_QUERIES = ("#ExtorsiónTelefónica", "#FraudeEnMéxico", "#Estafa")
SOURCE_PRIORITY = {
    "CONDUSEF": 5,
    "Profeco": 4,
    "Gobierno": 4,
    "Policía Cibernética": 4,
    "MiraQuienHabla": 3,
    "Reddit": 2,
    "Twitter": 2,
}
TAG_KEYWORDS = {
    "extorsion": ("extorsión", "extorsion", "secuestro virtual", "cobro por llamada"),
    "fraude": ("fraude", "estafa", "phishing", "engaño"),
    "spam": ("spam", "publicidad", "llamadas no deseadas", "telemarketing"),
}
LOG_HEADER = "## 📒 Registro automatizado Reddit/Twitter"


def normalize_number(candidate: str) -> str | None:
    digits = re.sub(r"\D", "", candidate)
    if len(digits) == 10:
        return f"+52{digits}"
    if len(digits) == 12 and digits.startswith("52"):
        return f"+{digits}"
    return None


def detect_tag(text: str) -> str:
    lowered = text.lower()
    scores = {
        tag: sum(1 for keyword in keywords if keyword in lowered)
        for tag, keywords in TAG_KEYWORDS.items()
    }
    best_tag, best_score = max(scores.items(), key=lambda item: item[1])
    return best_tag if best_score else "fraude"


def source_rank(source: str) -> int:
    for key, rank in SOURCE_PRIORITY.items():
        if key.lower() in source.lower():
            return rank
    return 1


def extract_numbers(text: str) -> set[str]:
    return {
        normalized
        for match in PHONE_PATTERN.findall(text or "")
        if (normalized := normalize_number(match)) and VALID_NUMBER_PATTERN.fullmatch(normalized)
    }


def collect_reddit_mentions() -> list[dict]:
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not all((client_id, client_secret, user_agent)):
        print("ℹ️ Se omite Reddit: faltan credenciales.")
        return []

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    mentions: list[dict] = []
    for subreddit_name in ("mexico", "Scams"):
        subreddit = reddit.subreddit(subreddit_name)
        for query in REDDIT_QUERIES:
            try:
                for submission in subreddit.search(query, limit=25, sort="new"):
                    if submission.score <= 5:
                        continue
                    submission.comments.replace_more(limit=0)
                    combined_text = "\n".join(
                        [
                            submission.title or "",
                            submission.selftext or "",
                            *(
                                comment.body
                                for comment in submission.comments.list()
                                if getattr(comment, "body", None)
                            ),
                        ]
                    )
                    numbers = extract_numbers(combined_text)
                    if not numbers:
                        continue
                    tag = detect_tag(combined_text)
                    mentions.append(
                        {
                            "numbers": numbers,
                            "tag": tag,
                            "source": "Reddit",
                        }
                    )
            except Exception as exc:  # pragma: no cover - API/network dependent
                print(f"⚠️ Error consultando Reddit ({subreddit_name}/{query}): {exc}")
    return mentions


def collect_twitter_mentions() -> list[dict]:
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("ℹ️ Se omite Twitter/X: falta bearer token.")
        return []

    client = tweepy.Client(bearer_token=bearer_token)
    mentions: list[dict] = []
    for query in TWITTER_QUERIES:
        try:
            response = client.search_recent_tweets(
                query=f"{query} -is:retweet lang:es",
                max_results=100,
                tweet_fields=["public_metrics", "created_at", "lang"],
            )
            for tweet in response.data or []:
                metrics = tweet.public_metrics or {}
                if metrics.get("like_count", 0) + metrics.get("retweet_count", 0) <= 10:
                    continue
                numbers = extract_numbers(tweet.text or "")
                if not numbers:
                    continue
                mentions.append(
                    {
                        "numbers": numbers,
                        "tag": detect_tag(tweet.text or ""),
                        "source": "Twitter",
                    }
                )
        except Exception as exc:  # pragma: no cover - API/network dependent
            print(f"⚠️ Error consultando Twitter/X ({query}): {exc}")
    return mentions


def reduce_mentions(mentions: list[dict]) -> list[dict]:
    by_number: dict[str, dict] = {}
    for mention in mentions:
        for number in mention["numbers"]:
            current = by_number.setdefault(
                number,
                {
                    "number": number,
                    "reports": 0,
                    "source": mention["source"],
                    "tag_counts": defaultdict(int),
                    "tag_sources": defaultdict(set),
                },
            )
            current["reports"] += 1
            current["tag_counts"][mention["tag"]] += 1
            current["tag_sources"][mention["tag"]].add(mention["source"])
            if source_rank(mention["source"]) > source_rank(current["source"]):
                current["source"] = mention["source"]

    reduced = []
    for item in by_number.values():
        tag = max(
            item["tag_counts"],
            key=lambda candidate: (
                item["tag_counts"][candidate],
                max(source_rank(source) for source in item["tag_sources"][candidate]),
            ),
        )
        reduced.append(
            {
                "number": item["number"],
                "reports": item["reports"],
                "tag": tag,
                "source": item["source"],
            }
        )
    return reduced


def merge_records(existing: list[dict], new_records: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    merged: dict[str, dict] = {}
    dropped_invalid: list[str] = []

    def absorb(record: dict) -> None:
        current = merged.setdefault(
            record["number"],
            {
                "number": record["number"],
                "reports": 0,
                "source": record["source"],
                "tag_counts": defaultdict(int),
                "tag_sources": defaultdict(set),
            },
        )
        current["reports"] += int(record["reports"])
        current["tag_counts"][record["tag"]] += int(record["reports"])
        current["tag_sources"][record["tag"]].add(record["source"])
        if source_rank(record["source"]) > source_rank(current["source"]):
            current["source"] = record["source"]

    for record in existing:
        normalized = normalize_number(record["number"])
        if not normalized or not VALID_NUMBER_PATTERN.fullmatch(normalized):
            dropped_invalid.append(record["number"])
            continue
        absorb(
            {
                "number": normalized,
                "reports": int(record["reports"]),
                "tag": record["tag"],
                "source": record["source"],
            }
        )

    additions: list[dict] = []
    for record in new_records:
        if record["number"] not in merged:
            additions.append(deepcopy(record))
        absorb(record)

    consolidated = []
    for item in merged.values():
        tag = max(
            item["tag_counts"],
            key=lambda candidate: (
                item["tag_counts"][candidate],
                max(source_rank(source) for source in item["tag_sources"][candidate]),
            ),
        )
        consolidated.append(
            {
                "number": item["number"],
                "reports": item["reports"],
                "tag": tag,
                "source": item["source"],
            }
        )

    return consolidated, additions, dropped_invalid


def write_database(data: dict) -> None:
    lines = [
        "{",
        f'  "version": {json.dumps(data["version"], ensure_ascii=False)},',
        f'  "updated_at": {json.dumps(data["updated_at"], ensure_ascii=False)},',
        f'  "description": {json.dumps(data["description"], ensure_ascii=False)},',
        '  "numbers": [',
    ]

    numbers = data["numbers"]
    for index, item in enumerate(numbers):
        suffix = "," if index < len(numbers) - 1 else ""
        lines.append(f"    {json.dumps(item, ensure_ascii=False)}{suffix}")

    lines.extend(["  ]", "}"])
    DB_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_log_entries(additions: list[dict], extraction_date: str) -> None:
    if not additions:
        return

    content = FUENTES_PATH.read_text(encoding="utf-8")
    if LOG_HEADER not in content:
        content = (
            f"{content.rstrip()}\n\n---\n\n{LOG_HEADER}\n\n"
            "Este registro resume los números añadidos por la extracción automatizada diaria "
            "desde Reddit y Twitter/X.\n"
        )

    entry_lines = [
        f"### {extraction_date}",
        *[
            f"- `{item['number']}` | Fuente: {item['source']} | Etiqueta: {item['tag']} | Reportes nuevos: {item['reports']}"
            for item in additions
        ],
    ]
    block = "\n".join(entry_lines)
    if block not in content:
        content = f"{content.rstrip()}\n\n{block}\n"
        FUENTES_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    mentions = collect_reddit_mentions() + collect_twitter_mentions()
    extracted_records = reduce_mentions(mentions)
    consolidated, additions, dropped_invalid = merge_records(data["numbers"], extracted_records)

    if dropped_invalid:
        print(f"⚠️ Números descartados por formato inválido: {', '.join(sorted(set(dropped_invalid)))}")

    data["numbers"] = consolidated
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data["version"] = "1.2"
    data["description"] = (
        "Base de datos colaborativa de números de extorsión telefónica en México. "
        "Fuentes: MiraQuienHabla, CONDUSEF, Profeco, Reddit, Twitter/X y reportes públicos."
    )

    write_database(data)
    append_log_entries(additions, data["updated_at"])

    print(f"✅ Números nuevos agregados: {len(additions)}")
    if additions:
        for item in additions:
            print(f"  - {item['number']} ({item['source']}, {item['tag']}, {item['reports']} reportes)")


if __name__ == "__main__":
    main()
