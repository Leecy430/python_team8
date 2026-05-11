/* =============================================
   exercise.js — 운동 페이지 로직
   ============================================= */

document.addEventListener('DOMContentLoaded', () => {
  loadExerciseRecommend();
  loadFreeSlots();
  loadWalk();
});

// ── 운동 루틴 추천 ──────────────────────────────
async function loadExerciseRecommend() {
  const el = document.getElementById('exerciseRecommend');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div><div>AI가 오늘 루틴을 분석 중...</div></div>';

  try {
    const data = await API.getExerciseRecommend();

    const intensityBadge = {
      '저강도': 'badge-blue',
      '중강도': 'badge-orange',
      '고강도': 'badge-red'
    }[data.intensity] || 'badge-blue';

    const exerciseIcons = {
      '걷기':'🚶','달리기':'🏃','스쿼트':'🏋','푸시업':'💪','플랭크':'🧘',
      '줄넘기':'🪢','자전거':'🚴','계단오르기':'🪜','스트레칭':'🤸','요가':'🧘',
      '데드리프트':'🏋','벤치프레스':'🏋',
    };

    el.innerHTML = `
      <div class="ai-label">🤖 AI 오늘의 운동 루틴</div>
      ${data.comment ? `<div class="ai-comment">${data.comment}</div>` : ''}
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
        <span class="badge ${intensityBadge}">${data.intensity || ''}</span>
        <span style="font-size:13px;color:var(--text-muted)">예상 소모: <strong style="color:var(--red)">${Math.round(data.total_kcal||0)}kcal</strong></span>
      </div>
      ${(data.routine || []).map(r => {
        const icon = Object.keys(exerciseIcons).find(k => (r.name||'').includes(k));
        return `
        <div class="exercise-item">
          <div class="exercise-icon">${icon ? exerciseIcons[icon] : '🏃'}</div>
          <div>
            <div class="exercise-name">${r.name}</div>
            <div class="exercise-meta">${r.sets ? r.sets+'세트 · ' : ''}${r.duration_min}분</div>
          </div>
          <div class="exercise-kcal">${Math.round(r.kcal||0)}kcal</div>
        </div>`;
      }).join('')}
      <button class="btn btn-primary btn-full" style="margin-top:8px" onclick="loadExerciseRecommend()">
        🔄 다시 추천받기
      </button>`;
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

// ── 공강 운동 ───────────────────────────────────
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

    el.innerHTML = slots.map(slot => `
      <div class="slot-card">
        <div class="slot-time">⏰ ${slot.time} (${slot.duration_min}분) · ${slot.location}</div>
        <div class="slot-exercises">
          ${(slot.exercises || []).map(ex => `<span class="badge badge-green">${ex}</span>`).join('')}
        </div>
      </div>`).join('');
  } catch(e) {
    el.innerHTML = `<div class="empty-state"><span class="empty-icon">📅</span><div class="empty-text">공강 데이터 없음</div></div>`;
  }
}

// ── 산책 추천 ───────────────────────────────────
async function loadWalk() {
  const el = document.getElementById('walkRecommend');
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div></div>';

  try {
    const data = await API.getWalkRecommend();

    if (!data.recommend) {
      el.innerHTML = `
        <div style="text-align:center;padding:16px">
          <div style="font-size:40px">🎉</div>
          <div style="font-size:18px;font-weight:800;color:var(--green);margin-top:8px">목표 달성!</div>
          <div style="font-size:13px;color:var(--text-muted);margin-top:4px">${data.reason}</div>
        </div>`;
      return;
    }

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
        <div style="margin-top:14px;font-size:13px;color:var(--text-muted)">
          📍 ${data.from || '현재위치'} → 🏠 ${data.to || '집'}
        </div>` : `
        <div class="alert alert-info">위치를 설정하면 Kakao Maps 경로를 볼 수 있어요
          <a href="/settings" style="margin-left:8px;font-weight:700">설정하기</a>
        </div>`}`;
  } catch(e) {
    el.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">🚶</span>
        <div class="empty-text">걸음수 데이터가 없습니다</div>
      </div>`;
  }
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
