#!/usr/bin/env python3
"""Check tables, columns, and row counts in a local MySQL project schema."""

from __future__ import annotations

import os
import sys
from getpass import getpass


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def connect_with_mysql_connector(config: dict[str, object]):
    import mysql.connector

    return mysql.connector.connect(**config)


def connect_with_pymysql(config: dict[str, object]):
    import pymysql

    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
    )


def quote_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def main() -> int:
    default_user = env("MYSQL_USER", "root")
    user = input(f"MySQL user [{default_user}]: ").strip() or default_user
    default_schema = env("MYSQL_DATABASE", "CS564")
    schema = input(f"MySQL schema [{default_schema}]: ").strip() or default_schema
    password = os.environ.get("MYSQL_PASSWORD")
    if password is None:
        password = getpass("MySQL password: ")

    config = {
        "host": env("MYSQL_HOST", "127.0.0.1"),
        "port": int(env("MYSQL_PORT", "3306")),
        "user": user,
        "password": password,
        "database": schema,
    }

    try:
        connection = connect_with_mysql_connector(config)
        driver = "mysql-connector-python"
    except ImportError:
        try:
            connection = connect_with_pymysql(config)
            driver = "PyMySQL"
        except ImportError:
            print(
                "Missing MySQL Python driver. Install one with:\n"
                "  python -m pip install mysql-connector-python\n"
                "or:\n"
                "  python -m pip install PyMySQL",
                file=sys.stderr,
            )
            return 1

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    DATABASE() AS current_schema,
                    NOW() AS server_time
                """
            )
            row = cursor.fetchone()

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY table_name
                """
            )
            tables = [table_row[0] for table_row in cursor.fetchall()]

            table_schemas: list[tuple[str, int, list[tuple[str, str]]]] = []
            for table_name in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}")
                record_count = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT column_name, column_type
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table_name,),
                )
                columns = [(column_row[0], column_row[1]) for column_row in cursor.fetchall()]
                table_schemas.append((table_name, record_count, columns))

        print(f"Connected to MySQL using {driver}")
        print(f"Schema: {row[0]}")
        print(f"Server time: {row[1]}")
        if not table_schemas:
            print("No tables found in current schema.")
        else:
            print("Tables:")
            for table_name, record_count, columns in table_schemas:
                print(f"  {table_name} ({record_count} records)")
                if not columns:
                    print("    (no columns found)")
                    continue
                for column_name, column_type in columns:
                    print(f"    {column_name}: {column_type}")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
