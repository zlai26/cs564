#!/usr/bin/env python3
"""Purge and import the six prepared CSV tables into the MySQL schema."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from getpass import getpass
from pathlib import Path
from typing import Iterable


TABLE_ORDER = [
    "CityState",
    "ZipCodeDemographics",
    "Address",
    "ApartmentListing",
    "Amenity",
    "ListingAmenity",
]
PURGE_ORDER = list(reversed(TABLE_ORDER))


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


def connect(config: dict[str, object]):
    try:
        return connect_with_mysql_connector(config), "mysql-connector-python"
    except ImportError:
        try:
            return connect_with_pymysql(config), "PyMySQL"
        except ImportError:
            print(
                "Missing MySQL Python driver. Install one with:\n"
                "  python -m pip install mysql-connector-python\n"
                "or:\n"
                "  python -m pip install PyMySQL",
                file=sys.stderr,
            )
            raise


def prompt_config() -> dict[str, object]:
    default_user = env("MYSQL_USER", "root")
    user = input(f"MySQL user [{default_user}]: ").strip() or default_user
    default_schema = env("MYSQL_DATABASE", "CS564")
    schema = input(f"MySQL schema [{default_schema}]: ").strip() or default_schema
    password = os.environ.get("MYSQL_PASSWORD")
    if password is None:
        password = getpass("MySQL password: ")

    return {
        "host": env("MYSQL_HOST", "127.0.0.1"),
        "port": int(env("MYSQL_PORT", "3306")),
        "user": user,
        "password": password,
        "database": schema,
    }


def quote_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def csv_rows(path: Path) -> tuple[list[str], Iterable[list[str]]]:
    csv.field_size_limit(sys.maxsize)
    raw_file = path.open(newline="", encoding="utf-8")
    reader = csv.reader(raw_file)

    try:
        headers = next(reader)
    except StopIteration:
        raw_file.close()
        raise ValueError(f"{path} is empty") from None

    def rows() -> Iterable[list[str]]:
        try:
            yield from reader
        finally:
            raw_file.close()

    return headers, rows()


def purge_tables(cursor) -> None:
    for table_name in PURGE_ORDER:
        cursor.execute(f"DELETE FROM {quote_identifier(table_name)}")
        print(f"Purged {table_name}")


def insert_table(cursor, table_name: str, import_dir: Path, batch_size: int) -> int:
    path = import_dir / f"{table_name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing import CSV: {path}")

    headers, rows = csv_rows(path)
    columns_sql = ", ".join(quote_identifier(header) for header in headers)
    placeholders = ", ".join(["%s"] * len(headers))
    insert_sql = (
        f"INSERT INTO {quote_identifier(table_name)} "
        f"({columns_sql}) VALUES ({placeholders})"
    )

    count = 0
    batch: list[list[str]] = []
    for row in rows:
        if len(row) != len(headers):
            raise ValueError(
                f"{path} row has {len(row)} values; expected {len(headers)}"
            )
        batch.append(row)
        if len(batch) >= batch_size:
            cursor.executemany(insert_sql, batch)
            count += len(batch)
            batch.clear()

    if batch:
        cursor.executemany(insert_sql, batch)
        count += len(batch)

    print(f"Inserted {count} rows into {table_name}")
    return count


def import_tables(connection, import_dir: Path, batch_size: int) -> dict[str, int]:
    cursor = connection.cursor()
    try:
        purge_tables(cursor)
        counts = {}
        for table_name in TABLE_ORDER:
            counts[table_name] = insert_table(cursor, table_name, import_dir, batch_size)
        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Purge and import the six prepared CSV tables into MySQL."
    )
    parser.add_argument("--import-dir", type=Path, default=Path("data/import"))
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    config = prompt_config()
    try:
        connection, driver = connect(config)
    except ImportError:
        return 1

    try:
        print(f"Connected to MySQL using {driver}")
        counts = import_tables(connection, args.import_dir, args.batch_size)
    except Exception as error:
        print(f"Import failed; transaction rolled back: {error}", file=sys.stderr)
        return 1
    finally:
        connection.close()

    print("Import complete")
    for table_name in TABLE_ORDER:
        print(f"{table_name}: {counts[table_name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
