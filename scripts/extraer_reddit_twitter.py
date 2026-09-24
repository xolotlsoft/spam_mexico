import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import ValidationError, validate


PHONE_PATTERN = re.compile(r"\+52\d{10}\b")
REDDIT_KEYWORDS = (
    "extorsión telefónica",
    "fraude México",
    "número sospechoso",
)
TWITTER_HASHTAGS = (
    "#ExtorsiónTelefónica",
    "#FraudeEnMéxico",
    "#Estafa",
)
SUBREDDITS = ("mexico", "Scams")
TAG_PRIORITY = {"spam": 0, "fraude": 1, "extorsion": 2}
EXTRACTION_LOG_HEADER = "## Registro de Extracciones Automatizadas"
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


def extract_numbers(text):
    return sorted(set(PHONE_PATTERN.findall(text or "")))


def infer_tag(text):
    normalized_text = (text or "").lower()
    if "extors" in normalized_text:
        return "extorsion"
    if "fraude" in normalized_text or "estafa" in normalized_text:
        return "fraude"
    return "spam"


def combine_sources(current_source, new_source):
    sources = []
    for source in (current_source, new_source):
        for item in source.split(","):
            cleaned_item = item.strip()
            if cleaned_item and cleaned_item not in sources:
                sources.append(cleaned_item)
    return ", ".join(sources)


def choose_tag(current_tag, new_tag):
    if TAG_PRIORITY[new_tag] > TAG_PRIORITY[current_tag]:
        return new_tag
    return current_tag


def accumulate_record(records_by_number, number, source, tag, reports=1):
    if number not in records_by_number:
        records_by_number[number] = {
            "number": number,
            "reports": reports,
            "tag": tag,
            "source": source,
        }
        return

    record = records_by_number[number]
    record["reports"] += reports
    record["tag"] = choose_tag(record["tag"], tag)
    record["source"] = combine_sources(record["source"], source)


def collect_reddit_records(reddit_client):
    records_by_number = {}
    for subreddit_name in SUBREDDITS:
        subreddit = reddit_client.subreddit(subreddit_name)
        for keyword in REDDIT_KEYWORDS:
            for submission in subreddit.search(keyword, limit=100, sort="new"):
                if (getattr(submission, "score", 0) or 0) <= 5:
                    continue
                text = " ".join(
                    filter(
                        None,
                        [
                            getattr(submission, "title", ""),
                            getattr(submission, "selftext", ""),
                        ],
                    )
                )
                numbers = extract_numbers(text)
                tag = infer_tag(text)
                for number in numbers:
                    accumulate_record(records_by_number, number, "Reddit", tag)
    return list(records_by_number.values())


def collect_twitter_records(twitter_client):
    records_by_number = {}
    for hashtag in TWITTER_HASHTAGS:
        response = twitter_client.search_recent_tweets(
            query=f"{hashtag} -is:retweet lang:es",
            max_results=100,
            tweet_fields=["public_metrics", "text"],
        )
        for tweet in getattr(response, "data", []) or []:
            public_metrics = getattr(tweet, "public_metrics", {}) or {}
            if public_metrics.get("like_count", 0) <= 10:
                continue
            text = f"{hashtag} {getattr(tweet, 'text', '')}".strip()
            numbers = extract_numbers(text)
            tag = infer_tag(text)
            for number in numbers:
                accumulate_record(records_by_number, number, "Twitter", tag)
    return list(records_by_number.values())


def merge_candidate_records(records):
    merged_records = {}
    for record in records:
        accumulate_record(
            merged_records,
            record["number"],
            record["source"],
            record["tag"],
            record["reports"],
        )
    return sorted(merged_records.values(), key=lambda item: item["number"])


def bump_version(version):
    parts = version.split(".")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return version
    return f"{parts[0]}.{int(parts[1]) + 1}"


def update_description(description):
    updated_description = (description or "").rstrip(".")
    for source in ("Reddit", "Twitter"):
        if source not in updated_description:
            updated_description = f"{updated_description}, {source}".strip(", ")
    return f"{updated_description}."


def validate_dataset(data):
    validate(instance=data, schema=JSON_SCHEMA)


def normalize_existing_numbers(data):
    normalized_records = {}
    for record in data.get("numbers", []):
        if record["number"] not in normalized_records:
            normalized_records[record["number"]] = dict(record)
            continue

        existing_record = normalized_records[record["number"]]
        existing_record["reports"] = max(existing_record["reports"], record["reports"])
        existing_record["tag"] = choose_tag(existing_record["tag"], record["tag"])
        existing_record["source"] = combine_sources(
            existing_record["source"],
            record["source"],
        )

    data["numbers"] = sorted(normalized_records.values(), key=lambda item: item["number"])


def merge_into_database(data, candidate_records):
    normalize_existing_numbers(data)
    existing_numbers = {entry["number"] for entry in data.get("numbers", [])}
    added_records = []

    for record in candidate_records:
        if record["number"] in existing_numbers:
            continue
        data["numbers"].append(record)
        existing_numbers.add(record["number"])
        added_records.append(record)

    if added_records:
        data["updated_at"] = datetime.now(timezone.utc).date().isoformat()
        data["version"] = bump_version(data.get("version", "1.0"))
        data["description"] = update_description(data.get("description", ""))

    validate_dataset(data)
    return added_records


def update_sources_log(sources_path, added_records, extraction_date):
    if not added_records:
        return

    current_content = sources_path.read_text(encoding="utf-8") if sources_path.exists() else ""
    if EXTRACTION_LOG_HEADER not in current_content:
        if current_content and not current_content.endswith("\n"):
            current_content += "\n"
        current_content += f"\n{EXTRACTION_LOG_HEADER}\n"

    log_lines = [f"\n### {extraction_date}\n"]
    for record in added_records:
        log_lines.append(
            f"- `{record['number']}` — {record['source']} — {record['tag']} — {record['reports']} reporte(s)\n"
        )

    sources_path.write_text(current_content + "".join(log_lines), encoding="utf-8")


def build_reddit_client():
    import praw

    required_env_vars = (
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
    )
    missing_env_vars = [name for name in required_env_vars if not os.getenv(name)]
    if missing_env_vars:
        raise RuntimeError(
            "Faltan credenciales de Reddit: " + ", ".join(sorted(missing_env_vars))
        )

    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
    )


def build_twitter_client():
    import tweepy

    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        raise RuntimeError("Falta la credencial TWITTER_BEARER_TOKEN.")
    return tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="mexico_spam_db.json")
    parser.add_argument("--sources-path", default="FUENTES.md")
    return parser.parse_args()


def main():
    args = parse_args()
    db_path = Path(args.db_path)
    sources_path = Path(args.sources_path)

    data = json.loads(db_path.read_text(encoding="utf-8"))

    reddit_records = collect_reddit_records(build_reddit_client())
    twitter_records = collect_twitter_records(build_twitter_client())
    candidate_records = merge_candidate_records(reddit_records + twitter_records)
    added_records = merge_into_database(data, candidate_records)

    if added_records:
        db_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        update_sources_log(
            sources_path,
            added_records,
            data["updated_at"],
        )
        print(f"✅ Se agregaron {len(added_records)} número(s) nuevos de Reddit/Twitter.")
        return

    try:
        validate_dataset(data)
        print("ℹ️ No se encontraron números nuevos para agregar.")
    except ValidationError as error:
        raise RuntimeError(f"Error de validación del JSON existente: {error.message}") from error


if __name__ == "__main__":
    main()
