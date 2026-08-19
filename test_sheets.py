import json
import os
import sys
import gspread
from datetime import datetime, timezone
from google.oauth2.service_account import Credentials

raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
sheet_id = os.environ.get("GOOGLE_SHEET_ID")

if not raw:
    sys.exit("FAIL: GOOGLE_CREDENTIALS_JSON is empty")
if not sheet_id:
    sys.exit("FAIL: GOOGLE_SHEET_ID is empty")

try:
    info = json.loads(raw)
except json.JSONDecodeError as e:
    sys.exit("FAIL: secret is not valid JSON: " + str(e))

print("service account :", info.get("client_email"))
print("project         :", info.get("project_id"))
print("sheet id        :", sheet_id)

creds = Credentials.from_service_account_info(
    info,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ],
)

client = gspread.authorize(creds)

try:
    ss = client.open_by_key(sheet_id)
except gspread.SpreadsheetNotFound:
    sys.exit(
        "FAIL: cannot open the sheet. Either the ID is wrong, or the sheet "
        "is not shared with " + str(info.get("client_email")) + " as Editor."
    )

print("\nOpened:", ss.title)
print("Existing tabs:", [w.title for w in ss.worksheets()])

tab_name = "connection_test"
try:
    ws = ss.worksheet(tab_name)
except gspread.WorksheetNotFound:
    ws = ss.add_worksheet(title=tab_name, rows=10, cols=3)
    print("Created tab:", tab_name)

stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
ws.clear()
ws.update(values=[["status", "timestamp"], ["write successful", stamp]], range_name="A1")

print("\nWrote to tab '" + tab_name + "' at " + stamp)
print("PASS - check the sheet to confirm.")
