import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "dashboard_data.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "학원활성화_대시보드.html")

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

daily_json = json.dumps(data['daily'], ensure_ascii=False)
feature_cols_json = json.dumps(data['feature_cols'], ensure_ascii=False)
summary = data['summary']

feature_names_json = json.dumps({
    '발급권사용량(학생)': '발급권(학생)',
    '열람권사용량(학생)': '열람권(학생)',
    '발급권사용량(스토리지)': '발급권(스토리지)',
    '열람권사용량(스토리지)': '열람권(스토리지)',
    '초안작성과제생성량': '초안 생성',
    '초안작성과제승인량': '초안 승인',
    '초안작성과제거절량': '초안 거절',
    '생기부업로드량': '생기부 업로드',
    '생기부분석량(pro)': '생기부 Pro분석',
    '생기부분석량(lite)': '생기부 Lite분석',
    '수시배치표진행량': '수시 배치표',
    '계열선택검사량': '계열선택 검사',
    '수행평가GPT사용량': '수행평가 GPT',
}, ensure_ascii=False)

ds = summary['date_start']
de = summary['date_end']

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>학쫑 학원 활성화 대시보드</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI','Malgun Gothic',sans-serif;background:#0f172a;color:#e2e8f0}}
  .header{{background:linear-gradient(135deg,#1e293b,#334155);padding:24px 32px;border-bottom:1px solid #475569}}
  .header h1{{font-size:24px;font-weight:700;color:#f8fafc}}
  .header .sub{{font-size:13px;color:#94a3b8;margin-top:4px}}
  .header .badge{{display:inline-block;background:#8b5cf6;color:#fff;font-size:11px;padding:2px 8px;border-radius:4px;margin-left:8px}}
  .container{{max-width:1400px;margin:0 auto;padding:20px}}
  .note-box{{background:#1e293b;border:1px solid #8b5cf6;border-radius:8px;padding:14px 18px;margin-bottom:20px;font-size:13px;color:#c4b5fd}}
  .note-box strong{{color:#a78bfa}}

  .date-bar{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 18px;margin-bottom:18px}}
  .date-bar label{{font-size:12px;color:#94a3b8}}
  .date-bar input[type=date]{{background:#0f172a;border:1px solid #475569;border-radius:6px;color:#e2e8f0;padding:6px 10px;font-size:13px;font-family:inherit}}
  .date-bar input[type=date]::-webkit-calendar-picker-indicator{{filter:invert(0.7)}}
  .preset-btn{{padding:6px 14px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px;transition:all .15s}}
  .preset-btn:hover{{background:#334155;color:#e2e8f0}}
  .preset-btn.active{{background:#8b5cf6;color:#fff;border-color:#8b5cf6}}
  .date-bar .sep{{color:#475569;font-size:16px}}
  .date-bar .range-info{{font-size:12px;color:#64748b;margin-left:auto}}

  .outlier-toggle{{display:flex;align-items:center;gap:8px;margin-left:8px;padding-left:12px;border-left:1px solid #334155}}
  .outlier-toggle label{{font-size:12px;color:#94a3b8;cursor:pointer;user-select:none}}
  .switch{{position:relative;width:36px;height:20px;flex-shrink:0}}
  .switch input{{opacity:0;width:0;height:0}}
  .slider{{position:absolute;cursor:pointer;inset:0;background:#475569;border-radius:20px;transition:.2s}}
  .slider::before{{content:'';position:absolute;width:16px;height:16px;left:2px;bottom:2px;background:#e2e8f0;border-radius:50%;transition:.2s}}
  .switch input:checked+.slider{{background:#8b5cf6}}
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
  .tab-btn.active{{background:#8b5cf6;color:#fff;border-color:#8b5cf6}}

  .chart-section{{margin-bottom:20px}}
  .card{{background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155;margin-bottom:14px}}
  .card h3{{font-size:15px;color:#f8fafc;margin-bottom:10px}}
  .row2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
  @media(max-width:900px){{.row2{{grid-template-columns:1fr}}}}
  .plot{{width:100%;height:370px}}
  .plot-tall{{width:100%;height:430px}}
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
  .tbl-toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap}}
  .tbl-toolbar .cnt{{font-size:12px;color:#64748b}}
  .csv-btn{{padding:6px 14px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#94a3b8;cursor:pointer;font-size:12px;transition:all .15s}}
  .csv-btn:hover{{background:#334155;color:#e2e8f0}}
</style>
</head>
<body>
<div class="header">
  <h1>학쫑 학원 활성화 대시보드 <span class="badge">일별 증분 기준</span></h1>
  <p class="sub">활성 기준: 전일 대비 수치형 사용량 증가 학원</p>
</div>
<div class="container">

  <div class="note-box">
    <strong>활성 학원 기준:</strong> 전일 대비 수치형 사용량(발급권·열람권·초안작성·생기부·배치표·계열검사·GPT 등) 중 하나라도 증가한 학원 + 신규 학원 중 사용 이력이 있는 학원.
  </div>

  <div class="date-bar">
    <label>시작</label>
    <input type="date" id="startDate" value="{ds}" min="{ds}" max="{de}">
    <span class="sep">~</span>
    <label>종료</label>
    <input type="date" id="endDate" value="{de}" min="{ds}" max="{de}">
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

  <div class="kpi-row">
    <div class="kpi"><div class="label">총 학원 수 (최종일)</div><div class="value" id="kTotal">-</div><div class="sub neutral" id="kTotalSub"></div></div>
    <div class="kpi"><div class="label">일평균 활성 학원</div><div class="value" id="kActive">-</div><div class="sub neutral" id="kActiveSub"></div></div>
    <div class="kpi"><div class="label">평균 활성화율</div><div class="value" id="kRate">-</div></div>
    <div class="kpi"><div class="label">등록 학생 수 (최종일)</div><div class="value" id="kStudents">-</div></div>
    <div class="kpi"><div class="label">기간 내 신규 학원</div><div class="value" id="kNew">-</div></div>
  </div>

  <div class="tab-bar">
    <button class="tab-btn active" onclick="showTab('daily',this)">일별</button>
    <button class="tab-btn" onclick="showTab('weekly',this)">주별</button>
    <button class="tab-btn" onclick="showTab('monthly',this)">월별</button>
    <button class="tab-btn" onclick="showTab('features',this)">기능별 사용현황</button>
    <button class="tab-btn" onclick="showTab('extra',this)">학원 부가지표</button>
    <button class="tab-btn" onclick="showTab('table',this)">데이터 테이블</button>
  </div>

  <div id="tab-daily" class="chart-section">
    <div class="row2">
      <div class="card"><h3>일별 활성 학원 수</h3><div id="d-active" class="plot"></div></div>
      <div class="card"><h3>일별 활성화율 (%)</h3><div id="d-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>일별 총 학원 수</h3><div id="d-total" class="plot"></div></div>
      <div class="card"><h3>일별 신규 학원</h3><div id="d-new" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-weekly" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3>주별 평균 활성 학원 수</h3><div id="w-active" class="plot"></div></div>
      <div class="card"><h3>주별 평균 활성화율 (%)</h3><div id="w-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>주별 최대 활성 학원 수</h3><div id="w-max" class="plot"></div></div>
      <div class="card"><h3>주별 신규 학원</h3><div id="w-new" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-monthly" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3>월별 평균 활성 학원 수</h3><div id="m-active" class="plot"></div></div>
      <div class="card"><h3>월별 평균 활성화율 (%)</h3><div id="m-rate" class="plot"></div></div>
    </div>
    <div class="row2">
      <div class="card"><h3>월별 최대 활성 학원 수</h3><div id="m-max" class="plot"></div></div>
      <div class="card"><h3>월별 신규 학원</h3><div id="m-new" class="plot"></div></div>
    </div>
    <div class="card"><h3>월별 총 학원 수 추이</h3><div id="m-total" class="plot"></div></div>
  </div>

  <div id="tab-features" class="chart-section hidden">
    <div class="card"><h3>기능별 일별 활성 학원 수</h3><div id="f-trend" class="plot-tall"></div></div>
    <div class="card"><h3>기간 내 기능별 평균 활성 학원</h3><div id="f-bar" class="plot"></div></div>
  </div>

  <div id="tab-extra" class="chart-section hidden">
    <div class="row2">
      <div class="card"><h3>등록 학생 수 추이</h3><div id="e-students" class="plot"></div></div>
      <div class="card"><h3>스토리지 사용 / 등록권 구매 학원 수</h3><div id="e-flags" class="plot"></div></div>
    </div>
  </div>

  <div id="tab-table" class="chart-section hidden">
    <div class="card">
      <h3>일별 데이터 테이블</h3>
      <div class="tbl-toolbar">
        <span class="cnt" id="tblCount"></span>
        <button class="csv-btn" onclick="downloadCSV()">CSV 다운로드</button>
      </div>
      <div class="tbl-wrap"><table class="data-tbl" id="dataTable"><thead id="tblHead"></thead><tbody id="tblBody"></tbody></table></div>
    </div>
  </div>

</div>

<script>
const RAW={daily_json};
const FEAT_COLS={feature_cols_json};
const FEAT_NAMES={feature_names_json};
const FCOL=['#a78bfa','#60a5fa','#4ade80','#f59e0b','#f472b6','#818cf8','#fb923c','#22d3ee','#e879f9','#facc15','#34d399','#f87171','#38bdf8'];

const L={{
  paper_bgcolor:'#1e293b',plot_bgcolor:'#1e293b',
  font:{{color:'#e2e8f0',family:'Segoe UI,Malgun Gothic,sans-serif',size:12}},
  xaxis:{{gridcolor:'#334155',linecolor:'#475569'}},
  yaxis:{{gridcolor:'#334155',linecolor:'#475569'}},
  margin:{{l:55,r:20,t:10,b:50}},
  legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:11}}}},
  hovermode:'x unified',
}};
const CFG={{responsive:true,displayModeBar:false}};

function ma(a,w=7){{return a.map((_,i)=>{{const s=Math.max(0,i-w+1);const sl=a.slice(s,i+1);return Math.round(sl.reduce((x,y)=>x+y,0)/sl.length*10)/10}})}}
function groupBy(a,fn){{const m={{}};a.forEach(d=>{{const k=fn(d);if(!m[k])m[k]=[];m[k].push(d)}});return m}}
function isoWeek(ds){{const d=new Date(ds);const j=new Date(d.getFullYear(),0,1);return d.getFullYear()+'-W'+String(Math.ceil(((d-j)/864e5+j.getDay()+1)/7)).padStart(2,'0')}}
function isoMonth(ds){{return ds.substring(0,7)}}

function iqrBounds(arr){{const s=[...arr].sort((a,b)=>a-b);const q1=s[Math.floor(s.length*.25)];const q3=s[Math.floor(s.length*.75)];const iqr=q3-q1;return{{hi:q3+1.5*iqr}}}}

function getFiltered(){{
  const s=document.getElementById('startDate').value,e=document.getElementById('endDate').value;
  let F=RAW.filter(d=>d.date>=s&&d.date<=e);
  const ex=document.getElementById('outlierToggle').checked,info=document.getElementById('outlierInfo');
  if(ex&&F.length>7){{
    const aB=iqrBounds(F.map(d=>d.active_institutions));
    const nB=iqrBounds(F.map(d=>d.new_institutions||0));
    const b=F.length;F=F.filter(d=>d.active_institutions<=aB.hi&&(d.new_institutions||0)<=nB.hi);
    info.textContent=(b-F.length)>0?`(${{b-F.length}}일 제외됨)`:'(이상치 없음)';
  }}else{{info.textContent=''}}
  return F;
}}

function renderAll(){{
  const F=getFiltered();if(!F.length)return;
  const dates=F.map(d=>d.date),last=F[F.length-1];
  const actI=F.map(d=>d.active_institutions),actR=F.map(d=>d.activation_rate);
  const totI=F.map(d=>d.total_institutions),newI=F.map(d=>d.new_institutions||0);
  const regS=F.map(d=>d.total_registered_students||0);
  const stoU=F.map(d=>d.storage_users||0),purU=F.map(d=>d.purchase_users||0);

  // KPI
  const avgA=Math.round(actI.reduce((a,b)=>a+b,0)/F.length*10)/10;
  const avgR=Math.round(actR.reduce((a,b)=>a+b,0)/F.length*100)/100;
  document.getElementById('kTotal').textContent=last.total_institutions.toLocaleString();
  document.getElementById('kTotalSub').textContent=dates[0]+' ~ '+dates[dates.length-1]+' ('+F.length+'일)';
  document.getElementById('kActive').textContent=avgA;
  document.getElementById('kActiveSub').textContent='최종일 '+last.active_institutions+'개';
  document.getElementById('kRate').textContent=avgR+'%';
  document.getElementById('kStudents').textContent=(last.total_registered_students||0).toLocaleString();
  document.getElementById('kNew').textContent=newI.reduce((a,b)=>a+b,0).toLocaleString();
  document.getElementById('rangeInfo').textContent=F.length+'일 선택됨';

  // DAILY
  Plotly.react('d-active',[
    {{x:dates,y:actI,name:'활성 학원',type:'bar',marker:{{color:'rgba(167,139,250,0.6)'}}}},
    {{x:dates,y:ma(actI),name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}}}},
  ],{{...L}},CFG);
  Plotly.react('d-rate',[
    {{x:dates,y:actR,name:'활성화율',type:'bar',marker:{{color:'rgba(74,222,128,0.5)'}}}},
    {{x:dates,y:ma(actR),name:'7일 이동평균',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2.5}}}},
  ],{{...L,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('d-total',[
    {{x:dates,y:totI,name:'총 학원',type:'scatter',mode:'lines',line:{{color:'#a78bfa',width:2}},fill:'tozeroy',fillcolor:'rgba(167,139,250,0.1)'}},
  ],{{...L}},CFG);
  Plotly.react('d-new',[
    {{x:dates,y:newI,name:'신규 학원',type:'bar',marker:{{color:'#818cf8'}}}},
  ],{{...L}},CFG);

  // WEEKLY
  const wG=groupBy(F,d=>isoWeek(d.date)),wK=Object.keys(wG).sort();
  const wLb=wK.map(k=>{{const g=wG[k];return g[0].date+'~'+g[g.length-1].date.substring(5)}});
  const wA=wK.map(k=>{{const g=wG[k];return Math.round(g.reduce((a,d)=>a+d.active_institutions,0)/g.length*10)/10}});
  const wR=wK.map(k=>{{const g=wG[k];return Math.round(g.reduce((a,d)=>a+d.activation_rate,0)/g.length*100)/100}});
  const wM=wK.map(k=>Math.max(...wG[k].map(d=>d.active_institutions)));
  const wN=wK.map(k=>wG[k].reduce((a,d)=>a+(d.new_institutions||0),0));

  Plotly.react('w-active',[{{x:wLb,y:wA,name:'평균 활성',type:'bar',marker:{{color:'#a78bfa'}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-rate',[{{x:wLb,y:wR,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:2}},marker:{{size:4}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}},yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('w-max',[{{x:wLb,y:wM,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);
  Plotly.react('w-new',[{{x:wLb,y:wN,name:'신규 학원',type:'bar',marker:{{color:'#818cf8'}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-45}}}},CFG);

  // MONTHLY
  const mG=groupBy(F,d=>isoMonth(d.date)),mK=Object.keys(mG).sort();
  const mA=mK.map(k=>{{const g=mG[k];return Math.round(g.reduce((a,d)=>a+d.active_institutions,0)/g.length*10)/10}});
  const mR=mK.map(k=>{{const g=mG[k];return Math.round(g.reduce((a,d)=>a+d.activation_rate,0)/g.length*100)/100}});
  const mM=mK.map(k=>Math.max(...mG[k].map(d=>d.active_institutions)));
  const mN=mK.map(k=>mG[k].reduce((a,d)=>a+(d.new_institutions||0),0));
  const mT=mK.map(k=>{{const g=mG[k];return Math.round(g.reduce((a,d)=>a+d.total_institutions,0)/g.length)}});

  Plotly.react('m-active',[{{x:mK,y:mA,name:'평균 활성',type:'bar',marker:{{color:'#a78bfa'}},text:mA.map(v=>v.toFixed(1)),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);
  Plotly.react('m-rate',[{{x:mK,y:mR,name:'평균 활성화율',type:'scatter',mode:'lines+markers',line:{{color:'#4ade80',width:3}},marker:{{size:7}}}}],{{...L,yaxis:{{...L.yaxis,ticksuffix:'%'}}}},CFG);
  Plotly.react('m-max',[{{x:mK,y:mM,name:'최대 활성',type:'bar',marker:{{color:'#f59e0b'}},text:mM,textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);
  Plotly.react('m-new',[{{x:mK,y:mN,name:'신규 학원',type:'bar',marker:{{color:'#818cf8'}},text:mN,textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);
  Plotly.react('m-total',[{{x:mK,y:mT,name:'평균 총 학원',type:'bar',marker:{{color:'#c4b5fd'}},text:mT.map(v=>v.toLocaleString()),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L}},CFG);

  // FEATURES
  const fT=FEAT_COLS.map((k,i)=>({{x:dates,y:F.map(d=>d[k]||0),name:FEAT_NAMES[k]||k,type:'scatter',mode:'lines',line:{{color:FCOL[i%FCOL.length],width:2}}}}));
  Plotly.react('f-trend',fT,{{...L,margin:{{...L.margin,b:60}}}},CFG);
  const fAvg=FEAT_COLS.map(k=>{{const v=F.map(d=>d[k]||0);return Math.round(v.reduce((a,b)=>a+b,0)/v.length*10)/10}});
  const fLb=FEAT_COLS.map(k=>FEAT_NAMES[k]||k);
  Plotly.react('f-bar',[{{x:fLb,y:fAvg,type:'bar',marker:{{color:FCOL.slice(0,FEAT_COLS.length)}},text:fAvg.map(v=>v.toString()),textposition:'outside',textfont:{{color:'#94a3b8',size:11}}}}],{{...L,xaxis:{{...L.xaxis,tickangle:-30}}}},CFG);

  // EXTRA
  Plotly.react('e-students',[
    {{x:dates,y:regS,name:'등록 학생 수',type:'scatter',mode:'lines',line:{{color:'#60a5fa',width:2}},fill:'tozeroy',fillcolor:'rgba(96,165,250,0.1)'}},
  ],{{...L}},CFG);
  Plotly.react('e-flags',[
    {{x:dates,y:stoU,name:'스토리지 사용',type:'scatter',mode:'lines',line:{{color:'#4ade80',width:2}}}},
    {{x:dates,y:purU,name:'등록권 구매',type:'scatter',mode:'lines',line:{{color:'#f59e0b',width:2}}}},
  ],{{...L}},CFG);

  renderTable(F);
}}

// TABLE
const TBL_COLS=[
  {{key:'date',label:'날짜',fmt:v=>v}},
  {{key:'day_of_week',label:'요일',fmt:v=>{{const m={{'Monday':'월','Tuesday':'화','Wednesday':'수','Thursday':'목','Friday':'금','Saturday':'토','Sunday':'일'}};return m[v]||v}}}},
  {{key:'total_institutions',label:'총 학원',fmt:v=>v.toLocaleString()}},
  {{key:'active_institutions',label:'활성 학원',fmt:v=>v.toLocaleString()}},
  {{key:'activation_rate',label:'활성화율(%)',fmt:v=>v.toFixed(2)}},
  {{key:'new_institutions',label:'신규 학원',fmt:v=>(v||0).toLocaleString()}},
  {{key:'total_registered_students',label:'등록 학생수',fmt:v=>(v||0).toLocaleString()}},
  {{key:'storage_users',label:'스토리지 사용',fmt:v=>(v||0).toLocaleString()}},
  {{key:'purchase_users',label:'등록권 구매',fmt:v=>(v||0).toLocaleString()}},
];
FEAT_COLS.forEach(k=>TBL_COLS.push({{key:k,label:FEAT_NAMES[k]||k,fmt:v=>(v||0).toLocaleString()}}));

let tblSortKey='date',tblSortAsc=false,tblData=[];
function renderTable(F){{tblData=F;document.getElementById('tblHead').innerHTML='<tr>'+TBL_COLS.map(c=>`<th onclick="sortTable('${{c.key}}')">${{c.label}}<span class="arrow">${{tblSortKey===c.key?(tblSortAsc?'▲':'▼'):''}}</span></th>`).join('')+'</tr>';fillTbl()}}
function fillTbl(){{const s=[...tblData].sort((a,b)=>{{let va=a[tblSortKey]??0,vb=b[tblSortKey]??0;if(typeof va==='string')return tblSortAsc?va.localeCompare(vb):vb.localeCompare(va);return tblSortAsc?va-vb:vb-va}});document.getElementById('tblBody').innerHTML=s.map(d=>'<tr>'+TBL_COLS.map(c=>`<td>${{c.fmt(d[c.key]??0)}}</td>`).join('')+'</tr>').join('');document.getElementById('tblCount').textContent=s.length+'일 데이터'}}
function sortTable(k){{if(tblSortKey===k)tblSortAsc=!tblSortAsc;else{{tblSortKey=k;tblSortAsc=k==='date'}};document.querySelectorAll('#tblHead th .arrow').forEach((el,i)=>el.textContent=TBL_COLS[i].key===tblSortKey?(tblSortAsc?'▲':'▼'):'');fillTbl()}}
function downloadCSV(){{const F=getFiltered();const h=TBL_COLS.map(c=>c.label).join(',');const r=F.map(d=>TBL_COLS.map(c=>{{let v=d[c.key]??0;if(c.key==='day_of_week'){{const m={{'Monday':'월','Tuesday':'화','Wednesday':'수','Thursday':'목','Friday':'금','Saturday':'토','Sunday':'일'}};v=m[v]||v}};return v}}).join(','));const csv='\\uFEFF'+h+'\\n'+r.join('\\n');const b=new Blob([csv],{{type:'text/csv;charset=utf-8'}});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='학원활성화_일별데이터.csv';a.click();URL.revokeObjectURL(u)}}

// DATE RANGE
function setRange(days){{const all=RAW.map(d=>d.date);const mn=all[0],mx=all[all.length-1];document.querySelectorAll('.preset-btn').forEach(b=>b.classList.remove('active'));event.target.classList.add('active');if(days===0){{document.getElementById('startDate').value=mn;document.getElementById('endDate').value=mx}}else{{const e=new Date(mx),s=new Date(e);s.setDate(s.getDate()-days+1);const ss=s.toISOString().substring(0,10);document.getElementById('startDate').value=ss<mn?mn:ss;document.getElementById('endDate').value=mx}};renderAll()}}
document.getElementById('startDate').addEventListener('change',()=>{{document.querySelectorAll('.preset-btn').forEach(b=>b.classList.remove('active'));renderAll()}});
document.getElementById('endDate').addEventListener('change',()=>{{document.querySelectorAll('.preset-btn').forEach(b=>b.classList.remove('active'));renderAll()}});

// TAB
function showTab(tab,btn){{document.querySelectorAll('.chart-section').forEach(el=>el.classList.add('hidden'));document.querySelectorAll('.tab-btn').forEach(el=>el.classList.remove('active'));document.getElementById('tab-'+tab).classList.remove('hidden');btn.classList.add('active');setTimeout(()=>document.querySelectorAll('#tab-'+tab+' .plot,#tab-'+tab+' .plot-tall').forEach(el=>Plotly.Plots.resize(el)),100)}}

renderAll();
</script>
</body>
</html>"""

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Dashboard saved: {OUTPUT_PATH}")
