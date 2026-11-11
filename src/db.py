from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from dotenv import load_dotenv

load_dotenv()


@contextmanager
def get_conn() -> Iterator[psycopg2.extensions.connection]:
    #Open a connection to the PostgreSQL database
    conn = psycopg2.connect(os.getenv("DATABASE_URL", ""))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
