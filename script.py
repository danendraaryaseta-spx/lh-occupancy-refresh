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
    print(f"\n--- Syncing {source_sheet} to {dest_sheet} ---")
    
    # Read
    source_ws = gc.open_by_key(source_id).worksheet(source_sheet)
    values = source_ws.get(source_range)
    values = [row for row in values if any(str(cell).strip() != "" for cell in row)]
    
    # Write
    dest_ws = gc.open_by_key(dest_id).worksheet(dest_sheet)
    
    # Ensure rows
    req = len(values) + 10
    if dest_ws.row_count < req:
        dest_ws.add_rows(req - dest_ws.row_count)
        
    # Clear and Update
    clear_range = f"A2:{dest_cols_to_clear}{dest_ws.row_count}"
    dest_ws.batch_clear([clear_range])
    
    dest_ws.update(range_name="A2", values=values, value_input_option="USER_ENTERED")
    print(f"✅ {dest_sheet} Updated!")

# --- EXECUTE BOTH TASKS ---

# TASK 1: The original sync (B:W -> A:V)
sync_data(
    source_id="1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4",
    source_sheet="raw_bi",
    source_range="B:W",
    dest_id="1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs",
    dest_sheet="raw",
    dest_cols_to_clear="V"
)

time.sleep(2) # Breath between tasks

# TASK 2: The new sync (B:AC -> A:AB)
sync_data(
    source_id="1xRjNqKiOSXIDiKDNYmbYhQaBz2n6NMyO5Uf6HrpMmFE",
    source_sheet="raw_bi",
    source_range="B:AC",
    dest_id="1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs",
    dest_sheet="raw_fm",
    dest_cols_to_clear="AB"
)
