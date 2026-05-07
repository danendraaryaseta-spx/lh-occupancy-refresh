import gspread
import math
import time
import os
import json
from google.oauth2.service_account import Credentials

# ============================================================
# CONFIG
# ============================================================
SOURCE_SPREADSHEET_ID  = "1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4"
SOURCE_SHEET_NAME      = "raw_bi"
SOURCE_RANGE           = "B:W"

DEST_SPREADSHEET_ID    = "1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs"
DEST_SHEET_NAME        = "raw"
DEST_START_ROW         = 2
DEST_START_COL         = "A"
BATCH_SIZE             = 10000

# ============================================================
# AUTHENTICATION
# ============================================================
# We will pull the JSON key from GitHub Secrets later
service_account_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
creds = Credentials.from_service_account_info(
    service_account_info, 
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(creds)

# ============================================================
# LOGIC (Same as your Colab code)
# ============================================================
print("Opening source spreadsheet...")
source_wb = gc.open_by_key(SOURCE_SPREADSHEET_ID)
source_ws = source_wb.worksheet(SOURCE_SHEET_NAME)

values = source_ws.get(SOURCE_RANGE)
values = [row for row in values if any(str(cell).strip() != "" for cell in row)]

print(f"Found {len(values)} rows. Opening destination...")
dest_wb = gc.open_by_key(DEST_SPREADSHEET_ID)
dest_ws = dest_wb.worksheet(DEST_SHEET_NAME)

# Expand and Clear
required_rows = len(values) + DEST_START_ROW + 10
if dest_ws.row_count < required_rows:
    dest_ws.add_rows(required_rows - dest_ws.row_count)

clear_range = f"A2:V{dest_ws.row_count}"
dest_ws.batch_clear([clear_range])

# Batch Write
total_rows_to_write = len(values)
total_batches = math.ceil(total_rows_to_write / BATCH_SIZE)

for i in range(total_batches):
    start_idx = i * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, total_rows_to_write)
    batch = values[start_idx:end_idx]
    start_row = DEST_START_ROW + start_idx
    range_name = f"{DEST_START_COL}{start_row}"
    
    print(f"Batch {i+1}/{total_batches}...")
    dest_ws.update(range_name=range_name, values=batch, value_input_option="USER_ENTERED")
    time.sleep(1.5)

print("✅ Done!")
