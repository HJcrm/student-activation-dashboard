import pandas as pd
import os
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load(ds):
    path = os.path.join(DATA_DIR, f"학생활성화현황_{ds}.csv")
    df = pd.read_csv(path, encoding='utf-8-sig')
    sc = next(c for c in df.columns if '학생' in c and '코드' in c)
    df = df.dropna(subset=[sc])
    df[sc] = df[sc].astype(str)
    df = df.drop_duplicates(subset=sc, keep='last')
    return df, sc

df21, sc21 = load('20251221')
df22, sc22 = load('20251222')

df21i = df21.set_index(sc21)
df22i = df22.set_index(sc22)

new_ids = df22i.index.difference(df21i.index)

acad_col = next(c for c in df22.columns if '학원명' in c)
acad_code = next(c for c in df22.columns if '학원코드' in c or '학원 코드' in c)
cat_col = '구분'
grade_col = next(c for c in df22.columns if '학년' in c)
usage_cols = [c for c in df22.columns if '사용량' in c or '횟수' in c]

new_df = df22i.loc[new_ids]

# Output as JSON for clean encoding
result = {
    "summary": {
        "dec21_total": len(df21),
        "dec22_total": len(df22),
        "new_students": len(new_ids),
        "new_with_usage": int((new_df[usage_cols].apply(pd.to_numeric, errors='coerce').fillna(0) > 0).any(axis=1).sum()),
    },
    "new_students_by_academy": {},
    "new_students_by_category": {},
    "new_students_by_grade": {},
    "new_students_usage_breakdown": {},
    "sample_new_students": [],
}

# Academy breakdown
acad_counts = new_df[acad_col].value_counts()
for a, c in acad_counts.items():
    code = new_df[new_df[acad_col] == a][acad_code].iloc[0] if acad_code in new_df.columns else ''
    result["new_students_by_academy"][f"{a} ({code})"] = int(c)

# Category
for cat, cnt in new_df[cat_col].value_counts().items():
    result["new_students_by_category"][str(cat)] = int(cnt)

# Grade
for g, cnt in new_df[grade_col].value_counts().sort_index().items():
    result["new_students_by_grade"][f"학년 {int(g)}"] = int(cnt)

# Usage column breakdown for new students
for uc in usage_cols:
    vals = pd.to_numeric(new_df[uc], errors='coerce').fillna(0)
    result["new_students_usage_breakdown"][uc] = {
        "count_with_usage": int((vals > 0).sum()),
        "mean": round(float(vals.mean()), 2),
        "max": int(vals.max()),
    }

# Sample
sample = new_df.head(5)[[acad_col, grade_col, cat_col] + usage_cols].reset_index()
for _, row in sample.iterrows():
    result["sample_new_students"].append({str(k): str(v) for k, v in row.items()})

out = os.path.join(os.path.dirname(__file__), "dec22_analysis.json")
with open(out, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("Saved to dec22_analysis.json")
