import gspread
import math
import time
import os
import json
from google.oauth2.service_account import Credentials

# --- Setup Connection ---
# Pulls the JSON key from the GitHub Secret you created
service_account_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
creds = Credentials.from_service_account_info(
    service_account_info, 
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(creds)

def sync_data(source_id, source_sheet, source_range, dest_id, dest_sheet, dest_cols_to_clear):
    print(f"\n--- Syncing {source_sheet} to {dest_sheet} ---")
    
    # 1. Open Source and Get Data
    source_wb = gc.open_by_key(source_id)
    source_ws = source_wb.worksheet(source_sheet)
    values = source_ws.get(source_range)
    
    # Filter out empty rows
    values = [row for row in values if any(str(cell).strip() != "" for cell in row)]
    print(f" -> Found {len(values)} rows of data.")
    
    # 2. Open Destination
    dest_wb = gc.open_by_key(dest_id)
    dest_ws = dest_wb.worksheet(dest_sheet)
    
    # 3. Handle Sheet Size (Expand if necessary)
    required_rows = len(values) + 10
    if dest_ws.row_count < required_rows:
        print(f" -> Expanding {dest_sheet} to {required_rows} rows...")
        dest_ws.add_rows(required_rows - dest_ws.row_count)
        
    # 4. Clear Old Data (A2 to the specified end column)
    clear_range = f"A2:{dest_cols_to_clear}{dest_ws.row_count}"
    print(f" -> Clearing range {clear_range}...")
    dest_ws.batch_clear([clear_range])
    
    # 5. Write New Data in Batches
    # (Using update for the whole block; gspread handles large updates well)
    dest_ws.update(range_name="A2", values=values, value_input_option="USER_ENTERED")
    print(f"✅ {dest_sheet} successfully updated!")

# ============================================================
# EXECUTION ZONE
# ============================================================

try:
    # TASK 1: Updated tab name "raw_soc"
    # Source B:W (22 cols) -> Dest A:V (22 cols)
    sync_data(
        source_id="1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4",
        source_sheet="raw_bi",
        source_range="B:W",
        dest_id="1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs",
        dest_sheet="raw_soc",  # <--- CHANGED FROM "raw"
        dest_cols_to_clear="V"
    )

    # Pause to prevent hitting Google API rate limits
    time.sleep(5) 

    # TASK 2: FM Sync
    # Source B:AC (28 cols) -> Dest A:AB (28 cols)
    sync_data(
        source_id="1xRjNqKiOSXIDiKDNYmbYhQaBz2n6NMyO5Uf6HrpMmFE",
        source_sheet="raw_bi",
        source_range="B:AC",
        dest_id="1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs",
        dest_sheet="raw_fm",
        dest_cols_to_clear="AB"
    )

    print("\n🚀 All sync tasks completed successfully.")

except Exception as e:
    print(f"\n❌ ERROR OCCURRED: {e}")
    exit(1) # Tells GitHub Actions that the run failed
