"""
Builds the tax work items dashboard from Snowflake.

Queries Karbon KPI, renders template.html into public/index.html.
Cloudflare Pages serves whatever lands in public/.
"""

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import snowflake.connector

QUERY = """
select
    work_item_id,
    work_title,
    client,
    coalesce(secondary_status, primary_status) as status,
    assigned_to,
    due_datetime
from work_item_details
where work_type = 'Tax Returns'
  and work_item_id not in ('2B5xjPBV5q3n', 'zyZfntyGpLr')
  and (
    work_template is not null
    or work_item_id in (
      '43PWNDsNRTrG','47ljmmdVL7x8','BYPSYgMzwpZ','2c64XtbHlz4Q','XyR5wQnVRpw',
      'YJ1vX3mb5jZ','3ZR6l73FCVVL','bqsBZGJF2cZ','CbWng3spZ9v','T9hsfCpZb9J',
      '4c8YSsS5Cwt','WhzgWhT1FR7','F1bl4hwvTrd','9YzvRWpt4q8','4fPPBrxqVDfw',
      '46nRmWQxrw2r','N2nq5mqXqQW','bMwyS8XVb9x','3Jl1GjjlHcJL','4CYQQh1fND7t',
      '4ysJf8lRVpJQ','4bchmx6RDFFg','4n9pq4grz656','2cF2Ln7vkhZl','2lrbcvnYkFR9'
    )
  )
order by due_datetime
"""

TEMPLATE = Path("template.html")
OUTPUT = Path("public/index.html")


def env(name, default=None, required=True):
    value = os.environ.get(name) or default
    if required and not value:
        sys.exit("FAIL: missing " + name)
    return value


def fetch():
    conn = snowflake.connector.connect(
        account=env("SNOWFLAKE_ACCOUNT"),
        user=env("SNOWFLAKE_USER"),
        password=env("SNOWFLAKE_PASSWORD"),
        warehouse=env("SNOWFLAKE_WAREHOUSE", "read_wh"),
        database=env("SNOWFLAKE_DATABASE", "KPI_DATABASE"),
        schema=env("SNOWFLAKE_SCHEMA", "SECURE_VIEWS"),
        role=env("SNOWFLAKE_ROLE", "PUBLIC", required=False),
        login_timeout=60,
    )
    with conn:
        cur = conn.cursor()
        cur.execute(QUERY)
        rows = cur.fetchall()
        cur.close()
    print("Fetched " + str(len(rows)) + " rows")
    return rows


def as_day(v):
    """due_datetime may come back as datetime, date, or string."""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.isoformat()
    if v:
        return str(v)[:10]
    return ""


def build(rows):
    # Template expects: [id, title, client, status, assignee, due]
    payload = [
        [
            str(r[0] or ""),
            str(r[1] or ""),
            str(r[2] or ""),
            str(r[3] or ""),
            str(r[4] or "Unassigned"),
            as_day(r[5]),
        ]
        for r in rows
        if as_day(r[5])  # rows without a due date break the deadline maths
    ]

    dropped = len(rows) - len(payload)
    if dropped:
        print("Skipped " + str(dropped) + " row(s) with no due date")

    now = datetime.now(timezone.utc)
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__ROWS__", json.dumps(payload, ensure_ascii=False))
    html = html.replace("__SYNCED__", now.strftime("%Y-%m-%d %H:%M UTC"))
    html = html.replace("__TODAY__", now.strftime("%Y-%m-%d"))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print("Wrote " + str(OUTPUT) + " (" + str(len(html)) + " bytes)")


rows = fetch()
if not rows:
    sys.exit("FAIL: query returned no rows — refusing to publish an empty dashboard")
build(rows)
print("PASS")
