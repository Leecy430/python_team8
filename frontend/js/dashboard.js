/* =============================================
   dashboard.js — 메인 대시보드 로직
   ============================================= */

let currentDate = today();

// ── 초기화 ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dateInput').value = currentDate;
  loadAll();
});

function loadAll() {
  loadDashboard();
  loadMeals();
  loadSchedule();
  loadOutfit();
}

// ── 날짜 이동 ───────────────────────────────────
function prevDay() {
  const d = new Date(currentDate);
  d.setDate(d.getDate() - 1);
  currentDate = d.toISOString().split('T')[0];
  document.getElementById('dateInput').value = currentDate;
  loadAll();
}

function nextDay() {
  const d = new Date(currentDate);
  d.setDate(d.getDate() + 1);
  const t = today();
  if (d.toISOString().split('T')[0] > t) return;
  currentDate = d.toISOString().split('T')[0];
  document.getElementById('dateInput').value = currentDate;
  loadAll();
}

function onDateChange(val) {
  currentDate = val;
  loadAll();
}

// ── 대시보드 메인 데이터 ─────────────────────────
async function loadDashboard() {
  setLoading('steps-card');
  setLoading('sleep-card');
  setLoading('hr-card');
  setLoading('inbody-card');
  setLoading('weather-card');
  setLoading('walk-card');

  try {
    const data = await API.getDashboard(currentDate);
    renderSteps(data.steps);
    renderSleep(data.sleep);
    renderHeartrate(data.heart_rate);
    renderInbody(data.inbody);
    renderWeather(data.weather);
    renderWalk(data.walk_ok, data.walk_msg);
  } catch(e) {
    showToast('대시보드 로딩 실패: ' + e.message);
    ['steps-card','sleep-card','hr-card','inbody-card','weather-card','walk-card']
      .forEach(id => setError(id, '데이터 없음'));
  }
}

// ── 걸음수 ─────────────────────────────────────
function renderSteps(s) {
  const el = document.getElementById('steps-card');
  if (!s || !s.count) {
    el.innerHTML = emptyCard('👟', '걸음수', '데이터 없음');
    return;
  }
  const pct = clamp(Math.round((s.count / 8000) * 100), 0, 100);
  const ringDash = Math.round(pct * 2.51); // circumference ≈ 251

  el.innerHTML = `
    <div class="stat-label">👟 걸음수</div>
    <div class="step-ring-wrap">
      <div class="step-ring">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="32" fill="none" stroke="var(--border)" stroke-width="7"/>
          <circle cx="40" cy="40" r="32" fill="none" stroke="var(--primary)" stroke-width="7"
            stroke-dasharray="${ringDash} 251" stroke-linecap="round"/>
        </svg>
        <div class="step-ring-pct">${pct}%</div>
      </div>
      <div>
        <div class="stat-value" style="color:var(--primary);font-size:26px">${s.count.toLocaleString()}<span style="font-size:14px;font-weight:600;color:var(--text-muted)">보</span></div>
        <div class="stat-sub">목표 8,000보</div>
        <div class="stat-sub" style="margin-top:4px">${s.distance_m ? (s.distance_m/1000).toFixed(1)+'km' : ''} ${s.calorie ? '· '+Math.round(s.calorie)+'kcal' : ''}</div>
      </div>
    </div>`;
}

