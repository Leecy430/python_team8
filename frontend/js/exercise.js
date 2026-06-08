/* =============================================
   exercise.js — 운동 페이지 로직
   ============================================= */

document.addEventListener('DOMContentLoaded', () => {
  loadExerciseRecommend();
  loadFreeSlots();
  loadWalk();
});

// ── 운동 루틴 추천 ──────────────────────────────
const ROUTINE_ICONS = {
  '걷기':'🚶','달리기':'🏃','스쿼트':'🏋','푸시업':'💪','플랭크':'🧘',
  '줄넘기':'🪢','자전거':'🚴','계단오르기':'🪜','스트레칭':'🤸','요가':'🧘‍♀️',
  '데드리프트':'🏋','벤치프레스':'🏋',
};

function routineKey(name) {
  return `routine_done_${today()}_${name}`;
}
function routineFeedbackKey() {
  return `routine_feedback_${today()}`;
}

let _routineData = null;

async function loadExerciseRecommend() {
  const el = document.getElementById('exerciseRecommend');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div><div>AI가 오늘 루틴을 분석 중...</div></div>';

  try {
    const data = await API.getExerciseRecommend();
    _routineData = data;
    renderRoutine(data);
  } catch(e) {
    el.innerHTML = `
      <div class="ai-label">🤖 AI 운동 루틴 추천</div>
      <div class="empty-state">
        <span class="empty-icon">⚠️</span>
        <div class="empty-text">인바디·수면 데이터가 필요합니다<br>${e.message}</div>
        <button class="btn btn-primary btn-sm" style="margin-top:12px" onclick="loadExerciseRecommend()">다시 시도</button>
      </div>`;
  }
}

function renderRoutine(data) {
  const el = document.getElementById('exerciseRecommend');
  const intensityBadge = {
    '저강도': 'badge-blue',
    '중강도': 'badge-orange',
    '고강도': 'badge-red'
  }[data.intensity] || 'badge-blue';

  const fb = localStorage.getItem(routineFeedbackKey());
  const goodActive = fb === 'good' ? 'btn-primary' : 'btn-secondary';
  const badActive  = fb === 'bad'  ? 'btn-primary' : 'btn-secondary';

  const items = (data.routine || []).map(r => {
    const iconKey = Object.keys(ROUTINE_ICONS).find(k => (r.name || '').includes(k));
    const icon = iconKey ? ROUTINE_ICONS[iconKey] : '🏃';
    const key  = routineKey(r.name);
    const done = localStorage.getItem(key) === 'true';
    return `
      <div class="exercise-item" style="${done ? 'opacity:0.5;' : ''}">
        <div class="exercise-icon">${icon}</div>
        <div style="flex:1">
          <div class="exercise-name" style="${done ? 'text-decoration:line-through' : ''}">${r.name}</div>
          <div class="exercise-meta">${r.sets ? r.sets + '세트 · ' : ''}${r.duration_min}분 · 약 ${Math.round(r.kcal || 0)}kcal</div>
        </div>
        <button
          class="btn btn-sm ${done ? 'btn-secondary' : 'btn-primary'}"
          onclick="toggleRoutineDone('${r.name}', ${r.duration_min})"
          style="min-width:60px">
          ${done ? '✅ 완료' : '완료'}
        </button>
      </div>`;
  }).join('');

  el.innerHTML = `
    <div class="ai-label">🤖 AI 오늘의 운동 루틴</div>
    ${data.comment ? `<div class="ai-comment">${data.comment}</div>` : ''}
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
      <span class="badge ${intensityBadge}">${data.intensity || ''}</span>
      <span style="font-size:13px;color:var(--text-muted)">예상 소모: <strong style="color:var(--red)">${Math.round(data.total_kcal || 0)}kcal</strong></span>
    </div>
    ${items}
    <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">이 루틴 방향이 도움이 됐나요?</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-sm ${goodActive}" onclick="setRoutineFeedback('good')">👍 좋아요</button>
        <button class="btn btn-sm ${badActive}"  onclick="setRoutineFeedback('bad')">👎 별로예요</button>
        <button class="btn btn-sm btn-secondary" style="margin-left:auto" onclick="loadExerciseRecommend()">🔄 다시 추천</button>
      </div>
    </div>`;
}

