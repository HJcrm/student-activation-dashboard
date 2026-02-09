import json
import os

BASE = os.path.dirname(__file__)

with open(os.path.join(BASE, "학생 관련 데이터", "dashboard_data_v2.json"), 'r', encoding='utf-8') as f:
    student_data = json.load(f)
with open(os.path.join(BASE, "학원 관련 데이터", "dashboard_data.json"), 'r', encoding='utf-8') as f:
    inst_data = json.load(f)

# Load academy search data
with open(os.path.join(BASE, "학원 관련 데이터", "academy_search_inst.json"), 'r', encoding='utf-8') as f:
    acad_inst_search = json.load(f)
with open(os.path.join(BASE, "학생 관련 데이터", "academy_search_stu.json"), 'r', encoding='utf-8') as f:
    acad_stu_search = json.load(f)

# Build academy list for autocomplete, merging names from both sources
# Supplement missing names from student data (which has academy_name per student row)
import pandas as pd, glob, re as _re
_stu_dir = os.path.join(BASE, "학생 관련 데이터", "data")
_stu_files = sorted(glob.glob(os.path.join(_stu_dir, "*.csv")))
_name_map = {}
if _stu_files:
    # Use the latest student CSV for name mapping
    _latest = _stu_files[-1]
    try:
        _sdf = pd.read_csv(_latest, encoding='utf-8-sig')
        _acol = next((c for c in _sdf.columns if '학원코드' in c), None)
        _ncol = next((c for c in _sdf.columns if '학원명' in c), None)
        if _acol and _ncol:
            for _, row in _sdf.drop_duplicates(subset=_acol).iterrows():
                code = str(row[_acol]).strip()
                name = row[_ncol]
                if pd.notna(name) and str(name).strip():
                    _name_map[code] = str(name).strip()
            print(f"Student name mapping loaded: {len(_name_map)} academies")
    except Exception as e:
        print(f"Warning: could not load student names: {e}")

# Also load names from registered academy list
_reg_csv = os.path.join(BASE, "가입학원_목록.csv")
_reg_name_map = {}
if os.path.exists(_reg_csv):
    try:
        _rdf = pd.read_csv(_reg_csv, encoding='utf-8-sig')
        for _, row in _rdf.iterrows():
            code = str(row.iloc[2]).strip()
            name = str(row.iloc[0]).strip()
            if code and name:
                _reg_name_map[code] = name
    except: pass

meta = acad_inst_search.get('meta', {})
academy_list = []
for code, info in meta.items():
    name = info['n'] or _name_map.get(code, '') or _reg_name_map.get(code, '')
    academy_list.append({'c': code, 'n': name, 'r': info['r']})
for code in acad_stu_search.get('data', {}):
    if code not in meta:
        name = _name_map.get(code, '') or _reg_name_map.get(code, '')
        academy_list.append({'c': code, 'n': name, 'r': 0})
academy_list.sort(key=lambda x: x['n'])

# Write combined academy search JSON (separate file for lazy loading)
combined_search = {'inst': acad_inst_search, 'stu': acad_stu_search}
acad_search_path = os.path.join(BASE, "academy_search.json")
with open(acad_search_path, 'w', encoding='utf-8') as f:
    json.dump(combined_search, f, ensure_ascii=False, separators=(',', ':'))
sz = os.path.getsize(acad_search_path)
print(f"Combined academy search JSON: {sz/1024/1024:.1f} MB")

OUTPUT = os.path.join(BASE, "학쫑_통합_대시보드.html")

student_json = json.dumps(student_data['daily'], ensure_ascii=False)
student_feat_json = json.dumps(student_data['feature_cols'], ensure_ascii=False)
inst_json = json.dumps(inst_data['daily'], ensure_ascii=False)
inst_feat_json = json.dumps(inst_data['feature_cols'], ensure_ascii=False)
academy_list_json = json.dumps(academy_list, ensure_ascii=False)

