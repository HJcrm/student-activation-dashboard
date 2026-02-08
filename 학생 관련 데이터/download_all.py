import os
import requests
from datetime import datetime, timedelta
import urllib.parse
import concurrent.futures
import time

BASE_URL = "https://operation.hakzzongpro.com/student-activation-logs/"
FILENAME_PREFIX = "학생활성화현황_"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

start_date = datetime(2025, 4, 2)
end_date = datetime.today()

dates = []
current = start_date
while current <= end_date:
    dates.append(current)
    current += timedelta(days=1)

def download_file(date):
    date_str = date.strftime("%Y%m%d")
    filename = f"{FILENAME_PREFIX}{date_str}.csv"
    encoded_filename = urllib.parse.quote(filename)
    url = BASE_URL + encoded_filename
    output_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return f"SKIP {date_str}"

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return f"OK   {date_str}"
        else:
            return f"FAIL {date_str} (HTTP {resp.status_code})"
    except Exception as e:
        return f"ERR  {date_str} ({e})"

print(f"Total dates to download: {len(dates)}")
print(f"Output directory: {OUTPUT_DIR}")
print("Starting download...")

success = 0
fail = 0
skip = 0

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(download_file, d): d for d in dates}
    for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
        result = future.result()
        if result.startswith("OK"):
            success += 1
        elif result.startswith("SKIP"):
            skip += 1
        else:
            fail += 1
        if i % 50 == 0 or i == len(dates):
            print(f"Progress: {i}/{len(dates)} | OK: {success} | Skip: {skip} | Fail: {fail}")

print(f"\nDone! OK: {success}, Skip: {skip}, Fail: {fail}")
