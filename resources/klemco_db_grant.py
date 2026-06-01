#!/usr/bin/env python
"""Self-heal the site DB user host grant (idempotent).

frappe_docker can create the site's MariaDB user pinned to a single container IP.
When container IPs churn (restart / recreate) the app then fails with
"Access denied for user ... (using password: YES)". This script re-grants the
site DB user for ANY host ('%') so the site keeps working regardless of IP.

Run on backend startup BEFORE `bench migrate`, using the MariaDB root password
(env DB_PASSWORD / MYSQL_ROOT_PASSWORD, default '123'). Safe to run repeatedly.
"""
import json
import os
import sys

BENCH = "/home/frappe/frappe-bench"


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def main():
    common = _load(f"{BENCH}/sites/common_site_config.json")
    site = os.environ.get("FRAPPE_SITE_NAME_HEADER") or common.get("default_site")
    if not site:
        print("[grant] no site resolved; skipping")
        return

    cfg = _load(f"{BENCH}/sites/{site}/site_config.json")
    db_name = cfg["db_name"]
    db_password = cfg["db_password"]
    host = common.get("db_host", "db")
    port = int(common.get("db_port", 3306))
    root_pw = os.environ.get("DB_PASSWORD") or os.environ.get("MYSQL_ROOT_PASSWORD") or "123"

    import MySQLdb

    conn = MySQLdb.connect(host=host, port=port, user="root", password=root_pw)
    cur = conn.cursor()
    # db_name is a Frappe-generated [a-z0-9_] hash — safe to interpolate for the GRANT object.
    cur.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", (db_name, db_password))
    cur.execute("ALTER USER %s@'%%' IDENTIFIED BY %s", (db_name, db_password))
    cur.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO %s@'%%'", (db_name,))
    cur.execute("FLUSH PRIVILEGES")
    conn.commit()
    print(f"[grant] ensured DB user {db_name}@'%' on {host}:{port}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never block startup on the self-heal
        print("[grant] skipped:", exc)
        sys.exit(0)
