import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal

import gspread
import snowflake.connector
from google.oauth2.service_account import Credentials

QUERY = """
select
    work_item_id,
    'https://app2.karbonhq.com/2GXQkWNYYRPp/work/' || work_item_id as work_link,
    work_title,
    client,
    work_type,
    primary_status,
    assigned_to,
    due_datetime,
    work_template
from work_item_details
where work_type = 'Tax Returns'
    and work_template is not null
"""

TAB_NAME = "tax_returns"


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
        columns = [c[0] for c in cur.description]
        rows = cur.fetchall()
        cur.close()
    print("Fetched " + str(len(rows)) + " rows, " + str(len(columns)) + " columns")
    return columns, rows


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return v
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (int, float, str)):
        return v
    return str(v)


def push(columns, rows):
    info = json.loads(env("GOOGLE_CREDENTIALS_JSON"))
    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ],
    )
    ss = gspread.authorize(creds).open_by_key(env("GOOGLE_SHEET_ID"))

    try:
        ws = ss.worksheet(TAB_NAME)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(
            title=TAB_NAME,
            rows=max(len(rows) + 50, 100),
            cols=max(len(columns) + 5, 20),
        )
        print("Created tab " + TAB_NAME)

    values = [list(columns)]
    values.extend([[cell(v) for v in row] for row in rows])

    ws.clear()
    ws.update(values=values, range_name="A1")
    ws.format("1:1", {"textFormat": {"bold": True}})
    ws.freeze(rows=1)
    print("Wrote " + str(len(rows)) + " rows to tab " + TAB_NAME)


columns, rows = fetch()
if not rows:
    print("No rows returned. Sheet left untouched.")
    sys.exit(0)
push(columns, rows)
print("PASS")
