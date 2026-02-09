import pandas as pd
import os
import glob
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_csv(date_str):
    fname = f"학생활성화현황_{date_str}.csv"
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, encoding='utf-8-sig')
        if len(df.columns) < 10:
            return None
        # Find student code col
        sc = next((c for c in df.columns if '학생' in c and '코드' in c), None)
        if not sc:
            return None
        df = df.dropna(subset=[sc])
        df[sc] = df[sc].astype(str)
        df = df.drop_duplicates(subset=sc, keep='last')
        return df, sc
    except:
        return None

# Load Dec 21, 22, 23
dates_to_check = ['20251220', '20251221', '20251222', '20251223', '20251224']
frames = {}
for ds in dates_to_check:
    result = load_csv(ds)
    if result:
        frames[ds] = result
        print(f"{ds}: {len(result[0])} rows loaded")
    else:
        print(f"{ds}: FAILED to load")

# Compare Dec 21 vs Dec 22
if '20251221' in frames and '20251222' in frames:
    df21, sc21 = frames['20251221']
    df22, sc22 = frames['20251222']

    usage_cols_21 = [c for c in df21.columns if '사용량' in c or '횟수' in c]
    usage_cols_22 = [c for c in df22.columns if '사용량' in c or '횟수' in c]
    common_usage = [c for c in usage_cols_22 if c in usage_cols_21]

    print(f"\n=== Dec 21 vs Dec 22 comparison ===")
    print(f"Dec 21 students: {len(df21)}")
    print(f"Dec 22 students: {len(df22)}")
    print(f"Common usage cols: {common_usage}")

    # Set index
    df21i = df21.set_index(sc21)
    df22i = df22.set_index(sc22)

    # New students on Dec 22
    new_ids = df22i.index.difference(df21i.index)
    print(f"\nNew students on Dec 22: {len(new_ids)}")

    # Common students
    common_ids = df22i.index.intersection(df21i.index)
    print(f"Common students: {len(common_ids)}")

    # Delta for common students
    for uc in common_usage:
        df21i[uc] = pd.to_numeric(df21i[uc], errors='coerce').fillna(0)
        df22i[uc] = pd.to_numeric(df22i[uc], errors='coerce').fillna(0)

    delta = df22i.loc[common_ids, common_usage] - df21i.loc[common_ids, common_usage]
    active_mask = (delta > 0).any(axis=1)
    active_common = active_mask.sum()
    print(f"Common students with increased usage: {active_common}")

    # Per-feature breakdown
    print(f"\nPer-feature active (common students):")
    for uc in common_usage:
        cnt = (delta[uc] > 0).sum()
        print(f"  {uc}: {cnt} students increased")

    # New students with usage > 0
    if len(new_ids) > 0:
        new_df = df22i.loc[new_ids, common_usage]
        new_active = (new_df > 0).any(axis=1).sum()
        print(f"\nNew students with usage > 0: {new_active}")
        for uc in common_usage:
            cnt = (new_df[uc] > 0).sum()
            print(f"  {uc}: {cnt} new students with usage")

    # Who are the active common students? What changed?
    active_ids = delta[active_mask].index
    active_details = df22i.loc[active_ids].copy()

    # Academy distribution of active students
    acad_col = next((c for c in df22.columns if '학원명' in c), None)
    if acad_col:
        acad_dist = active_details[acad_col].value_counts().head(20)
        print(f"\nTop 20 academies with active students on Dec 22:")
        for acad, cnt in acad_dist.items():
            print(f"  {acad}: {cnt}")

    # Grade distribution of active students
    grade_col = next((c for c in df22.columns if '학년' in c), None)
    if grade_col:
        grade_dist = active_details[grade_col].value_counts().sort_index()
        print(f"\nGrade distribution of active students:")
        for g, cnt in grade_dist.items():
            print(f"  학년 {int(g)}: {cnt}")

    # What specific feature drove the spike?
    print(f"\nTotal delta sums (how much total increase):")
    for uc in common_usage:
        total_increase = delta.loc[active_mask, uc].sum()
        print(f"  {uc}: total +{total_increase}")

    # Compare with surrounding days
    print(f"\n=== Surrounding days comparison ===")
    prev_date = None
    for ds in dates_to_check:
        if ds not in frames:
            continue
        df_curr, sc_curr = frames[ds]
        if prev_date and prev_date in frames:
            df_prev, sc_prev = frames[prev_date]
            df_pi = df_prev.set_index(sc_prev)
            df_ci = df_curr.set_index(sc_curr)
            uc_prev = [c for c in df_pi.columns if '사용량' in c or '횟수' in c]
            uc_curr = [c for c in df_ci.columns if '사용량' in c or '횟수' in c]
            uc_common = [c for c in uc_curr if c in uc_prev]
            common = df_ci.index.intersection(df_pi.index)
            for uc in uc_common:
                df_pi[uc] = pd.to_numeric(df_pi[uc], errors='coerce').fillna(0)
                df_ci[uc] = pd.to_numeric(df_ci[uc], errors='coerce').fillna(0)
            d = df_ci.loc[common, uc_common] - df_pi.loc[common, uc_common]
            act = (d > 0).any(axis=1).sum()
            new_s = len(df_ci.index.difference(df_pi.index))
            print(f"  {prev_date} -> {ds}: active_common={act}, new_students={new_s}")
        prev_date = ds

    # Check if Dec 22 new students came from specific academies
    if len(new_ids) > 0 and acad_col:
        new_acad = df22i.loc[new_ids, acad_col].value_counts().head(20)
        print(f"\nTop 20 academies of NEW students on Dec 22:")
        for acad, cnt in new_acad.items():
            print(f"  {acad}: {cnt}")

    # Category distribution of new students
    cat_col = next((c for c in df22.columns if c == '구분'), None)
    if cat_col and len(new_ids) > 0:
        new_cat = df22i.loc[new_ids, cat_col].value_counts()
        print(f"\nCategory of new students on Dec 22:")
        for cat, cnt in new_cat.items():
            print(f"  {cat}: {cnt}")
