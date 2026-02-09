import pandas as pd
import os
import glob
import json
import re
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
print(f"Total CSV files found: {len(files)}")

# ============================================================
# 1. Load all valid CSVs
# ============================================================
all_daily = []
skipped = []

for f in files:
    fname = os.path.basename(f)
    date_match = re.search(r'(\d{8})', fname)
    if not date_match:
        skipped.append((fname, "no date in filename"))
        continue
    date_str = date_match.group(1)

    try:
        df = pd.read_csv(f, encoding='utf-8-sig')
        # Validate: must have at least the core columns
        if len(df.columns) < 10:
            skipped.append((fname, f"only {len(df.columns)} columns"))
            continue
        if len(df) == 0:
            skipped.append((fname, "empty"))
            continue

        # Standardize column access - use positional for core columns
        # Col 0: 학원명, 1: 학원코드, 2: 학생명, 3: 학생코드, 4: 학교명, 5: 현재학년
        # Find 구분, usage columns by name
        cols = list(df.columns)

        # Build a standardized row per file (daily summary)
        date = pd.to_datetime(date_str, format='%Y%m%d')
        total_students = len(df)

        # Find usage columns by pattern matching
        usage_cols = []
        yn_cols = []
        for c in cols:
            if '사용량' in c or '횟수' in c:
                usage_cols.append(c)
            if '여부' in c:
                yn_cols.append(c)

        # Active student: any usage > 0 OR any Y/N field == 'Y'
        active_mask = pd.Series(False, index=df.index)
        for c in usage_cols:
            active_mask = active_mask | (pd.to_numeric(df[c], errors='coerce').fillna(0) > 0)
        for c in yn_cols:
            active_mask = active_mask | (df[c].astype(str).str.strip().str.upper() == 'Y')

        active_students = active_mask.sum()

        # Grade distribution
        grade_col = [c for c in cols if '학년' in c]
        grade_dist = {}
        if grade_col:
            gc = grade_col[0]
            for g in [0, 1, 2, 3]:
                grade_dist[f'grade_{g}'] = int((df[gc] == g).sum())

        # Category (구분) distribution
        cat_col = [c for c in cols if c == '구분']
        cat_dist = {}
        if cat_col:
            vc = df[cat_col[0]].value_counts()
            for k, v in vc.items():
                cat_dist[str(k)] = int(v)

        # Academy count
        academy_col = [c for c in cols if '학원명' in c]
        n_academies = df[academy_col[0]].nunique() if academy_col else 0

        # Individual feature usage
        feature_counts = {}
        for c in usage_cols:
            feature_counts[c] = int((pd.to_numeric(df[c], errors='coerce').fillna(0) > 0).sum())
        for c in yn_cols:
            feature_counts[c] = int((df[c].astype(str).str.strip().str.upper() == 'Y').sum())

        # Student codes for tracking new/churned students
        student_code_col = [c for c in cols if '학생' in c and '코드' in c]
        student_codes = set()
        if student_code_col:
            student_codes = set(df[student_code_col[0]].dropna().astype(str).unique())

        row = {
            'date': date,
            'total_students': total_students,
            'active_students': active_students,
            'activation_rate': round(active_students / total_students * 100, 2) if total_students > 0 else 0,
            'n_academies': n_academies,
            'student_codes': student_codes,
            **grade_dist,
            **feature_counts,
        }
        # Store category distribution as separate columns
        for k, v in cat_dist.items():
            row[f'cat_{k}'] = v

        all_daily.append(row)

    except Exception as e:
        skipped.append((fname, str(e)))

print(f"Valid files: {len(all_daily)}")
print(f"Skipped files: {len(skipped)}")
for s in skipped[:10]:
    print(f"  {s[0]}: {s[1]}")

# ============================================================
# 2. Build daily DataFrame
# ============================================================
daily_df = pd.DataFrame(all_daily).sort_values('date').reset_index(drop=True)

# Calculate new students per day (delta)
new_students = []
prev_codes = set()
for _, row in daily_df.iterrows():
    codes = row['student_codes']
    new = len(codes - prev_codes) if prev_codes else 0
    new_students.append(new)
    prev_codes = codes

daily_df['new_students'] = new_students
daily_df = daily_df.drop(columns=['student_codes'])

# Day of week
daily_df['day_of_week'] = daily_df['date'].dt.day_name()
daily_df['year_month'] = daily_df['date'].dt.to_period('M').astype(str)
daily_df['year_week'] = daily_df['date'].dt.strftime('%Y-W%W')

print(f"\nDaily data shape: {daily_df.shape}")
print(f"Date range: {daily_df['date'].min()} ~ {daily_df['date'].max()}")
print(f"\nSample daily data:")
print(daily_df[['date','total_students','active_students','activation_rate','n_academies','new_students']].head(10).to_string())
print(f"\nColumns: {list(daily_df.columns)}")

