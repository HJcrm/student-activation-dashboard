import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "dashboard_data_v2.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "학생활성화_대시보드.html")

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

daily_json = json.dumps(data['daily'], ensure_ascii=False)
feature_cols_json = json.dumps(data['feature_cols'], ensure_ascii=False)
cat_cols_json = json.dumps(data['cat_cols'], ensure_ascii=False)

feature_names_json = json.dumps({
    '열람권사용량': '열람권 사용',
    '발급권사용량': '발급권 사용',
    '주제발급횟수': '주제 발급',
    '학쫑GPT사용량': '학쫑GPT 사용',
}, ensure_ascii=False)

cat_names_json = json.dumps({
    'cat_기본 이용권': '기본 이용권',
    'cat_전 학교 이용권': '전 학교 이용권(전)',
    'cat_무료 모니터링': '무료 모니터링',
    'cat_全 학교 이용권': '전 학교 이용권(全)',
    'cat_1년 이용권': '1년 이용권',
}, ensure_ascii=False)

date_start = data['summary']['date_start']
date_end = data['summary']['date_end']

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>학쫑 학생 활성화 대시보드</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI','Malgun Gothic',sans-serif;background:#0f172a;color:#e2e8f0}}
  .header{{background:linear-gradient(135deg,#1e293b,#334155);padding:24px 32px;border-bottom:1px solid #475569}}
  .header h1{{font-size:24px;font-weight:700;color:#f8fafc}}
  .header .sub{{font-size:13px;color:#94a3b8;margin-top:4px}}
  .header .badge{{display:inline-block;background:#3b82f6;color:#fff;font-size:11px;padding:2px 8px;border-radius:4px;margin-left:8px}}
  .container{{max-width:1400px;margin:0 auto;padding:20px}}
  .note-box{{background:#1e293b;border:1px solid #f59e0b;border-radius:8px;padding:14px 18px;margin-bottom:20px;font-size:13px;color:#fbbf24}}
  .note-box strong{{color:#f59e0b}}

  /* Date picker bar */
  .date-bar{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 18px;margin-bottom:18px}}
  .date-bar label{{font-size:12px;color:#94a3b8}}
  .date-bar input[type=date]{{background:#0f172a;border:1px solid #475569;border-radius:6px;color:#e2e8f0;padding:6px 10px;font-size:13px;font-family:inherit}}
  .date-bar input[type=date]::-webkit-calendar-picker-indicator{{filter:invert(0.7)}}
  .preset-btn{{padding:6px 14px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px;transition:all .15s}}
  .preset-btn:hover{{background:#334155;color:#e2e8f0}}
  .preset-btn.active{{background:#3b82f6;color:#fff;border-color:#3b82f6}}
  .date-bar .sep{{color:#475569;font-size:16px}}
  .date-bar .range-info{{font-size:12px;color:#64748b;margin-left:auto}}

  .kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:22px}}
  .kpi{{background:#1e293b;border-radius:12px;padding:18px;border:1px solid #334155}}
  .kpi .label{{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px}}
  .kpi .value{{font-size:26px;font-weight:700;color:#f8fafc;margin:6px 0 3px}}
  .kpi .sub{{font-size:11px}}
  .up{{color:#4ade80}} .down{{color:#f87171}} .neutral{{color:#94a3b8}}

  .tab-bar{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
  .tab-btn{{padding:8px 20px;border:1px solid #475569;border-radius:8px;background:#1e293b;color:#94a3b8;cursor:pointer;font-size:13px;transition:all .2s}}
  .tab-btn:hover{{background:#334155;color:#e2e8f0}}
  .tab-btn.active{{background:#3b82f6;color:#fff;border-color:#3b82f6}}

  .chart-section{{margin-bottom:20px}}
  .card{{background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155;margin-bottom:14px}}
  .card h3{{font-size:15px;color:#f8fafc;margin-bottom:10px}}
  .row2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
  @media(max-width:900px){{.row2{{grid-template-columns:1fr}}}}
  .plot{{width:100%;height:370px}}
  .plot-tall{{width:100%;height:430px}}
  .hidden{{display:none}}

  /* Data table */
  .tbl-wrap{{max-height:700px;overflow:auto;border-radius:8px;border:1px solid #334155}}
  .tbl-wrap::-webkit-scrollbar{{width:8px;height:8px}}
  .tbl-wrap::-webkit-scrollbar-track{{background:#1e293b}}
  .tbl-wrap::-webkit-scrollbar-thumb{{background:#475569;border-radius:4px}}
  .data-tbl{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}
  .data-tbl thead{{position:sticky;top:0;z-index:2}}
  .data-tbl th{{background:#334155;color:#e2e8f0;padding:10px 14px;text-align:right;cursor:pointer;user-select:none;border-bottom:2px solid #475569;font-weight:600}}
  .data-tbl th:first-child{{text-align:left;position:sticky;left:0;z-index:3;background:#334155}}
  .data-tbl th:hover{{background:#475569}}
  .data-tbl th .arrow{{font-size:10px;margin-left:4px;color:#94a3b8}}
  .data-tbl td{{padding:8px 14px;text-align:right;border-bottom:1px solid #1e293b}}
  .data-tbl td:first-child{{text-align:left;font-weight:500;position:sticky;left:0;background:#0f172a;z-index:1}}
  .data-tbl tbody tr{{background:#0f172a}}
  .data-tbl tbody tr:hover{{background:#1e293b}}
  .data-tbl tbody tr:nth-child(even){{background:#0c1322}}
  .data-tbl tbody tr:nth-child(even):hover{{background:#1e293b}}
  .data-tbl tbody tr:nth-child(even) td:first-child{{background:#0c1322}}
  .data-tbl tbody tr:hover td:first-child{{background:#1e293b}}
  .tbl-toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap}}
  .tbl-toolbar .cnt{{font-size:12px;color:#64748b}}
  .csv-btn{{padding:6px 14px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px;transition:all .15s}}
  .csv-btn:hover{{background:#334155;color:#e2e8f0}}

  /* Outlier toggle */
  .outlier-toggle{{display:flex;align-items:center;gap:8px;margin-left:8px;padding-left:12px;border-left:1px solid #334155}}
  .outlier-toggle label{{font-size:12px;color:#94a3b8;cursor:pointer;user-select:none}}
  .switch{{position:relative;width:36px;height:20px;flex-shrink:0}}
  .switch input{{opacity:0;width:0;height:0}}
  .slider{{position:absolute;cursor:pointer;inset:0;background:#475569;border-radius:20px;transition:.2s}}
  .slider::before{{content:'';position:absolute;width:16px;height:16px;left:2px;bottom:2px;background:#e2e8f0;border-radius:50%;transition:.2s}}
  .switch input:checked+.slider{{background:#3b82f6}}
  .switch input:checked+.slider::before{{transform:translateX(16px)}}
  .outlier-info{{font-size:11px;color:#f87171;margin-left:4px}}
</style>
</head>
<body>
<div class="header">
  <h1>학쫑 학생 활성화 대시보드 <span class="badge">일별 증분 기준</span></h1>
  <p class="sub">활성 기준: 전일 대비 수치형 사용량(열람권·발급권·주제발급·학쫑GPT) 증가 학생</p>
</div>
<div class="container">

  <div class="note-box">
    <strong>활성 학생 기준:</strong> 전일 대비 수치형 데이터(열람권사용량, 발급권사용량, 주제발급횟수, 학쫑GPT사용량) 중 하나라도 증가한 학생 + 신규 등록 학생 중 사용량 > 0인 학생. Y/N 플래그는 제외.
  </div>

  <!-- Date range picker -->
  <div class="date-bar">
    <label>시작</label>
    <input type="date" id="startDate" value="{date_start}" min="{date_start}" max="{date_end}">
    <span class="sep">~</span>
    <label>종료</label>
    <input type="date" id="endDate" value="{date_end}" min="{date_start}" max="{date_end}">
    <button class="preset-btn" onclick="setRange(7)">최근 7일</button>
    <button class="preset-btn" onclick="setRange(14)">최근 14일</button>
    <button class="preset-btn" onclick="setRange(30)">최근 30일</button>
    <button class="preset-btn" onclick="setRange(90)">최근 90일</button>
    <button class="preset-btn" onclick="setRange(180)">최근 6개월</button>
    <button class="preset-btn active" onclick="setRange(0)">전체</button>
    <span class="range-info" id="rangeInfo"></span>
    <div class="outlier-toggle">
      <label class="switch"><input type="checkbox" id="outlierToggle" onchange="renderAll()"><span class="slider"></span></label>
      <label for="outlierToggle">이상치 제외</label>
      <span class="outlier-info" id="outlierInfo"></span>
    </div>
  </div>

  <!-- KPI -->
  <div class="kpi-row">
    <div class="kpi"><div class="label">기간 내 총 등록 학생 (최종일)</div><div class="value" id="kTotal">-</div><div class="sub neutral" id="kTotalSub"></div></div>
    <div class="kpi"><div class="label">기간 내 일평균 활성 학생</div><div class="value" id="kActive">-</div><div class="sub neutral" id="kActiveSub"></div></div>
    <div class="kpi"><div class="label">기간 내 평균 활성화율</div><div class="value" id="kRate">-</div></div>
    <div class="kpi"><div class="label">기간 내 학원 수 (최종일)</div><div class="value" id="kAcad">-</div></div>
    <div class="kpi"><div class="label">기간 내 신규 학생 합계</div><div class="value" id="kNew">-</div></div>
  </div>

  <!-- Tabs -->
  <div class="tab-bar">
    <button class="tab-btn active" onclick="showTab('daily',this)">일별</button>
    <button class="tab-btn" onclick="showTab('weekly',this)">주별</button>
    <button class="tab-btn" onclick="showTab('monthly',this)">월별</button>
    <button class="tab-btn" onclick="showTab('features',this)">기능별 사용현황</button>
    <button class="tab-btn" onclick="showTab('grades',this)">학년별 분포</button>
    <button class="tab-btn" onclick="showTab('categories',this)">이용권별 분포</button>
    <button class="tab-btn" onclick="showTab('table',this)">데이터 테이블</button>
  </div>

  <div id="tab-daily" class="chart-section">
    <div class="row2">
      <div class="card"><h3>일별 활성 학생 수 (전일 대비 증분)</h3><div id="d-active" class="plot"></div></div>
      <div class="card"><h3>일별 활성화율 (%)</h3><div id="d-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>일별 총 등록 학생 수</h3><div id="d-total" class="plot"></div></div>
      <div class="card"><h3>일별 신규 등록 학생</h3><div id="d-new" class="plot"></div></div>
    </div>
    <div class="card"><h3>일별 학원 수</h3><div id="d-acad" class="plot"></div></div>
  </div>

  <div id="tab-weekly" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3>주별 평균 활성 학생 수</h3><div id="w-active" class="plot"></div></div>
      <div class="card"><h3>주별 평균 활성화율 (%)</h3><div id="w-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>주별 최대 활성 학생 수</h3><div id="w-max" class="plot"></div></div>
      <div class="card"><h3>주별 신규 학생 수</h3><div id="w-new" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-monthly" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3>월별 평균 활성 학생 수</h3><div id="m-active" class="plot"></div></div>
      <div class="card"><h3>월별 평균 활성화율 (%)</h3><div id="m-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>월별 최대 활성 학생 수</h3><div id="m-max" class="plot"></div></div>
      <div class="card"><h3>월별 신규 학생 수</h3><div id="m-new" class="plot"></div></div>
    </div>
    <div class="card"><h3>월별 총 등록 학생 추이</h3><div id="m-total" class="plot"></div></div>
  </div>

  <div id="tab-features" class="chart-section hidden">
    <div class="card"><h3>기능별 일별 활성 학생 수</h3><div id="f-trend" class="plot-tall"></div></div>
    <div class="card"><h3>기간 내 기능별 평균 활성 학생</h3><div id="f-bar" class="plot"></div></div>
  </div>

  <div id="tab-grades" class="chart-section hidden">
    <div class="card"><h3>학년별 학생 수 추이</h3><div id="g-trend" class="plot-tall"></div></div>
    <div class="card"><h3>최종일 학년별 분포</h3><div id="g-pie" class="plot"></div></div>
  </div>

  <div id="tab-categories" class="chart-section hidden">
    <div class="card"><h3>이용권 유형별 학생 수 추이</h3><div id="c-trend" class="plot-tall"></div></div>
    <div class="card"><h3>최종일 이용권별 분포</h3><div id="c-pie" class="plot"></div></div>
  </div>

  <div id="tab-table" class="chart-section hidden">
    <div class="card">
      <h3>일별 데이터 테이블</h3>
      <div class="tbl-toolbar">
        <span class="cnt" id="tblCount"></span>
        <button class="csv-btn" onclick="downloadCSV()">CSV 다운로드</button>
      </div>
      <div class="tbl-wrap">
        <table class="data-tbl" id="dataTable">
          <thead id="tblHead"></thead>
          <tbody id="tblBody"></tbody>
        </table>
      </div>
    </div>
  </div>

</div>

<script>
// ===== RAW DATA =====
const RAW = {daily_json};
const FEAT_COLS = {feature_cols_json};
const CAT_COLS = {cat_cols_json};
const FEAT_NAMES = {feature_names_json};
const CAT_NAMES = {cat_names_json};
const FCOL = ['#60a5fa','#4ade80','#f59e0b','#e879f9'];
const CCOL = ['#60a5fa','#4ade80','#f59e0b','#f472b6','#818cf8'];

const L = {{
  paper_bgcolor:'#1e293b', plot_bgcolor:'#1e293b',
  font:{{color:'#e2e8f0',family:'Segoe UI,Malgun Gothic,sans-serif',size:12}},
  xaxis:{{gridcolor:'#334155',linecolor:'#475569'}},
  yaxis:{{gridcolor:'#334155',linecolor:'#475569'}},
  margin:{{l:55,r:20,t:10,b:50}},
  legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:11}}}},
  hovermode:'x unified',
}};
const CFG = {{responsive:true,displayModeBar:false}};

// ===== HELPERS =====
function ma(arr,w=7){{
  return arr.map((_,i)=>{{const s=Math.max(0,i-w+1);const sl=arr.slice(s,i+1);return Math.round(sl.reduce((a,b)=>a+b,0)/sl.length*10)/10}});
}}
function groupBy(arr,keyFn){{
  const m={{}};
  arr.forEach(d=>{{const k=keyFn(d);if(!m[k])m[k]=[];m[k].push(d)}});
  return m;
}}
function isoWeek(ds){{
  const d=new Date(ds);const jan1=new Date(d.getFullYear(),0,1);
  const days=Math.floor((d-jan1)/86400000);
  const wn=Math.ceil((days+jan1.getDay()+1)/7);
  return d.getFullYear()+'-W'+String(wn).padStart(2,'0');
}}
function isoMonth(ds){{return ds.substring(0,7)}}

// ===== FILTER & RENDER =====
function iqrBounds(arr){{
  const sorted=[...arr].sort((a,b)=>a-b);
  const q1=sorted[Math.floor(sorted.length*0.25)];
  const q3=sorted[Math.floor(sorted.length*0.75)];
  const iqr=q3-q1;
  return {{ lo:q1-1.5*iqr, hi:q3+1.5*iqr }};
}}

function getFiltered(){{
  const s=document.getElementById('startDate').value;
  const e=document.getElementById('endDate').value;
  let F=RAW.filter(d=>d.date>=s && d.date<=e);

  const excludeOutliers=document.getElementById('outlierToggle').checked;
  const infoEl=document.getElementById('outlierInfo');

  if(excludeOutliers && F.length>7){{
    const actVals=F.map(d=>d.active_students);
    const newVals=F.map(d=>d.new_students||0);
    const actB=iqrBounds(actVals);
    const newB=iqrBounds(newVals);
    const before=F.length;
    F=F.filter(d=>d.active_students<=actB.hi && (d.new_students||0)<=newB.hi);
    const removed=before-F.length;
    infoEl.textContent=removed>0?`(${{removed}}일 제외됨)`:'(이상치 없음)';
  }} else {{
    infoEl.textContent='';
  }}
  return F;
}}

function renderAll(){{
  const F=getFiltered();
  if(F.length===0)return;

  const dates=F.map(d=>d.date);
  const totalSt=F.map(d=>d.total_students);
  const activeSt=F.map(d=>d.active_students);
  const actRate=F.map(d=>d.activation_rate);
  const newSt=F.map(d=>d.new_students||0);
  const nAcad=F.map(d=>d.n_academies);
  const aMa7=ma(activeSt,7);
  const rMa7=ma(actRate,7);

  // KPI
  const last=F[F.length-1];
  const avgAct=Math.round(activeSt.reduce((a,b)=>a+b,0)/F.length*10)/10;
  const avgRate=Math.round(actRate.reduce((a,b)=>a+b,0)/F.length*100)/100;
  const sumNew=newSt.reduce((a,b)=>a+b,0);
  document.getElementById('kTotal').textContent=last.total_students.toLocaleString();
  document.getElementById('kTotalSub').textContent=dates[0]+' ~ '+dates[dates.length-1]+' ('+F.length+'일)';
  document.getElementById('kActive').textContent=avgAct.toLocaleString();
  document.getElementById('kActiveSub').textContent='최종일 '+last.active_students+'명';
  document.getElementById('kRate').textContent=avgRate+'%';
  document.getElementById('kAcad').textContent=last.n_academies.toLocaleString();
  document.getElementById('kNew').textContent=sumNew.toLocaleString();
  document.getElementById('rangeInfo').textContent=F.length+'일 선택됨';

  // DAILY
  Plotly.react('d-active',[
    {{x:dates,y:activeSt,name:'활성 학생',type:'bar',marker:{{color:'rgba(96,165,250,0.6)'}}}},
    {{x:dates,y:aMa7,name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}}}},
  ],{{...L}},CFG);
  Plotly.react('d-rate',[
    {{x:dates,y:actRate,name:'활성화율',type:'bar',marker:{{color:'rgba(74,222,128,0.5)'}}}},
    {{x:dates,y:rMa7,name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}}}},
  ],{{...L,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('d-total',[
    {{x:dates,y:totalSt,name:'총 학생',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}},fill:'tozeroy',fillcolor:'rgba(96,165,250,0.1)'}},
  ],{{...L}},CFG);
  Plotly.react('d-new',[
    {{x:dates,y:newSt,name:'신규 학생',type:'bar',marker:{{color:'#818cf8'}}}},
  ],{{...L}},CFG);
  Plotly.react('d-acad',[
    {{x:dates,y:nAcad,name:'학원 수',type:'scatter',mode:'lines',line:{{color:'#f472b6',width:2}},fill:'tozeroy',fillcolor:'rgba(244,114,182,0.08)'}},
  ],{{...L}},CFG);

  // WEEKLY aggregation
  const wGrp=groupBy(F,d=>isoWeek(d.date));
  const wKeys=Object.keys(wGrp).sort();
  const wLabels=wKeys.map(k=>{{const g=wGrp[k];return g[0].date+'~'+g[g.length-1].date.substring(5)}});
  const wAvgAct=wKeys.map(k=>{{const g=wGrp[k];return Math.round(g.reduce((a,d)=>a+d.active_students,0)/g.length*10)/10}});
  const wAvgRate=wKeys.map(k=>{{const g=wGrp[k];return Math.round(g.reduce((a,d)=>a+d.activation_rate,0)/g.length*100)/100}});
  const wMaxAct=wKeys.map(k=>Math.max(...wGrp[k].map(d=>d.active_students)));
  const wNew=wKeys.map(k=>wGrp[k].reduce((a,d)=>a+(d.new_students||0),0));

  Plotly.react('w-active',[
    {{x:wLabels,y:wAvgAct,name:'평균 활성',type:'bar',marker:{{color:'#60a5fa'}}}},
  ],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-rate',[
    {{x:wLabels,y:wAvgRate,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:2}},marker:{{size:4}}}},
  ],{{...L,xaxis:{{...L.xaxis,tickangle:-45}},yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('w-max',[
    {{x:wLabels,y:wMaxAct,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}}}},
  ],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-new',[
    {{x:wLabels,y:wNew,name:'신규 학생',type:'bar',marker:{{color:'#818cf8'}}}},
  ],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);

  // MONTHLY aggregation
  const mGrp=groupBy(F,d=>isoMonth(d.date));
  const mKeys=Object.keys(mGrp).sort();
  const mAvgAct=mKeys.map(k=>{{const g=mGrp[k];return Math.round(g.reduce((a,d)=>a+d.active_students,0)/g.length*10)/10}});
  const mAvgRate=mKeys.map(k=>{{const g=mGrp[k];return Math.round(g.reduce((a,d)=>a+d.activation_rate,0)/g.length*100)/100}});
  const mMaxAct=mKeys.map(k=>Math.max(...mGrp[k].map(d=>d.active_students)));
  const mNew=mKeys.map(k=>mGrp[k].reduce((a,d)=>a+(d.new_students||0),0));
  const mTot=mKeys.map(k=>{{const g=mGrp[k];return Math.round(g.reduce((a,d)=>a+d.total_students,0)/g.length)}});

  Plotly.react('m-active',[
    {{x:mKeys,y:mAvgAct,name:'평균 활성',type:'bar',marker:{{color:'#60a5fa'}},text:mAvgAct.map(v=>v.toFixed(1)),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}},
  ],{{...L}},CFG);
  Plotly.react('m-rate',[
    {{x:mKeys,y:mAvgRate,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:3}},marker:{{size:7}}}},
  ],{{...L,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('m-max',[
    {{x:mKeys,y:mMaxAct,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}},text:mMaxAct,textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}},
  ],{{...L}},CFG);
  Plotly.react('m-new',[
    {{x:mKeys,y:mNew,name:'신규 학생',type:'bar',marker:{{color:'#818cf8'}},text:mNew,textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}},
  ],{{...L}},CFG);
  Plotly.react('m-total',[
    {{x:mKeys,y:mTot,name:'평균 총 학생',type:'bar',marker:{{color:'#38bdf8'}},text:mTot.map(v=>v.toLocaleString()),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}},
  ],{{...L}},CFG);

  // FEATURES
  const fTraces=FEAT_COLS.map((k,i)=>({{
    x:dates,y:F.map(d=>d[k]||0),name:FEAT_NAMES[k]||k,type:'scatter',mode:'lines',
    line:{{color:FCOL[i%FCOL.length],width:2}},
  }}));
  Plotly.react('f-trend',fTraces,{{...L,margin:{{...L.margin,b:60}}}},CFG);

  const fAvg=FEAT_COLS.map(k=>{{const vals=F.map(d=>d[k]||0);return Math.round(vals.reduce((a,b)=>a+b,0)/vals.length*10)/10}});
  const fLabels=FEAT_COLS.map(k=>FEAT_NAMES[k]||k);
  Plotly.react('f-bar',[{{
    x:fLabels,y:fAvg,type:'bar',marker:{{color:FCOL}},
    text:fAvg.map(v=>v.toString()),textposition:'outside',textfont:{{color:'#94a3b8',size:12}},
  }}],{{...L}},CFG);

  // GRADES
  const g0=F.map(d=>d.grade_0||0),g1=F.map(d=>d.grade_1||0),g2=F.map(d=>d.grade_2||0),g3=F.map(d=>d.grade_3||0);
  Plotly.react('g-trend',[
    {{x:dates,y:g0,name:'예비(0학년)',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#f472b6'}}}},
    {{x:dates,y:g1,name:'고1',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#60a5fa'}}}},
    {{x:dates,y:g2,name:'고2',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#4ade80'}}}},
    {{x:dates,y:g3,name:'고3',type:'scatter',mode:'lines',stackgroup:'one',line:{{color:'#f59e0b'}}}},
  ],{{...L}},CFG);

  const lg=[g0[g0.length-1],g1[g1.length-1],g2[g2.length-1],g3[g3.length-1]];
  Plotly.react('g-pie',[{{
    values:lg,labels:['예비(0학년)','고1','고2','고3'],type:'pie',hole:.4,
    marker:{{colors:['#f472b6','#60a5fa','#4ade80','#f59e0b']}},
    textinfo:'label+value+percent',textfont:{{size:12}},
  }}],{{...L,margin:{{l:20,r:20,t:10,b:10}}}},CFG);

  // CATEGORIES
  const cTraces=CAT_COLS.map((k,i)=>({{
    x:dates,y:F.map(d=>d[k]||0),name:CAT_NAMES[k]||k,type:'scatter',mode:'lines',
    stackgroup:'one',line:{{color:CCOL[i%CCOL.length]}},
  }}));
  Plotly.react('c-trend',cTraces,{{...L}},CFG);

  const lcV=CAT_COLS.map(k=>last[k]||0);
  const lcL=CAT_COLS.map(k=>CAT_NAMES[k]||k);
  Plotly.react('c-pie',[{{
    values:lcV,labels:lcL,type:'pie',hole:.4,
    marker:{{colors:CCOL}},textinfo:'label+value+percent',textfont:{{size:11}},
  }}],{{...L,margin:{{l:20,r:20,t:10,b:10}}}},CFG);

  // DATA TABLE
  renderTable(F);
}}

// ===== DATA TABLE =====
const TBL_COLS = [
  {{key:'date',label:'날짜',fmt:v=>v}},
  {{key:'day_of_week',label:'요일',fmt:v=>{{const m={{'Monday':'월','Tuesday':'화','Wednesday':'수','Thursday':'목','Friday':'금','Saturday':'토','Sunday':'일'}};return m[v]||v}}}},
  {{key:'total_students',label:'총 학생',fmt:v=>v.toLocaleString()}},
  {{key:'active_students',label:'활성 학생',fmt:v=>v.toLocaleString()}},
  {{key:'activation_rate',label:'활성화율(%)',fmt:v=>v.toFixed(2)}},
  {{key:'new_students',label:'신규 학생',fmt:v=>(v||0).toLocaleString()}},
  {{key:'n_academies',label:'학원 수',fmt:v=>v.toLocaleString()}},
  {{key:'grade_0',label:'예비(0)',fmt:v=>(v||0).toLocaleString()}},
  {{key:'grade_1',label:'고1',fmt:v=>(v||0).toLocaleString()}},
  {{key:'grade_2',label:'고2',fmt:v=>(v||0).toLocaleString()}},
  {{key:'grade_3',label:'고3',fmt:v=>(v||0).toLocaleString()}},
];
FEAT_COLS.forEach(k=>TBL_COLS.push({{key:k,label:FEAT_NAMES[k]||k,fmt:v=>(v||0).toLocaleString()}}));
CAT_COLS.forEach(k=>TBL_COLS.push({{key:k,label:CAT_NAMES[k]||k,fmt:v=>(v||0).toLocaleString()}}));

let tblSortKey='date', tblSortAsc=false, tblData=[];

function renderTable(F){{
  tblData=F;
  const head=document.getElementById('tblHead');
  head.innerHTML='<tr>'+TBL_COLS.map(c=>
    `<th onclick="sortTable('${{c.key}}')">${{c.label}}<span class="arrow">${{tblSortKey===c.key?(tblSortAsc?'▲':'▼'):''}}</span></th>`
  ).join('')+'</tr>';
  fillTableBody();
}}

function fillTableBody(){{
  const sorted=[...tblData].sort((a,b)=>{{
    let va=a[tblSortKey]??0, vb=b[tblSortKey]??0;
    if(typeof va==='string') return tblSortAsc?va.localeCompare(vb):vb.localeCompare(va);
    return tblSortAsc?va-vb:vb-va;
  }});
  const body=document.getElementById('tblBody');
  body.innerHTML=sorted.map(d=>
    '<tr>'+TBL_COLS.map(c=>`<td>${{c.fmt(d[c.key]??0)}}</td>`).join('')+'</tr>'
  ).join('');
  document.getElementById('tblCount').textContent=`${{sorted.length}}일 데이터`;
}}

function sortTable(key){{
  if(tblSortKey===key) tblSortAsc=!tblSortAsc;
  else {{ tblSortKey=key; tblSortAsc=(key==='date'); }}
  // re-render header arrows
  document.querySelectorAll('#tblHead th .arrow').forEach((el,i)=>{{
    el.textContent=TBL_COLS[i].key===tblSortKey?(tblSortAsc?'▲':'▼'):'';
  }});
  fillTableBody();
}}

function downloadCSV(){{
  const F=getFiltered();
  const header=TBL_COLS.map(c=>c.label).join(',');
  const rows=F.map(d=>TBL_COLS.map(c=>{{
    let v=d[c.key]??0;
    if(c.key==='day_of_week'){{const m={{'Monday':'월','Tuesday':'화','Wednesday':'수','Thursday':'목','Friday':'금','Saturday':'토','Sunday':'일'}};v=m[v]||v;}}
    return v;
  }}).join(','));
  const csv='\\uFEFF'+header+'\\n'+rows.join('\\n');
  const blob=new Blob([csv],{{type:'text/csv;charset=utf-8'}});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='학생활성화_일별데이터.csv';a.click();
  URL.revokeObjectURL(url);
}}

// ===== DATE RANGE CONTROLS =====
function setRange(days){{
  const allDates=RAW.map(d=>d.date);
  const minD=allDates[0], maxD=allDates[allDates.length-1];
  document.querySelectorAll('.preset-btn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  if(days===0){{
    document.getElementById('startDate').value=minD;
    document.getElementById('endDate').value=maxD;
  }} else {{
    const end=new Date(maxD);
    const start=new Date(end);
    start.setDate(start.getDate()-days+1);
    const startStr=start.toISOString().substring(0,10);
    document.getElementById('startDate').value=startStr<minD?minD:startStr;
    document.getElementById('endDate').value=maxD;
  }}
  renderAll();
}}

document.getElementById('startDate').addEventListener('change',()=>{{
  document.querySelectorAll('.preset-btn').forEach(b=>b.classList.remove('active'));
  renderAll();
}});
document.getElementById('endDate').addEventListener('change',()=>{{
  document.querySelectorAll('.preset-btn').forEach(b=>b.classList.remove('active'));
  renderAll();
}});

// ===== TAB =====
let currentTab='daily';
function showTab(tab,btn){{
  document.querySelectorAll('.chart-section').forEach(el=>el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(el=>el.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.remove('hidden');
  btn.classList.add('active');
  currentTab=tab;
  setTimeout(()=>{{
    document.querySelectorAll('#tab-'+tab+' .plot, #tab-'+tab+' .plot-tall').forEach(el=>Plotly.Plots.resize(el));
  }},100);
}}

// Initial render
renderAll();
</script>
</body>
</html>"""

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Dashboard saved: {OUTPUT_PATH}")
