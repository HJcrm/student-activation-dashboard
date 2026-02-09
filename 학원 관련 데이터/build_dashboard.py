import pandas as pd
import os
import glob
import json
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
print(f"Total CSV files: {len(files)}")

# Load registered academy codes
_REG_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "가입학원_목록.csv")
REG_CODES = set()
if os.path.exists(_REG_CSV):
    _rdf = pd.read_csv(_REG_CSV, encoding='utf-8-sig')
    REG_CODES = set(_rdf.iloc[:, 2].astype(str).str.strip().tolist())
    print(f"Registered academy codes loaded: {len(REG_CODES)}")
else:
    print("Warning: registered academy list not found")

# Usage columns (numeric, cumulative) for delta-based active detection
USAGE_KEYWORDS = ['사용량', '진행량', '검사량', '생성량', '승인량', '거절량', '업로드량', '분석량']

daily_frames = {}
skipped = []

for f in files:
    fname = os.path.basename(f)
    dm = re.search(r'(\d{8})', fname)
    if not dm:
        continue
    ds = dm.group(1)
    try:
        df = pd.read_csv(f, encoding='utf-8-sig')
        if len(df.columns) < 10 or len(df) == 0:
            skipped.append(ds)
            continue
        cols = list(df.columns)
        # Academy code column
        code_col = next((c for c in cols if '학원코드' in c), None)
        if not code_col:
            skipped.append(ds)
            continue

        # Usage columns
        usage_cols = [c for c in cols if any(k in c for k in USAGE_KEYWORDS)]

        df = df.dropna(subset=[code_col])
        df[code_col] = df[code_col].astype(str)
        df = df.drop_duplicates(subset=code_col, keep='last')

        for uc in usage_cols:
            df[uc] = pd.to_numeric(df[uc], errors='coerce').fillna(0)

        df = df.set_index(code_col)
        date = pd.to_datetime(ds, format='%Y%m%d')
        daily_frames[date] = {'df': df, 'usage_cols': usage_cols, 'cols': cols}
    except Exception as e:
        skipped.append(f"{ds}: {e}")

sorted_dates = sorted(daily_frames.keys())
print(f"Valid days: {len(sorted_dates)}, Skipped: {len(skipped)}")

# ============================================================
# Compute daily metrics (delta-based active)
# ============================================================
results = []
prev_date = None

