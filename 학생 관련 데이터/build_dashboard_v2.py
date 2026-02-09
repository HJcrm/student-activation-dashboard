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

# Load registered academy codes
_REG_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "가입학원_목록.csv")
REG_CODES = set()
if os.path.exists(_REG_CSV):
    _rdf = pd.read_csv(_REG_CSV, encoding='utf-8-sig')
    REG_CODES = set(_rdf.iloc[:, 2].astype(str).str.strip().tolist())
    print(f"Registered academy codes loaded: {len(REG_CODES)}")
else:
    print("Warning: registered academy list not found")

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
    reg_by_feature = {uc: 0 for uc in usage_cols}
    active_student_codes = []

    # Registration mask for today's students
    acad_code = info['academy_code_col']
    if acad_code and acad_code in df_today.columns:
        reg_mask = df_today[acad_code].astype(str).isin(REG_CODES)
    else:
        reg_mask = pd.Series(False, index=df_today.index)

    if prev_date is not None:
        df_prev = daily_frames[prev_date]['df']
        prev_usage_cols = daily_frames[prev_date]['usage_cols']

        # Common students
        common_students = df_today.index.intersection(df_prev.index)
        common_usage = [c for c in usage_cols if c in prev_usage_cols and c in df_prev.columns]

        if len(common_students) > 0 and len(common_usage) > 0:
            today_vals = df_today.loc[common_students, common_usage]
            prev_vals = df_prev.loc[common_students, common_usage]
            delta = today_vals - prev_vals

            active_mask = (delta > 0).any(axis=1)
            active_students = int(active_mask.sum())
            active_student_codes.extend(common_students[active_mask].tolist())

            reg_cm = reg_mask.reindex(common_students, fill_value=False)
            for uc in common_usage:
                fa = delta[uc] > 0
                active_by_feature[uc] = int(fa.sum())
                reg_by_feature[uc] = int((fa & reg_cm).sum())

        # New students
        new_student_ids = df_today.index.difference(df_prev.index)
        if len(new_student_ids) > 0:
            new_df = df_today.loc[new_student_ids, [c for c in usage_cols if c in df_today.columns]]
            new_active_mask = (new_df > 0).any(axis=1)
            active_students += int(new_active_mask.sum())
            active_student_codes.extend(new_student_ids[new_active_mask].tolist())
            new_reg_m = reg_mask.reindex(new_student_ids, fill_value=False)
            for uc in usage_cols:
                if uc in new_df.columns:
                    fa = new_df[uc] > 0
                    active_by_feature[uc] += int(fa.sum())
                    reg_by_feature[uc] += int((fa & new_reg_m).sum())

    # Academy summary helper
    acad_col = info['academy_col']
    def _acad_str(codes):
        if not acad_col or acad_col not in df_today.columns or not codes: return ''
        vc = [c for c in codes if c in df_today.index]
        if not vc: return ''
        an = df_today.loc[vc, acad_col].dropna()
        ac = an.value_counts().sort_values(ascending=False)
        parts = [f'{n} ({c}명)' for n, c in ac.head(10).items()]
        s = '<br>'.join(parts)
        if len(ac) > 10: s += f'<br>외 {len(ac)-10}개 학원'
        return s

    # Split active students by registration
    rac = [c for c in active_student_codes if c in reg_mask.index and reg_mask.get(c, False)]
    uac = [c for c in active_student_codes if c not in rac]

    # Registration breakdown totals
    rt = int(reg_mask.sum()); ut = total_students - rt
    ra = len(rac); ua = len(uac)
    rr = round(ra / rt * 100, 2) if rt > 0 else 0
    ur = round(ua / ut * 100, 2) if ut > 0 else 0

    # Academies per group
    r_nacad = 0; u_nacad = 0
    _acol = acad_code or acad_col
    if _acol and _acol in df_today.columns:
        r_nacad = int(df_today.loc[reg_mask, _acol].nunique())
        u_nacad = int(df_today.loc[~reg_mask, _acol].nunique())

    # New students count
    new_students = 0; reg_new = 0; unreg_new = 0
    if prev_date is not None:
        df_prev = daily_frames[prev_date]['df']
        _ni = df_today.index.difference(df_prev.index)
        new_students = len(_ni)
        if len(_ni) > 0:
            reg_new = int(reg_mask.reindex(_ni, fill_value=False).sum())
            unreg_new = new_students - reg_new

    row = {
        'date': date,
        'total_students': total_students,
        'active_students': active_students,
        'activation_rate': round(active_students / total_students * 100, 2) if total_students > 0 else 0,
        'n_academies': n_academies,
        'new_students': new_students,
        'active_academies': _acad_str(active_student_codes),
        'reg_total': rt, 'reg_active': ra, 'reg_rate': rr, 'reg_new': reg_new,
        'reg_n_academies': r_nacad, 'reg_active_academies': _acad_str(rac),
        'unreg_total': ut, 'unreg_active': ua, 'unreg_rate': ur, 'unreg_new': unreg_new,
        'unreg_n_academies': u_nacad, 'unreg_active_academies': _acad_str(uac),
        **grade_dist,
        **active_by_feature,
        **{f'reg_{k}': v for k, v in reg_by_feature.items()},
        **{f'unreg_{k}': active_by_feature.get(k, 0) - reg_by_feature.get(k, 0) for k in active_by_feature},
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
feature_cols = [c for c in daily_df.columns if any(k in c for k in USAGE_COLS_KEYWORDS) and c not in ['total_students','active_students','new_students','n_academies'] and not c.startswith('reg_') and not c.startswith('unreg_')]
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

reg_extra = ['reg_total','reg_active','reg_rate','reg_new','reg_n_academies','reg_active_academies',
             'unreg_total','unreg_active','unreg_rate','unreg_new','unreg_n_academies','unreg_active_academies']
reg_feat = [f'reg_{c}' for c in feature_cols] + [f'unreg_{c}' for c in feature_cols]
daily_export_cols = ['date','total_students','active_students','activation_rate',
                     'n_academies','new_students','active_academies','day_of_week','year_month','year_week'] \
                    + feature_cols + cat_cols \
                    + [c for c in ['grade_0','grade_1','grade_2','grade_3'] if c in daily_df.columns] \
                    + reg_extra + reg_feat

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

# ============================================================
# Per-academy student aggregation for search feature
# ============================================================
print("\nBuilding per-academy student search data...")

# Shared date list
date_strs = [d.strftime('%Y-%m-%d') for d in sorted_dates]

# Collect consistent usage columns
all_stu_feat = set()
for date in sorted_dates:
    all_stu_feat.update(daily_frames[date]['usage_cols'])
all_stu_feat_cols = sorted(all_stu_feat)

# Build per-academy student data
acad_stu = {}  # code -> {d: [], t: [], a: [], f: []}
prev_student_vals = {}  # student_code -> {feat: val}

for di, date in enumerate(sorted_dates):
    info = daily_frames[date]
    df_day = info['df']
    usage_cols = info['usage_cols']
    acad_code_col = info['academy_code_col']
    academy_col = info['academy_col']

    if not acad_code_col or acad_code_col not in df_day.columns:
        continue

    # Group students by academy
    acad_groups = df_day.groupby(acad_code_col)
    current_student_vals = {}

    for acad_code, group in acad_groups:
        acad_code = str(acad_code).strip()
        if not acad_code or acad_code == 'nan':
            continue

        if acad_code not in acad_stu:
            acad_stu[acad_code] = {'d': [], 't': [], 'a': []}
            acad_stu[acad_code]['_feat'] = {i: [] for i in range(len(all_stu_feat_cols))}

        ad = acad_stu[acad_code]
        ad['d'].append(di)
        ad['t'].append(len(group))

        # Active students (delta-based)
        active_count = 0
        feat_sums = [0] * len(all_stu_feat_cols)

        for stu_code in group.index:
            stu_feats = {}
            for fi, fc in enumerate(all_stu_feat_cols):
                val = 0
                if fc in group.columns:
                    val = int(pd.to_numeric(group.loc[stu_code, fc] if fc in group.columns else 0, errors='coerce') or 0)
                stu_feats[fc] = val
                feat_sums[fi] += val

            is_active = False
            if stu_code in prev_student_vals:
                for fc in all_stu_feat_cols:
                    if stu_feats.get(fc, 0) > prev_student_vals[stu_code].get(fc, 0):
                        is_active = True
                        break
            elif di > 0:
                if any(v > 0 for v in stu_feats.values()):
                    is_active = True

            if is_active:
                active_count += 1

            current_student_vals[stu_code] = stu_feats

        ad['a'].append(active_count)
        for fi in range(len(all_stu_feat_cols)):
            ad['_feat'][fi].append(feat_sums[fi])

    prev_student_vals = current_student_vals

# Compact: only keep non-zero feature arrays per academy
for code, ad in acad_stu.items():
    f_dict = {}
    for fi, arr in ad['_feat'].items():
        if any(v != 0 for v in arr):
            f_dict[str(fi)] = arr
    ad['f'] = f_dict
    del ad['_feat']

academy_search_stu = {
    'dates': date_strs,
    'feat_cols': all_stu_feat_cols,
    'data': acad_stu,
}

out2 = os.path.join(os.path.dirname(__file__), "academy_search_stu.json")
with open(out2, 'w', encoding='utf-8') as f:
    json.dump(academy_search_stu, f, ensure_ascii=False, separators=(',', ':'))

sz = os.path.getsize(out2)
print(f"Academy student search data saved: {out2} ({sz/1024/1024:.1f} MB, {len(acad_stu)} academies)")
