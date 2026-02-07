import pandas as pd
import os
import glob
import json
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
print(f"Total CSV files found: {len(files)}")

# ============================================================
# 1. Load all valid CSVs, keep per-student data
# ============================================================
USAGE_COLS_KEYWORDS = ['사용량', '횟수']  # numeric usage columns only

daily_frames = {}
skipped = []

for f in files:
    fname = os.path.basename(f)
    date_match = re.search(r'(\d{8})', fname)
    if not date_match:
        continue
    date_str = date_match.group(1)

    try:
        df = pd.read_csv(f, encoding='utf-8-sig')
        if len(df.columns) < 10 or len(df) == 0:
            skipped.append(date_str)
            continue

        cols = list(df.columns)

        # Find student code column
        student_code_col = None
        for c in cols:
            if '학생' in c and '코드' in c:
                student_code_col = c
                break
        if not student_code_col:
            skipped.append(date_str)
            continue

        # Find numeric usage columns
        usage_cols = [c for c in cols if any(k in c for k in USAGE_COLS_KEYWORDS)]

        # Find grade, category, academy columns
        grade_col = next((c for c in cols if '학년' in c), None)
        cat_col = next((c for c in cols if c == '구분'), None)
        academy_col = next((c for c in cols if '학원명' in c), None)
        academy_code_col = next((c for c in cols if '학원코드' in c or '학원 코드' in c), None)

        keep_cols = [student_code_col] + usage_cols
        if grade_col: keep_cols.append(grade_col)
        if cat_col: keep_cols.append(cat_col)
        if academy_col: keep_cols.append(academy_col)
        if academy_code_col: keep_cols.append(academy_code_col)

        sub = df[keep_cols].copy()
        sub = sub.rename(columns={student_code_col: 'student_code'})

        # Convert usage cols to numeric
        for uc in usage_cols:
            sub[uc] = pd.to_numeric(sub[uc], errors='coerce').fillna(0)

        # Drop rows with missing student code, then deduplicate
        sub = sub.dropna(subset='student_code')
        sub['student_code'] = sub['student_code'].astype(str)
        sub = sub.drop_duplicates(subset='student_code', keep='last')
        sub = sub.set_index('student_code')

        date = pd.to_datetime(date_str, format='%Y%m%d')
        daily_frames[date] = {
            'df': sub,
            'usage_cols': usage_cols,
            'grade_col': grade_col,
            'cat_col': cat_col,
            'academy_col': academy_col,
            'academy_code_col': academy_code_col,
        }
    except Exception as e:
        skipped.append(f"{date_str}: {e}")

sorted_dates = sorted(daily_frames.keys())
print(f"Valid days: {len(sorted_dates)}")
print(f"Skipped: {len(skipped)}")
print(f"Date range: {sorted_dates[0].strftime('%Y-%m-%d')} ~ {sorted_dates[-1].strftime('%Y-%m-%d')}")

# ============================================================
# 2. Compute daily active students (delta-based)
# ============================================================
results = []
prev_date = None

for date in sorted_dates:
    info = daily_frames[date]
    df_today = info['df']
    usage_cols = info['usage_cols']
    total_students = len(df_today)

    # Grade distribution
    grade_dist = {f'grade_{g}': 0 for g in [0, 1, 2, 3]}
    if info['grade_col'] and info['grade_col'] in df_today.columns:
        for g in [0, 1, 2, 3]:
            grade_dist[f'grade_{g}'] = int((df_today[info['grade_col']] == g).sum())

    # Category distribution
    cat_dist = {}
    if info['cat_col'] and info['cat_col'] in df_today.columns:
        vc = df_today[info['cat_col']].value_counts()
        for k, v in vc.items():
            cat_dist[f'cat_{k}'] = int(v)

    # Academy count
    n_academies = 0
    acol = info['academy_code_col'] or info['academy_col']
    if acol and acol in df_today.columns:
        n_academies = df_today[acol].nunique()

    # Active students: compare with previous day
    active_students = 0
    active_by_feature = {uc: 0 for uc in usage_cols}
    active_student_codes = []

    if prev_date is not None:
        df_prev = daily_frames[prev_date]['df']
        prev_usage_cols = daily_frames[prev_date]['usage_cols']

        # Common students
        common_students = df_today.index.intersection(df_prev.index)
        # Common usage columns
        common_usage = [c for c in usage_cols if c in prev_usage_cols and c in df_prev.columns]

        if len(common_students) > 0 and len(common_usage) > 0:
            today_vals = df_today.loc[common_students, common_usage]
            prev_vals = df_prev.loc[common_students, common_usage]
            delta = today_vals - prev_vals

            # A student is active if any usage column increased
            active_mask = (delta > 0).any(axis=1)
            active_students = int(active_mask.sum())
            active_student_codes.extend(common_students[active_mask].tolist())

            # Per-feature active counts
            for uc in common_usage:
                active_by_feature[uc] = int((delta[uc] > 0).sum())

        # New students (not in previous day) who have any usage > 0
        new_student_ids = df_today.index.difference(df_prev.index)
        if len(new_student_ids) > 0:
            new_df = df_today.loc[new_student_ids, [c for c in usage_cols if c in df_today.columns]]
            new_active_mask = (new_df > 0).any(axis=1)
            active_students += int(new_active_mask.sum())
            active_student_codes.extend(new_student_ids[new_active_mask].tolist())
            for uc in usage_cols:
                if uc in new_df.columns:
                    active_by_feature[uc] += int((new_df[uc] > 0).sum())

    # Build active students' academy summary
    acad_col = info['academy_col']
    active_academies_str = ''
    if acad_col and acad_col in df_today.columns and len(active_student_codes) > 0:
        valid_codes = [c for c in active_student_codes if c in df_today.index]
        if valid_codes:
            acad_names = df_today.loc[valid_codes, acad_col].dropna()
            acad_counts = acad_names.value_counts().sort_values(ascending=False)
            top = acad_counts.head(10)
            parts = [f'{name} ({cnt}명)' for name, cnt in top.items()]
            active_academies_str = '<br>'.join(parts)
            remainder = len(acad_counts) - 10
            if remainder > 0:
                active_academies_str += f'<br>외 {remainder}개 학원'

    # New students count
    new_students = 0
    if prev_date is not None:
        df_prev = daily_frames[prev_date]['df']
        new_students = len(df_today.index.difference(df_prev.index))

    row = {
        'date': date,
        'total_students': total_students,
        'active_students': active_students,
        'activation_rate': round(active_students / total_students * 100, 2) if total_students > 0 else 0,
        'n_academies': n_academies,
        'new_students': new_students,
        'active_academies': active_academies_str,
        **grade_dist,
        **active_by_feature,
        **cat_dist,
    }
    results.append(row)
    prev_date = date

