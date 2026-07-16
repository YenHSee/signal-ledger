import os
import sys

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

db_pool = None


def init_db_pool(min_conn: int = 1, max_conn: int = 20) -> None:
    """Initialize the global thread-safe database connection pool."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = ThreadedConnectionPool(
                min_conn, max_conn,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME
            )
            print(f"📡 [POOL] Database connection pool created (maximum: {max_conn})")
        except Exception as e:
            print(f"❌ [POOL] Failed to initialize the connection pool: {e}")
            sys.exit(1)


def close_db_pool() -> None:
    """Close every connection in the global pool."""
    global db_pool
    if db_pool:
        db_pool.closeall()
        db_pool = None
        print("🔌 [POOL] All database connections have been released.")


def get_connection():
    """
    Borrow a pooled connection when available, otherwise create a standalone one.
    Return (connection, is_from_pool); callers must pass both to release_connection().
    """
    if db_pool is not None:
        return db_pool.getconn(), True
    connection = psycopg2.connect(
        user=config.DB_USER, password=config.DB_PASSWORD,
        host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
    )
    return connection, False


def release_connection(connection, is_from_pool: bool) -> None:
    """Return a pooled connection or close a standalone connection."""
    if connection is None:
        return
    if is_from_pool and db_pool is not None:
        db_pool.putconn(connection)
    else:
        connection.close()
