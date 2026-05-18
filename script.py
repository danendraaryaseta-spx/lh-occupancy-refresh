import gspread
import math
import time
import os
import json
from google.oauth2.service_account import Credentials

# --- Auth ---
service_account_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
creds = Credentials.from_service_account_info(
    service_account_info, 
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(creds)

def run_sync(s_id, s_name, s_range, d_id, d_name, clear_to):
    print(f"\n--- Starting Sync: {s_name} -> {d_name} ---")
    try:
        swb = gc.open_by_key(s_id)
        sws = swb.worksheet(s_name)
        
        print(f"Fetching data from {s_name}...")
        data = sws.get(s_range)
        data = [r for r in data if any(str(c).strip() != "" for c in r)]
        total_rows = len(data)
        print(f"Captured {total_rows} rows.")
        
        dwb = gc.open_by_key(d_id)
        dws = dwb.worksheet(d_name)
        
        # 1. Ensure sheet has enough rows
        if dws.row_count < total_rows + 10:
            print("Expanding destination sheet...")
            dws.add_rows((total_rows + 10) - dws.row_count)
            
        # 2. Clear old data
        print(f"Clearing A2:{clear_to}...")
        dws.batch_clear([f"A2:{clear_to}{dws.row_count}"])
        
        # 3. Write in chunks to prevent 500 Internal Errors
        # 10k to 20k is usually the "sweet spot" for large sheets
        CHUNK_SIZE = 15000 
        for i in range(0, total_rows, CHUNK_SIZE):
            chunk = data[i : i + CHUNK_SIZE]
            start_row = i + 2
            end_row = start_row + len(chunk) - 1
            range_label = f"A{start_row}:{clear_to}{end_row}"
            
            print(f"Writing rows {start_row} to {end_row}...")
            dws.update(range_name=range_label, values=chunk, value_input_option="USER_ENTERED")
            
            # Brief sleep to avoid hitting quota/timeout
            time.sleep(2)
            
        print(f"✅ Successfully synced to {d_name}")
        
    except Exception as e:
        print(f"❌ Error in {d_name}: {e}")
        raise e

# --- EXECUTION ---

# TASK 1: SOC SYNC
run_sync(
    "1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4", "raw_bi", "B:W",
    "1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs", "raw_soc", "V"
)

# Longer pause between different sheets
print("Waiting for API cooldown...")
time.sleep(10)

# TASK 2: FM SYNC
run_sync(
    "1xRjNqKiOSXIDiKDNYmbYhQaBz2n6NMyO5Uf6HrpMmFE", "raw_bi", "B:AA",
    "1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs", "raw_fm", "Z"
)
