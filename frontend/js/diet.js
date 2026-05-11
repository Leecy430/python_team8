/* =============================================
   diet.js — 식단 페이지 로직
   ============================================= */

let dietDate = today();

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dateInput').value = dietDate;
  setupUpload();
  loadMeals();
});

// ── 날짜 ───────────────────────────────────────
function prevDay() {
  const d = new Date(dietDate);
  d.setDate(d.getDate() - 1);
  dietDate = d.toISOString().split('T')[0];
  document.getElementById('dateInput').value = dietDate;
  loadMeals();
}

function nextDay() {
  const d = new Date(dietDate);
  d.setDate(d.getDate() + 1);
  if (d.toISOString().split('T')[0] > today()) return;
  dietDate = d.toISOString().split('T')[0];
  document.getElementById('dateInput').value = dietDate;
  loadMeals();
}

function onDateChange(val) {
  dietDate = val;
  loadMeals();
}

// ── 사진 업로드 ─────────────────────────────────
function setupUpload() {
  const area = document.getElementById('uploadArea');
  const input = document.getElementById('fileInput');

  area.addEventListener('dragover', e => {
    e.preventDefault();
    area.classList.add('drag-over');
  });

  area.addEventListener('dragleave', () => area.classList.remove('drag-over'));

  area.addEventListener('drop', e => {
    e.preventDefault();
    area.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) uploadFood(file);
  });

  area.addEventListener('click', () => input.click());

  input.addEventListener('change', e => {
    if (e.target.files[0]) uploadFood(e.target.files[0]);
  });
}

async function uploadFood(file) {
  const area = document.getElementById('uploadArea');
  const result = document.getElementById('uploadResult');

  area.innerHTML = `<div class="loading-box"><div class="spinner"></div><div>AI가 음식을 분석 중입니다...</div></div>`;
  result.innerHTML = '';

  try {
    const data = await API.uploadFoodPhoto(file);

    if (data.success && data.foods && data.foods.length > 0) {
      showToast('✅ 식단이 저장되었습니다!');
      result.innerHTML = `
        <div class="ai-card">
          <div class="ai-label">🤖 AI 인식 결과</div>
          ${data.foods.map(f => `
            <div class="rec-meal">
              <div>
                <div class="rec-meal-name">${f.food_name}</div>
                <div class="rec-meal-reason">단백질 ${Math.round(f.protein_g||0)}g · 탄수화물 ${Math.round(f.carb_g||0)}g · 지방 ${Math.round(f.fat_g||0)}g</div>
              </div>
              <div class="rec-meal-kcal">${Math.round(f.kcal||0)}<small style="font-size:11px;font-weight:600;color:var(--text-muted)">kcal</small></div>
            </div>`).join('')}
        </div>`;
      loadMeals();
    } else {
      showToast('음식을 인식하지 못했습니다.');
    }
  } catch(e) {
    showToast('업로드 실패: ' + e.message);
  }

  // 업로드 영역 복원
  area.innerHTML = `
    <span class="upload-icon">📸</span>
    <div class="upload-title">음식 사진을 올려주세요</div>
    <div class="upload-sub">클릭하거나 드래그하여 업로드 · JPG · PNG</div>`;
}

