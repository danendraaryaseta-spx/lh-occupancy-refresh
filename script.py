import gspread
import time
import os
import json
import string
from google.oauth2.service_account import Credentials

# --- Auth ---
service_account_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.Client(auth=creds)

def col_letter_to_index(letter):
    return string.ascii_uppercase.index(letter.upper())

def index_to_col_letter(index):
    return string.ascii_uppercase[index]

def run_sync(s_id, s_name, s_columns, d_id, d_name):
    print(f"\n--- Starting Sync: {s_name} -> {d_name} ---")
    try:
        swb = gc.open_by_key(s_id)
        sws = swb.worksheet(s_name)

        # Fetch the smallest contiguous block that covers all requested columns,
        # then pick out just the ones we want by position.
        col_indices = [col_letter_to_index(c) for c in s_columns]
        first_col, last_col = min(col_indices), max(col_indices)
        first_letter = index_to_col_letter(first_col)
        last_letter = index_to_col_letter(last_col)
        width = last_col - first_col + 1

        print(f"Fetching columns {s_columns} (range {first_letter}:{last_letter}) from {s_name}...")
        raw = sws.get(f"{first_letter}:{last_letter}")

        data = []
        for row in raw:
            padded = row + [""] * (width - len(row))
            if any(str(c).strip() != "" for c in padded):
                data.append([padded[i - first_col] for i in col_indices])

        total_rows = len(data)
        print(f"Captured {total_rows} rows.")

        dwb = gc.open_by_key(d_id)
        dws = dwb.worksheet(d_name)

        # Destination is always written starting at column A, so its width is
        # just the number of source columns requested.
        dest_last_col = index_to_col_letter(len(s_columns) - 1)

        # 1. Ensure sheet has enough rows
        if dws.row_count < total_rows + 10:
            print("Expanding destination sheet...")
            dws.add_rows((total_rows + 10) - dws.row_count)

        # 2. Clear old data — only A:dest_last_col, so helper columns further
        #    right are left untouched.
        print(f"Clearing A2:{dest_last_col}{dws.row_count}...")
        dws.batch_clear([f"A2:{dest_last_col}{dws.row_count}"])

        # 3. Write in chunks to prevent 500 Internal Errors
        CHUNK_SIZE = 15000
        for i in range(0, total_rows, CHUNK_SIZE):
            chunk = data[i : i + CHUNK_SIZE]
            start_row = i + 2
            end_row = start_row + len(chunk) - 1
            range_label = f"A{start_row}:{dest_last_col}{end_row}"

            print(f"Writing rows {start_row} to {end_row}...")
            dws.update(range_name=range_label, values=chunk, value_input_option="USER_ENTERED")

            time.sleep(2)

        print(f"Successfully synced to {d_name}")

    except Exception as e:
        print(f"Error in {d_name}: {e}")
        raise e

# --- EXECUTION ---
# TASK 1: SOC SYNC
run_sync(
    "1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4", "raw_bi",
    ["B", "C", "D", "E", "F", "J", "K", "V", "W"],
    "1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs", "raw_soc"
)
