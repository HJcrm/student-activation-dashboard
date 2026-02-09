import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "dashboard_data.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "학생활성화_대시보드.html")

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filter out anomalous data (total_students < 100)
daily = [d for d in data['daily'] if d['total_students'] >= 100]
weekly = [w for w in data['weekly'] if w['avg_total_students'] >= 100]
monthly = [m for m in data['monthly'] if m['avg_total_students'] >= 100]
summary = data['summary']

# Recalculate summary from clean data
if daily:
    summary['total_days'] = len(daily)
    summary['date_start'] = daily[0]['date']

# Extract chart data
dates = [d['date'] for d in daily]
total_students = [d['total_students'] for d in daily]
active_students = [d['active_students'] for d in daily]
activation_rate = [d['activation_rate'] for d in daily]
new_students = [d.get('new_students', 0) for d in daily]
n_academies = [d['n_academies'] for d in daily]

# Grade data
grade_0 = [d.get('grade_0', 0) for d in daily]
grade_1 = [d.get('grade_1', 0) for d in daily]
grade_2 = [d.get('grade_2', 0) for d in daily]
grade_3 = [d.get('grade_3', 0) for d in daily]

# Feature columns
feature_cols = data['feature_cols']
feature_data = {}
for fc in feature_cols:
    feature_data[fc] = [d.get(fc, 0) for d in daily]

# Category columns
cat_cols = data['cat_cols']
cat_data = {}
for cc in cat_cols:
    cat_data[cc] = [d.get(cc, 0) for d in daily]

# Weekly data
w_labels = [f"{w['date_start']}~{w['date_end'][-5:]}" for w in weekly]
w_avg_total = [round(w['avg_total_students']) for w in weekly]
w_avg_active = [round(w['avg_active_students']) for w in weekly]
w_avg_rate = [round(w['avg_activation_rate'], 1) for w in weekly]
w_new = [w['total_new_students'] for w in weekly]

# Monthly data
m_labels = [m['year_month'] for m in monthly]
m_avg_total = [round(m['avg_total_students']) for m in monthly]
m_avg_active = [round(m['avg_active_students']) for m in monthly]
m_avg_rate = [round(m['avg_activation_rate'], 1) for m in monthly]
m_new = [m['total_new_students'] for m in monthly]
m_max_total = [m['max_total_students'] for m in monthly]
m_max_active = [m['max_active_students'] for m in monthly]

# Feature names mapping (Korean)
feature_names = {
    '열람권사용량': '열람권 사용',
    '발급권사용량': '발급권 사용',
    '주제발급횟수': '주제 발급',
    '샘플주제과제발급여부': '샘플주제 과제발급',
    'AILite진단여부': 'AI Lite 진단',
    'AiPro진단여부': 'AI Pro 진단',
    '수시배치표여부': '수시 배치표',
    '계열선택검사여부': '계열선택 검사',
    '학쫑GPT사용량': '학쫑GPT 사용',
}

cat_names = {
    'cat_기본 이용권': '기본 이용권',
    'cat_전 학교 이용권': '전 학교 이용권(전)',
    'cat_무료 모니터링': '무료 모니터링',
    'cat_全 학교 이용권': '전 학교 이용권(全)',
    'cat_1년 이용권': '1년 이용권',
}

# Compute latest vs previous month comparison
latest_month = monthly[-1] if monthly else {}
prev_month = monthly[-2] if len(monthly) >= 2 else {}

def pct_change(new, old):
    if old and old != 0:
        return round((new - old) / old * 100, 1)
    return 0

