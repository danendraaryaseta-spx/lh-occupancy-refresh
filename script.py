import gspread
import time
import os
import json
import random
import requests
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials

# --- Auth ---
service_account_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.Client(auth=creds)

# --- Transient-failure retry ---------------------------------------------
# Google routinely returns 503 (and friends) under load. They are not errors
# in our request, they just mean "try again shortly", so every API call goes
# through this wrapper instead of failing the whole run on one blip.
RETRY_CODES = {408, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 6

def api(label, fn, *args, **kwargs):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn(*args, **kwargs)
        except APIError as e:
            # code is -1 when Google answers with a non-JSON body (e.g. an
            # HTML 503 page), so fall back to the raw HTTP status.
            code = e.code if e.code != -1 else getattr(e.response, "status_code", None)
            if code not in RETRY_CODES or attempt == MAX_ATTEMPTS:
                raise
            reason = f"HTTP {code}"
        except requests.exceptions.RequestException as e:
            if attempt == MAX_ATTEMPTS:
                raise
            reason = type(e).__name__

        wait = min(2 ** attempt, 64) + random.uniform(0, 1.5)
        print(f"  [{label}] {reason} on attempt {attempt}/{MAX_ATTEMPTS} - retrying in {wait:.1f}s")
        time.sleep(wait)

def col_letter_to_index(letter):
    n = 0
    for ch in letter.upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1

def index_to_col_letter(index):
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters

# Both tasks read the identical range from the identical tab, so fetch it
# once and filter it twice. Halves the heaviest call in the script.
_source_cache = {}

def fetch_source(s_id, s_name, first_letter, last_letter):
    key = (s_id, s_name, first_letter, last_letter)
    if key in _source_cache:
        print(f"Reusing cached read of {s_name} ({first_letter}:{last_letter}).")
        return _source_cache[key]

    swb = api("open source", gc.open_by_key, s_id)
    sws = api("open tab", swb.worksheet, s_name)
    print(f"Fetching range {first_letter}:{last_letter} from {s_name}...")
    raw = api("read", sws.get, f"{first_letter}:{last_letter}")
    _source_cache[key] = raw
    return raw

def run_sync(s_id, s_name, s_columns, d_id, d_name, filter_col=None, filter_value=None):
    print(f"\n--- Starting Sync: {s_name} -> {d_name} ---")
    try:
        # Fetch the smallest contiguous block that covers all requested columns,
        # then pick out just the ones we want by position.
        col_indices = [col_letter_to_index(c) for c in s_columns]
        first_col, last_col = min(col_indices), max(col_indices)
        first_letter = index_to_col_letter(first_col)
        last_letter = index_to_col_letter(last_col)
        width = last_col - first_col + 1

        filter_index = col_letter_to_index(filter_col) - first_col if filter_col else None

        raw = fetch_source(s_id, s_name, first_letter, last_letter)

        data = []
        for row in raw:
            padded = row + [""] * (width - len(row))
            if not any(str(c).strip() != "" for c in padded):
                continue
            if filter_index is not None and filter_value.upper() not in str(padded[filter_index]).upper():
                continue
            data.append([padded[i - first_col] for i in col_indices])

        total_rows = len(data)
        print(f"Captured {total_rows} rows.")

        dwb = api("open dest", gc.open_by_key, d_id)
        dws = api("open dest tab", dwb.worksheet, d_name)

        # Destination is always written starting at column A, so its width is
        # just the number of source columns requested.
        dest_last_col = index_to_col_letter(len(s_columns) - 1)

        # 1. Ensure sheet has enough rows
        if dws.row_count < total_rows + 10:
            print("Expanding destination sheet...")
            api("add rows", dws.add_rows, (total_rows + 10) - dws.row_count)

        # 2. Clear old data - only A:dest_last_col, so helper columns further
        #    right are left untouched.
        print(f"Clearing A2:{dest_last_col}{dws.row_count}...")
        api("clear", dws.batch_clear, [f"A2:{dest_last_col}{dws.row_count}"])

        # 3. Write in chunks. Smaller chunks are far less likely to trip a
        #    500/503 than one giant payload, and a retry costs less when it does.
        CHUNK_SIZE = 5000
        for i in range(0, total_rows, CHUNK_SIZE):
            chunk = data[i : i + CHUNK_SIZE]
            start_row = i + 2
            end_row = start_row + len(chunk) - 1
            range_label = f"A{start_row}:{dest_last_col}{end_row}"

            print(f"Writing rows {start_row} to {end_row}...")
            api(
                f"write {start_row}-{end_row}",
                dws.update,
                range_name=range_label,
                values=chunk,
                value_input_option="USER_ENTERED",
            )

            time.sleep(1)

        print(f"Successfully synced to {d_name}")

    except Exception as e:
        print(f"Error in {d_name}: {e}")
        raise e

# --- EXECUTION ---
# TASK 1: SOC SYNC
run_sync(
    "1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4", "raw_bi",
    ["B", "C", "D", "E", "F", "J", "K", "V", "W"],
    "1dh755S5NnbyRNsytWc8JYJ6BgYIOD979-AZwBH8yshs", "raw_soc",
    filter_col="C", filter_value="Hub"
)

# TASK 2: SOC SYNC (DC)
run_sync(
    "1Eb5K-ZnX6WyYr1kUXmLG03RVuz0IOPLru8IHSZc4Je4", "raw_bi",
    ["B", "C", "D", "E", "F", "J", "K", "V", "W"],
    "1rruN5xFUi7YXm122fN5aSpidEjsLV_U0iw6rl5IMDyQ", "raw_soc",
    filter_col="C", filter_value="DC"
)