async function toggleRoutineDone(name, durationMin) {
  const key  = routineKey(name);
  const done = localStorage.getItem(key) === 'true';
  localStorage.setItem(key, !done);

  if (!done) {
    try { await API.saveExercise(name, durationMin); } catch(_) {}
    showToast(`✅ ${name} 완료 기록!`);
  }

  if (_routineData) renderRoutine(_routineData);
}

function setRoutineFeedback(value) {
  if (value === 'bad') {
    const context = _routineData
      ? `강도: ${_routineData.intensity}, 운동: ${(_routineData.routine || []).map(r => r.name).join(', ')}`
      : '';
    openFeedbackModal('exercise_routine', context);
    return;
  }
  localStorage.setItem(routineFeedbackKey(), 'good');
  showToast('👍 좋은 피드백 감사해요!');
  if (_routineData) renderRoutine(_routineData);
}

// ── 공강 운동 ───────────────────────────────────
const SLOT_ICONS = {
  '걷기':'🚶','달리기':'🏃','스쿼트':'🏋','푸시업':'💪',
  '플랭크':'🧘','줄넘기':'🪢','자전거':'🚴','계단오르기':'🪜',
  '스트레칭':'🤸','요가':'🧘‍♀️','데드리프트':'🏋','벤치프레스':'🏋',
};
const SLOT_MET = {
  '걷기':3.5,'달리기':8.0,'스쿼트':5.0,'푸시업':4.0,
  '플랭크':3.0,'줄넘기':10.0,'자전거':6.0,'계단오르기':6.0,
  '스트레칭':2.5,'요가':2.5,'데드리프트':6.0,'벤치프레스':5.0,
};
// 종목별 권장 시간 비율 (비례 배분 기준)
const SLOT_BASE_MIN = {
  '걷기':15,'달리기':10,'스쿼트':10,'푸시업':8,
  '플랭크':5,'줄넘기':8,'자전거':15,'계단오르기':8,
  '스트레칭':8,'요가':10,'데드리프트':10,'벤치프레스':10,
};

function calcEffectiveTime(slotTime, totalMin, exCount) {
  // slotTime 형식: "11:00~13:00" → 시작/끝 시간 파싱
  const [startStr, endStr] = slotTime.split('~');
  const [sh, sm] = startStr.split(':').map(Number);
  const [eh, em] = (endStr || startStr).split(':').map(Number);
  const startTotal = sh * 60 + sm;
  const endTotal   = eh * 60 + em;
  // 슬롯이 점심 시간대(11:30~14:00)와 겹치면 점심으로 간주
  const isLunch = startTotal < 14 * 60 && endTotal > 11 * 60 + 30;

  let deduct = 5; // 이동/준비
  if (isLunch) deduct += 30; // 점심 식사
  const restBetween = Math.max(0, exCount - 1) * 2; // 운동 간 휴식
  const raw = Math.max(totalMin - deduct - restBetween, exCount * 3);
  const effective = Math.min(raw, 40); // 최대 40분으로 제한

  return { effective, isLunch, deduct, restBetween };
}

function distributeTime(exList, effectiveMin) {
  const bases = exList.map(ex => {
    const key = Object.keys(SLOT_BASE_MIN).find(k => ex.includes(k));
    return key ? SLOT_BASE_MIN[key] : 8;
  });
  const total = bases.reduce((a, b) => a + b, 0);
  return bases.map(b => Math.max(3, Math.round((b / total) * effectiveMin)));
}

function slotKey(slotTime, ex) {
  return `slot_done_${today()}_${slotTime}_${ex}`;
}
function feedbackKey(slotTime) {
  return `slot_feedback_${today()}_${slotTime}`;
}