for date in sorted_dates:
    info = daily_frames[date]
    df_today = info['df']
    usage_cols = info['usage_cols']
    cols = info['cols']
    total_inst = len(df_today)

    # Registered students column
    reg_col = next((c for c in cols if '등록학생수' in c), None)
    total_registered_students = 0
    if reg_col and reg_col in df_today.columns:
        total_registered_students = int(pd.to_numeric(df_today[reg_col], errors='coerce').fillna(0).sum())

    # Storage usage
    storage_col = next((c for c in cols if '스토리지사용여부' in c), None)
    storage_yes = 0
    if storage_col and storage_col in df_today.columns:
        storage_yes = int((df_today[storage_col].astype(str).str.strip().str.upper() == 'Y').sum())

    # 등록권구매여부
    purchase_col = next((c for c in cols if '등록권구매여부' in c), None)
    purchase_yes = 0
    if purchase_col and purchase_col in df_today.columns:
        purchase_yes = int((df_today[purchase_col].astype(str).str.strip().str.upper() == 'Y').sum())

    # Active institutions (delta-based)
    active_inst = 0
    active_by_feature = {uc: 0 for uc in usage_cols}
    reg_by_feature = {uc: 0 for uc in usage_cols}
    active_codes = []

    if prev_date is not None:
        df_prev = daily_frames[prev_date]['df']
        prev_usage = daily_frames[prev_date]['usage_cols']
        common_usage = [c for c in usage_cols if c in prev_usage and c in df_prev.columns]
        common_ids = df_today.index.intersection(df_prev.index)

        if len(common_ids) > 0 and len(common_usage) > 0:
            delta = df_today.loc[common_ids, common_usage] - df_prev.loc[common_ids, common_usage]
            active_mask = (delta > 0).any(axis=1)
            active_inst = int(active_mask.sum())
            active_codes.extend(common_ids[active_mask].tolist())
            reg_common = common_ids.isin(REG_CODES)
            for uc in common_usage:
                fa = delta[uc] > 0
                active_by_feature[uc] = int(fa.sum())
                reg_by_feature[uc] = int((fa & reg_common).sum())

        # New institutions with usage > 0
        new_ids = df_today.index.difference(df_prev.index)
        if len(new_ids) > 0:
            new_uc = [c for c in usage_cols if c in df_today.columns]
            new_df = df_today.loc[new_ids, new_uc]
            new_active_mask = (new_df > 0).any(axis=1)
            new_active = int(new_active_mask.sum())
            active_inst += new_active
            active_codes.extend(new_ids[new_active_mask].tolist())
            new_reg = new_ids.isin(REG_CODES)
            for uc in new_uc:
                fa = new_df[uc] > 0
                active_by_feature[uc] += int(fa.sum())
                reg_by_feature[uc] += int((fa & new_reg).sum())

    # Active names (all / reg / unreg)
    name_col = next((c for c in cols if '학원명' in c), None)
    def _names_str(codes):
        if not name_col or name_col not in df_today.columns or not codes:
            return ''
        vc = [c for c in codes if c in df_today.index]
        if not vc: return ''
        ns = sorted(set(df_today.loc[vc, name_col].dropna().tolist()))
        s = '<br>'.join(ns[:10])
        if len(ns) > 10: s += f'<br>외 {len(ns)-10}개'
        return s

    rac = [c for c in active_codes if c in REG_CODES]
    uac = [c for c in active_codes if c not in REG_CODES]

    # Registration breakdown
    rm = df_today.index.isin(REG_CODES)
    rt = int(rm.sum()); ut = total_inst - rt
    ra = len(rac); ua = len(uac)
    rr = round(ra / rt * 100, 2) if rt > 0 else 0
    ur = round(ua / ut * 100, 2) if ut > 0 else 0
    rs = int(pd.to_numeric(df_today.loc[rm, reg_col], errors='coerce').fillna(0).sum()) if reg_col and reg_col in df_today.columns else 0
    us = total_registered_students - rs
    rsto = int((df_today.loc[rm, storage_col].astype(str).str.strip().str.upper() == 'Y').sum()) if storage_col and storage_col in df_today.columns else 0
    usto = storage_yes - rsto
    rpur = int((df_today.loc[rm, purchase_col].astype(str).str.strip().str.upper() == 'Y').sum()) if purchase_col and purchase_col in df_today.columns else 0
    upur = purchase_yes - rpur

    # New institutions count
    new_inst = 0; reg_new = 0; unreg_new = 0
    if prev_date is not None:
        _ni = df_today.index.difference(daily_frames[prev_date]['df'].index)
        new_inst = len(_ni)
        reg_new = int(_ni.isin(REG_CODES).sum())
        unreg_new = new_inst - reg_new

    row = {
        'date': date,
        'total_institutions': total_inst,
        'active_institutions': active_inst,
        'activation_rate': round(active_inst / total_inst * 100, 2) if total_inst > 0 else 0,
        'new_institutions': new_inst,
        'total_registered_students': total_registered_students,
        'storage_users': storage_yes,
        'purchase_users': purchase_yes,
        'active_names': _names_str(active_codes),
        'reg_total': rt, 'reg_active': ra, 'reg_rate': rr, 'reg_new': reg_new,
        'reg_students': rs, 'reg_storage': rsto, 'reg_purchase': rpur,
        'reg_active_names': _names_str(rac),
        'unreg_total': ut, 'unreg_active': ua, 'unreg_rate': ur, 'unreg_new': unreg_new,
        'unreg_students': us, 'unreg_storage': usto, 'unreg_purchase': upur,
        'unreg_active_names': _names_str(uac),
        **active_by_feature,
        **{f'reg_{k}': v for k, v in reg_by_feature.items()},
        **{f'unreg_{k}': active_by_feature.get(k, 0) - reg_by_feature.get(k, 0) for k in active_by_feature},
    }
    results.append(row)
    prev_date = date

