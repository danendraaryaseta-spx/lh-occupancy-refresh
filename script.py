import gspread
import math
import time
import os
import json
from google.oauth2.service_account import Credentials

# --- Setup Connection ---
service_account_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
creds = Credentials.from_service_account_info(
    service_account_info, 
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(creds)

def sync_data(source_id, source_sheet, source_range, dest_id, dest_sheet, dest_cols_to_clear):
    print(f"\nOpening source: {source_sheet}...")
    source_wb = gc.open_by_key(source_id)
    source_ws = source_wb.worksheet(source_sheet)
    
    values = source_ws.get(source_range)
    values = [row for row in values if any(str(cell).strip() != "" for cell in row)]
    print(f" -> Found {len(values)} rows. Opening destination: {dest_sheet}...")
    
    dest_wb = gc.open_by_key(dest_id)
    # This is where the error was happening - dest_sheet must match exactly!
    dest_ws = dest_wb.worksheet(dest_sheet)
    
    # Expand if needed
    required_rows = len(values) + 10
    if dest_ws.row_count < required_rows:
        dest_ws.add_rows(required_rows - dest_ws.row_count)
        
    # Clear A2:EndCol
    clear_range = f"A2:{dest_cols_to_clear}{dest_ws.row_count}"
    print(f" -> Clearing {clear_range}...")
    dest_ws.batch_clear([clear_range])
    
    # Update
    print(f" -> Writing data to {dest_sheet}...")
    dest_ws.update(range_name="A2", values=values, value_input_option="USER_ENTERED")
    print(f"✅ {dest_sheet} updated successfully.")

# ============================================================
# RUN TASKS
# ============================================================
try:
    # TASK 1: SOC SYNC (B:W -> A:V)
    sync_data(
        source_id="1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4",
        source_sheet="raw_bi",
        source_range="B:W",
        dest_id="1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs",
        dest_sheet="raw_soc",  # Updated name
        dest_cols_to_clear="V"
    )

    time.sleep(5) 

    # TASK 2: FM SYNC (B:AC -> A:AB)
    sync_data(
        source_id="1xRjNqKiOSXIDiKDNYmbYhQaBz2n6NMyO5Uf6HrpMmFE",
        source_sheet="raw_bi",
        source_range="B:AC",
        dest_id="1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs",
        dest_sheet="raw_fm",   # New destination tab
        dest_cols_to_clear="AB"
    )

except Exception as e:
    print(f"\n❌ SCRIPT FAILED: {e}")
    raise e