async function loadFreeSlots() {
  const el = document.getElementById('freeSlots');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div></div>';

  try {
    const { slots } = await API.getExerciseFreeSlots();

    if (!slots || slots.length === 0) {
      el.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📅</span>
          <div class="empty-text">오늘 공강이 없거나 시간표가 등록되지 않았어요</div>
          <a href="/settings" class="btn btn-secondary btn-sm" style="margin-top:12px">시간표 등록</a>
        </div>`;
      return;
    }

    el.innerHTML = slots.map(slot => renderSlotCard(slot)).join('');
  } catch(e) {
    el.innerHTML = `<div class="empty-state"><span class="empty-icon">📅</span><div class="empty-text">공강 데이터 없음</div></div>`;
  }
}

function renderSlotCard(slot) {
  const exList = slot.exercises || [];
  const { effective, isLunch, deduct, restBetween } = calcEffectiveTime(slot.time, slot.duration_min, exList.length);
  const durations = distributeTime(exList, effective);
  const fb = localStorage.getItem(feedbackKey(slot.time));

  const infoChips = [];
  if (isLunch) infoChips.push('🍱 식사 30분 포함');
  infoChips.push(`🏃 실제 운동 ${effective}분`);
  if (restBetween > 0) infoChips.push(`😮‍💨 휴식 ${restBetween}분`);

  const exItems = exList.map((ex, i) => {
    const iconKey = Object.keys(SLOT_ICONS).find(k => ex.includes(k));
    const icon = iconKey ? SLOT_ICONS[iconKey] : '🏃';
    const min  = durations[i];
    const metKey = Object.keys(SLOT_MET).find(k => ex.includes(k));
    const kcal = Math.round((metKey ? SLOT_MET[metKey] : 4) * 70 * (min / 60));
    const done = localStorage.getItem(slotKey(slot.time, ex)) === 'true';
    const key  = slotKey(slot.time, ex);
    return `
      <div class="exercise-item" id="item-${key}" style="${done ? 'opacity:0.5;' : ''}">
        <div class="exercise-icon">${icon}</div>
        <div style="flex:1">
          <div class="exercise-name" style="${done ? 'text-decoration:line-through' : ''}">${ex}</div>
          <div class="exercise-meta">${min}분 · 약 ${kcal}kcal</div>
        </div>
        <button
          class="btn btn-sm ${done ? 'btn-secondary' : 'btn-primary'}"
          id="btn-${key}"
          onclick="toggleDone('${slot.time}', '${ex}', ${min})"
          style="min-width:60px">
          ${done ? '✅ 완료' : '완료'}
        </button>
      </div>`;
  }).join('');

  const goodActive = fb === 'good' ? 'btn-primary' : 'btn-secondary';
  const badActive  = fb === 'bad'  ? 'btn-primary' : 'btn-secondary';

  return `
    <div style="border:1.5px solid var(--border);border-radius:16px;overflow:hidden;margin-bottom:16px">
      <div style="background:var(--primary-light);padding:12px 16px;display:flex;justify-content:space-between;align-items:center">
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-weight:700;font-size:15px">⏰ ${slot.time}</span>
          <span class="badge badge-blue">${slot.duration_min}분 공강</span>
        </div>
        <span style="font-size:13px;color:var(--text-muted)">📍 ${slot.location}</span>
      </div>
      <div style="padding:8px 16px 4px;display:flex;flex-wrap:wrap;gap:6px">
        ${infoChips.map(c => `<span style="font-size:12px;color:var(--text-muted);background:var(--bg);border:1px solid var(--border);border-radius:20px;padding:2px 10px">${c}</span>`).join('')}
      </div>
      <div style="padding:4px 16px 8px">${exItems}</div>
      <div style="padding:12px 16px;border-top:1px solid var(--border);background:var(--bg)">
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">이 추천 방향이 도움이 됐나요?</div>
        <div style="display:flex;gap:8px">
          <button id="fb-good-${slot.time}" class="btn btn-sm ${goodActive}"
            onclick="setFeedback('${slot.time}', 'good')">👍 좋아요</button>
          <button id="fb-bad-${slot.time}"  class="btn btn-sm ${badActive}"
            onclick="setFeedback('${slot.time}', 'bad', ${JSON.stringify(exList)})">👎 별로예요</button>
        </div>
      </div>
    </div>`;
}

async function toggleDone(slotTime, exName, durationMin) {
  const key  = slotKey(slotTime, exName);
  const done = localStorage.getItem(key) === 'true';
  const next = !done;
  localStorage.setItem(key, next);

  // 완료로 바꿀 때 DB에 운동 기록 저장
  if (next) {
    try { await API.saveExercise(exName, durationMin); } catch(_) {}
    showToast(`✅ ${exName} 완료 기록!`);
  }

  // 해당 슬롯만 다시 렌더링
  const { slots } = await API.getExerciseFreeSlots();
  const slot = slots.find(s => s.time === slotTime);
  if (!slot) return;

  const el = document.getElementById(`item-${key}`);
  if (el) el.outerHTML = renderSlotCard(slot)
    .match(new RegExp(`id="item-${key.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}"[^]*?<\/div>\s*<\/div>`))?.[0] || '';

  // 간단히 전체 재렌더링
  loadFreeSlots();
}

function setFeedback(slotTime, value, exercises) {
  if (value === 'bad') {
    const context = exercises && exercises.length
      ? `${slotTime} / 이전 추천: ${exercises.join(', ')}`
      : slotTime;
    openFeedbackModal('exercise_slot', context);
    return;
  }
  localStorage.setItem(feedbackKey(slotTime), 'good');
  showToast('👍 좋은 피드백 감사해요!');
  loadFreeSlots();
}

// ── 피드백 모달 ─────────────────────────────────
let _fbType = null;
let _fbContext = '';

function openFeedbackModal(type, context) {
  _fbType = type;
  _fbContext = context;
  document.getElementById('feedbackText').value = '';
  document.getElementById('feedbackModal').style.display = 'flex';
}

function closeFeedbackModal() {
  document.getElementById('feedbackModal').style.display = 'none';
}

async function submitFeedbackModal() {
  const content = document.getElementById('feedbackText').value.trim();
  if (!content) {
    showToast('피드백 내용을 입력해주세요.');
    return;
  }
  try {
    await API.submitFeedback(_fbType, 'bad', content, _fbContext);
    showToast('👎 피드백이 저장됐어요. 다음 추천에 반영할게요!');
    if (_fbType === 'exercise_routine') {
      localStorage.setItem(routineFeedbackKey(), 'bad');
      if (_routineData) renderRoutine(_routineData);
    } else if (_fbType === 'exercise_slot') {
      localStorage.setItem(feedbackKey(_fbContext), 'bad');
      loadFreeSlots();
    }
    closeFeedbackModal();
  } catch(e) {
    showToast('저장 실패: ' + e.message);
  }
}

// ── 산책 추천 ───────────────────────────────────
let _walkData = null;

async function loadWalk() {
  const el = document.getElementById('walkRecommend');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div></div>';

  try {
    const data = await API.getWalkRecommend();
    _walkData = data;

    if (!data.recommend) {
      el.innerHTML = `
        <div style="text-align:center;padding:16px">
          <div style="font-size:40px">🎉</div>
          <div style="font-size:18px;font-weight:800;color:var(--green);margin-top:8px">목표 달성!</div>
          <div style="font-size:13px;color:var(--text-muted);margin-top:4px">${data.reason}</div>
        </div>`;
      return;
    }

    const hasMap = data.origin_lat && data.dest_lat;

    el.innerHTML = `
      <div class="alert alert-warning" style="margin-bottom:14px">${data.reason}</div>
      ${data.route ? `
        <div class="walk-stat">
          <div class="walk-stat-item">
            <div class="walk-stat-val">${(data.route.distance_m/1000).toFixed(1)}</div>
            <div class="walk-stat-lbl">km</div>
          </div>
          <div class="walk-stat-item">
            <div class="walk-stat-val">${data.route.duration_min}</div>
            <div class="walk-stat-lbl">분</div>
          </div>
          <div class="walk-stat-item">
            <div class="walk-stat-val">${data.extra_steps?.toLocaleString() || '-'}</div>
            <div class="walk-stat-lbl">예상 걸음</div>
          </div>
        </div>
        <div style="margin-top:10px;font-size:13px;color:var(--text-muted)">
          📍 ${data.from || '현재위치'} → 🏠 ${data.to || '집'}
        </div>
        ${hasMap ? `
        <div id="walkMapSmall" style="width:100%;height:200px;border-radius:12px;margin-top:12px;overflow:hidden;border:1px solid var(--border)"></div>
        <button onclick="openMapModal()" class="btn btn-secondary btn-full btn-sm" style="margin-top:8px">🔍 지도 크게 보기</button>
        ` : ''}` : `
        <div class="alert alert-info">위치를 설정하면 Kakao Maps 경로를 볼 수 있어요
          <a href="/settings" style="margin-left:8px;font-weight:700">설정하기</a>
        </div>`}`;

    if (hasMap) {
      setTimeout(() => renderMap('walkMapSmall', data, false), 50);
    }
  } catch(e) {
    el.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">🚶</span>
        <div class="empty-text">걸음수 데이터가 없습니다</div>
      </div>`;
  }
}

// ── 지도 렌더링 (Leaflet + OpenStreetMap) ────────
let _mapInstances = {};

function renderMap(containerId, data, isModal) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // 기존 지도 인스턴스 제거
  if (_mapInstances[containerId]) {
    _mapInstances[containerId].remove();
    delete _mapInstances[containerId];
  }

  const centerLat = (data.origin_lat + data.dest_lat) / 2;
  const centerLng = (data.origin_lon + data.dest_lon) / 2;

  const map = L.map(containerId).setView([centerLat, centerLng], isModal ? 15 : 14);
  _mapInstances[containerId] = map;

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
    maxZoom: 19,
  }).addTo(map);

  // 출발 마커 (파란색)
  const originIcon = L.divIcon({
    html: '<div style="background:#3b82f6;color:white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 6px rgba(0,0,0,0.3)">📍</div>',
    iconSize: [32, 32], iconAnchor: [16, 32], className: '',
  });
  L.marker([data.origin_lat, data.origin_lon], { icon: originIcon })
    .addTo(map)
    .bindPopup(`<b>출발</b><br>${data.from || '현재위치'}`);

  // 도착 마커 (초록색)
  const destIcon = L.divIcon({
    html: '<div style="background:#22c55e;color:white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 6px rgba(0,0,0,0.3)">🏠</div>',
    iconSize: [32, 32], iconAnchor: [16, 32], className: '',
  });
  L.marker([data.dest_lat, data.dest_lon], { icon: destIcon })
    .addTo(map)
    .bindPopup(`<b>도착</b><br>${data.to || '집'}`);

  // 경로 폴리라인
  const path = data.route?.path;
  if (path && path.length > 1) {
    L.polyline(path.map(p => [p.lat, p.lng]), {
      color: '#3b82f6', weight: 5, opacity: 0.85,
    }).addTo(map);
  } else {
    L.polyline([
      [data.origin_lat, data.origin_lon],
      [data.dest_lat,   data.dest_lon],
    ], { color: '#3b82f6', weight: 4, opacity: 0.6, dashArray: '8 6' }).addTo(map);
  }

  // 모달에서는 지도 크기 재계산
  if (isModal) setTimeout(() => map.invalidateSize(), 150);
}

