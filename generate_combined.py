import json
import os

BASE = os.path.dirname(__file__)

with open(os.path.join(BASE, "학생 관련 데이터", "dashboard_data_v2.json"), 'r', encoding='utf-8') as f:
    student_data = json.load(f)
with open(os.path.join(BASE, "학원 관련 데이터", "dashboard_data.json"), 'r', encoding='utf-8') as f:
    inst_data = json.load(f)

OUTPUT = os.path.join(BASE, "학쫑_통합_대시보드.html")

student_json = json.dumps(student_data['daily'], ensure_ascii=False)
student_feat_json = json.dumps(student_data['feature_cols'], ensure_ascii=False)
inst_json = json.dumps(inst_data['daily'], ensure_ascii=False)
inst_feat_json = json.dumps(inst_data['feature_cols'], ensure_ascii=False)

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
  body{{font-family:'Segoe UI','Malgun Gothic',sans-serif;background:#0f172a;color:#e2e8f0}}

  .header{{background:linear-gradient(135deg,#1e293b,#334155);padding:20px 32px;border-bottom:1px solid #475569;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
  .header h1{{font-size:22px;font-weight:700;color:#f8fafc}}
  .mode-bar{{display:flex;gap:0;border-radius:10px;overflow:hidden;border:1px solid #475569}}
  .mode-btn{{padding:10px 28px;background:#1e293b;color:#94a3b8;border:none;cursor:pointer;font-size:14px;font-weight:600;font-family:inherit;transition:all .2s}}
  .mode-btn:hover{{background:#334155;color:#e2e8f0}}
  .mode-btn.active-student{{background:#3b82f6;color:#fff}}
  .mode-btn.active-inst{{background:#8b5cf6;color:#fff}}

  .container{{max-width:1400px;margin:0 auto;padding:20px}}
  .note-box{{border-radius:8px;padding:14px 18px;margin-bottom:20px;font-size:13px}}
  .note-box.student{{background:#1e293b;border:1px solid #f59e0b;color:#fbbf24}}
  .note-box.student strong{{color:#f59e0b}}
  .note-box.inst{{background:#1e293b;border:1px solid #8b5cf6;color:#c4b5fd}}
  .note-box.inst strong{{color:#a78bfa}}

  .date-bar{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 18px;margin-bottom:18px}}
  .date-bar label{{font-size:12px;color:#94a3b8}}
  .date-bar input[type=date]{{background:#0f172a;border:1px solid #475569;border-radius:6px;color:#e2e8f0;padding:6px 10px;font-size:13px;font-family:inherit}}
  .date-bar input[type=date]::-webkit-calendar-picker-indicator{{filter:invert(0.7)}}
  .preset-btn{{padding:6px 14px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px;transition:all .15s}}
  .preset-btn:hover{{background:#334155;color:#e2e8f0}}
  .preset-btn.active{{color:#fff;border-color:currentColor}}
  .date-bar .sep{{color:#475569;font-size:16px}}
  .date-bar .range-info{{font-size:12px;color:#64748b;margin-left:auto}}
  .outlier-toggle{{display:flex;align-items:center;gap:8px;margin-left:8px;padding-left:12px;border-left:1px solid #334155}}
  .outlier-toggle label{{font-size:12px;color:#94a3b8;cursor:pointer;user-select:none}}
  .switch{{position:relative;width:36px;height:20px;flex-shrink:0}}
  .switch input{{opacity:0;width:0;height:0}}
  .slider{{position:absolute;cursor:pointer;inset:0;background:#475569;border-radius:20px;transition:.2s}}
  .slider::before{{content:'';position:absolute;width:16px;height:16px;left:2px;bottom:2px;background:#e2e8f0;border-radius:50%;transition:.2s}}
  .switch input:checked+.slider{{background:#3b82f6}}
  .switch input:checked+.slider::before{{transform:translateX(16px)}}
  .outlier-info{{font-size:11px;color:#f87171;margin-left:4px}}

  .kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:22px}}
  .kpi{{background:#1e293b;border-radius:12px;padding:18px;border:1px solid #334155}}
  .kpi .label{{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px}}
  .kpi .value{{font-size:26px;font-weight:700;color:#f8fafc;margin:6px 0 3px}}
  .kpi .sub{{font-size:11px}}
  .up{{color:#4ade80}} .down{{color:#f87171}} .neutral{{color:#94a3b8}}

  .tab-bar{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
  .tab-btn{{padding:8px 20px;border:1px solid #475569;border-radius:8px;background:#1e293b;color:#94a3b8;cursor:pointer;font-size:13px;transition:all .2s}}
  .tab-btn:hover{{background:#334155;color:#e2e8f0}}
  .tab-btn.active{{color:#fff}}

  .chart-section{{margin-bottom:20px}}
  .card{{background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155;margin-bottom:14px}}
  .card h3{{font-size:15px;color:#f8fafc;margin-bottom:10px}}
  .row2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
  @media(max-width:900px){{.row2{{grid-template-columns:1fr}}}}
  .plot{{width:100%;height:370px}}.plot-tall{{width:100%;height:430px}}
  .hidden{{display:none}}

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
  .tbl-toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:10px}}
  .tbl-toolbar .cnt{{font-size:12px;color:#64748b}}
  .csv-btn{{padding:6px 14px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px}}
  .csv-btn:hover{{background:#334155;color:#e2e8f0}}
</style>
</head>
<body>
<div class="header">
  <h1>학쫑 통합 대시보드</h1>
  <div class="mode-bar">
    <button class="mode-btn active-student" id="modeStudent" onclick="switchMode('student')">학생 활성화</button>
    <button class="mode-btn" id="modeInst" onclick="switchMode('inst')">학원 활성화</button>
  </div>
</div>
<div class="container">

  <div class="note-box student" id="noteStudent">
    <strong>활성 학생 기준:</strong> 전일 대비 수치형 데이터(열람권사용량, 발급권사용량, 주제발급횟수, 학쫑GPT사용량) 중 하나라도 증가한 학생. Y/N 플래그 제외.
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

  <div id="tab-table" class="chart-section hidden">
    <div class="card">
      <h3>일별 데이터 테이블</h3>
      <div class="tbl-toolbar"><span class="cnt" id="tblCount"></span><button class="csv-btn" onclick="downloadCSV()">CSV 다운로드</button></div>
      <div class="tbl-wrap"><table class="data-tbl"><thead id="tblHead"></thead><tbody id="tblBody"></tbody></table></div>
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

const SCOL=['#60a5fa','#4ade80','#f59e0b','#e879f9','#818cf8'];
const ICOL=['#a78bfa','#60a5fa','#4ade80','#f59e0b','#f472b6','#818cf8','#fb923c','#22d3ee','#e879f9','#facc15','#34d399','#f87171','#38bdf8'];

function accent(){{return MODE==='student'?'#3b82f6':'#8b5cf6'}}
function raw(){{return MODE==='student'?S_RAW:I_RAW}}
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

// ===== MODE SWITCH =====
function switchMode(m){{
  MODE=m;
  document.getElementById('modeStudent').className='mode-btn'+(m==='student'?' active-student':'');
  document.getElementById('modeInst').className='mode-btn'+(m==='inst'?' active-inst':'');
  document.getElementById('noteStudent').classList.toggle('hidden',m!=='student');
  document.getElementById('noteInst').classList.toggle('hidden',m!=='inst');
  // Update accent on active preset/tab buttons
  document.querySelectorAll('.preset-btn.active,.tab-btn.active').forEach(b=>b.style.background=accent());
  document.querySelector('.switch input:checked+.slider')?.style&&document.querySelectorAll('.switch input:checked+.slider').forEach(s=>s.style.background=accent());
  buildTabs();
  renderAll();
}}

function buildTabs(){{
  const e=entity();
  const tabs=[
    ['daily','일별'],['weekly','주별'],['monthly','월별'],['features','기능별 사용현황'],
  ];
  if(MODE==='student') tabs.push(['extra','학년/이용권']);
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
    kpiHTML+=`<div class="kpi"><div class="label">학원 수 (최종일)</div><div class="value">${{(last.n_academies||0).toLocaleString()}}</div></div>`;
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

  const barC=ac.replace(')',',0.6)').replace('rgb','rgba').replace('#','');
  const barColor=`rgba(${{parseInt(ac.slice(1,3),16)}},${{parseInt(ac.slice(3,5),16)}},${{parseInt(ac.slice(5,7),16)}},0.6)`;

  // DAILY
  Plotly.react('d-active',[
    {{x:dates,y:actV,name:`활성 ${{e}}`,type:'bar',marker:{{color:barColor}}}},
    {{x:dates,y:ma(actV),name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}}}},
  ],{{...L}},CFG);
  Plotly.react('d-rate',[
    {{x:dates,y:actR,name:'활성화율',type:'bar',marker:{{color:'rgba(74,222,128,0.5)'}}}},
    {{x:dates,y:ma(actR),name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}}}},
  ],{{...L,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('d-total',[
    {{x:dates,y:totV,name:`총 ${{e}}`,type:'scatter',mode:'lines',line:{{color:ac,width:2}},fill:'tozeroy',fillcolor:barColor.replace('0.6','0.1')}},
  ],{{...L}},CFG);
  Plotly.react('d-new',[
    {{x:dates,y:newV,name:`신규 ${{e}}`,type:'bar',marker:{{color:'#818cf8'}}}},
  ],{{...L}},CFG);

  // Extra daily card
  const eCard=document.getElementById('extraDailyCard');
  if(MODE==='student'){{
    eCard.classList.remove('hidden');
    document.getElementById('hDE').textContent='일별 학원 수';
    Plotly.react('d-extra',[{{x:dates,y:F.map(d=>d.n_academies||0),name:'학원 수',type:'scatter',mode:'lines',line:{{color:'#f472b6',width:2}},fill:'tozeroy',fillcolor:'rgba(244,114,182,0.08)'}}],{{...L}},CFG);
  }}else{{
    eCard.classList.remove('hidden');
    document.getElementById('hDE').textContent='등록 학생 수 추이';
    Plotly.react('d-extra',[{{x:dates,y:F.map(d=>d.total_registered_students||0),name:'등록 학생',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}},fill:'tozeroy',fillcolor:'rgba(96,165,250,0.1)'}}],{{...L}},CFG);
  }}

  // WEEKLY
  const wG=groupBy(F,d=>isoWeek(d.date)),wK=Object.keys(wG).sort();
  const wLb=wK.map(k=>{{const g=wG[k];return g[0].date+'~'+g[g.length-1].date.substring(5)}});
  const wA=wK.map(k=>{{const g=wG[k];return +(g.reduce((a,d)=>a+d[ak],0)/g.length).toFixed(1)}});
  const wR=wK.map(k=>{{const g=wG[k];return +(g.reduce((a,d)=>a+d.activation_rate,0)/g.length).toFixed(2)}});
  const wM=wK.map(k=>Math.max(...wG[k].map(d=>d[ak])));
  const wN=wK.map(k=>wG[k].reduce((a,d)=>a+(d[nk]||0),0));
  Plotly.react('w-active',[{{x:wLb,y:wA,name:'평균 활성',type:'bar',marker:{{color:ac}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-rate',[{{x:wLb,y:wR,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:2}},marker:{{size:4}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}},yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('w-max',[{{x:wLb,y:wM,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-new',[{{x:wLb,y:wN,name:`신규 ${{e}}`,type:'bar',marker:{{color:'#818cf8'}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);

  // MONTHLY
  const mG=groupBy(F,d=>isoMonth(d.date)),mK=Object.keys(mG).sort();
  const mA=mK.map(k=>+(mG[k].reduce((a,d)=>a+d[ak],0)/mG[k].length).toFixed(1));
  const mR=mK.map(k=>+(mG[k].reduce((a,d)=>a+d.activation_rate,0)/mG[k].length).toFixed(2));
  const mM=mK.map(k=>Math.max(...mG[k].map(d=>d[ak])));
  const mN=mK.map(k=>mG[k].reduce((a,d)=>a+(d[nk]||0),0));
  const mT=mK.map(k=>Math.round(mG[k].reduce((a,d)=>a+d[tk],0)/mG[k].length));
  Plotly.react('m-active',[{{x:mK,y:mA,name:'평균 활성',type:'bar',marker:{{color:ac}},text:mA.map(v=>v.toFixed(1)),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);
  Plotly.react('m-rate',[{{x:mK,y:mR,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:3}},marker:{{size:7}}}}],{{...L,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('m-max',[{{x:mK,y:mM,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}},text:mM,textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);
  Plotly.react('m-new',[{{x:mK,y:mN,name:`신규 ${{e}}`,type:'bar',marker:{{color:'#818cf8'}},text:mN,textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);
  Plotly.react('m-total',[{{x:mK,y:mT,name:`평균 총 ${{e}}`,type:'bar',marker:{{color:ac}},text:mT.map(v=>v.toLocaleString()),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);

  // FEATURES
  const fc=featCols(),fn=featNames(),fcl=fColors();
  const fT=fc.map((k,i)=>({{x:dates,y:F.map(d=>d[k]||0),name:fn[k]||k,type:'scatter',mode:'lines',line:{{color:fcl[i%fcl.length],width:2}}}}));
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

// INIT
buildTabs();
renderAll();
</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Combined dashboard saved: {OUTPUT}")