# ============================================================
# 3. Build weekly aggregation
# ============================================================
weekly_df = daily_df.groupby('year_week').agg(
    date_start=('date', 'min'),
    date_end=('date', 'max'),
    avg_total_students=('total_students', 'mean'),
    avg_active_students=('active_students', 'mean'),
    avg_activation_rate=('activation_rate', 'mean'),
    max_total_students=('total_students', 'max'),
    max_active_students=('active_students', 'max'),
    total_new_students=('new_students', 'sum'),
    avg_academies=('n_academies', 'mean'),
    n_days=('date', 'count'),
).reset_index()

print(f"\nWeekly data shape: {weekly_df.shape}")
print(weekly_df.head(10).to_string())

# ============================================================
# 4. Build monthly aggregation
# ============================================================
monthly_df = daily_df.groupby('year_month').agg(
    date_start=('date', 'min'),
    date_end=('date', 'max'),
    avg_total_students=('total_students', 'mean'),
    avg_active_students=('active_students', 'mean'),
    avg_activation_rate=('activation_rate', 'mean'),
    max_total_students=('total_students', 'max'),
    max_active_students=('active_students', 'max'),
    total_new_students=('new_students', 'sum'),
    avg_academies=('n_academies', 'mean'),
    n_days=('date', 'count'),
).reset_index()

print(f"\nMonthly data shape: {monthly_df.shape}")
print(monthly_df.to_string())

# ============================================================
# 5. Feature usage columns
# ============================================================
feature_cols = [c for c in daily_df.columns if '사용량' in c or '횟수' in c or '여부' in c]
print(f"\nFeature columns: {feature_cols}")

# ============================================================
# 6. Category columns
# ============================================================
cat_cols = [c for c in daily_df.columns if c.startswith('cat_')]
print(f"Category columns: {cat_cols}")

# ============================================================
# 7. Save processed data as JSON for the dashboard
# ============================================================

def safe_serialize(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d')
    if isinstance(obj, (pd.Period,)):
        return str(obj)
    if hasattr(obj, 'item'):
        return obj.item()
    return str(obj)

# Daily data for charts
daily_chart = daily_df[['date','total_students','active_students','activation_rate',
                         'n_academies','new_students','day_of_week','year_month','year_week']
                        + [c for c in feature_cols if c in daily_df.columns]
                        + [c for c in cat_cols if c in daily_df.columns]
                        + [c for c in ['grade_0','grade_1','grade_2','grade_3'] if c in daily_df.columns]
                       ].copy()
daily_chart['date'] = daily_chart['date'].dt.strftime('%Y-%m-%d')

# Fill NaN with 0 for numeric cols
for c in daily_chart.columns:
    if daily_chart[c].dtype in ['float64', 'int64', 'float32', 'int32']:
        daily_chart[c] = daily_chart[c].fillna(0)

dashboard_data = {
    'daily': daily_chart.to_dict(orient='records'),
    'weekly': weekly_df.to_dict(orient='records'),
    'monthly': monthly_df.to_dict(orient='records'),
    'feature_cols': feature_cols,
    'cat_cols': cat_cols,
    'summary': {
        'total_days': len(daily_df),
        'date_start': daily_df['date'].min().strftime('%Y-%m-%d'),
        'date_end': daily_df['date'].max().strftime('%Y-%m-%d'),
        'latest_total': int(daily_df.iloc[-1]['total_students']),
        'latest_active': int(daily_df.iloc[-1]['active_students']),
        'latest_rate': float(daily_df.iloc[-1]['activation_rate']),
        'latest_academies': int(daily_df.iloc[-1]['n_academies']),
        'avg_activation_rate': round(float(daily_df['activation_rate'].mean()), 2),
        'total_new_students_all': int(daily_df['new_students'].sum()),
    }
}

# Serialize weekly/monthly dates
for row in dashboard_data['weekly']:
    row['date_start'] = safe_serialize(row['date_start'])
    row['date_end'] = safe_serialize(row['date_end'])
    for k, v in row.items():
        if hasattr(v, 'item'):
            row[k] = v.item()

for row in dashboard_data['monthly']:
    row['date_start'] = safe_serialize(row['date_start'])
    row['date_end'] = safe_serialize(row['date_end'])
    for k, v in row.items():
        if hasattr(v, 'item'):
            row[k] = v.item()

output_path = os.path.join(os.path.dirname(__file__), "dashboard_data.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(dashboard_data, f, ensure_ascii=False, default=safe_serialize)

print(f"\nDashboard data saved to: {output_path}")
print(f"Summary: {json.dumps(dashboard_data['summary'], ensure_ascii=False, indent=2)}")
