
Test connection · PY
"""
Snowflake connection test for Karbon Practice Intelligence.
 
Verifies credentials, prints session context, and lists the views you can
actually query. Touches nothing in Google -- run this before sync_tax_data.py.
 
Needs only: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD
(and optionally WAREHOUSE / DATABASE / SCHEMA / ROLE)
"""
 
import os
import sys
import traceback
 
import snowflake.connector
 
 
def env(name, default=None):
    return os.environ.get(name) or default
 
 
def main():
    account = env("SNOWFLAKE_ACCOUNT")
    user = env("SNOWFLAKE_USER")
    password = env("SNOWFLAKE_PASSWORD")
 
    missing = [n for n, v in [
        ("SNOWFLAKE_ACCOUNT", account),
        ("SNOWFLAKE_USER", user),
        ("SNOWFLAKE_PASSWORD", password),
    ] if not v]
    if missing:
        sys.exit(f"FAIL: missing secrets: {', '.join(missing)}")
 
    warehouse = env("SNOWFLAKE_WAREHOUSE", "read_wh")
    database = env("SNOWFLAKE_DATABASE", "KPI_DATABASE")
    schema = env("SNOWFLAKE_SCHEMA", "SECURE_VIEWS")
    role = env("SNOWFLAKE_ROLE", "PUBLIC")
 
    # Show shape without leaking values.
    print("=" * 62)
    print(f"account   : {account}")
    print(f"user      : {user[:4]}...{user[-4:]} (len {len(user)})")
    print(f"password  : {'*' * 8} (len {len(password)})")
    print(f"warehouse : {warehouse}")
    print(f"database  : {database}")
    print(f"schema    : {schema}")
    print(f"role      : {role}")
    print("=" * 62)
 
    if account.count(".") < 2:
        print("NOTE: account has fewer than two dots. Karbon accounts usually")
        print("      look like LOCATOR.REGION.azure -- check this if it fails.")
 
    try:
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
    except Exception as exc:
        print("\nFAIL: could not connect.\n")
        print(traceback.format_exc())
        diagnose(exc)
        sys.exit(1)
 
    print("\nConnected.\n")
 
    with conn:
        cur = conn.cursor()
 
        # 1. Session context
        cur.execute("""
            SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_ROLE(),
                   CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA(),
                   CURRENT_VERSION()
        """)
        labels = ["account", "user", "role", "warehouse", "database",
                  "schema", "version"]
        print("-- session context " + "-" * 43)
        for label, value in zip(labels, cur.fetchone()):
            print(f"{label:>10} : {value}")
 
        if not cur.description:
            pass
 
        # 2. Warehouse check -- a null warehouse means queries will fail later
        cur.execute("SELECT CURRENT_WAREHOUSE()")
        if not cur.fetchone()[0]:
            print("\nWARNING: no warehouse in session. Queries needing compute")
            print("         will fail. Confirm the warehouse name with Karbon.")
 
        # 3. What can we actually read?
        print("\n-- views in {}.{} ".format(database, schema) + "-" * 25)
        try:
            cur.execute(f"SHOW VIEWS IN SCHEMA {database}.{schema}")
            rows = cur.fetchall()
            names = [r[1] for r in rows]
            if names:
                for n in sorted(names):
                    print(f"  {n}")
                print(f"\n{len(names)} view(s) found.")
            else:
                print("  (none visible to this role)")
        except Exception as exc:
            print(f"  could not list views: {exc}")
 
        # 4. Also list tables, in case the data is not exposed as views
        try:
            cur.execute(f"SHOW TABLES IN SCHEMA {database}.{schema}")
            tables = [r[1] for r in cur.fetchall()]
            if tables:
                print(f"\n-- tables in {database}.{schema} " + "-" * 24)
                for t in sorted(tables):
                    print(f"  {t}")
        except Exception:
            pass
 
        cur.close()
 
    print("\nPASS: connection works.")
    print("Next: pick a view above, put it in QUERY in sync_tax_data.py.")
 
 
def diagnose(exc):
    """Map the common failures to something actionable."""
    text = str(exc).lower()
    hints = [
        ("250001", "Account identifier is probably wrong. Karbon uses "
                   "LOCATOR.REGION.azure -- check for a doubled or missing "
                   "'.azure' suffix."),
        ("incorrect username or password",
         "Credentials rejected. Re-copy them from Karbon's Intelligence tab; "
         "they may have rotated."),
        ("multi-factor", "Password auth is being blocked on this user. This is "
                         "Snowflake's password deprecation -- Karbon has to "
                         "move KPI to key-pair or token auth."),
        ("network policy", "Your IP is blocked. GitHub runner IPs rotate, so "
                           "this needs an exception from Karbon."),
        ("does not exist or not authorized",
         "Warehouse, database, or schema name is wrong, or PUBLIC lacks access."),
        ("timed out", "Network reachability problem, or the account URL is wrong."),
    ]
    for needle, hint in hints:
        if needle in text:
            print(f"LIKELY CAUSE: {hint}")
            return
    print("No specific diagnosis. Check the account identifier format first -- "
          "it is the most common cause.")
 
 
if __name__ == "__main__":
    main()
 
