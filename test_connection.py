import os
import sys
import snowflake.connector

account = os.environ.get("SNOWFLAKE_ACCOUNT")
user = os.environ.get("SNOWFLAKE_USER")
password = os.environ.get("SNOWFLAKE_PASSWORD")
warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE") or "read_wh"
database = os.environ.get("SNOWFLAKE_DATABASE") or "KPI_DATABASE"
schema = os.environ.get("SNOWFLAKE_SCHEMA") or "SECURE_VIEWS"
role = os.environ.get("SNOWFLAKE_ROLE") or "PUBLIC"

if not all([account, user, password]):
    sys.exit("FAIL: missing SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER or SNOWFLAKE_PASSWORD")

print("account   :", account)
print("user      :", user[:4] + "..." + user[-4:])
print("warehouse :", warehouse)
print("database  :", database)
print("schema    :", schema)
print("role      :", role)

conn = snowflake.connector.connect(
    account=account,
    user=user,
    password=password,
    warehouse=warehouse,
    database=database,
    schema=schema,
    role=role,
    login_timeout=60,
)

print("\nConnected.\n")

with conn:
    cur = conn.cursor()

    cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
    print("session:", cur.fetchone())

    print("\nViews:")
    cur.execute("SHOW VIEWS IN SCHEMA " + database + "." + schema)
    for r in cur.fetchall():
        print("  " + r[1])

    print("\nTables:")
    cur.execute("SHOW TABLES IN SCHEMA " + database + "." + schema)
    for r in cur.fetchall():
        print("  " + r[1])

    cur.close()

print("\nPASS")