active_change = pct_change(
    latest_month.get('avg_active_students', 0),
    prev_month.get('avg_active_students', 0)
)
total_change = pct_change(
    latest_month.get('avg_total_students', 0),
    prev_month.get('avg_total_students', 0)
)

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>학쫑 학생 활성화 대시보드</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI','Malgun Gothic',sans-serif; background:#0f172a; color:#e2e8f0; }}
  .header {{ background:linear-gradient(135deg,#1e293b,#334155); padding:24px 32px; border-bottom:1px solid #475569; }}
  .header h1 {{ font-size:24px; font-weight:700; color:#f8fafc; }}
  .header p {{ font-size:13px; color:#94a3b8; margin-top:4px; }}
  .container {{ max-width:1400px; margin:0 auto; padding:20px; }}

  /* KPI Cards */
  .kpi-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:24px; }}
  .kpi-card {{ background:#1e293b; border-radius:12px; padding:20px; border:1px solid #334155; }}
  .kpi-card .label {{ font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; }}
  .kpi-card .value {{ font-size:28px; font-weight:700; color:#f8fafc; margin:8px 0 4px; }}
  .kpi-card .change {{ font-size:12px; }}
  .kpi-card .change.up {{ color:#4ade80; }}
  .kpi-card .change.down {{ color:#f87171; }}

  /* Tabs */
  .tab-bar {{ display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }}
  .tab-btn {{ padding:8px 20px; border:1px solid #475569; border-radius:8px; background:#1e293b; color:#94a3b8;
              cursor:pointer; font-size:13px; transition:all 0.2s; }}
  .tab-btn:hover {{ background:#334155; color:#e2e8f0; }}
  .tab-btn.active {{ background:#3b82f6; color:#fff; border-color:#3b82f6; }}

  /* Chart container */
  .chart-section {{ margin-bottom:24px; }}
  .chart-card {{ background:#1e293b; border-radius:12px; padding:20px; border:1px solid #334155; margin-bottom:16px; }}
  .chart-card h3 {{ font-size:16px; color:#f8fafc; margin-bottom:12px; }}
  .chart-row {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media(max-width:900px) {{ .chart-row {{ grid-template-columns:1fr; }} }}
  .plot {{ width:100%; height:380px; }}
  .plot-tall {{ width:100%; height:450px; }}

  /* Section headers */
  .section-title {{ font-size:18px; font-weight:600; color:#f8fafc; margin:24px 0 12px; padding-left:12px; border-left:3px solid #3b82f6; }}

  .hidden {{ display:none; }}
</style>
</head>
<body>
<div class="header">
  <h1>학쫑 학생 활성화 대시보드</h1>
  <p>데이터 기간: {summary['date_start']} ~ {summary['date_end']} | 총 {summary['total_days']}일 | 최종 업데이트: {summary['date_end']}</p>
</div>
<div class="container">

  <!-- KPI Cards -->
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="label">총 등록 학생</div>
      <div class="value">{summary['latest_total']:,}</div>
      <div class="change {'up' if total_change>=0 else 'down'}">{'▲' if total_change>=0 else '▼'} 전월 대비 {abs(total_change)}%</div>
    </div>
    <div class="kpi-card">
      <div class="label">활성 학생</div>
      <div class="value">{summary['latest_active']:,}</div>
      <div class="change {'up' if active_change>=0 else 'down'}">{'▲' if active_change>=0 else '▼'} 전월 대비 {abs(active_change)}%</div>
    </div>
    <div class="kpi-card">
      <div class="label">활성화율</div>
      <div class="value">{summary['latest_rate']}%</div>
      <div class="change up">평균 {summary['avg_activation_rate']}%</div>
    </div>
    <div class="kpi-card">
      <div class="label">등록 학원 수</div>
      <div class="value">{summary['latest_academies']:,}</div>
    </div>
    <div class="kpi-card">
      <div class="label">누적 신규 학생</div>
      <div class="value">{summary['total_new_students_all']:,}</div>
    </div>
  </div>

  <!-- Tab Navigation -->
  <div class="tab-bar">
    <button class="tab-btn active" onclick="showTab('daily')">일별</button>
    <button class="tab-btn" onclick="showTab('weekly')">주별</button>
    <button class="tab-btn" onclick="showTab('monthly')">월별</button>
    <button class="tab-btn" onclick="showTab('features')">기능별 사용현황</button>
    <button class="tab-btn" onclick="showTab('grades')">학년별 분포</button>
    <button class="tab-btn" onclick="showTab('categories')">이용권별 분포</button>
  </div>

  <!-- DAILY TAB -->
  <div id="tab-daily" class="chart-section">
    <div class="chart-row">
      <div class="chart-card">
        <h3>일별 총 학생 / 활성 학생</h3>
        <div id="daily-students" class="plot"></div>
      </div>
      <div class="chart-card">
        <h3>일별 활성화율 (%)</h3>
        <div id="daily-rate" class="plot"></div>
      </div>
    </div>
    <div class="chart-row">
      <div class="chart-card">
        <h3>일별 신규 학생 수</h3>
        <div id="daily-new" class="plot"></div>
      </div>
      <div class="chart-card">
        <h3>일별 학원 수</h3>
        <div id="daily-academies" class="plot"></div>
      </div>
    </div>
  </div>

  <!-- WEEKLY TAB -->
  <div id="tab-weekly" class="chart-section hidden">
    <div class="chart-row">
      <div class="chart-card">
        <h3>주별 평균 학생 수</h3>
        <div id="weekly-students" class="plot"></div>
      </div>
      <div class="chart-card">
        <h3>주별 평균 활성화율 (%)</h3>
        <div id="weekly-rate" class="plot"></div>
      </div>
    </div>
    <div class="chart-card">
      <h3>주별 신규 학생 수</h3>
      <div id="weekly-new" class="plot"></div>
    </div>
  </div>

  <!-- MONTHLY TAB -->
  <div id="tab-monthly" class="chart-section hidden">
    <div class="chart-row">
      <div class="chart-card">
        <h3>월별 평균 학생 수</h3>
        <div id="monthly-students" class="plot"></div>
      </div>
      <div class="chart-card">
        <h3>월별 활성화율 추이</h3>
        <div id="monthly-rate" class="plot"></div>
      </div>
    </div>
    <div class="chart-row">
      <div class="chart-card">
        <h3>월별 신규 학생 수</h3>
        <div id="monthly-new" class="plot"></div>
      </div>
      <div class="chart-card">
        <h3>월별 최대 학생 수</h3>
        <div id="monthly-max" class="plot"></div>
      </div>
    </div>
  </div>

  <!-- FEATURES TAB -->
  <div id="tab-features" class="chart-section hidden">
    <div class="chart-card">
      <h3>기능별 일별 사용 학생 수</h3>
      <div id="features-trend" class="plot-tall"></div>
    </div>
    <div class="chart-card">
      <h3>최근 기능별 사용 학생 비율</h3>
      <div id="features-pie" class="plot"></div>
    </div>
  </div>

  <!-- GRADES TAB -->
  <div id="tab-grades" class="chart-section hidden">
    <div class="chart-card">
      <h3>학년별 학생 수 추이</h3>
      <div id="grades-trend" class="plot-tall"></div>
    </div>
    <div class="chart-card">
      <h3>최근 학년별 분포</h3>
      <div id="grades-pie" class="plot"></div>
    </div>
  </div>

  <!-- CATEGORIES TAB -->
  <div id="tab-categories" class="chart-section hidden">
    <div class="chart-card">
      <h3>이용권 유형별 학생 수 추이</h3>
      <div id="cats-trend" class="plot-tall"></div>
    </div>
    <div class="chart-card">
      <h3>최근 이용권별 분포</h3>
      <div id="cats-pie" class="plot"></div>
    </div>
  </div>

</div>

<script>
const darkLayout = {{
  paper_bgcolor:'#1e293b', plot_bgcolor:'#1e293b',
  font:{{ color:'#e2e8f0', family:'Segoe UI, Malgun Gothic, sans-serif' }},
  xaxis:{{ gridcolor:'#334155', linecolor:'#475569' }},
  yaxis:{{ gridcolor:'#334155', linecolor:'#475569' }},
  margin:{{ l:50, r:20, t:10, b:50 }},
  legend:{{ bgcolor:'rgba(0,0,0,0)', font:{{ size:11 }} }},
  hovermode:'x unified',
}};
const config = {{ responsive:true, displayModeBar:false }};

// ========== DAILY ==========
const dates = {json.dumps(dates)};
const totalStudents = {json.dumps(total_students)};
const activeStudents = {json.dumps(active_students)};
const activationRate = {json.dumps(activation_rate)};
const newStudents = {json.dumps(new_students)};
const nAcademies = {json.dumps(n_academies)};

Plotly.newPlot('daily-students', [
  {{ x:dates, y:totalStudents, name:'총 학생', type:'scatter', mode:'lines', line:{{color:'#60a5fa',width:2}}, fill:'tozeroy', fillcolor:'rgba(96,165,250,0.1)' }},
  {{ x:dates, y:activeStudents, name:'활성 학생', type:'scatter', mode:'lines', line:{{color:'#4ade80',width:2}}, fill:'tozeroy', fillcolor:'rgba(74,222,128,0.1)' }},
], {{...darkLayout}}, config);

Plotly.newPlot('daily-rate', [
  {{ x:dates, y:activationRate, name:'활성화율', type:'scatter', mode:'lines', line:{{color:'#f59e0b',width:2}}, fill:'tozeroy', fillcolor:'rgba(245,158,11,0.1)' }},
], {{...darkLayout, yaxis:{{...darkLayout.yaxis, ticksuffix:'%'}}}}, config);

Plotly.newPlot('daily-new', [
  {{ x:dates, y:newStudents, name:'신규 학생', type:'bar', marker:{{color:'#818cf8'}} }},
], {{...darkLayout}}, config);

Plotly.newPlot('daily-academies', [
  {{ x:dates, y:nAcademies, name:'학원 수', type:'scatter', mode:'lines', line:{{color:'#f472b6',width:2}}, fill:'tozeroy', fillcolor:'rgba(244,114,182,0.1)' }},
], {{...darkLayout}}, config);

// ========== WEEKLY ==========
const wLabels = {json.dumps(w_labels)};
const wTotal = {json.dumps(w_avg_total)};
const wActive = {json.dumps(w_avg_active)};
const wRate = {json.dumps(w_avg_rate)};
const wNew = {json.dumps(w_new)};

Plotly.newPlot('weekly-students', [
  {{ x:wLabels, y:wTotal, name:'평균 총 학생', type:'bar', marker:{{color:'#60a5fa'}} }},
  {{ x:wLabels, y:wActive, name:'평균 활성 학생', type:'bar', marker:{{color:'#4ade80'}} }},
], {{...darkLayout, barmode:'group', xaxis:{{...darkLayout.xaxis, tickangle:-45}}}}, config);

Plotly.newPlot('weekly-rate', [
  {{ x:wLabels, y:wRate, name:'활성화율', type:'scatter', mode:'lines+markers', line:{{color:'#f59e0b',width:2}}, marker:{{size:5}} }},
], {{...darkLayout, xaxis:{{...darkLayout.xaxis, tickangle:-45}}, yaxis:{{...darkLayout.yaxis, ticksuffix:'%'}}}}, config);

Plotly.newPlot('weekly-new', [
  {{ x:wLabels, y:wNew, name:'신규 학생', type:'bar', marker:{{color:'#818cf8'}} }},
], {{...darkLayout, xaxis:{{...darkLayout.xaxis, tickangle:-45}}}}, config);

// ========== MONTHLY ==========
const mLabels = {json.dumps(m_labels)};
const mTotal = {json.dumps(m_avg_total)};
const mActive = {json.dumps(m_avg_active)};
const mRate = {json.dumps(m_avg_rate)};
const mNew = {json.dumps(m_new)};
const mMaxTotal = {json.dumps(m_max_total)};
const mMaxActive = {json.dumps(m_max_active)};

Plotly.newPlot('monthly-students', [
  {{ x:mLabels, y:mTotal, name:'평균 총 학생', type:'bar', marker:{{color:'#60a5fa'}} }},
  {{ x:mLabels, y:mActive, name:'평균 활성 학생', type:'bar', marker:{{color:'#4ade80'}} }},
], {{...darkLayout, barmode:'group'}}, config);

Plotly.newPlot('monthly-rate', [
  {{ x:mLabels, y:mRate, name:'활성화율', type:'scatter', mode:'lines+markers', line:{{color:'#f59e0b',width:3}}, marker:{{size:8}} }},
], {{...darkLayout, yaxis:{{...darkLayout.yaxis, ticksuffix:'%'}}}}, config);

Plotly.newPlot('monthly-new', [
  {{ x:mLabels, y:mNew, name:'신규 학생', type:'bar', marker:{{color:'#818cf8'}} }},
], {{...darkLayout}}, config);

Plotly.newPlot('monthly-max', [
  {{ x:mLabels, y:mMaxTotal, name:'최대 총 학생', type:'bar', marker:{{color:'#38bdf8'}} }},
  {{ x:mLabels, y:mMaxActive, name:'최대 활성 학생', type:'bar', marker:{{color:'#34d399'}} }},
], {{...darkLayout, barmode:'group'}}, config);

// ========== FEATURES ==========
const featureData = {json.dumps(feature_data, ensure_ascii=False)};
const featureNames = {json.dumps(feature_names, ensure_ascii=False)};
const featureColors = ['#60a5fa','#4ade80','#f59e0b','#f472b6','#818cf8','#fb923c','#a78bfa','#22d3ee','#e879f9'];

const featureTraces = Object.keys(featureData).map((key, i) => ({{
  x: dates,
  y: featureData[key],
  name: featureNames[key] || key,
  type: 'scatter',
  mode: 'lines',
  line: {{ color: featureColors[i % featureColors.length], width: 2 }},
}}));
Plotly.newPlot('features-trend', featureTraces, {{...darkLayout, margin:{{...darkLayout.margin, b:60}}}}, config);

// Feature pie (latest day)
const latestFeatureVals = Object.keys(featureData).map(k => {{
  const vals = featureData[k];
  return vals[vals.length-1] || 0;
}});
const latestFeatureLabels = Object.keys(featureData).map(k => featureNames[k] || k);
Plotly.newPlot('features-pie', [{{
  values: latestFeatureVals,
  labels: latestFeatureLabels,
  type: 'pie',
  hole: 0.4,
  marker: {{ colors: featureColors }},
  textinfo: 'label+value',
  textfont: {{ size: 11 }},
}}], {{...darkLayout, margin:{{l:20,r:20,t:10,b:10}}, showlegend:true, legend:{{font:{{size:10}}}}}}, config);

// ========== GRADES ==========
const grade0 = {json.dumps(grade_0)};
const grade1 = {json.dumps(grade_1)};
const grade2 = {json.dumps(grade_2)};
const grade3 = {json.dumps(grade_3)};

Plotly.newPlot('grades-trend', [
  {{ x:dates, y:grade0, name:'예비(0학년)', type:'scatter', mode:'lines', stackgroup:'one', line:{{color:'#f472b6'}} }},
  {{ x:dates, y:grade1, name:'고1', type:'scatter', mode:'lines', stackgroup:'one', line:{{color:'#60a5fa'}} }},
  {{ x:dates, y:grade2, name:'고2', type:'scatter', mode:'lines', stackgroup:'one', line:{{color:'#4ade80'}} }},
  {{ x:dates, y:grade3, name:'고3', type:'scatter', mode:'lines', stackgroup:'one', line:{{color:'#f59e0b'}} }},
], {{...darkLayout}}, config);

const latestGrades = [grade0[grade0.length-1],grade1[grade1.length-1],grade2[grade2.length-1],grade3[grade3.length-1]];
Plotly.newPlot('grades-pie', [{{
  values: latestGrades,
  labels: ['예비(0학년)','고1','고2','고3'],
  type: 'pie',
  hole: 0.4,
  marker: {{ colors: ['#f472b6','#60a5fa','#4ade80','#f59e0b'] }},
  textinfo: 'label+value+percent',
  textfont: {{ size: 12 }},
}}], {{...darkLayout, margin:{{l:20,r:20,t:10,b:10}}}}, config);

// ========== CATEGORIES ==========
const catData = {json.dumps(cat_data, ensure_ascii=False)};
const catNames = {json.dumps(cat_names, ensure_ascii=False)};
const catColors = ['#60a5fa','#4ade80','#f59e0b','#f472b6','#818cf8'];

const catTraces = Object.keys(catData).map((key, i) => ({{
  x: dates,
  y: catData[key],
  name: catNames[key] || key,
  type: 'scatter',
  mode: 'lines',
  stackgroup: 'one',
  line: {{ color: catColors[i % catColors.length] }},
}}));
Plotly.newPlot('cats-trend', catTraces, {{...darkLayout}}, config);

const latestCatVals = Object.keys(catData).map(k => {{
  const vals = catData[k];
  return vals[vals.length-1] || 0;
}});
const latestCatLabels = Object.keys(catData).map(k => catNames[k] || k);
Plotly.newPlot('cats-pie', [{{
  values: latestCatVals,
  labels: latestCatLabels,
  type: 'pie',
  hole: 0.4,
  marker: {{ colors: catColors }},
  textinfo: 'label+value+percent',
  textfont: {{ size: 11 }},
}}], {{...darkLayout, margin:{{l:20,r:20,t:10,b:10}}}}, config);

// ========== TAB SWITCHING ==========
function showTab(tab) {{
  document.querySelectorAll('.chart-section').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.remove('hidden');
  event.target.classList.add('active');

  // Resize plots after showing
  setTimeout(() => {{
    document.querySelectorAll('#tab-' + tab + ' .plot, #tab-' + tab + ' .plot-tall').forEach(el => {{
      Plotly.Plots.resize(el);
    }});
  }}, 100);
}}
</script>
</body>
</html>"""

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Dashboard saved to: {OUTPUT_PATH}")
print(f"Data points: {len(daily)} daily, {len(weekly)} weekly, {len(monthly)} monthly")