// ── 식단 목록 로드 ─────────────────────────────
async function loadMeals() {
  const listEl = document.getElementById('mealList');
  const summaryEl = document.getElementById('nutritionSummary');

  listEl.innerHTML = '<div class="loading-box"><div class="spinner"></div></div>';
  summaryEl.innerHTML = '';

  try {
    const data = await API.getMeals(dietDate);
    const meals = data.meals || [];
    const s = data.summary || {};

    // 영양소 요약
    const goal = 2000;
    const proteinGoal = 60;
    const carbGoal = 250;
    const fatGoal = 65;

    summaryEl.innerHTML = `
      <div class="card-header">
        <div class="card-label">📊 영양소 요약</div>
        <div style="font-size:22px;font-weight:800;color:var(--orange)">${Math.round(s.total_kcal||0)}<span style="font-size:13px;font-weight:600;color:var(--text-muted)">kcal</span></div>
      </div>
      <div class="progress-wrap prog-orange">
        <div class="progress-label"><span>칼로리</span><span>${Math.round(s.total_kcal||0)} / ${goal}kcal</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${clamp(Math.round((s.total_kcal||0)/goal*100),0,100)}%"></div></div>
      </div>
      <div class="progress-wrap prog-blue">
        <div class="progress-label"><span>단백질</span><span>${Math.round(s.total_protein||0)}g / ${proteinGoal}g</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${clamp(Math.round((s.total_protein||0)/proteinGoal*100),0,100)}%"></div></div>
      </div>
      <div class="progress-wrap prog-green">
        <div class="progress-label"><span>탄수화물</span><span>${Math.round(s.total_carb||0)}g / ${carbGoal}g</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${clamp(Math.round((s.total_carb||0)/carbGoal*100),0,100)}%"></div></div>
      </div>
      <div class="progress-wrap prog-red">
        <div class="progress-label"><span>지방</span><span>${Math.round(s.total_fat||0)}g / ${fatGoal}g</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${clamp(Math.round((s.total_fat||0)/fatGoal*100),0,100)}%"></div></div>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-top:4px">${s.meal_count||0}끼 기록됨</div>`;

    // 식단 목록
    if (meals.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">🍽</span>
          <div class="empty-text">오늘 기록된 식단이 없어요<br>사진을 올려 기록해보세요!</div>
        </div>`;
    } else {
      // 시간대별 그룹
      const groups = {};
      meals.forEach(m => {
        const hour = parseInt(m.eaten_at.slice(11,13));
        const label = hour < 10 ? '🌅 아침' : hour < 14 ? '☀️ 점심' : hour < 18 ? '🌤 오후' : '🌙 저녁';
        if (!groups[label]) groups[label] = [];
        groups[label].push(m);
      });

      listEl.innerHTML = Object.entries(groups).map(([label, items]) => `
        <div style="margin-bottom:16px">
          <div style="font-size:12px;font-weight:700;color:var(--text-muted);margin-bottom:8px">${label}</div>
          ${items.map(m => `
            <div class="meal-item">
              <div>
                <div class="meal-name">${m.food_name}</div>
                <div class="meal-meta">
                  ${m.eaten_at.slice(11,16)} &nbsp;·&nbsp;
                  단백질 ${Math.round(m.protein_g||0)}g · 탄수 ${Math.round(m.carb_g||0)}g · 지방 ${Math.round(m.fat_g||0)}g
                </div>
              </div>
              <div class="meal-kcal">${Math.round(m.kcal||0)}<small style="font-size:11px;font-weight:600;color:var(--text-muted)">kcal</small></div>
            </div>`).join('')}
        </div>`).join('');
    }
  } catch(e) {
    listEl.innerHTML = `<div class="empty-state"><span class="empty-icon">⚠️</span><div class="empty-text">데이터 로딩 실패</div></div>`;
  }
}

// ── AI 식단 추천 ────────────────────────────────
async function getRecommend() {
  const el = document.getElementById('recommendResult');
  const btn = document.getElementById('recommendBtn');

  btn.disabled = true;
  btn.textContent = 'AI 분석 중...';
  el.innerHTML = '<div class="loading-box"><div class="spinner"></div><div>Claude AI가 분석 중입니다...</div></div>';

  try {
    const data = await API.getMealRecommend(dietDate);

    const balanceColor = (data.calorie_balance || 0) >= 0 ? 'var(--green)' : 'var(--red)';
    const balanceLabel = (data.calorie_balance || 0) >= 0 ? '칼로리 여유' : '칼로리 부족';

    el.innerHTML = `
      <div class="ai-card">
        <div class="ai-label">🤖 AI 다음 끼니 추천</div>
        ${data.comment ? `<div class="ai-comment">${data.comment}</div>` : ''}
        <div style="margin-bottom:10px">
          ${(data.meals || []).map(m => `
            <div class="rec-meal">
              <div>
                <div class="rec-meal-name">${m.name}</div>
                <div class="rec-meal-reason">${m.reason}</div>
              </div>
              <div class="rec-meal-kcal">${m.kcal}<small style="font-size:11px;font-weight:600;color:var(--text-muted)">kcal</small></div>
            </div>`).join('')}
        </div>
        <div style="text-align:right;font-size:13px;color:${balanceColor};font-weight:700">
          ${balanceLabel}: ${Math.abs(data.calorie_balance||0)}kcal
        </div>
      </div>`;
  } catch(e) {
    el.innerHTML = `<div class="alert alert-warning">추천 실패: ${e.message}</div>`;
  }

  btn.disabled = false;
  btn.textContent = '🤖 AI 추천 받기';
}