// ── 모달 ────────────────────────────────────────
function openMapModal() {
  document.getElementById('mapModal').style.display = 'block';
  setTimeout(() => renderMap('mapModalContainer', _walkData, true), 100);
}

function closeMapModal() {
  document.getElementById('mapModal').style.display = 'none';
  document.getElementById('mapModalContainer').innerHTML = '';
}

// ── 운동 수동 기록 ──────────────────────────────
async function saveExercise() {
  const name = document.getElementById('exName').value.trim();
  const duration = parseFloat(document.getElementById('exDuration').value);
  const weight = parseFloat(document.getElementById('exWeight').value) || 70;

  if (!name || !duration) {
    showToast('운동명과 시간을 입력해주세요.');
    return;
  }

  const btn = document.getElementById('saveExBtn');
  btn.disabled = true;

  try {
    await API.saveExercise(name, duration, weight);
    showToast('✅ 운동이 기록되었습니다!');
    document.getElementById('exName').value = '';
    document.getElementById('exDuration').value = '';
  } catch(e) {
    showToast('저장 실패: ' + e.message);
  }

  btn.disabled = false;
}

// ── 운동명 자동완성 ─────────────────────────────
const EXERCISES = ['걷기','달리기','스쿼트','푸시업','플랭크','줄넘기','자전거','계단오르기','스트레칭','요가','데드리프트','벤치프레스'];

function setupAutocomplete() {
  const input = document.getElementById('exName');
  const list = document.getElementById('exSuggestions');

  input.addEventListener('input', () => {
    const val = input.value;
    const matches = EXERCISES.filter(e => e.includes(val) && val !== '');
    list.innerHTML = matches.map(e =>
      `<div class="exercise-suggestion" onclick="selectExercise('${e}')">${e}</div>`
    ).join('');
  });

  input.addEventListener('blur', () => {
    setTimeout(() => { list.innerHTML = ''; }, 150);
  });
}

function selectExercise(name) {
  document.getElementById('exName').value = name;
  document.getElementById('exSuggestions').innerHTML = '';
}

document.addEventListener('DOMContentLoaded', setupAutocomplete);
