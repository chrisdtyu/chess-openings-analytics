from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable, List

import berserk
from datetime import datetime, timezone

BATCH_SIZE = 300  
SINCE_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)
SINCE_MS = int(SINCE_DATE.timestamp() * 1000)


def chunked(seq: List[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def export_games(usernames: List[str], out_path: Path) -> None:
    token = os.getenv("LICHESS_API_TOKEN")
    if not token:
        raise RuntimeError("LICHESS_API_TOKEN not set in environment or .env file")

    client = berserk.Client(token=token, timeout=60)

    with out_path.open("w", encoding="utf-8") as f_out:
        for username in usernames:
            print(f"Downloading games for {username}…", flush=True)
            try:
                stream = client.games.export_by_user(
                    username=username,
                    max=BATCH_SIZE,
                    rated=True,
                    perf_type="blitz,rapid",
                    openings=True,
                    moves=False,
                    tags=True,
                    since=SINCE_MS,
                )
            except berserk.exceptions.ResponseError as exc:
                print(f"  ! API error for {username}: {exc}")
                continue

            for pgn_line in stream:
                f_out.write(pgn_line + "\n")

    print(f"Saved PGN to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Lichess games for given users")
    parser.add_argument("user_list", help="File containing one username per line")
    parser.add_argument("output_pgn", help="Output PGN file path")
    args = parser.parse_args()

    usernames = Path(args.user_list).read_text(encoding="utf-8").splitlines()
    export_games(usernames, Path(args.output_pgn))


if __name__ == "__main__":
    main()