s_start = student_data['summary']['date_start']
s_end = student_data['summary']['date_end']
i_start = inst_data['summary']['date_start']
i_end = inst_data['summary']['date_end']
all_start = min(s_start, i_start)
all_end = max(s_end, i_end)

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>학쫑 통합 대시보드</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI','Malgun Gothic',sans-serif;background:#0a0f1e;color:#e2e8f0}}

  .header{{background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);padding:24px 36px;border-bottom:1px solid rgba(71,85,105,0.4);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;box-shadow:0 4px 24px rgba(0,0,0,0.4)}}
  .header h1{{font-size:24px;font-weight:700;color:#f8fafc;letter-spacing:-0.5px}}
  .mode-bar{{display:flex;gap:0;border-radius:12px;overflow:hidden;border:1px solid rgba(71,85,105,0.5)}}
  .mode-btn{{padding:11px 30px;background:rgba(30,41,59,0.8);color:#94a3b8;border:none;cursor:pointer;font-size:14px;font-weight:600;font-family:inherit;transition:all .3s ease}}
  .mode-btn:hover{{background:rgba(51,65,85,0.8);color:#e2e8f0}}
  .mode-btn.active-student{{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;box-shadow:0 0 20px rgba(59,130,246,0.3)}}
  .mode-btn.active-inst{{background:linear-gradient(135deg,#8b5cf6,#7c3aed);color:#fff;box-shadow:0 0 20px rgba(139,92,246,0.3)}}

  .container{{max-width:1440px;margin:0 auto;padding:24px}}
  .note-box{{border-radius:10px;padding:14px 20px;margin-bottom:20px;font-size:13px;backdrop-filter:blur(5px)}}
  .note-box.student{{background:rgba(30,41,59,0.7);border:1px solid rgba(245,158,11,0.4);color:#fbbf24}}
  .note-box.student strong{{color:#f59e0b}}
  .note-box.inst{{background:rgba(30,41,59,0.7);border:1px solid rgba(139,92,246,0.4);color:#c4b5fd}}
  .note-box.inst strong{{color:#a78bfa}}

  .date-bar{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:rgba(30,41,59,0.6);border:1px solid rgba(51,65,85,0.5);border-radius:12px;padding:16px 20px;margin-bottom:20px;backdrop-filter:blur(5px)}}
  .date-bar label{{font-size:12px;color:#94a3b8;font-weight:500}}
  .date-bar input[type=date]{{background:rgba(15,23,42,0.8);border:1px solid rgba(71,85,105,0.6);border-radius:8px;color:#e2e8f0;padding:7px 12px;font-size:13px;font-family:inherit;transition:border-color .2s}}
  .date-bar input[type=date]:focus{{border-color:#3b82f6;outline:none}}
  .date-bar input[type=date]::-webkit-calendar-picker-indicator{{filter:invert(0.7)}}
  .preset-btn{{padding:7px 16px;border:1px solid rgba(71,85,105,0.6);border-radius:8px;background:rgba(15,23,42,0.6);color:#94a3b8;cursor:pointer;font-size:12px;font-weight:500;transition:all .2s ease}}
  .preset-btn:hover{{background:rgba(51,65,85,0.6);color:#e2e8f0;transform:translateY(-1px)}}
  .preset-btn.active{{color:#fff;border-color:currentColor;box-shadow:0 2px 8px rgba(0,0,0,0.2)}}
  .date-bar .sep{{color:#475569;font-size:16px}}
  .date-bar .range-info{{font-size:12px;color:#64748b;margin-left:auto}}
  .outlier-toggle{{display:flex;align-items:center;gap:8px;margin-left:8px;padding-left:12px;border-left:1px solid rgba(51,65,85,0.5)}}
  .outlier-toggle label{{font-size:12px;color:#94a3b8;cursor:pointer;user-select:none}}
  .switch{{position:relative;width:38px;height:20px;flex-shrink:0}}
  .switch input{{opacity:0;width:0;height:0}}
  .slider{{position:absolute;cursor:pointer;inset:0;background:#475569;border-radius:20px;transition:.3s}}
  .slider::before{{content:'';position:absolute;width:16px;height:16px;left:2px;bottom:2px;background:#e2e8f0;border-radius:50%;transition:.3s}}
  .switch input:checked+.slider{{background:#3b82f6}}
  .switch input:checked+.slider::before{{transform:translateX(16px)}}
  .outlier-info{{font-size:11px;color:#f87171;margin-left:4px}}

  .reg-filter{{display:flex;gap:0;border-radius:10px;overflow:hidden;border:1px solid rgba(71,85,105,0.5);margin-left:12px}}
  .reg-btn{{padding:7px 14px;background:rgba(15,23,42,0.6);color:#94a3b8;border:none;border-right:1px solid rgba(71,85,105,0.3);cursor:pointer;font-size:12px;font-weight:500;transition:all .2s;font-family:inherit}}
  .reg-btn:last-child{{border-right:none}}
  .reg-btn:hover{{background:rgba(51,65,85,0.5);color:#e2e8f0}}
  .reg-btn.active{{background:rgba(59,130,246,0.25);color:#60a5fa;font-weight:600}}

  .kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}}
  .kpi{{background:linear-gradient(145deg,rgba(30,41,59,0.95),rgba(30,41,59,0.6));border-radius:14px;padding:20px;border:1px solid rgba(51,65,85,0.5);transition:all .3s ease;position:relative;overflow:hidden}}
  .kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0}}
  .kpi:nth-child(1)::before{{background:linear-gradient(90deg,#3b82f6,#60a5fa)}}
  .kpi:nth-child(2)::before{{background:linear-gradient(90deg,#4ade80,#22c55e)}}
  .kpi:nth-child(3)::before{{background:linear-gradient(90deg,#f59e0b,#fbbf24)}}
  .kpi:nth-child(4)::before{{background:linear-gradient(90deg,#e879f9,#a855f7)}}
  .kpi:nth-child(5)::before{{background:linear-gradient(90deg,#818cf8,#6366f1)}}
  .kpi:hover{{transform:translateY(-3px);box-shadow:0 8px 25px rgba(0,0,0,0.3);border-color:rgba(71,85,105,0.8)}}
  .kpi .label{{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.8px;font-weight:600}}
  .kpi .value{{font-size:28px;font-weight:700;color:#f8fafc;margin:8px 0 4px;letter-spacing:-0.5px}}
  .kpi .sub{{font-size:11px}}
  .up{{color:#4ade80}} .down{{color:#f87171}} .neutral{{color:#94a3b8}}

  .tab-bar{{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap;background:rgba(15,23,42,0.4);padding:6px;border-radius:14px;border:1px solid rgba(51,65,85,0.3)}}
  .tab-btn{{padding:9px 22px;border:none;border-radius:10px;background:transparent;color:#94a3b8;cursor:pointer;font-size:13px;font-weight:500;transition:all .25s ease}}
  .tab-btn:hover{{background:rgba(51,65,85,0.5);color:#e2e8f0}}
  .tab-btn.active{{color:#fff;box-shadow:0 2px 10px rgba(0,0,0,0.25)}}

  .chart-section{{margin-bottom:20px}}
  .card{{background:linear-gradient(180deg,rgba(30,41,59,0.9) 0%,rgba(30,41,59,0.7) 100%);border-radius:14px;padding:22px;border:1px solid rgba(51,65,85,0.5);margin-bottom:16px;transition:all .3s ease;box-shadow:0 2px 12px rgba(0,0,0,0.15)}}
  .card:hover{{border-color:rgba(71,85,105,0.7);box-shadow:0 4px 20px rgba(0,0,0,0.25)}}
  .card h3{{font-size:15px;color:#f8fafc;margin-bottom:12px;font-weight:600}}
  .row2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  @media(max-width:900px){{.row2{{grid-template-columns:1fr}}}}
  .plot{{width:100%;height:380px}}.plot-tall{{width:100%;height:440px}}
  .hidden{{display:none}}

  .tbl-wrap{{max-height:700px;overflow:auto;border-radius:10px;border:1px solid rgba(51,65,85,0.5)}}
  .tbl-wrap::-webkit-scrollbar{{width:8px;height:8px}}
  .tbl-wrap::-webkit-scrollbar-track{{background:rgba(30,41,59,0.5)}}
  .tbl-wrap::-webkit-scrollbar-thumb{{background:#475569;border-radius:4px}}
  .tbl-wrap::-webkit-scrollbar-thumb:hover{{background:#64748b}}
  .data-tbl{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}
  .data-tbl thead{{position:sticky;top:0;z-index:2}}
  .data-tbl th{{background:linear-gradient(180deg,#334155,#2d3a4d);color:#e2e8f0;padding:11px 14px;text-align:right;cursor:pointer;user-select:none;border-bottom:2px solid rgba(71,85,105,0.6);font-weight:600;transition:background .2s}}
  .data-tbl th:first-child{{text-align:left;position:sticky;left:0;z-index:3;background:linear-gradient(180deg,#334155,#2d3a4d)}}
  .data-tbl th:hover{{background:#475569}}
  .data-tbl th .arrow{{font-size:10px;margin-left:4px;color:#94a3b8}}
  .data-tbl td{{padding:8px 14px;text-align:right;border-bottom:1px solid #1e293b}}
  .data-tbl td:first-child{{text-align:left;font-weight:500;position:sticky;left:0;background:#0a0f1e;z-index:1}}
  .data-tbl tbody tr{{background:#0a0f1e;transition:background .15s}}
  .data-tbl tbody tr:hover{{background:rgba(30,41,59,0.8)}}
  .data-tbl tbody tr:nth-child(even){{background:#0d1425}}
  .data-tbl tbody tr:nth-child(even):hover{{background:rgba(30,41,59,0.8)}}
  .data-tbl tbody tr:nth-child(even) td:first-child{{background:#0d1425}}
  .data-tbl tbody tr:hover td:first-child{{background:rgba(30,41,59,0.8)}}
  .tbl-toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:10px}}
  .tbl-toolbar .cnt{{font-size:12px;color:#64748b}}
  .csv-btn{{padding:7px 16px;border:1px solid rgba(71,85,105,0.6);border-radius:8px;background:rgba(15,23,42,0.6);color:#94a3b8;cursor:pointer;font-size:12px;font-weight:500;transition:all .2s ease}}
  .csv-btn:hover{{background:rgba(51,65,85,0.6);color:#e2e8f0;transform:translateY(-1px)}}

  .search-wrap{{position:relative;display:flex;align-items:center;gap:8px}}
  .search-input{{background:rgba(15,23,42,0.8);border:1px solid rgba(71,85,105,0.6);border-radius:8px;color:#e2e8f0;padding:8px 14px 8px 36px;font-size:13px;font-family:inherit;width:260px;transition:border-color .2s,width .2s}}
  .search-input:focus{{border-color:#3b82f6;outline:none;width:320px}}
  .search-input::placeholder{{color:#64748b}}
  .search-icon{{position:absolute;left:12px;color:#64748b;font-size:14px;pointer-events:none}}
  .search-dropdown{{position:absolute;top:100%;left:0;right:0;margin-top:4px;background:#1e293b;border:1px solid rgba(71,85,105,0.7);border-radius:10px;max-height:320px;overflow-y:auto;z-index:100;box-shadow:0 8px 30px rgba(0,0,0,0.5);display:none}}
  .search-dropdown.open{{display:block}}
  .search-item{{padding:10px 14px;cursor:pointer;font-size:13px;border-bottom:1px solid rgba(51,65,85,0.3);display:flex;align-items:center;gap:8px;transition:background .15s}}
  .search-item:last-child{{border-bottom:none}}
  .search-item:hover,.search-item.selected{{background:rgba(59,130,246,0.15)}}
  .search-item .code{{color:#94a3b8;font-family:monospace;font-size:12px;min-width:60px}}
  .search-item .name{{color:#e2e8f0;flex:1}}
  .search-item .badge{{font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600}}
  .search-item .badge.reg{{background:rgba(74,222,128,0.15);color:#4ade80}}
  .search-item .badge.unreg{{background:rgba(148,163,184,0.15);color:#94a3b8}}
  .search-dropdown::-webkit-scrollbar{{width:6px}}
  .search-dropdown::-webkit-scrollbar-track{{background:transparent}}
  .search-dropdown::-webkit-scrollbar-thumb{{background:#475569;border-radius:3px}}

  .acad-header{{display:flex;align-items:center;gap:16px;margin-bottom:20px;flex-wrap:wrap}}
  .acad-title{{font-size:20px;font-weight:700;color:#f8fafc}}
  .acad-code{{font-family:monospace;font-size:14px;color:#94a3b8;background:rgba(51,65,85,0.5);padding:4px 10px;border-radius:6px}}
  .acad-badge{{font-size:12px;padding:4px 10px;border-radius:6px;font-weight:600}}
  .acad-badge.reg{{background:rgba(74,222,128,0.15);color:#4ade80}}
  .acad-badge.unreg{{background:rgba(148,163,184,0.15);color:#94a3b8}}
  .acad-close{{margin-left:auto;padding:8px 18px;border:1px solid rgba(71,85,105,0.6);border-radius:8px;background:rgba(15,23,42,0.6);color:#94a3b8;cursor:pointer;font-size:13px;font-weight:500;transition:all .2s;font-family:inherit}}
  .acad-close:hover{{background:rgba(51,65,85,0.6);color:#e2e8f0}}
  .acad-loading{{text-align:center;padding:60px 20px;color:#94a3b8;font-size:14px}}
</style>
</head>
<body>
<div class="header">
  <h1>학쫑 통합 대시보드</h1>
  <div class="search-wrap" id="searchWrap">
    <span class="search-icon">&#128269;</span>
    <input type="text" class="search-input" id="searchInput" placeholder="학원 코드 또는 이름으로 검색..." autocomplete="off" oninput="onSearchInput()" onfocus="onSearchFocus()" onkeydown="onSearchKey(event)">
    <div class="search-dropdown" id="searchDropdown"></div>
  </div>
  <div class="mode-bar">
    <button class="mode-btn active-student" id="modeStudent" onclick="switchMode('student')">학생 활성화</button>
    <button class="mode-btn" id="modeInst" onclick="switchMode('inst')">학원 활성화</button>
  </div>
</div>
<div class="container">

  <div class="note-box student" id="noteStudent">
    <strong>PU (Premium User):</strong> 전일 대비 수치형 데이터(열람권·발급권·주제발급·학쫑GPT) 증가 학생 &nbsp;|&nbsp;
    <strong>AU (Active User):</strong> PU + Y/N 플래그(샘플주제·AI진단·수시배치·계열선택) N→Y 변경 학생 &nbsp;|&nbsp;
    <strong>TU:</strong> 전체 등록 학생
  </div>
  <div class="note-box inst hidden" id="noteInst">
    <strong>활성 학원 기준:</strong> 전일 대비 수치형 사용량(발급권·열람권·초안작성·생기부·배치표·계열검사·GPT 등) 중 하나라도 증가한 학원.
  </div>

  <div class="date-bar">
    <label>시작</label><input type="date" id="startDate" value="{all_start}" min="{all_start}" max="{all_end}">
    <span class="sep">~</span>
    <label>종료</label><input type="date" id="endDate" value="{all_end}" min="{all_start}" max="{all_end}">
    <button class="preset-btn" onclick="setRange(7)">최근 7일</button>
    <button class="preset-btn" onclick="setRange(14)">최근 14일</button>
    <button class="preset-btn" onclick="setRange(30)">최근 30일</button>
    <button class="preset-btn" onclick="setRange(90)">최근 90일</button>
    <button class="preset-btn" onclick="setRange(180)">최근 6개월</button>
    <button class="preset-btn active" onclick="setRange(0)">전체</button>
    <span class="range-info" id="rangeInfo"></span>
    <div class="reg-filter">
      <button class="reg-btn active" onclick="setRegFilter('all',this)">전체</button>
      <button class="reg-btn" onclick="setRegFilter('reg',this)">가입학원만</button>
      <button class="reg-btn" onclick="setRegFilter('unreg',this)">비가입학원만</button>
    </div>
    <div class="outlier-toggle">
      <label class="switch"><input type="checkbox" id="outlierToggle" onchange="renderAll()"><span class="slider"></span></label>
      <label for="outlierToggle">이상치 제외</label>
      <span class="outlier-info" id="outlierInfo"></span>
    </div>
  </div>

  <div class="kpi-row" id="kpiRow"></div>

  <div class="tab-bar" id="tabBar"></div>

  <div id="tab-daily" class="chart-section">
    <div class="row2">
      <div class="card"><h3 id="hDA">일별 활성 수</h3><div id="d-active" class="plot"></div></div>
      <div class="card"><h3>일별 활성화율 (%)</h3><div id="d-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3 id="hDT">일별 총 수</h3><div id="d-total" class="plot"></div></div>
      <div class="card"><h3 id="hDN">일별 신규</h3><div id="d-new" class="plot"></div></div>
    </div>
    <div class="card" id="extraDailyCard"><h3 id="hDE"></h3><div id="d-extra" class="plot"></div></div>
  </div>

  <div id="tab-weekly" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3 id="hWA">주별 평균 활성</h3><div id="w-active" class="plot"></div></div>
      <div class="card"><h3>주별 평균 활성화율 (%)</h3><div id="w-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3 id="hWM">주별 최대 활성</h3><div id="w-max" class="plot"></div></div>
      <div class="card"><h3 id="hWN">주별 신규</h3><div id="w-new" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-monthly" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3 id="hMA">월별 평균 활성</h3><div id="m-active" class="plot"></div></div>
      <div class="card"><h3>월별 평균 활성화율 (%)</h3><div id="m-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3 id="hMM">월별 최대 활성</h3><div id="m-max" class="plot"></div></div>
      <div class="card"><h3 id="hMN">월별 신규</h3><div id="m-new" class="plot"></div></div>
    </div>
    <div class="card"><h3 id="hMT">월별 총 수 추이</h3><div id="m-total" class="plot"></div></div>
  </div>

  <div id="tab-features" class="chart-section hidden">
    <div class="card"><h3 id="hFT">기능별 일별 활성 수</h3><div id="f-trend" class="plot-tall"></div></div>
    <div class="card"><h3 id="hFB">기간 내 기능별 평균 활성</h3><div id="f-bar" class="plot"></div></div>
  </div>

  <div id="tab-extra" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3 id="hE1"></h3><div id="e1" class="plot"></div></div>
      <div class="card"><h3 id="hE2"></h3><div id="e2" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-users" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3>일별 AU / PU</h3><div id="u-aupu" class="plot"></div></div>
      <div class="card"><h3>일별 AU Rate / PU Rate (%)</h3><div id="u-rates" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>Rolling WAU / MAU (7일/28일 순 이용자)</h3><div id="u-waumau" class="plot"></div></div>
      <div class="card"><h3>Rolling WPU / MPU (7일/28일 순 이용자)</h3><div id="u-wpumpu" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>Stickiness Ratio (WAU/MAU, WPU/MPU)</h3><div id="u-sticky" class="plot"></div></div>
      <div class="card"><h3>Y/N 플래그 일별 Y 수</h3><div id="u-yn" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-retention" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3>D7 리텐션율 (가입 후 7일 내 활동 비율)</h3><div id="r-d7" class="plot"></div></div>
      <div class="card"><h3>D28 리텐션율 (가입 후 28일 내 활동 비율)</h3><div id="r-d28" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>D7 코호트 크기 (7일 전 가입 학생 수)</h3><div id="r-d7n" class="plot"></div></div>
      <div class="card"><h3>D28 코호트 크기 (28일 전 가입 학생 수)</h3><div id="r-d28n" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-table" class="chart-section hidden">
    <div class="card">
      <h3>일별 데이터 테이블</h3>
      <div class="tbl-toolbar"><span class="cnt" id="tblCount"></span><button class="csv-btn" onclick="downloadCSV()">CSV 다운로드</button></div>
      <div class="tbl-wrap"><table class="data-tbl"><thead id="tblHead"></thead><tbody id="tblBody"></tbody></table></div>
    </div>
  </div>

  <!-- Academy search view (hidden by default) -->
  <div id="academyView" class="hidden">
    <div class="acad-header" id="acadHeader"></div>
    <div class="kpi-row" id="acadKpi"></div>
    <div class="row2">
      <div class="card"><h3 id="hAcadA">기능별 누적 사용량 추이</h3><div id="acad-feat" class="plot-tall"></div></div>
      <div class="card"><h3 id="hAcadB">활성 여부 타임라인</h3><div id="acad-active" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3 id="hAcadC"></h3><div id="acad-c" class="plot"></div></div>
      <div class="card"><h3 id="hAcadD">기능별 일일 변화량</h3><div id="acad-delta" class="plot"></div></div>
    </div>
  </div>

</div>

<script>
// ===== DATA =====
const S_RAW={student_json};
const S_FEAT={student_feat_json};
const S_FNAMES={json.dumps({
    '열람권사용량':'열람권 사용','발급권사용량':'발급권 사용',
    '주제발급횟수':'주제 발급','학쫑GPT사용량':'학쫑GPT 사용',
}, ensure_ascii=False)};
const S_YN_NAMES={json.dumps({
    'yn_샘플주제과제발급여부':'샘플주제','yn_AILite진단여부':'AI Lite',
    'yn_AiPro진단여부':'AI Pro','yn_수시배치표여부':'수시배치표','yn_계열선택검사여부':'계열선택',
}, ensure_ascii=False)};
const S_YN_KEYS=Object.keys(S_YN_NAMES);
const S_YN_DELTA_KEYS=S_YN_KEYS.map(k=>k.replace('yn_','yn_delta_'));
const S_CAT_COLS={json.dumps(student_data.get('cat_cols',[]), ensure_ascii=False)};
const S_CNAMES={json.dumps({
    'cat_기본 이용권':'기본 이용권','cat_전 학교 이용권':'전 학교 이용권(전)',
    'cat_무료 모니터링':'무료 모니터링','cat_全 학교 이용권':'전 학교 이용권(全)',
    'cat_1년 이용권':'1년 이용권',
}, ensure_ascii=False)};

const I_RAW={inst_json};
const I_FEAT={inst_feat_json};
const I_FNAMES={json.dumps({
    '발급권사용량(학생)':'발급권(학생)','열람권사용량(학생)':'열람권(학생)',
    '발급권사용량(스토리지)':'발급권(스토리지)','열람권사용량(스토리지)':'열람권(스토리지)',
    '초안작성과제생성량':'초안 생성','초안작성과제승인량':'초안 승인','초안작성과제거절량':'초안 거절',
    '생기부업로드량':'생기부 업로드','생기부분석량(pro)':'생기부 Pro','생기부분석량(lite)':'생기부 Lite',
    '수시배치표진행량':'수시 배치표','계열선택검사량':'계열선택 검사','수행평가GPT사용량':'수행평가 GPT',
}, ensure_ascii=False)};

let MODE='student'; // 'student' | 'inst'
let REG_FILTER='all'; // 'all' | 'reg' | 'unreg'

const SCOL=['#60a5fa','#4ade80','#f59e0b','#e879f9','#818cf8'];
const ICOL=['#a78bfa','#60a5fa','#4ade80','#f59e0b','#f472b6','#818cf8','#fb923c','#22d3ee','#e879f9','#facc15','#34d399','#f87171','#38bdf8'];

function accent(){{return MODE==='student'?'#3b82f6':'#8b5cf6'}}
function raw(){{
  const data=MODE==='student'?S_RAW:I_RAW;
  if(REG_FILTER==='all') return data;
  const p=REG_FILTER==='reg'?'reg_':'unreg_';
  const tk=totalKey(),ak=activeKey(),nk=newKey();
  return data.map(d=>{{
    const r={{...d}};
    r[tk]=d[p+'total']??d[tk];
    r[ak]=d[p+'active']??d[ak];
    r.activation_rate=d[p+'rate']??d.activation_rate;
    r[nk]=d[p+'new']??d[nk];
    if(MODE==='inst'){{
      r.total_registered_students=d[p+'students']??d.total_registered_students;
      r.active_names=d[p+'active_names']??d.active_names;
      r.storage_users=d[p+'storage']??d.storage_users;
      r.purchase_users=d[p+'purchase']??d.purchase_users;
    }}else{{
      r.n_academies=d[p+'n_academies']??d.n_academies;
      r.active_academies=d[p+'active_academies']??d.active_academies;
    }}
    featCols().forEach(k=>{{if(d[p+k]!==undefined)r[k]=d[p+k]}});
    return r;
  }});
}}
function featCols(){{return MODE==='student'?S_FEAT:I_FEAT}}
function featNames(){{return MODE==='student'?S_FNAMES:I_FNAMES}}
function fColors(){{return MODE==='student'?SCOL:ICOL}}
function entity(){{return MODE==='student'?'학생':'학원'}}
function totalKey(){{return MODE==='student'?'total_students':'total_institutions'}}
function activeKey(){{return MODE==='student'?'active_students':'active_institutions'}}
function newKey(){{return MODE==='student'?'new_students':'new_institutions'}}

const L={{paper_bgcolor:'#1e293b',plot_bgcolor:'#1e293b',font:{{color:'#e2e8f0',family:'Segoe UI,Malgun Gothic,sans-serif',size:12}},xaxis:{{gridcolor:'#334155',linecolor:'#475569'}},yaxis:{{gridcolor:'#334155',linecolor:'#475569'}},margin:{{l:55,r:20,t:10,b:50}},legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:11}}}},hovermode:'x unified'}};
const CFG={{responsive:true,displayModeBar:false}};
function ma(a,w=7){{return a.map((_,i)=>{{const s=Math.max(0,i-w+1),sl=a.slice(s,i+1);return Math.round(sl.reduce((x,y)=>x+y,0)/sl.length*10)/10}})}}
function groupBy(a,fn){{const m={{}};a.forEach(d=>{{const k=fn(d);(m[k]=m[k]||[]).push(d)}});return m}}
function isoWeek(ds){{const d=new Date(ds),j=new Date(d.getFullYear(),0,1);return d.getFullYear()+'-W'+String(Math.ceil(((d-j)/864e5+j.getDay()+1)/7)).padStart(2,'0')}}
function isoMonth(ds){{return ds.substring(0,7)}}
function iqrHi(arr){{const s=[...arr].sort((a,b)=>a-b);const q1=s[Math.floor(s.length*.25)],q3=s[Math.floor(s.length*.75)];return q3+1.5*(q3-q1)}}
function dayName(v){{const m={{'Monday':'월','Tuesday':'화','Wednesday':'수','Thursday':'목','Friday':'금','Saturday':'토','Sunday':'일'}};return m[v]||v}}

// ===== REGISTRATION FILTER =====
function setRegFilter(f,btn){{
  REG_FILTER=f;
  document.querySelectorAll('.reg-btn').forEach(b=>{{b.classList.remove('active')}});
  if(btn) btn.classList.add('active');
  renderAll();
}}

// ===== MODE SWITCH =====
function switchMode(m){{
  MODE=m;
  REG_FILTER='all';
  document.querySelectorAll('.reg-btn').forEach((b,i)=>{{b.classList.toggle('active',i===0)}});
  document.getElementById('modeStudent').className='mode-btn'+(m==='student'?' active-student':'');
  document.getElementById('modeInst').className='mode-btn'+(m==='inst'?' active-inst':'');
  document.getElementById('noteStudent').classList.toggle('hidden',m!=='student');
  document.getElementById('noteInst').classList.toggle('hidden',m!=='inst');
  // Update accent on active preset/tab buttons
  document.querySelectorAll('.preset-btn.active,.tab-btn.active').forEach(b=>b.style.background=accent());
  document.querySelector('.switch input:checked+.slider')?.style&&document.querySelectorAll('.switch input:checked+.slider').forEach(s=>s.style.background=accent());
  buildTabs();
  if(SEARCH_CODE&&ACAD_DATA){{renderAcademyView(SEARCH_CODE,ACAD_DATA)}}else{{renderAll()}}
}}

function buildTabs(){{
  const e=entity();
  const tabs=[
    ['daily','일별'],['weekly','주별'],['monthly','월별'],['features','기능별 사용현황'],
  ];
  if(MODE==='student'){{tabs.push(['users','사용자 지표']);tabs.push(['retention','리텐션']);tabs.push(['extra','학년/이용권']);}}
  else tabs.push(['extra','부가지표']);
  tabs.push(['table','데이터 테이블']);
  const bar=document.getElementById('tabBar');
  bar.innerHTML=tabs.map(([id,label],i)=>
    `<button class="tab-btn${{i===0?' active':''}}" style="${{i===0?'background:'+accent():'' }}" onclick="showTab('${{id}}',this)">${{label}}</button>`
  ).join('');
}}

// ===== FILTER =====
function getFiltered(){{
  const s=document.getElementById('startDate').value,e=document.getElementById('endDate').value;
  let F=raw().filter(d=>d.date>=s&&d.date<=e);
  const ex=document.getElementById('outlierToggle').checked,info=document.getElementById('outlierInfo');
  if(ex&&F.length>7){{
    const aH=iqrHi(F.map(d=>d[activeKey()]));
    const nH=iqrHi(F.map(d=>d[newKey()]||0));
    const b=F.length;F=F.filter(d=>d[activeKey()]<=aH&&(d[newKey()]||0)<=nH);
    info.textContent=(b-F.length)>0?`(${{b-F.length}}일 제외됨)`:'(이상치 없음)';
  }}else info.textContent='';
  return F;
}}

// ===== RENDER =====
function renderAll(){{
  const F=getFiltered();if(!F.length)return;
  const e=entity(),ak=activeKey(),tk=totalKey(),nk=newKey(),ac=accent();
  const dates=F.map(d=>d.date),last=F[F.length-1];
  const actV=F.map(d=>d[ak]),actR=F.map(d=>d.activation_rate);
  const totV=F.map(d=>d[tk]),newV=F.map(d=>d[nk]||0);

  // KPI
  const avgA=Math.round(actV.reduce((a,b)=>a+b,0)/F.length*10)/10;
  const avgR=Math.round(actR.reduce((a,b)=>a+b,0)/F.length*100)/100;
  const sumN=newV.reduce((a,b)=>a+b,0);

  let kpiHTML=`
    <div class="kpi"><div class="label">총 ${{e}} 수 (최종일)</div><div class="value">${{last[tk].toLocaleString()}}</div><div class="sub neutral">${{dates[0]}} ~ ${{dates[dates.length-1]}} (${{F.length}}일)</div></div>
    <div class="kpi"><div class="label">일평균 활성 ${{e}}</div><div class="value">${{avgA}}</div><div class="sub neutral">최종일 ${{last[ak]}}${{MODE==='student'?'명':'개'}}</div></div>
    <div class="kpi"><div class="label">평균 활성화율</div><div class="value">${{avgR}}%</div></div>`;
  if(MODE==='student'){{
    const avgAU=Math.round(F.reduce((a,d)=>a+(d.au||0),0)/F.length*10)/10;
    const avgPU=Math.round(F.reduce((a,d)=>a+(d.pu||0),0)/F.length*10)/10;
    const lastWM=last.wau_mau_ratio!=null?(last.wau_mau_ratio*100).toFixed(1)+'%':'-';
    kpiHTML+=`<div class="kpi"><div class="label">일평균 AU / PU</div><div class="value">${{avgAU}} / ${{avgPU}}</div><div class="sub neutral">최종일 AU ${{last.au||0}} / PU ${{last.pu||0}}</div></div>`;
    kpiHTML+=`<div class="kpi"><div class="label">WAU/MAU Stickiness</div><div class="value">${{lastWM}}</div><div class="sub neutral">WAU ${{(last.rolling_wau||0).toLocaleString()}} / MAU ${{(last.rolling_mau||0).toLocaleString()}}</div></div>`;
  }}else{{
    kpiHTML+=`<div class="kpi"><div class="label">등록 학생 수 (최종일)</div><div class="value">${{(last.total_registered_students||0).toLocaleString()}}</div></div>`;
  }}
  kpiHTML+=`<div class="kpi"><div class="label">기간 내 신규 ${{e}}</div><div class="value">${{sumN.toLocaleString()}}</div></div>`;
  document.getElementById('kpiRow').innerHTML=kpiHTML;
  document.getElementById('rangeInfo').textContent=F.length+'일 선택됨';

  // Dynamic headers
  document.getElementById('hDA').textContent=`일별 활성 ${{e}} 수`;
  document.getElementById('hDT').textContent=`일별 총 ${{e}} 수`;
  document.getElementById('hDN').textContent=`일별 신규 ${{e}}`;
  document.getElementById('hWA').textContent=`주별 평균 활성 ${{e}} 수`;
  document.getElementById('hWM').textContent=`주별 최대 활성 ${{e}} 수`;
  document.getElementById('hWN').textContent=`주별 신규 ${{e}}`;
  document.getElementById('hMA').textContent=`월별 평균 활성 ${{e}} 수`;
  document.getElementById('hMM').textContent=`월별 최대 활성 ${{e}} 수`;
  document.getElementById('hMN').textContent=`월별 신규 ${{e}}`;
  document.getElementById('hMT').textContent=`월별 총 ${{e}} 수 추이`;
  document.getElementById('hFT').textContent=`기능별 일별 활성 ${{e}} 수`;
  document.getElementById('hFB').textContent=`기간 내 기능별 평균 활성 ${{e}}`;

  const barColor=`rgba(${{parseInt(ac.slice(1,3),16)}},${{parseInt(ac.slice(3,5),16)}},${{parseInt(ac.slice(5,7),16)}},0.6)`;

  // Build customdata: [total, active, rate, new, extra, dayname, detail]
  const detailLabel=MODE==='student'?'소속 학원':'활성 학원 명단';
  const cd=F.map(d=>{{
    const rawDetail=MODE==='student'?(d.active_academies||''):(d.active_names||'');
    const detail=rawDetail?`<br>──────<br><b>${{detailLabel}}:</b><br>${{rawDetail}}`:'';
    return [d[tk],d[ak],d.activation_rate,d[nk]||0,
      MODE==='student'?(d.n_academies||0):(d.total_registered_students||0),
      dayName(d.day_of_week),detail];
  }});
  const extraLabel=MODE==='student'?'학원 수':'등록 학생';
  const unit=MODE==='student'?'명':'개';

  const ht_active=`<b>%{{x}} (%{{customdata[5]}})</b><br>총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br><b>활성 ${{e}}: %{{y:,}}${{unit}}</b><br>활성화율: %{{customdata[2]:.2f}}%<br>신규 ${{e}}: %{{customdata[3]:,}}${{unit}}<br>${{extraLabel}}: %{{customdata[4]:,}}%{{customdata[6]}}<extra></extra>`;
  const ht_rate=`<b>%{{x}} (%{{customdata[5]}})</b><br>총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br>활성 ${{e}}: %{{customdata[1]:,}}${{unit}}<br><b>활성화율: %{{y:.2f}}%</b><br>신규 ${{e}}: %{{customdata[3]:,}}${{unit}}%{{customdata[6]}}<extra></extra>`;
  const ht_total=`<b>%{{x}} (%{{customdata[5]}})</b><br><b>총 ${{e}}: %{{y:,}}${{unit}}</b><br>활성 ${{e}}: %{{customdata[1]:,}}${{unit}}<br>활성화율: %{{customdata[2]:.2f}}%<br>신규 ${{e}}: %{{customdata[3]:,}}${{unit}}<br>${{extraLabel}}: %{{customdata[4]:,}}%{{customdata[6]}}<extra></extra>`;
  const ht_new=`<b>%{{x}} (%{{customdata[5]}})</b><br>총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br>활성 ${{e}}: %{{customdata[1]:,}}${{unit}}<br><b>신규 ${{e}}: %{{y:,}}${{unit}}</b>%{{customdata[6]}}<extra></extra>`;
  const ht_ma='<b>7일 이동평균: %{{y}}</b><extra></extra>';

  const hoverL={{...L,hovermode:'closest'}};

  // DAILY
  Plotly.react('d-active',[
    {{x:dates,y:actV,customdata:cd,name:`활성 ${{e}}`,type:'bar',marker:{{color:barColor}},hovertemplate:ht_active}},
    {{x:dates,y:ma(actV),name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}},hovertemplate:ht_ma}},
  ],{{...hoverL}},CFG);
  Plotly.react('d-rate',[
    {{x:dates,y:actR,customdata:cd,name:'활성화율',type:'bar',marker:{{color:'rgba(74,222,128,0.5)'}},hovertemplate:ht_rate}},
    {{x:dates,y:ma(actR),name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}},hovertemplate:ht_ma}},
  ],{{...hoverL,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('d-total',[
    {{x:dates,y:totV,customdata:cd,name:`총 ${{e}}`,type:'scatter',mode:'lines',line:{{color:ac,width:2}},fill:'tozeroy',fillcolor:barColor.replace('0.6','0.1'),hovertemplate:ht_total}},
  ],{{...hoverL}},CFG);
  Plotly.react('d-new',[
    {{x:dates,y:newV,customdata:cd,name:`신규 ${{e}}`,type:'bar',marker:{{color:'#818cf8'}},hovertemplate:ht_new}},
  ],{{...hoverL}},CFG);

  // Extra daily card
  const eCard=document.getElementById('extraDailyCard');
  const ht_extra=`<b>%{{x}} (%{{customdata[5]}})</b><br>총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br>활성 ${{e}}: %{{customdata[1]:,}}${{unit}}<br><b>${{extraLabel}}: %{{y:,}}</b><extra></extra>`;
  if(MODE==='student'){{
    eCard.classList.remove('hidden');
    document.getElementById('hDE').textContent='일별 학원 수';
    Plotly.react('d-extra',[{{x:dates,y:F.map(d=>d.n_academies||0),customdata:cd,name:'학원 수',type:'scatter',mode:'lines',line:{{color:'#f472b6',width:2}},fill:'tozeroy',fillcolor:'rgba(244,114,182,0.08)',hovertemplate:ht_extra}}],{{...hoverL}},CFG);
  }}else{{
    eCard.classList.remove('hidden');
    document.getElementById('hDE').textContent='등록 학생 수 추이';
    Plotly.react('d-extra',[{{x:dates,y:F.map(d=>d.total_registered_students||0),customdata:cd,name:'등록 학생',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}},fill:'tozeroy',fillcolor:'rgba(96,165,250,0.1)',hovertemplate:ht_extra}}],{{...hoverL}},CFG);
  }}

  // WEEKLY
  const wG=groupBy(F,d=>isoWeek(d.date)),wK=Object.keys(wG).sort();
  const wLb=wK.map(k=>{{const g=wG[k];return g[0].date+'~'+g[g.length-1].date.substring(5)}});
  const wA=wK.map(k=>{{const g=wG[k];return +(g.reduce((a,d)=>a+d[ak],0)/g.length).toFixed(1)}});
  const wR=wK.map(k=>{{const g=wG[k];return +(g.reduce((a,d)=>a+d.activation_rate,0)/g.length).toFixed(2)}});
  const wM=wK.map(k=>Math.max(...wG[k].map(d=>d[ak])));
  const wN=wK.map(k=>wG[k].reduce((a,d)=>a+(d[nk]||0),0));
  const wT=wK.map(k=>Math.round(wG[k].reduce((a,d)=>a+d[tk],0)/wG[k].length));
  const wDays=wK.map(k=>wG[k].length);
  const wCd=wK.map((_,i)=>[wT[i],wA[i],wR[i],wN[i],wM[i],wDays[i]]);
  const wHt=`<b>%{{x}}</b> (%{{customdata[5]}}일)<br>평균 총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br><b>평균 활성: %{{y}}${{unit}}</b><br>평균 활성화율: %{{customdata[2]}}%<br>최대 활성: %{{customdata[4]:,}}${{unit}}<br>신규 ${{e}}: %{{customdata[3]:,}}${{unit}}<extra></extra>`;

  Plotly.react('w-active',[{{x:wLb,y:wA,customdata:wCd,name:'평균 활성',type:'bar',marker:{{color:ac}},hovertemplate:wHt}}],{{...hoverL,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-rate',[{{x:wLb,y:wR,customdata:wCd,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:2}},marker:{{size:4}},hovertemplate:`<b>%{{x}}</b> (%{{customdata[5]}}일)<br>평균 총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br>평균 활성: %{{customdata[1]}}${{unit}}<br><b>평균 활성화율: %{{y}}%</b><br>신규 ${{e}}: %{{customdata[3]:,}}${{unit}}<extra></extra>`}}],{{...hoverL,xaxis:{{...L.xaxis,tickangle:-45}},yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('w-max',[{{x:wLb,y:wM,customdata:wCd,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}},hovertemplate:`<b>%{{x}}</b> (%{{customdata[5]}}일)<br>평균 총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br><b>최대 활성: %{{y:,}}${{unit}}</b><br>평균 활성: %{{customdata[1]}}${{unit}}<extra></extra>`}}],{{...hoverL,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-new',[{{x:wLb,y:wN,customdata:wCd,name:`신규 ${{e}}`,type:'bar',marker:{{color:'#818cf8'}},hovertemplate:`<b>%{{x}}</b> (%{{customdata[5]}}일)<br>평균 총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br><b>신규 ${{e}}: %{{y:,}}${{unit}}</b><extra></extra>`}}],{{...hoverL,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);

  // MONTHLY
  const mG=groupBy(F,d=>isoMonth(d.date)),mK=Object.keys(mG).sort();
  const mA=mK.map(k=>+(mG[k].reduce((a,d)=>a+d[ak],0)/mG[k].length).toFixed(1));
  const mR=mK.map(k=>+(mG[k].reduce((a,d)=>a+d.activation_rate,0)/mG[k].length).toFixed(2));
  const mM=mK.map(k=>Math.max(...mG[k].map(d=>d[ak])));
  const mN=mK.map(k=>mG[k].reduce((a,d)=>a+(d[nk]||0),0));
  const mT=mK.map(k=>Math.round(mG[k].reduce((a,d)=>a+d[tk],0)/mG[k].length));
  const mDays=mK.map(k=>mG[k].length);
  const mCd=mK.map((_,i)=>[mT[i],mA[i],mR[i],mN[i],mM[i],mDays[i]]);
  const mHt=`<b>%{{x}}</b> (%{{customdata[5]}}일)<br>평균 총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br><b>평균 활성: %{{y}}${{unit}}</b><br>평균 활성화율: %{{customdata[2]}}%<br>최대 활성: %{{customdata[4]:,}}${{unit}}<br>신규 ${{e}}: %{{customdata[3]:,}}${{unit}}<extra></extra>`;

  Plotly.react('m-active',[{{x:mK,y:mA,customdata:mCd,name:'평균 활성',type:'bar',marker:{{color:ac}},text:mA.map(v=>v.toFixed(1)),textposition:'outside',textfont:{{color:'#94a3b8',size:11}},hovertemplate:mHt}}],{{...hoverL}},CFG);
  Plotly.react('m-rate',[{{x:mK,y:mR,customdata:mCd,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:3}},marker:{{size:7}},hovertemplate:`<b>%{{x}}</b> (%{{customdata[5]}}일)<br>평균 총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br>평균 활성: %{{customdata[1]}}${{unit}}<br><b>평균 활성화율: %{{y}}%</b><br>신규 ${{e}}: %{{customdata[3]:,}}${{unit}}<extra></extra>`}}],{{...hoverL,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('m-max',[{{x:mK,y:mM,customdata:mCd,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}},text:mM,textposition:'outside',textfont:{{color:'#94a3b8',size:11}},hovertemplate:`<b>%{{x}}</b> (%{{customdata[5]}}일)<br><b>최대 활성: %{{y:,}}${{unit}}</b><br>평균 활성: %{{customdata[1]}}${{unit}}<br>평균 활성화율: %{{customdata[2]}}%<extra></extra>`}}],{{...hoverL}},CFG);
  Plotly.react('m-new',[{{x:mK,y:mN,customdata:mCd,name:`신규 ${{e}}`,type:'bar',marker:{{color:'#818cf8'}},text:mN,textposition:'outside',textfont:{{color:'#94a3b8',size:11}},hovertemplate:`<b>%{{x}}</b> (%{{customdata[5]}}일)<br>평균 총 ${{e}}: %{{customdata[0]:,}}${{unit}}<br><b>신규 ${{e}}: %{{y:,}}${{unit}}</b><extra></extra>`}}],{{...hoverL}},CFG);
  Plotly.react('m-total',[{{x:mK,y:mT,customdata:mCd,name:`평균 총 ${{e}}`,type:'bar',marker:{{color:ac}},text:mT.map(v=>v.toLocaleString()),textposition:'outside',textfont:{{color:'#94a3b8',size:11}},hovertemplate:`<b>%{{x}}</b> (%{{customdata[5]}}일)<br><b>평균 총 ${{e}}: %{{y:,}}${{unit}}</b><br>평균 활성: %{{customdata[1]}}${{unit}}<br>활성화율: %{{customdata[2]}}%<extra></extra>`}}],{{...hoverL}},CFG);

  // FEATURES
  const fc=featCols(),fn=featNames(),fcl=fColors();
  const fT=fc.map((k,i)=>({{x:dates,y:F.map(d=>d[k]||0),customdata:cd,name:fn[k]||k,type:'scatter',mode:'lines',line:{{color:fcl[i%fcl.length],width:2}},hovertemplate:`<b>%{{x}}</b><br>${{fn[k]||k}}: <b>%{{y:,}}${{unit}}</b><br>총 ${{e}}: %{{customdata[0]:,}}<br>전체 활성: %{{customdata[1]:,}}<extra></extra>`}}));
  Plotly.react('f-trend',fT,{{...L,margin:{{...L.margin,b:60}}}},CFG);
  const fAvg=fc.map(k=>{{const v=F.map(d=>d[k]||0);return +(v.reduce((a,b)=>a+b,0)/v.length).toFixed(1)}});
  const fLb=fc.map(k=>fn[k]||k);
  Plotly.react('f-bar',[{{x:fLb,y:fAvg,type:'bar',marker:{{color:fcl.slice(0,fc.length)}},text:fAvg.map(String),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-30}}}},CFG);

  // EXTRA TAB
  if(MODE==='student'){{
    document.getElementById('hE1').textContent='학년별 학생 수 추이';
    document.getElementById('hE2').textContent='최종일 이용권별 분포';
    const g0=F.map(d=>d.grade_0||0),g1=F.map(d=>d.grade_1||0),g2=F.map(d=>d.grade_2||0),g3=F.map(d=>d.grade_3||0);
    Plotly.react('e1',[
      {{x:dates,y:g0,name:'예비(0)',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#f472b6'}}}},
      {{x:dates,y:g1,name:'고1',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#60a5fa'}}}},
      {{x:dates,y:g2,name:'고2',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#4ade80'}}}},
      {{x:dates,y:g3,name:'고3',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#f59e0b'}}}},
    ],{{...L}},CFG);
    const ccols=S_CAT_COLS,cnames=S_CNAMES,cclrs=['#60a5fa','#4ade80','#f59e0b','#f472b6','#818cf8'];
    const lcV=ccols.map(k=>last[k]||0),lcL=ccols.map(k=>cnames[k]||k);
    Plotly.react('e2',[{{values:lcV,labels:lcL,type:'pie',hole:.4,marker:{{colors:cclrs}},textinfo:'label+value+percent',textfont:{{size:11}}}}],{{...L,margin:{{l:20,r:20,t:10,b:10}}}},CFG);
  }}else{{
    document.getElementById('hE1').textContent='등록 학생 수 추이';
    document.getElementById('hE2').textContent='스토리지 사용 / 등록권 구매 학원';
    Plotly.react('e1',[{{x:dates,y:F.map(d=>d.total_registered_students||0),name:'등록 학생',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}},fill:'tozeroy',fillcolor:'rgba(96,165,250,0.1)'}}],{{...L}},CFG);
    Plotly.react('e2',[
      {{x:dates,y:F.map(d=>d.storage_users||0),name:'스토리지 사용',type:'scatter',mode:'lines',line:{{color:'#4ade80',width:2}}}},
      {{x:dates,y:F.map(d=>d.purchase_users||0),name:'등록권 구매',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2}}}},
    ],{{...L}},CFG);
  }}

  // USER METRICS TAB (student mode only)
  if(MODE==='student'){{
    const auV=F.map(d=>d.au||0),puV=F.map(d=>d.pu||0);
    const auR=F.map(d=>d.au_rate||0),puR=F.map(d=>d.pu_rate||0);
    // AU vs PU
    Plotly.react('u-aupu',[
      {{x:dates,y:auV,name:'AU (Active User)',type:'bar',marker:{{color:'rgba(96,165,250,0.6)'}},hovertemplate:'<b>%{{x}}</b><br>AU: <b>%{{y}}명</b><extra></extra>'}},
      {{x:dates,y:puV,name:'PU (Premium User)',type:'bar',marker:{{color:'rgba(74,222,128,0.6)'}},hovertemplate:'<b>%{{x}}</b><br>PU: <b>%{{y}}명</b><extra></extra>'}},
      {{x:dates,y:ma(auV),name:'AU 7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#3b82f6',width:2.5}},hovertemplate:'<b>AU 7일 평균: %{{y}}</b><extra></extra>'}},
    ],{{...hoverL,barmode:'overlay'}},CFG);
    // AU Rate vs PU Rate
    Plotly.react('u-rates',[
      {{x:dates,y:auR,name:'AU Rate',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}},hovertemplate:'<b>%{{x}}</b><br>AU Rate: <b>%{{y:.2f}}%</b><extra></extra>'}},
      {{x:dates,y:puR,name:'PU Rate',type:'scatter',mode:'lines',line:{{color:'#4ade80',width:2}},hovertemplate:'<b>%{{x}}</b><br>PU Rate: <b>%{{y:.2f}}%</b><extra></extra>'}},
      {{x:dates,y:ma(auR),name:'AU Rate 7일 평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2,dash:'dot'}},hovertemplate:'<b>AU Rate 7일 평균: %{{y:.2f}}%</b><extra></extra>'}},
    ],{{...hoverL,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
    // Rolling WAU/MAU
    Plotly.react('u-waumau',[
      {{x:dates,y:F.map(d=>d.rolling_wau||0),name:'WAU (7일)',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>WAU: <b>%{{y}}명</b><extra></extra>'}},
      {{x:dates,y:F.map(d=>d.rolling_mau||0),name:'MAU (28일)',type:'scatter',mode:'lines',line:{{color:'#a78bfa',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>MAU: <b>%{{y}}명</b><extra></extra>'}},
    ],{{...hoverL}},CFG);
    // Rolling WPU/MPU
    Plotly.react('u-wpumpu',[
      {{x:dates,y:F.map(d=>d.rolling_wpu||0),name:'WPU (7일)',type:'scatter',mode:'lines',line:{{color:'#4ade80',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>WPU: <b>%{{y}}명</b><extra></extra>'}},
      {{x:dates,y:F.map(d=>d.rolling_mpu||0),name:'MPU (28일)',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>MPU: <b>%{{y}}명</b><extra></extra>'}},
    ],{{...hoverL}},CFG);
    // Stickiness
    Plotly.react('u-sticky',[
      {{x:dates,y:F.map(d=>(d.wau_mau_ratio||0)*100),name:'WAU/MAU',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>WAU/MAU: <b>%{{y:.1f}}%</b><extra></extra>'}},
      {{x:dates,y:F.map(d=>(d.wpu_mpu_ratio||0)*100),name:'WPU/MPU',type:'scatter',mode:'lines',line:{{color:'#4ade80',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>WPU/MPU: <b>%{{y:.1f}}%</b><extra></extra>'}},
    ],{{...hoverL,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
    // Y/N flags
    const ynColors=['#f472b6','#38bdf8','#818cf8','#fb923c','#34d399'];
    const ynTraces=S_YN_KEYS.map((k,i)=>({{x:dates,y:F.map(d=>d[k]||0),name:S_YN_NAMES[k],type:'scatter',mode:'lines',line:{{color:ynColors[i],width:2}},hovertemplate:`<b>%{{x}}</b><br>${{S_YN_NAMES[k]}}: <b>%{{y}}명</b><extra></extra>`}}));
    Plotly.react('u-yn',ynTraces,{{...hoverL}},CFG);

    // RETENTION TAB
    // D7 retention
    Plotly.react('r-d7',[
      {{x:dates,y:F.map(d=>d.d7_au_rate||0),name:'D7 AU 리텐션',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>D7 AU: <b>%{{y:.1f}}%</b><br>코호트: %{{customdata}}명<extra></extra>',customdata:F.map(d=>d.d7_au_total||0)}},
      {{x:dates,y:F.map(d=>d.d7_pu_rate||0),name:'D7 PU 리텐션',type:'scatter',mode:'lines',line:{{color:'#4ade80',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>D7 PU: <b>%{{y:.1f}}%</b><extra></extra>'}},
    ],{{...hoverL,yaxis:{{...L.yaxis,ticksuffix:'%',range:[0,105]}}}},CFG);
    // D28 retention
    Plotly.react('r-d28',[
      {{x:dates,y:F.map(d=>d.d28_au_rate||0),name:'D28 AU 리텐션',type:'scatter',mode:'lines',line:{{color:'#a78bfa',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>D28 AU: <b>%{{y:.1f}}%</b><br>코호트: %{{customdata}}명<extra></extra>',customdata:F.map(d=>d.d28_au_total||0)}},
      {{x:dates,y:F.map(d=>d.d28_pu_rate||0),name:'D28 PU 리텐션',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}},hovertemplate:'<b>%{{x}}</b><br>D28 PU: <b>%{{y:.1f}}%</b><extra></extra>'}},
    ],{{...hoverL,yaxis:{{...L.yaxis,ticksuffix:'%',range:[0,105]}}}},CFG);
    // D7 cohort size
    Plotly.react('r-d7n',[
      {{x:dates,y:F.map(d=>d.d7_au_total||0),name:'D7 코호트',type:'bar',marker:{{color:'rgba(96,165,250,0.5)'}},hovertemplate:'<b>%{{x}}</b><br>7일 전 가입: <b>%{{y}}명</b><extra></extra>'}},
    ],{{...hoverL}},CFG);
    // D28 cohort size
    Plotly.react('r-d28n',[
      {{x:dates,y:F.map(d=>d.d28_au_total||0),name:'D28 코호트',type:'bar',marker:{{color:'rgba(167,139,250,0.5)'}},hovertemplate:'<b>%{{x}}</b><br>28일 전 가입: <b>%{{y}}명</b><extra></extra>'}},
    ],{{...hoverL}},CFG);
  }}

  renderTable(F);
}}

// ===== TABLE =====
let tblSortKey='date',tblSortAsc=false,tblData=[];
function buildTblCols(){{
  const e=entity(),cols=[
    {{key:'date',label:'날짜',fmt:v=>v}},
    {{key:'day_of_week',label:'요일',fmt:v=>dayName(v)}},
    {{key:totalKey(),label:`총 ${{e}}`,fmt:v=>v.toLocaleString()}},
    {{key:activeKey(),label:`활성 ${{e}}`,fmt:v=>v.toLocaleString()}},
    {{key:'activation_rate',label:'활성화율(%)',fmt:v=>v.toFixed(2)}},
    {{key:newKey(),label:`신규 ${{e}}`,fmt:v=>(v||0).toLocaleString()}},
  ];
  if(MODE==='student'){{
    cols.push({{key:'n_academies',label:'학원 수',fmt:v=>(v||0).toLocaleString()}});
    ['grade_0','grade_1','grade_2','grade_3'].forEach((k,i)=>cols.push({{key:k,label:['예비','고1','고2','고3'][i],fmt:v=>(v||0).toLocaleString()}}));
  }}else{{
    cols.push({{key:'total_registered_students',label:'등록 학생',fmt:v=>(v||0).toLocaleString()}});
    cols.push({{key:'storage_users',label:'스토리지',fmt:v=>(v||0).toLocaleString()}});
    cols.push({{key:'purchase_users',label:'등록권구매',fmt:v=>(v||0).toLocaleString()}});
  }}
  featCols().forEach(k=>cols.push({{key:k,label:featNames()[k]||k,fmt:v=>(v||0).toLocaleString()}}));
  return cols;
}}
function renderTable(F){{tblData=F;const cols=buildTblCols();document.getElementById('tblHead').innerHTML='<tr>'+cols.map(c=>`<th onclick="sortTable('${{c.key}}')">${{c.label}}<span class="arrow">${{tblSortKey===c.key?(tblSortAsc?'▲':'▼'):''}}</span></th>`).join('')+'</tr>';fillTbl()}}
function fillTbl(){{const cols=buildTblCols();const s=[...tblData].sort((a,b)=>{{let va=a[tblSortKey]??0,vb=b[tblSortKey]??0;return typeof va==='string'?(tblSortAsc?va.localeCompare(vb):vb.localeCompare(va)):(tblSortAsc?va-vb:vb-va)}});document.getElementById('tblBody').innerHTML=s.map(d=>'<tr>'+cols.map(c=>`<td>${{c.fmt(d[c.key]??0)}}</td>`).join('')+'</tr>').join('');document.getElementById('tblCount').textContent=s.length+'일 데이터'}}
function sortTable(k){{if(tblSortKey===k)tblSortAsc=!tblSortAsc;else{{tblSortKey=k;tblSortAsc=k==='date'}};const cols=buildTblCols();document.querySelectorAll('#tblHead th .arrow').forEach((el,i)=>el.textContent=cols[i]?.key===tblSortKey?(tblSortAsc?'▲':'▼'):'');fillTbl()}}
function downloadCSV(){{const F=getFiltered(),cols=buildTblCols();const h=cols.map(c=>c.label).join(',');const r=F.map(d=>cols.map(c=>{{let v=d[c.key]??0;if(c.key==='day_of_week')v=dayName(v);return v}}).join(','));const csv='\\uFEFF'+h+'\\n'+r.join('\\n');const b=new Blob([csv],{{type:'text/csv;charset=utf-8'}});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=(MODE==='student'?'학생':'학원')+'활성화_일별데이터.csv';a.click();URL.revokeObjectURL(u)}}

// ===== DATE RANGE =====
function setRange(days){{const all=raw().map(d=>d.date);const mn=all[0],mx=all[all.length-1];document.querySelectorAll('.preset-btn').forEach(b=>{{b.classList.remove('active');b.style.background=''}});event.target.classList.add('active');event.target.style.background=accent();if(days===0){{document.getElementById('startDate').value=mn;document.getElementById('endDate').value=mx}}else{{const e=new Date(mx),s=new Date(e);s.setDate(s.getDate()-days+1);const ss=s.toISOString().substring(0,10);document.getElementById('startDate').value=ss<mn?mn:ss;document.getElementById('endDate').value=mx}};renderAll()}}
document.getElementById('startDate').addEventListener('change',()=>{{document.querySelectorAll('.preset-btn').forEach(b=>{{b.classList.remove('active');b.style.background=''}});renderAll()}});
document.getElementById('endDate').addEventListener('change',()=>{{document.querySelectorAll('.preset-btn').forEach(b=>{{b.classList.remove('active');b.style.background=''}});renderAll()}});

// ===== TAB =====
function showTab(tab,btn){{document.querySelectorAll('.chart-section').forEach(el=>el.classList.add('hidden'));document.querySelectorAll('.tab-btn').forEach(el=>{{el.classList.remove('active');el.style.background=''}});document.getElementById('tab-'+tab).classList.remove('hidden');btn.classList.add('active');btn.style.background=accent();setTimeout(()=>document.querySelectorAll('#tab-'+tab+' .plot,#tab-'+tab+' .plot-tall').forEach(el=>Plotly.Plots.resize(el)),100)}}

// ===== ACADEMY SEARCH =====
const ACAD_LIST={academy_list_json};
let ACAD_DATA=null; // loaded on demand
let SEARCH_CODE=null; // currently selected academy code
let searchIdx=-1;

function onSearchInput(){{
  const q=document.getElementById('searchInput').value.trim().toLowerCase();
  const dd=document.getElementById('searchDropdown');
  if(!q){{dd.classList.remove('open');return}}
  const matches=ACAD_LIST.filter(a=>a.c.toLowerCase().includes(q)||a.n.toLowerCase().includes(q)).slice(0,50);
  if(!matches.length){{dd.innerHTML='<div style="padding:12px;color:#64748b;font-size:13px">검색 결과 없음</div>';dd.classList.add('open');return}}
  searchIdx=-1;
  dd.innerHTML=matches.map((a,i)=>`<div class="search-item" data-code="${{a.c}}" onclick="selectAcademy('${{a.c}}')" onmouseenter="searchIdx=${{i}}"><span class="code">${{a.c}}</span><span class="name">${{a.n||'(이름 없음)'}}</span><span class="badge ${{a.r?'reg':'unreg'}}">${{a.r?'가입':'비가입'}}</span></div>`).join('');
  dd.classList.add('open');
}}
function onSearchFocus(){{
  const q=document.getElementById('searchInput').value.trim();
  if(q) onSearchInput();
}}
function onSearchKey(e){{
  const dd=document.getElementById('searchDropdown');
  const items=dd.querySelectorAll('.search-item');
  if(!items.length)return;
  if(e.key==='ArrowDown'){{e.preventDefault();searchIdx=Math.min(searchIdx+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('selected',i===searchIdx));items[searchIdx]?.scrollIntoView({{block:'nearest'}})}}
  else if(e.key==='ArrowUp'){{e.preventDefault();searchIdx=Math.max(searchIdx-1,0);items.forEach((el,i)=>el.classList.toggle('selected',i===searchIdx));items[searchIdx]?.scrollIntoView({{block:'nearest'}})}}
  else if(e.key==='Enter'&&searchIdx>=0){{e.preventDefault();const code=items[searchIdx]?.dataset?.code;if(code) selectAcademy(code)}}
  else if(e.key==='Escape'){{dd.classList.remove('open')}}
}}
document.addEventListener('click',e=>{{
  if(!document.getElementById('searchWrap').contains(e.target))
    document.getElementById('searchDropdown').classList.remove('open');
}});

async function loadAcademyData(){{
  if(ACAD_DATA) return ACAD_DATA;
  try{{
    const r=await fetch('academy_search.json');
    if(!r.ok) throw new Error(r.status);
    ACAD_DATA=await r.json();
    return ACAD_DATA;
  }}catch(e){{
    console.error('Academy search data load failed:',e);
    alert('학원 검색 데이터를 불러올 수 없습니다.\\nacademy_search.json 파일이 같은 경로에 있는지 확인해주세요.');
    return null;
  }}
}}

async function selectAcademy(code){{
  document.getElementById('searchDropdown').classList.remove('open');
  const info=ACAD_LIST.find(a=>a.c===code);
  document.getElementById('searchInput').value=info?`${{info.n}} (${{code}})`:code;
  SEARCH_CODE=code;

  // Show loading
  document.getElementById('academyView').classList.remove('hidden');
  document.getElementById('academyView').innerHTML='<div class="acad-loading">데이터 로딩 중...</div>';

  // Hide aggregate views
  document.querySelectorAll('.note-box,.date-bar,#kpiRow').forEach(el=>{{el.style.display='none'}});
  document.getElementById('tabBar').style.display='none';
  document.querySelectorAll('.chart-section').forEach(el=>{{if(el.id!=='academyView') el.style.display='none'}});

  const data=await loadAcademyData();
  if(!data){{clearSearch();return}}

  // Restore academy view HTML
  document.getElementById('academyView').innerHTML=`
    <div class="acad-header" id="acadHeader"></div>
    <div class="kpi-row" id="acadKpi"></div>
    <div class="row2">
      <div class="card"><h3 id="hAcadA">기능별 누적 사용량 추이</h3><div id="acad-feat" class="plot-tall"></div></div>
      <div class="card"><h3 id="hAcadB">활성 여부 타임라인</h3><div id="acad-active" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3 id="hAcadC"></h3><div id="acad-c" class="plot"></div></div>
      <div class="card"><h3 id="hAcadD">기능별 일일 변화량</h3><div id="acad-delta" class="plot"></div></div>
    </div>`;

  renderAcademyView(code,data);
}}

function clearSearch(){{
  SEARCH_CODE=null;
  document.getElementById('searchInput').value='';
  document.getElementById('academyView').classList.add('hidden');
  // Restore aggregate views
  document.querySelectorAll('.note-box,.date-bar,#kpiRow').forEach(el=>{{el.style.display=''}});
  document.getElementById('tabBar').style.display='';
  document.querySelectorAll('.chart-section').forEach(el=>{{el.style.display='';el.classList.add('hidden')}});
  document.getElementById('tab-daily').classList.remove('hidden');
  buildTabs();
  renderAll();
}}

function renderAcademyView(code,data){{
  const info=ACAD_LIST.find(a=>a.c===code)||{{c:code,n:'',r:0}};
  const ac=accent();

  // Header
  document.getElementById('acadHeader').innerHTML=`
    <span class="acad-title">${{info.n||'(이름 없음)'}}</span>
    <span class="acad-code">${{code}}</span>
    <span class="acad-badge ${{info.r?'reg':'unreg'}}">${{info.r?'가입학원':'비가입학원'}}</span>
    <button class="acad-close" onclick="clearSearch()">&#10005; 전체 보기로 돌아가기</button>`;

  if(MODE==='inst'){{
    renderAcadInst(code,data,info,ac);
  }}else{{
    renderAcadStudent(code,data,info,ac);
  }}
}}

function renderAcadInst(code,data,info,ac){{
  const src=data.inst;
  const allDates=src.dates;
  const featCols=src.feat_cols;
  const ad=src.data[code];

  if(!ad||!ad.d.length){{
    document.getElementById('acadKpi').innerHTML='<div class="kpi"><div class="label">데이터 없음</div><div class="value">-</div><div class="sub neutral">이 학원의 학원 활성화 데이터가 없습니다</div></div>';
    return;
  }}

  const dates=ad.d.map(i=>allDates[i]);
  const active=ad.a;
  const students=ad.s;
  const totalDays=dates.length;
  const activeDays=active.filter(v=>v>0).length;
  const lastStudents=students[students.length-1]||0;

  // KPIs
  document.getElementById('acadKpi').innerHTML=`
    <div class="kpi"><div class="label">데이터 기간</div><div class="value">${{totalDays}}일</div><div class="sub neutral">${{dates[0]}} ~ ${{dates[dates.length-1]}}</div></div>
    <div class="kpi"><div class="label">활성 일수</div><div class="value">${{activeDays}}일</div><div class="sub neutral">활성화율 ${{totalDays>0?(activeDays/totalDays*100).toFixed(1):0}}%</div></div>
    <div class="kpi"><div class="label">최종 등록 학생 수</div><div class="value">${{lastStudents.toLocaleString()}}</div></div>
    <div class="kpi"><div class="label">가입 상태</div><div class="value">${{info.r?'가입':'비가입'}}</div></div>`;

  // Feature usage chart
  const fn=I_FNAMES;
  const fcl=ICOL;
  const traces=[];
  for(const [fi,arr] of Object.entries(ad.f)){{
    const idx=parseInt(fi);
    const name=fn[featCols[idx]]||featCols[idx];
    traces.push({{x:dates,y:arr,name:name,type:'scatter',mode:'lines',line:{{color:fcl[idx%fcl.length],width:2}}}});
  }}
  if(!traces.length) traces.push({{x:dates,y:dates.map(()=>0),name:'사용량 없음',type:'scatter',mode:'lines'}});
  document.getElementById('hAcadA').textContent='기능별 누적 사용량 추이';
  Plotly.react('acad-feat',traces,{{...L,margin:{{...L.margin,b:60}}}},CFG);

  // Active timeline
  const activeColors=active.map(v=>v>0?'#4ade80':'rgba(71,85,105,0.3)');
  Plotly.react('acad-active',[{{x:dates,y:active,type:'bar',marker:{{color:activeColors}},hovertemplate:'<b>%{{x}}</b><br>활성: %{{y}}<extra></extra>'}}],{{...L,yaxis:{{...L.yaxis,tickvals:[0,1],ticktext:['비활성','활성']}}}},CFG);

  // Registered students chart
  document.getElementById('hAcadC').textContent='등록 학생 수 추이';
  Plotly.react('acad-c',[{{x:dates,y:students,type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}},fill:'tozeroy',fillcolor:'rgba(96,165,250,0.1)',name:'등록 학생'}}],{{...L}},CFG);

  // Daily delta chart
  const deltaTraces=[];
  for(const [fi,arr] of Object.entries(ad.f)){{
    const idx=parseInt(fi);
    const name=fn[featCols[idx]]||featCols[idx];
    const delta=arr.map((v,i)=>i===0?0:Math.max(0,v-arr[i-1]));
    if(delta.some(v=>v>0)){{
      deltaTraces.push({{x:dates,y:delta,name:name,type:'bar',marker:{{color:fcl[idx%fcl.length]}}}});
    }}
  }}
  if(!deltaTraces.length) deltaTraces.push({{x:dates,y:dates.map(()=>0),name:'변화 없음',type:'bar'}});
  Plotly.react('acad-delta',deltaTraces,{{...L,barmode:'stack'}},CFG);
}}

function renderAcadStudent(code,data,info,ac){{
  const src=data.stu;
  const allDates=src.dates;
  const featCols=src.feat_cols;
  const ad=src.data[code];

  if(!ad||!ad.d.length){{
    document.getElementById('acadKpi').innerHTML='<div class="kpi"><div class="label">데이터 없음</div><div class="value">-</div><div class="sub neutral">이 학원의 학생 활성화 데이터가 없습니다</div></div>';
    return;
  }}

  const dates=ad.d.map(i=>allDates[i]);
  const total=ad.t;
  const activeArr=ad.a;
  const totalDays=dates.length;
  const avgActive=totalDays>0?Math.round(activeArr.reduce((a,b)=>a+b,0)/totalDays*10)/10:0;
  const lastTotal=total[total.length-1]||0;
  const maxActive=Math.max(...activeArr);

  // KPIs
  document.getElementById('acadKpi').innerHTML=`
    <div class="kpi"><div class="label">데이터 기간</div><div class="value">${{totalDays}}일</div><div class="sub neutral">${{dates[0]}} ~ ${{dates[dates.length-1]}}</div></div>
    <div class="kpi"><div class="label">최종 학생 수</div><div class="value">${{lastTotal.toLocaleString()}}</div></div>
    <div class="kpi"><div class="label">일평균 활성 학생</div><div class="value">${{avgActive}}</div><div class="sub neutral">최대 ${{maxActive}}명</div></div>
    <div class="kpi"><div class="label">가입 상태</div><div class="value">${{info.r?'가입':'비가입'}}</div></div>`;

  // Feature usage chart
  const fn=S_FNAMES;
  const fcl=SCOL;
  const traces=[];
  for(const [fi,arr] of Object.entries(ad.f)){{
    const idx=parseInt(fi);
    const name=fn[featCols[idx]]||featCols[idx];
    traces.push({{x:dates,y:arr,name:name,type:'scatter',mode:'lines',line:{{color:fcl[idx%fcl.length],width:2}}}});
  }}
  if(!traces.length) traces.push({{x:dates,y:dates.map(()=>0),name:'사용량 없음',type:'scatter',mode:'lines'}});
  document.getElementById('hAcadA').textContent='기능별 누적 사용량 추이 (학생 합계)';
  Plotly.react('acad-feat',traces,{{...L,margin:{{...L.margin,b:60}}}},CFG);

  // Total vs Active students
  document.getElementById('hAcadB').textContent='총 학생 수 vs 활성 학생 수';
  Plotly.react('acad-active',[
    {{x:dates,y:total,name:'총 학생',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}}}},
    {{x:dates,y:activeArr,name:'활성 학생',type:'bar',marker:{{color:'rgba(74,222,128,0.5)'}}}},
  ],{{...L}},CFG);

  // Activation rate
  document.getElementById('hAcadC').textContent='활성화율 추이';
  const rates=total.map((t,i)=>t>0?Math.round(activeArr[i]/t*10000)/100:0);
  Plotly.react('acad-c',[{{x:dates,y:rates,type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2}},fill:'tozeroy',fillcolor:'rgba(245,158,11,0.08)',name:'활성화율'}}],{{...L,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);

  // Daily delta
  const deltaTraces=[];
  for(const [fi,arr] of Object.entries(ad.f)){{
    const idx=parseInt(fi);
    const name=fn[featCols[idx]]||featCols[idx];
    const delta=arr.map((v,i)=>i===0?0:Math.max(0,v-arr[i-1]));
    if(delta.some(v=>v>0)){{
      deltaTraces.push({{x:dates,y:delta,name:name,type:'bar',marker:{{color:fcl[idx%fcl.length]}}}});
    }}
  }}
  if(!deltaTraces.length) deltaTraces.push({{x:dates,y:dates.map(()=>0),name:'변화 없음',type:'bar'}});
  Plotly.react('acad-delta',deltaTraces,{{...L,barmode:'stack'}},CFG);
}}

// INIT
buildTabs();
renderAll();
</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Combined dashboard saved: {OUTPUT}")
