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
    print(f"Starting: {s_name} -> {d_name}")
    try:
        swb = gc.open_by_key(s_id)
        sws = swb.worksheet(s_name)
        data = sws.get(s_range)
        data = [r for r in data if any(str(c).strip() != "" for c in r)]
        
        dwb = gc.open_by_key(d_id)
        dws = dwb.worksheet(d_name) # THE ERROR HAPPENS HERE IF NAME IS WRONG
        
        if dws.row_count < len(data) + 10:
            dws.add_rows((len(data) + 10) - dws.row_count)
            
        dws.batch_clear([f"A2:{clear_to}{dws.row_count}"])
        dws.update(range_name="A2", values=data, value_input_option="USER_ENTERED")
        print(f"Done: {d_name}")
    except Exception as e:
        print(f"Error in {d_name}: {e}")
        raise e

# TASK 1: raw_soc
run_sync(
    "1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4", "raw_bi", "B:W",
    "1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs", "raw_soc", "V"
)

time.sleep(5)

# TASK 2: raw_fm
run_sync(
    "1xRjNqKiOSXIDiKDNYmbYhQaBz2n6NMyO5Uf6HrpMmFE", "raw_bi", "B:AC",
    "1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs", "raw_fm", "AB"
)
