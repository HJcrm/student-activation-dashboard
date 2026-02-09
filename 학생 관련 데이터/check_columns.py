import pandas as pd
import os
import glob

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))

# Check first file columns
df1 = pd.read_csv(files[0], encoding='utf-8-sig', nrows=2)
cols1 = list(df1.columns)

# Check last file columns
df2 = pd.read_csv(files[-1], encoding='utf-8-sig', nrows=2)
cols2 = list(df2.columns)

print("=== First file columns (19) ===")
for i, c in enumerate(cols1):
    print(f"  {i}: {c}")

print(f"\n=== Last file columns (22) ===")
for i, c in enumerate(cols2):
    print(f"  {i}: {c}")

print(f"\n=== New columns in last file ===")
for c in cols2:
    if c not in cols1:
        print(f"  NEW: {c}")

print(f"\n=== Columns removed from last file ===")
for c in cols1:
    if c not in cols2:
        print(f"  REMOVED: {c}")

# Find when columns changed
prev_cols = None
for f in files:
    df = pd.read_csv(f, encoding='utf-8-sig', nrows=0)
    curr_cols = list(df.columns)
    if prev_cols is not None and len(curr_cols) != len(prev_cols):
        fname = os.path.basename(f)
        date_str = fname.replace('학생활성화현황_','').replace('.csv','')
        print(f"\nColumn change detected at {date_str}: {len(prev_cols)} -> {len(curr_cols)}")
        new_cols = [c for c in curr_cols if c not in prev_cols]
        removed_cols = [c for c in prev_cols if c not in curr_cols]
        if new_cols:
            print(f"  Added: {new_cols}")
        if removed_cols:
            print(f"  Removed: {removed_cols}")
    prev_cols = curr_cols

# Check 구분 values across files
print("\n=== 구분 (Category) values across sample files ===")
for idx in [0, len(files)//4, len(files)//2, 3*len(files)//4, -1]:
    f = files[idx]
    df = pd.read_csv(f, encoding='utf-8-sig')
    fname = os.path.basename(f)
    date_str = fname.replace('학생활성화현황_','').replace('.csv','')
    vals = df['구분'].dropna().unique()
    print(f"  {date_str}: rows={len(df)}, 구분={list(vals)}")

# Check a recent file's data
df_recent = pd.read_csv(files[-1], encoding='utf-8-sig')
print(f"\n=== Recent file sample ===")
print(df_recent.head(3).to_string())
