#!/usr/bin/env python3
"""Ensure local Postgres has pocp DB and root role (for dev)."""

import psycopg

ADMIN = dict(host="127.0.0.1", port=5432, dbname="postgres", user="postgres", password="postgres")


def main() -> int:
    with psycopg.connect(**ADMIN) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("pocp",))
            if not cur.fetchone():
                cur.execute("CREATE DATABASE pocp")
                print("created database pocp")

            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("root",))
            if not cur.fetchone():
                cur.execute("CREATE ROLE root WITH LOGIN PASSWORD 'postgres' SUPERUSER")
                print("created role root")
            else:
                cur.execute("ALTER ROLE root WITH PASSWORD 'postgres'")
                print("updated role root")

            cur.execute("GRANT ALL PRIVILEGES ON DATABASE pocp TO root")

    with psycopg.connect(
        host="127.0.0.1", port=5432, dbname="pocp", user="root", password="postgres"
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            print("root@pocp connection ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
