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

# === TU / AU / PU configuration ===
# PU: numeric columns whose delta > 0 means Premium usage
PU_COLS_KEYWORDS = USAGE_COLS_KEYWORDS  # same as usage keywords
# AU additional: Y/N flag columns; N→Y change counts as Active (free+paid)
AU_YN_COL_NAMES = ['샘플주제과제발급여부', 'AILite진단여부', 'AiPro진단여부', '수시배치표여부', '계열선택검사여부']
# Creation date column (for D7/D28 retention)
CREATION_COL_NAME = '생성일'

def parse_creation_date(s):
    """Parse '2022. 7. 18. PM 6:28:42' → datetime date"""
    if pd.isna(s) or not s:
        return None
    try:
        m = re.match(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.', str(s).strip())
        if m:
            return pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return None
    except:
        return None

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

        # Find Y/N flag columns
        yn_cols = [c for c in cols if c in AU_YN_COL_NAMES]
        # Find creation date column
        creation_col = next((c for c in cols if c == CREATION_COL_NAME or '생성일' in c), None)

        keep_cols = [student_code_col] + usage_cols + yn_cols
        if grade_col: keep_cols.append(grade_col)
        if cat_col: keep_cols.append(cat_col)
        if academy_col: keep_cols.append(academy_col)
        if academy_code_col: keep_cols.append(academy_code_col)
        if creation_col and creation_col not in keep_cols: keep_cols.append(creation_col)

        sub = df[keep_cols].copy()
        sub = sub.rename(columns={student_code_col: 'student_code'})

        # Convert usage cols to numeric
        for uc in usage_cols:
            sub[uc] = pd.to_numeric(sub[uc], errors='coerce').fillna(0)

        # Normalize Y/N cols to uppercase
        for yc in yn_cols:
            sub[yc] = sub[yc].astype(str).str.strip().str.upper()

        # Drop rows with missing student code, then deduplicate
        sub = sub.dropna(subset='student_code')
        sub['student_code'] = sub['student_code'].astype(str)
        sub = sub.drop_duplicates(subset='student_code', keep='last')
        sub = sub.set_index('student_code')

        date = pd.to_datetime(date_str, format='%Y%m%d')
        daily_frames[date] = {
            'df': sub,
            'usage_cols': usage_cols,
            'yn_cols': yn_cols,
            'creation_col': creation_col,
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
# 2. Compute daily TU / AU / PU metrics (delta-based)
# ============================================================
results = []
prev_date = None
# Per-day AU/PU code sets for Rolling calculation
daily_au_sets = {}  # date -> set of student codes
daily_pu_sets = {}  # date -> set of student codes
# Student creation dates (accumulated across CSVs)
student_creation_dates = {}  # student_code -> pd.Timestamp

for date in sorted_dates:
    info = daily_frames[date]
    df_today = info['df']
    usage_cols = info['usage_cols']
    yn_cols = info['yn_cols']
    total_students = len(df_today)

    # Collect student creation dates
    ccol = info['creation_col']
    if ccol and ccol in df_today.columns:
        for stu, val in df_today[ccol].items():
            if stu not in student_creation_dates:
                cd = parse_creation_date(val)
                if cd:
                    student_creation_dates[stu] = cd

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

    # Y/N flag daily totals (count of Y)
    yn_totals = {}
    yn_deltas = {}  # net new Y (N→Y) compared to previous day
    for yc in AU_YN_COL_NAMES:
        yn_totals[f'yn_{yc}'] = 0
        yn_deltas[f'yn_delta_{yc}'] = 0
    for yc in yn_cols:
        if yc in df_today.columns:
            yn_totals[f'yn_{yc}'] = int((df_today[yc] == 'Y').sum())

    # === PU / AU detection ===
    pu_codes = set()  # Premium Users (numeric delta > 0)
    au_codes = set()  # Active Users (PU + Y/N flag changes)
    active_by_feature = {uc: 0 for uc in usage_cols}
    reg_by_feature = {uc: 0 for uc in usage_cols}

    # Registration mask
    acad_code = info['academy_code_col']
    if acad_code and acad_code in df_today.columns:
        reg_mask = df_today[acad_code].astype(str).isin(REG_CODES)
    else:
        reg_mask = pd.Series(False, index=df_today.index)

    if prev_date is not None:
        df_prev = daily_frames[prev_date]['df']
        prev_usage_cols = daily_frames[prev_date]['usage_cols']
        prev_yn_cols = daily_frames[prev_date]['yn_cols']

        # --- Common students ---
        common_students = df_today.index.intersection(df_prev.index)
        common_usage = [c for c in usage_cols if c in prev_usage_cols and c in df_prev.columns]

        if len(common_students) > 0:
            # PU: numeric delta > 0
            if len(common_usage) > 0:
                today_vals = df_today.loc[common_students, common_usage]
                prev_vals = df_prev.loc[common_students, common_usage]
                delta = today_vals - prev_vals
                pu_mask = (delta > 0).any(axis=1)
                pu_codes.update(common_students[pu_mask].tolist())

                reg_cm = reg_mask.reindex(common_students, fill_value=False)
                for uc in common_usage:
                    fa = delta[uc] > 0
                    active_by_feature[uc] = int(fa.sum())
                    reg_by_feature[uc] = int((fa & reg_cm).sum())

            # AU additional: Y/N flag N→Y changes
            common_yn = [c for c in yn_cols if c in prev_yn_cols and c in df_prev.columns]
            yn_change_mask = pd.Series(False, index=common_students)
            for yc in common_yn:
                if yc in df_today.columns and yc in df_prev.columns:
                    today_yn = df_today.loc[common_students, yc]
                    prev_yn = df_prev.loc[common_students, yc]
                    changed = (prev_yn != 'Y') & (today_yn == 'Y')
                    yn_change_mask = yn_change_mask | changed
                    yn_deltas[f'yn_delta_{yc}'] = int(changed.sum())

            au_codes.update(pu_codes)
            au_only = common_students[yn_change_mask & ~common_students.isin(pu_codes)]
            au_codes.update(au_only.tolist())

        # --- New students ---
        new_student_ids = df_today.index.difference(df_prev.index)
        if len(new_student_ids) > 0:
            new_uc = [c for c in usage_cols if c in df_today.columns]
            new_df = df_today.loc[new_student_ids, new_uc] if new_uc else pd.DataFrame(index=new_student_ids)
            new_pu_mask = (new_df > 0).any(axis=1) if len(new_uc) > 0 else pd.Series(False, index=new_student_ids)
            pu_codes.update(new_student_ids[new_pu_mask].tolist())

            new_reg_m = reg_mask.reindex(new_student_ids, fill_value=False)
            for uc in usage_cols:
                if uc in new_df.columns:
                    fa = new_df[uc] > 0
                    active_by_feature[uc] += int(fa.sum())
                    reg_by_feature[uc] += int((fa & new_reg_m).sum())

            # New students AU: any usage > 0 OR any Y/N == Y
            new_yn_mask = pd.Series(False, index=new_student_ids)
            for yc in yn_cols:
                if yc in df_today.columns:
                    new_yn_mask = new_yn_mask | (df_today.loc[new_student_ids, yc] == 'Y')
            new_au_mask = new_pu_mask | new_yn_mask
            au_codes.update(new_student_ids[new_au_mask].tolist())
            # Also add PU new students that might not be in au_codes yet
            au_codes.update(new_student_ids[new_pu_mask].tolist())

    # Store daily code sets
    daily_au_sets[date] = au_codes
    daily_pu_sets[date] = pu_codes

    # Counts
    pu_count = len(pu_codes)
    au_count = len(au_codes)
    active_student_codes = list(au_codes)  # for backward compat (academy summary)

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

    # Split by registration (use AU codes for active breakdown)
    rac = [c for c in active_student_codes if c in reg_mask.index and reg_mask.get(c, False)]
    uac = [c for c in active_student_codes if c not in rac]
    pu_rac = [c for c in pu_codes if c in reg_mask.index and reg_mask.get(c, False)]
    pu_uac = [c for c in pu_codes if c not in pu_rac]

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
        'au': au_count,
        'pu': pu_count,
        'active_students': pu_count,  # backward compat: active_students = PU
        'au_rate': round(au_count / total_students * 100, 2) if total_students > 0 else 0,
        'pu_rate': round(pu_count / total_students * 100, 2) if total_students > 0 else 0,
        'activation_rate': round(pu_count / total_students * 100, 2) if total_students > 0 else 0,
        'n_academies': n_academies,
        'new_students': new_students,
        'active_academies': _acad_str(active_student_codes),
        'reg_total': rt, 'reg_active': ra, 'reg_rate': rr, 'reg_new': reg_new,
        'reg_au': len(rac), 'reg_pu': len(pu_rac),
        'reg_n_academies': r_nacad, 'reg_active_academies': _acad_str(rac),
        'unreg_total': ut, 'unreg_active': ua, 'unreg_rate': ur, 'unreg_new': unreg_new,
        'unreg_au': len(uac), 'unreg_pu': len(pu_uac),
        'unreg_n_academies': u_nacad, 'unreg_active_academies': _acad_str(uac),
        **grade_dist,
        **active_by_feature,
        **{f'reg_{k}': v for k, v in reg_by_feature.items()},
        **{f'unreg_{k}': active_by_feature.get(k, 0) - reg_by_feature.get(k, 0) for k in active_by_feature},
        **cat_dist,
        **yn_totals,
        **yn_deltas,
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
feature_cols = [c for c in daily_df.columns if any(k in c for k in USAGE_COLS_KEYWORDS) and c not in ['total_students','active_students','new_students','n_academies','au','pu'] and not c.startswith('reg_') and not c.startswith('unreg_')]
cat_cols = [c for c in daily_df.columns if c.startswith('cat_')]
yn_total_cols = [c for c in daily_df.columns if c.startswith('yn_') and not c.startswith('yn_delta_')]
yn_delta_cols = [c for c in daily_df.columns if c.startswith('yn_delta_')]

print(f"\nClean daily data: {len(daily_df)} days")
print(f"Feature columns: {feature_cols}")
print(f"Y/N total cols: {yn_total_cols}")
print(f"\nSample (TU/AU/PU):")
print(daily_df[['date','total_students','au','pu','au_rate','pu_rate']].tail(15).to_string())

# ============================================================
# 2b. Rolling WAU / MAU / WPU / MPU
# ============================================================
print("\nComputing Rolling WAU/MAU/WPU/MPU...")

valid_dates = daily_df['date'].tolist()
rolling_wau = []
rolling_mau = []
rolling_wpu = []
rolling_mpu = []
wau_mau_ratio = []
wpu_mpu_ratio = []

for i, date in enumerate(valid_dates):
    # Rolling 7-day window
    w7_start = max(0, i - 6)
    w7_dates = valid_dates[w7_start:i + 1]
    wau_set = set()
    wpu_set = set()
    for d in w7_dates:
        wau_set.update(daily_au_sets.get(d, set()))
        wpu_set.update(daily_pu_sets.get(d, set()))

    # Rolling 28-day window
    w28_start = max(0, i - 27)
    w28_dates = valid_dates[w28_start:i + 1]
    mau_set = set()
    mpu_set = set()
    for d in w28_dates:
        mau_set.update(daily_au_sets.get(d, set()))
        mpu_set.update(daily_pu_sets.get(d, set()))

    _wau = len(wau_set)
    _mau = len(mau_set)
    _wpu = len(wpu_set)
    _mpu = len(mpu_set)

    rolling_wau.append(_wau)
    rolling_mau.append(_mau)
    rolling_wpu.append(_wpu)
    rolling_mpu.append(_mpu)
    wau_mau_ratio.append(round(_wau / _mau, 4) if _mau > 0 else 0)
    wpu_mpu_ratio.append(round(_wpu / _mpu, 4) if _mpu > 0 else 0)

daily_df['rolling_wau'] = rolling_wau
daily_df['rolling_mau'] = rolling_mau
daily_df['rolling_wpu'] = rolling_wpu
daily_df['rolling_mpu'] = rolling_mpu
daily_df['wau_mau_ratio'] = wau_mau_ratio
daily_df['wpu_mpu_ratio'] = wpu_mpu_ratio

print(f"Rolling sample (last 5 days):")
print(daily_df[['date','rolling_wau','rolling_mau','wau_mau_ratio','rolling_wpu','rolling_mpu','wpu_mpu_ratio']].tail(5).to_string())

# ============================================================
# 2c. D7 / D28 Retention
# ============================================================
print(f"\nComputing D7/D28 retention... ({len(student_creation_dates)} students with creation dates)")

# For each day, find students whose D7/D28 window closes on that day
# D7: students whose creation_date + 7 days == today
# Check if they were AU/PU at least once during [creation_date, creation_date+7]
d7_au_count = []
d7_au_total = []
d7_au_rate = []
d28_au_count = []
d28_au_total = []
d28_au_rate = []
d7_pu_count = []
d7_pu_rate = []
d28_pu_count = []
d28_pu_rate = []

# Build student → set of AU/PU dates (only within our data range)
stu_au_dates = {}  # student_code -> set of dates
stu_pu_dates = {}
for d, au_set in daily_au_sets.items():
    for code in au_set:
        if code not in stu_au_dates:
            stu_au_dates[code] = set()
        stu_au_dates[code].add(d)
for d, pu_set in daily_pu_sets.items():
    for code in pu_set:
        if code not in stu_pu_dates:
            stu_pu_dates[code] = set()
        stu_pu_dates[code].add(d)

for date in valid_dates:
    # D7 cohort: students created exactly 7 days ago
    d7_target = date - pd.Timedelta(days=7)
    d7_cohort = [s for s, cd in student_creation_dates.items() if cd.date() == d7_target.date()]
    d7_retained_au = sum(1 for s in d7_cohort if any(
        d7_target < d <= date for d in stu_au_dates.get(s, set())
    ))
    d7_retained_pu = sum(1 for s in d7_cohort if any(
        d7_target < d <= date for d in stu_pu_dates.get(s, set())
    ))
    d7_au_count.append(d7_retained_au)
    d7_au_total.append(len(d7_cohort))
    d7_au_rate.append(round(d7_retained_au / len(d7_cohort) * 100, 2) if d7_cohort else 0)
    d7_pu_count.append(d7_retained_pu)
    d7_pu_rate.append(round(d7_retained_pu / len(d7_cohort) * 100, 2) if d7_cohort else 0)

    # D28 cohort: students created exactly 28 days ago
    d28_target = date - pd.Timedelta(days=28)
    d28_cohort = [s for s, cd in student_creation_dates.items() if cd.date() == d28_target.date()]
    d28_retained_au = sum(1 for s in d28_cohort if any(
        d28_target < d <= date for d in stu_au_dates.get(s, set())
    ))
    d28_retained_pu = sum(1 for s in d28_cohort if any(
        d28_target < d <= date for d in stu_pu_dates.get(s, set())
    ))
    d28_au_count.append(d28_retained_au)
    d28_au_total.append(len(d28_cohort))
    d28_au_rate.append(round(d28_retained_au / len(d28_cohort) * 100, 2) if d28_cohort else 0)
    d28_pu_count.append(d28_retained_pu)
    d28_pu_rate.append(round(d28_retained_pu / len(d28_cohort) * 100, 2) if d28_cohort else 0)

daily_df['d7_au_count'] = d7_au_count
daily_df['d7_au_total'] = d7_au_total
daily_df['d7_au_rate'] = d7_au_rate
daily_df['d7_pu_count'] = d7_pu_count
daily_df['d7_pu_rate'] = d7_pu_rate
daily_df['d28_au_count'] = d28_au_count
daily_df['d28_au_total'] = d28_au_total
daily_df['d28_au_rate'] = d28_au_rate
daily_df['d28_pu_count'] = d28_pu_count
daily_df['d28_pu_rate'] = d28_pu_rate

print(f"D7/D28 retention sample (last 5 days):")
print(daily_df[['date','d7_au_total','d7_au_rate','d7_pu_rate','d28_au_total','d28_au_rate','d28_pu_rate']].tail(5).to_string())

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
    avg_au=('au', 'mean'), avg_pu=('pu', 'mean'),
    avg_au_rate=('au_rate', 'mean'), avg_pu_rate=('pu_rate', 'mean'),
    avg_rolling_wau=('rolling_wau', 'mean'), avg_rolling_mau=('rolling_mau', 'mean'),
    avg_rolling_wpu=('rolling_wpu', 'mean'), avg_rolling_mpu=('rolling_mpu', 'mean'),
    avg_wau_mau=('wau_mau_ratio', 'mean'), avg_wpu_mpu=('wpu_mpu_ratio', 'mean'),
    avg_d7_au_rate=('d7_au_rate', 'mean'), avg_d7_pu_rate=('d7_pu_rate', 'mean'),
    avg_d28_au_rate=('d28_au_rate', 'mean'), avg_d28_pu_rate=('d28_pu_rate', 'mean'),
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
    avg_au=('au', 'mean'), avg_pu=('pu', 'mean'),
    avg_au_rate=('au_rate', 'mean'), avg_pu_rate=('pu_rate', 'mean'),
    avg_rolling_wau=('rolling_wau', 'mean'), avg_rolling_mau=('rolling_mau', 'mean'),
    avg_rolling_wpu=('rolling_wpu', 'mean'), avg_rolling_mpu=('rolling_mpu', 'mean'),
    avg_wau_mau=('wau_mau_ratio', 'mean'), avg_wpu_mpu=('wpu_mpu_ratio', 'mean'),
    avg_d7_au_rate=('d7_au_rate', 'mean'), avg_d7_pu_rate=('d7_pu_rate', 'mean'),
    avg_d28_au_rate=('d28_au_rate', 'mean'), avg_d28_pu_rate=('d28_pu_rate', 'mean'),
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

reg_extra = ['reg_total','reg_active','reg_rate','reg_new','reg_au','reg_pu',
             'reg_n_academies','reg_active_academies',
             'unreg_total','unreg_active','unreg_rate','unreg_new','unreg_au','unreg_pu',
             'unreg_n_academies','unreg_active_academies']
reg_feat = [f'reg_{c}' for c in feature_cols] + [f'unreg_{c}' for c in feature_cols]
new_metric_cols = ['au','pu','au_rate','pu_rate',
                   'rolling_wau','rolling_mau','rolling_wpu','rolling_mpu',
                   'wau_mau_ratio','wpu_mpu_ratio',
                   'd7_au_count','d7_au_total','d7_au_rate','d7_pu_count','d7_pu_rate',
                   'd28_au_count','d28_au_total','d28_au_rate','d28_pu_count','d28_pu_rate']
daily_export_cols = ['date','total_students','active_students','activation_rate',
                     'n_academies','new_students','active_academies','day_of_week','year_month','year_week'] \
                    + new_metric_cols + feature_cols + cat_cols + yn_total_cols + yn_delta_cols \
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
