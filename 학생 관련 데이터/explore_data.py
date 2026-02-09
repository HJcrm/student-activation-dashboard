import pandas as pd
import os
import glob

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
print(f"Total files: {len(files)}")

# Check first file
df = pd.read_csv(files[0], encoding='utf-8-sig')
print(f"\nFirst file: {os.path.basename(files[0])}")
print(f"Shape: {df.shape}")
print(f"\nColumns:\n{list(df.columns)}")
print(f"\nDtypes:\n{df.dtypes}")
print(f"\nFirst 5 rows:")
print(df.head().to_string())
print(f"\n구분 unique values: {df['구분'].unique()}")
print(f"\n현재 학년 unique values: {sorted(df['현재 학년'].dropna().unique())}")

# Check last file
df2 = pd.read_csv(files[-1], encoding='utf-8-sig')
print(f"\n\nLast file: {os.path.basename(files[-1])}")
print(f"Shape: {df2.shape}")
print(f"Columns match: {list(df.columns) == list(df2.columns)}")

# Check a middle file
mid = len(files)//2
df3 = pd.read_csv(files[mid], encoding='utf-8-sig')
print(f"\nMiddle file: {os.path.basename(files[mid])}")
print(f"Shape: {df3.shape}")

# Check date range of files
first_date = os.path.basename(files[0]).replace('학생활성화현황_','').replace('.csv','')
last_date = os.path.basename(files[-1]).replace('학생활성화현황_','').replace('.csv','')
print(f"\nDate range: {first_date} ~ {last_date}")

# Sample values
print(f"\n열람권사용량 stats:\n{df['열람권사용량'].describe()}")
print(f"\n발급권사용량 stats:\n{df['발급권사용량'].describe()}")
print(f"\n주제발급횟수 stats:\n{df['주제발급횟수'].describe()}")
print(f"\n샘플주제과제발급여부 unique: {df['샘플주제과제발급여부'].unique()}")
print(f"AILite진단여부 unique: {df['AILite진단여부'].unique()}")
print(f"AiPro진단여부 unique: {df['AiPro진단여부'].unique()}")
print(f"수시배치표여부 unique: {df['수시배치표여부'].unique()}")
print(f"계열선택검사여부 unique: {df['계열선택검사여부'].unique()}")
