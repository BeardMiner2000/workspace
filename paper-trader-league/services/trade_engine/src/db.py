import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


def get_dsn() -> str:
    host = os.getenv('POSTGRES_HOST', 'timescaledb')
    port = os.getenv('POSTGRES_PORT', '5432')
    user = os.getenv('POSTGRES_USER', 'paperbot')
    password = os.getenv('POSTGRES_PASSWORD', 'paperbot')
    database = os.getenv('POSTGRES_DB', 'paperbot')
    return f"dbname={database} user={user} password={password} host={host} port={port}"


@contextmanager
def get_conn():
    conn = psycopg2.connect(get_dsn(), cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