// ── 수면 ───────────────────────────────────────
function renderSleep(s) {
  const el = document.getElementById('sleep-card');
  if (!s || !s.duration_min) {
    el.innerHTML = emptyCard('💤', '수면', '데이터 없음');
    return;
  }
  const score = s.sleep_score ? Math.round(s.sleep_score) : null;
  const scoreColor = score >= 80 ? 'var(--green)' : score >= 60 ? 'var(--yellow)' : 'var(--red)';

  el.innerHTML = `
    <div class="stat-label">💤 수면</div>
    <div class="stat-value" style="color:var(--purple)">${fmtMin(s.duration_min)}</div>
    ${score != null ? `<div><span class="badge badge-purple">수면점수 ${score}</span></div>` : ''}
    <div class="stat-sub">효율 ${s.efficiency ? Math.round(s.efficiency)+'%' : '-'} &nbsp;·&nbsp; REM ${s.total_rem_min ? fmtMin(s.total_rem_min) : '-'}</div>
    <div class="stat-sub">신체회복 ${s.physical_recovery ? Math.round(s.physical_recovery) : '-'} &nbsp;·&nbsp; 정신회복 ${s.mental_recovery ? Math.round(s.mental_recovery) : '-'}</div>`;
}

// ── 심박수 ─────────────────────────────────────
function renderHeartrate(hr) {
  const el = document.getElementById('hr-card');
  if (!hr || !hr.bpm) {
    el.innerHTML = emptyCard('❤️', '심박수', '데이터 없음');
    return;
  }
  const bpmColor = hr.bpm < 60 ? 'var(--primary)' : hr.bpm < 100 ? 'var(--green)' : 'var(--red)';

  el.innerHTML = `
    <div class="stat-label">❤️ 심박수</div>
    <div class="stat-value" style="color:${bpmColor}">${hr.bpm}<span style="font-size:14px;font-weight:600;color:var(--text-muted)">bpm</span></div>
    <div class="stat-sub">${hr.bpm_min ? `최소 ${hr.bpm_min}` : ''} ${hr.bpm_max ? `· 최대 ${hr.bpm_max}` : ''}</div>
    <div class="stat-sub" style="margin-top:4px">${hr.tag ? `<span class="badge badge-red">${hr.tag}</span>` : ''}</div>`;
}

// ── 인바디 ─────────────────────────────────────
function renderInbody(ib) {
  const el = document.getElementById('inbody-card');
  if (!ib || !ib.weight_kg) {
    el.innerHTML = emptyCard('⚖️', '인바디', '데이터 없음');
    return;
  }

  el.innerHTML = `
    <div class="stat-label">⚖️ 인바디</div>
    <div class="stat-value" style="color:var(--orange)">${ib.weight_kg}<span style="font-size:14px;font-weight:600;color:var(--text-muted)">kg</span></div>
    <div class="inbody-grid" style="grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">
      <div class="inbody-item">
        <div class="inbody-val" style="font-size:15px">${ib.skeletal_muscle_kg ?? '-'}</div>
        <div class="inbody-lbl">골격근 kg</div>
      </div>
      <div class="inbody-item">
        <div class="inbody-val" style="font-size:15px;color:var(--orange)">${ib.body_fat_pct ?? '-'}</div>
        <div class="inbody-lbl">체지방 %</div>
      </div>
    </div>
    <div class="stat-sub" style="margin-top:8px">BMI ${ib.bmi ?? '-'} &nbsp;·&nbsp; BMR ${ib.bmr_kcal ?? '-'}kcal</div>`;
}

// ── 날씨 ───────────────────────────────────────
function renderWeather(w) {
  const el = document.getElementById('weather-card');
  if (!w || !w.temp_c) {
    el.innerHTML = '<div class="loading-box"><div>날씨 정보 없음</div></div>';
    return;
  }

  el.innerHTML = `
    <div class="card-header">
      <div class="card-label">🌤 현재 날씨</div>
      <span class="badge ${w.is_raining ? 'badge-blue' : 'badge-green'}">${w.is_raining ? '🌧 비' : '☀️ 맑음'}</span>
    </div>
    <div class="weather-main">
      <img class="weather-icon-img" src="${w.icon}" alt="${w.condition}">
      <div>
        <div class="weather-temp">${Math.round(w.temp_c)}°</div>
        <div class="weather-cond">${w.condition}</div>
      </div>
    </div>
    <div class="weather-grid">
      <div class="weather-item">🌡 체감 ${Math.round(w.feels_like)}°C</div>
      <div class="weather-item">💧 습도 ${w.humidity}%</div>
      <div class="weather-item">💨 바람 ${w.wind_kph}km/h</div>
      <div class="weather-item">☀️ UV ${w.uv}</div>
    </div>`;
}