# ============================================================
# 3. Build DataFrame
# ============================================================
daily_df = pd.DataFrame(results).sort_values('date').reset_index(drop=True)

# Filter out anomalous days
daily_df = daily_df[daily_df['total_students'] >= 100].reset_index(drop=True)

daily_df['day_of_week'] = daily_df['date'].dt.day_name()
daily_df['year_month'] = daily_df['date'].dt.to_period('M').astype(str)
daily_df['year_week'] = daily_df['date'].dt.strftime('%Y-W%W')

# Identify feature columns (usage-based)
feature_cols = [c for c in daily_df.columns if any(k in c for k in USAGE_COLS_KEYWORDS) and c not in ['total_students','active_students','new_students','n_academies']]
cat_cols = [c for c in daily_df.columns if c.startswith('cat_')]

print(f"\nClean daily data: {len(daily_df)} days")
print(f"Feature columns: {feature_cols}")
print(f"Category columns: {cat_cols}")
print(f"\nSample:")
print(daily_df[['date','total_students','active_students','activation_rate','new_students']].head(15).to_string())
print(f"\n... tail:")
print(daily_df[['date','total_students','active_students','activation_rate','new_students']].tail(10).to_string())

# ============================================================
# 4. Weekly / Monthly aggregation
# ============================================================
weekly_df = daily_df.groupby('year_week').agg(
    date_start=('date', 'min'),
    date_end=('date', 'max'),
    avg_total_students=('total_students', 'mean'),
    avg_active_students=('active_students', 'mean'),
    avg_activation_rate=('activation_rate', 'mean'),
    max_active_students=('active_students', 'max'),
    total_new_students=('new_students', 'sum'),
    avg_academies=('n_academies', 'mean'),
    n_days=('date', 'count'),
).reset_index()

monthly_df = daily_df.groupby('year_month').agg(
    date_start=('date', 'min'),
    date_end=('date', 'max'),
    avg_total_students=('total_students', 'mean'),
    avg_active_students=('active_students', 'mean'),
    avg_activation_rate=('activation_rate', 'mean'),
    max_active_students=('active_students', 'max'),
    total_new_students=('new_students', 'sum'),
    avg_academies=('n_academies', 'mean'),
    n_days=('date', 'count'),
).reset_index()

print(f"\nMonthly summary:")
print(monthly_df.to_string())

# ============================================================
# 5. Export JSON
# ============================================================
def safe_val(v):
    if isinstance(v, pd.Timestamp):
        return v.strftime('%Y-%m-%d')
    if hasattr(v, 'item'):
        return v.item()
    if isinstance(v, float) and pd.isna(v):
        return 0
    return v

daily_export_cols = ['date','total_students','active_students','activation_rate',
                     'n_academies','new_students','active_academies','day_of_week','year_month','year_week'] \
                    + feature_cols + cat_cols \
                    + [c for c in ['grade_0','grade_1','grade_2','grade_3'] if c in daily_df.columns]

daily_chart = daily_df[[c for c in daily_export_cols if c in daily_df.columns]].copy()
daily_chart['date'] = daily_chart['date'].dt.strftime('%Y-%m-%d')
daily_chart = daily_chart.fillna(0)

def rows_to_dicts(df_rows):
    records = df_rows.to_dict(orient='records')
    for r in records:
        for k, v in r.items():
            r[k] = safe_val(v)
    return records

dashboard_data = {
    'daily': rows_to_dicts(daily_chart),
    'weekly': rows_to_dicts(weekly_df),
    'monthly': rows_to_dicts(monthly_df),
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
        'avg_daily_active': round(float(daily_df['active_students'].mean()), 1),
        'avg_activation_rate': round(float(daily_df['activation_rate'].mean()), 2),
        'total_new_students_all': int(daily_df['new_students'].sum()),
    }
}

output_path = os.path.join(os.path.dirname(__file__), "dashboard_data_v2.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(dashboard_data, f, ensure_ascii=False, default=str)

print(f"\nJSON saved: {output_path}")
print(f"Summary: {json.dumps(dashboard_data['summary'], ensure_ascii=False, indent=2)}")