daily_df = pd.DataFrame(results).sort_values('date').reset_index(drop=True)
daily_df = daily_df[daily_df['total_institutions'] >= 10].reset_index(drop=True)

daily_df['day_of_week'] = daily_df['date'].dt.day_name()
daily_df['year_month'] = daily_df['date'].dt.to_period('M').astype(str)
daily_df['year_week'] = daily_df['date'].dt.strftime('%Y-W%W')

feature_cols = [c for c in daily_df.columns if any(k in c for k in USAGE_KEYWORDS) and not c.startswith('reg_') and not c.startswith('unreg_')]

print(f"\nClean daily data: {len(daily_df)} days")
print(f"Feature columns: {feature_cols}")
print(f"\nSample:")
print(daily_df[['date','total_institutions','active_institutions','activation_rate','new_institutions','total_registered_students']].head(10).to_string())
print(f"\nTail:")
print(daily_df[['date','total_institutions','active_institutions','activation_rate','new_institutions','total_registered_students']].tail(5).to_string())

# ============================================================
# Export JSON
# ============================================================
def safe_val(v):
    if isinstance(v, pd.Timestamp): return v.strftime('%Y-%m-%d')
    if hasattr(v, 'item'): return v.item()
    if isinstance(v, float) and pd.isna(v): return 0
    return v

reg_extra = ['reg_total','reg_active','reg_rate','reg_new','reg_students','reg_storage','reg_purchase','reg_active_names',
             'unreg_total','unreg_active','unreg_rate','unreg_new','unreg_students','unreg_storage','unreg_purchase','unreg_active_names']
reg_feat = [f'reg_{c}' for c in feature_cols] + [f'unreg_{c}' for c in feature_cols]
export_cols = ['date','total_institutions','active_institutions','activation_rate',
               'new_institutions','total_registered_students','storage_users','purchase_users',
               'active_names','day_of_week','year_month','year_week'] + feature_cols + reg_extra + reg_feat

dc = daily_df[[c for c in export_cols if c in daily_df.columns]].copy()
dc['date'] = dc['date'].dt.strftime('%Y-%m-%d')
dc = dc.fillna(0)

records = dc.to_dict(orient='records')
for r in records:
    for k, v in r.items():
        r[k] = safe_val(v)

dashboard_data = {
    'daily': records,
    'feature_cols': feature_cols,
    'summary': {
        'total_days': len(daily_df),
        'date_start': daily_df['date'].min().strftime('%Y-%m-%d'),
        'date_end': daily_df['date'].max().strftime('%Y-%m-%d'),
        'latest_total': int(daily_df.iloc[-1]['total_institutions']),
        'latest_active': int(daily_df.iloc[-1]['active_institutions']),
        'latest_rate': float(daily_df.iloc[-1]['activation_rate']),
        'latest_students': int(daily_df.iloc[-1]['total_registered_students']),
        'avg_daily_active': round(float(daily_df['active_institutions'].mean()), 1),
        'avg_activation_rate': round(float(daily_df['activation_rate'].mean()), 2),
        'total_new_all': int(daily_df['new_institutions'].sum()),
    }
}

out = os.path.join(os.path.dirname(__file__), "dashboard_data.json")
with open(out, 'w', encoding='utf-8') as f:
    json.dump(dashboard_data, f, ensure_ascii=False, default=str)

print(f"\nJSON saved: {out}")
print(f"Summary: {json.dumps(dashboard_data['summary'], ensure_ascii=False, indent=2)}")