// ── 산책 ───────────────────────────────────────
function renderWalk(ok, msg) {
  const el = document.getElementById('walk-card');
  if (ok === undefined) {
    el.innerHTML = '<div class="loading-box"><div>산책 정보 없음</div></div>';
    return;
  }

  if (!ok) {
    el.innerHTML = `
      <div class="card-label">🚶 산책</div>
      <div style="margin-top:12px;font-size:28px;text-align:center">🎉</div>
      <div style="text-align:center;margin-top:8px;font-weight:700;color:var(--green)">목표 달성!</div>
      <div style="text-align:center;font-size:13px;color:var(--text-muted);margin-top:4px">${msg}</div>`;
    return;
  }

  el.innerHTML = `
    <div class="card-label">🚶 산책 추천</div>
    <div style="margin-top:10px">
      <div class="alert alert-warning">${msg}</div>
      <a href="/exercise" class="btn btn-green btn-full btn-sm" style="margin-top:8px">경로 보기 →</a>
    </div>`;
}

// ── 식단 요약 ───────────────────────────────────
async function loadMeals() {
  const el = document.getElementById('meal-summary');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div><div>식단 로딩 중</div></div>';

  try {
    const data = await API.getMeals(currentDate);
    const s = data.summary;
    const meals = data.meals || [];

    const goal = 2000;
    const pct = clamp(Math.round((s.total_kcal / goal) * 100), 0, 100);

    el.innerHTML = `
      <div class="card-header">
        <div class="card-label">🍽 오늘 식단</div>
        <a href="/diet" class="btn btn-secondary btn-xs">상세 →</a>
      </div>
      <div style="font-size:28px;font-weight:800;color:var(--orange)">${Math.round(s.total_kcal)}<span style="font-size:14px;font-weight:600;color:var(--text-muted)">kcal</span></div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:12px">${s.meal_count}끼 섭취</div>
      <div class="progress-wrap prog-orange">
        <div class="progress-label"><span>칼로리</span><span>${Math.round(s.total_kcal)} / ${goal}</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      </div>
      <div class="progress-wrap prog-blue">
        <div class="progress-label"><span>단백질</span><span>${Math.round(s.total_protein)}g</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${clamp(Math.round(s.total_protein/60*100),0,100)}%"></div></div>
      </div>
      ${meals.length === 0 ? '<div class="empty-state" style="padding:16px"><span class="empty-icon">🍽</span><div class="empty-text">오늘 식단 기록 없음</div></div>' :
        meals.slice(0,3).map(m => `
          <div class="meal-item">
            <div><div class="meal-name">${m.food_name}</div>
            <div class="meal-meta">${m.eaten_at.slice(11,16)}</div></div>
            <div class="meal-kcal">${Math.round(m.kcal)}kcal</div>
          </div>`).join('')
      }`;
  } catch(e) {
    el.innerHTML = '<div class="empty-state"><span class="empty-icon">🍽</span><div class="empty-text">식단 데이터 없음</div></div>';
  }
}

