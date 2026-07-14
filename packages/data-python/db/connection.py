import os
import sys

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

db_pool = None


def init_db_pool(min_conn: int = 1, max_conn: int = 20) -> None:
    """初始化全局多线程安全的数据库连接池"""
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
            print(f"📡 [POOL] 成功创建 Supabase 线程安全连接池 (最大容量: {max_conn})")
        except Exception as e:
            print(f"❌ [POOL] 连接池初始化失败: {e}")
            sys.exit(1)


def close_db_pool() -> None:
    """安全关闭全局连接池"""
    global db_pool
    if db_pool:
        db_pool.closeall()
        db_pool = None
        print("🔌 [POOL] 连接池所有资源已安全释放。")


def get_connection():
    """
    获取一个数据库连接。优先从全局连接池租借；池子未初始化时（如单独跑脚本）新建独立连接。
    返回 (connection, is_from_pool)，用完必须交给 release_connection() 归还。
    """
    if db_pool is not None:
        return db_pool.getconn(), True
    connection = psycopg2.connect(
        user=config.DB_USER, password=config.DB_PASSWORD,
        host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
    )
    return connection, False


def release_connection(connection, is_from_pool: bool) -> None:
    """归还连接：池子借的还回池子，独立建的直接关闭"""
    if connection is None:
        return
    if is_from_pool and db_pool is not None:
        db_pool.putconn(connection)
    else:
        connection.close()
