#!/usr/bin/env python3
"""Replay a timestamped SQL log into a SQLite database.

Each line in the log file should be a JSON object containing at least:
- "operation": one of execute, queryone, queryall
- "query": the SQL statement
- "args": a list of bound arguments

The script reads the log in order and executes the statements against the target
SQLite database. It ignores lines that cannot be parsed.
"""

import argparse
import json
import sqlite3
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Replay a timestamped SQL log file into a SQLite database."
    )
    parser.add_argument(
        "log_file",
        help="Path to the JSONL SQL log file (for example, experiments_log.txt).",
    )
    parser.add_argument(
        "db_file",
        help="Path to the SQLite database file to rebuild or update.",
    )
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="Skip malformed log entries instead of stopping.",
    )
    return parser.parse_args()


def replay_log(log_path: Path, db_path: Path, skip_invalid: bool = False):
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        with log_path.open("r", encoding="utf-8") as f:
            for line_number, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    operation = entry.get("operation")
                    query = entry.get("query")
                    args = entry.get("args", [])
                except json.JSONDecodeError:
                    if skip_invalid:
                        print(f"Skipping invalid JSON on line {line_number}")
                        continue
                    raise

                if operation not in {"execute", "queryone", "queryall"}:
                    if skip_invalid:
                        print(
                            f"Skipping unsupported operation {operation!r} on line {line_number}"
                        )
                        continue
                    raise ValueError(
                        f"Unsupported operation {operation!r} on line {line_number}"
                    )

                if not query:
                    if skip_invalid:
                        print(f"Skipping missing query on line {line_number}")
                        continue
                    raise ValueError(f"Missing query on line {line_number}")

                try:
                    if operation == "execute":
                        cur.execute(query, tuple(args))
                        con.commit()
                    elif operation == "queryone":
                        cur.execute(query, tuple(args))
                        cur.fetchone()
                    elif operation == "queryall":
                        cur.execute(query, tuple(args))
                        cur.fetchall()
                except Exception as exc:
                    if skip_invalid:
                        print(
                            f"Skipping failed statement on line {line_number}: {exc}"
                        )
                        continue
                    raise

        print(f"Replayed {line_number if 'line_number' in locals() else 0} log lines into {db_path}")


def main():
    args = parse_args()
    replay_log(Path(args.log_file), Path(args.db_file), skip_invalid=args.skip_invalid)


if __name__ == "__main__":
    main()