// ── 시간표 ─────────────────────────────────────
async function loadSchedule() {
  const el = document.getElementById('schedule-card');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div></div>';

  try {
    const { schedule } = await API.getSchedule();
    const days = ['월','화','수','목','금'];
    const kstNow = new Date(Date.now() + 9*60*60*1000);
    const dayOfWeek = (kstNow.getUTCDay() + 6) % 7; // 0=월
    const todayStr = days[dayOfWeek];

    const todayClasses = schedule.filter(s => s.day_of_week === dayOfWeek);

    el.innerHTML = `
      <div class="card-header">
        <div class="card-label">📅 오늘 시간표 (${todayStr})</div>
        <a href="/settings" class="btn btn-secondary btn-xs">편집 →</a>
      </div>
      ${todayClasses.length === 0
        ? '<div class="empty-state" style="padding:16px"><span class="empty-icon">📭</span><div class="empty-text">오늘 수업 없음</div></div>'
        : todayClasses.map(c => `
          <div class="event-item">
            <div class="event-time">${c.start_time}</div>
            <div>
              <div class="event-title">${c.subject}</div>
              <div class="event-sub">${c.classroom || ''} ${c.professor ? '· '+c.professor : ''}</div>
            </div>
          </div>`).join('')
      }`;
  } catch(e) {
    el.innerHTML = `
      <div class="card-header"><div class="card-label">📅 시간표</div></div>
      <div class="empty-state" style="padding:16px">
        <span class="empty-icon">📸</span>
        <div class="empty-text">시간표를 등록해주세요</div>
        <a href="/settings" class="btn btn-primary btn-sm" style="margin-top:12px">등록하러 가기</a>
      </div>`;
  }
}

// ── 옷차림 ─────────────────────────────────────
async function loadOutfit() {
  const el = document.getElementById('outfit-card');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div><div>AI 분석 중...</div></div>';

  try {
    const data = await API.getOutfit();

    if (!data.has_events) {
      el.innerHTML = `
        <div class="card-label" style="margin-bottom:12px">👕 오늘 옷차림</div>
        <div class="empty-state" style="padding:20px">
          <span class="empty-icon">😴</span>
          <div class="empty-text">${data.message || '오늘 일정이 없어요'}</div>
        </div>`;
      return;
    }

    el.innerHTML = `
      <div class="card-header">
        <div class="card-label">👕 오늘 옷차림 추천</div>
        <span class="badge badge-purple">AI</span>
      </div>
      <div class="ai-comment">${data.comment || ''}</div>
      <div class="outfit-row"><div class="outfit-row-icon">👕</div><div class="outfit-row-label">상의</div><div class="outfit-row-val">${data.top || '-'}</div></div>
      <div class="outfit-row"><div class="outfit-row-icon">👖</div><div class="outfit-row-label">하의</div><div class="outfit-row-val">${data.bottom || '-'}</div></div>
      <div class="outfit-row"><div class="outfit-row-icon">🧥</div><div class="outfit-row-label">겉옷</div><div class="outfit-row-val">${data.outer || '필요없음'}</div></div>
      <div class="outfit-row"><div class="outfit-row-icon">${data.umbrella ? '☂️' : '🌂'}</div><div class="outfit-row-label">우산</div><div class="outfit-row-val">${data.umbrella ? '챙기세요' : '불필요'}</div></div>
      <div class="outfit-row"><div class="outfit-row-icon">🧴</div><div class="outfit-row-label">썬크림</div><div class="outfit-row-val">${data.sunscreen ? '필요' : '불필요'}</div></div>
      ${data.extra ? `<div class="alert alert-info" style="margin-top:12px;font-size:13px">${data.extra}</div>` : ''}`;
  } catch(e) {
    el.innerHTML = `
      <div class="card-label" style="margin-bottom:12px">👕 오늘 옷차림</div>
      <div class="empty-state" style="padding:20px">
        <span class="empty-icon">📡</span>
        <div class="empty-text">시간표를 먼저 등록하면 AI가 옷차림을 추천해드려요</div>
      </div>`;
  }
}

// ── 헬퍼 ───────────────────────────────────────
function setLoading(id) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = '<div class="loading-box"><div class="spinner"></div></div>';
}

function setError(id, msg) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<div class="empty-state"><div class="empty-text">${msg}</div></div>`;
}

function emptyCard(icon, label, msg) {
  return `<div class="stat-label">${icon} ${label}</div>
    <div class="empty-state" style="padding:16px 0">
      <span class="empty-icon">${icon}</span>
      <div class="empty-text">${msg}</div>
    </div>`;
}
