/* =============================================
   settings.js — 설정 페이지 로직
   ============================================= */

document.addEventListener('DOMContentLoaded', () => {
  loadLocations();
  loadSchedule();
  loadInbody();
  setupScheduleUpload();
  setupInbodyUpload();
});

// ── 위치 설정 ───────────────────────────────────
async function loadLocations() {
  const el = document.getElementById('locationList');

  try {
    const data = await API.getLocations();
    const entries = Object.entries(data);

    if (entries.length === 0) {
      el.innerHTML = `<div class="empty-state" style="padding:16px">
        <span class="empty-icon">📍</span>
        <div class="empty-text">저장된 위치가 없어요</div>
      </div>`;
      return;
    }

    el.innerHTML = entries.map(([name, loc]) => `
      <div class="location-card">
        <div>
          <div class="location-name">${locIcon(name)} ${name}</div>
          <div class="location-addr">${loc.address || ''} (${loc.lat?.toFixed(4)}, ${loc.lon?.toFixed(4)})</div>
        </div>
        <span class="badge badge-blue">등록됨</span>
      </div>`).join('');
  } catch(e) {
    el.innerHTML = '<div class="text-muted text-sm">위치 정보 없음</div>';
  }
}

function locIcon(name) {
  return name === '집' ? '🏠' : name === '학교' ? '🏫' : name === '알바' ? '💼' : '📍';
}

async function saveLocation() {
  const name    = document.getElementById('locName').value;
  const address = document.getElementById('locAddress').value.trim();
  const lat     = parseFloat(document.getElementById('locLat').value);
  const lon     = parseFloat(document.getElementById('locLon').value);
  const start   = document.getElementById('locStart').value;
  const end     = document.getElementById('locEnd').value;

  if (!address || isNaN(lat) || isNaN(lon)) {
    showToast('주소와 좌표를 모두 입력해주세요.');
    return;
  }

  const btn = document.getElementById('saveLocBtn');
  btn.disabled = true;
  btn.textContent = '저장 중...';

  try {
    await API.saveLocation(name, address, lat, lon, start || null, end || null);
    showToast(`✅ ${name} 위치가 저장되었습니다!`);
    loadLocations();
    // 폼 초기화
    document.getElementById('locAddress').value = '';
    document.getElementById('locLat').value = '';
    document.getElementById('locLon').value = '';
    document.getElementById('locStart').value = '';
    document.getElementById('locEnd').value = '';
  } catch(e) {
    showToast('저장 실패: ' + e.message);
  }

  btn.disabled = false;
  btn.textContent = '💾 위치 저장';
}

// ── 시간표 업로드 ────────────────────────────────
function setupScheduleUpload() {
  const area  = document.getElementById('scheduleUploadArea');
  const input = document.getElementById('scheduleFileInput');

  area.addEventListener('click', () => input.click());
  area.addEventListener('dragover', e => { e.preventDefault(); area.classList.add('drag-over'); });
  area.addEventListener('dragleave', () => area.classList.remove('drag-over'));
  area.addEventListener('drop', e => {
    e.preventDefault();
    area.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) uploadSchedule(file);
  });
  input.addEventListener('change', e => {
    if (e.target.files[0]) uploadSchedule(e.target.files[0]);
  });
}

async function uploadSchedule(file) {
  const area = document.getElementById('scheduleUploadArea');
  const result = document.getElementById('scheduleResult');

  area.innerHTML = `<div class="loading-box"><div class="spinner"></div><div>AI가 시간표를 분석 중입니다...</div></div>`;

  try {
    const data = await API.uploadSchedulePhoto(file);

    if (data.success && data.schedule) {
      showToast('✅ 시간표가 저장되었습니다!');
      const days = ['월','화','수','목','금'];
      result.innerHTML = `
        <div class="ai-card" style="margin-top:16px">
          <div class="ai-label">🤖 파싱된 시간표</div>
          <table style="width:100%;font-size:13px;border-collapse:collapse">
            <thead>
              <tr style="background:var(--bg)">
                <th style="padding:8px;text-align:left;border-radius:6px 0 0 6px">요일</th>
                <th style="padding:8px;text-align:left">시간</th>
                <th style="padding:8px;text-align:left">과목</th>
                <th style="padding:8px;text-align:left;border-radius:0 6px 6px 0">강의실</th>
              </tr>
            </thead>
            <tbody>
              ${data.schedule.map(s => `
                <tr style="border-bottom:1px solid var(--border)">
                  <td style="padding:8px 8px 8px 0"><span class="badge badge-blue">${days[s.day_of_week]}</span></td>
                  <td style="padding:8px">${s.start_time} ~ ${s.end_time}</td>
                  <td style="padding:8px;font-weight:700">${s.subject}</td>
                  <td style="padding:8px;color:var(--text-muted)">${s.classroom || '-'}</td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>`;
      loadSchedule();
    }
  } catch(e) {
    showToast('업로드 실패: ' + e.message);
    result.innerHTML = `<div class="alert alert-warning" style="margin-top:12px">파싱 실패: ${e.message}</div>`;
  }

  area.innerHTML = `
    <span class="upload-icon">📸</span>
    <div class="upload-title">시간표 사진을 올려주세요</div>
    <div class="upload-sub">에브리타임 스크린샷 등 · Claude AI가 자동 분석</div>`;
}

async function loadSchedule() {
  const el = document.getElementById('scheduleView');
  try {
    const { schedule } = await API.getSchedule();
    if (!schedule || schedule.length === 0) {
      el.innerHTML = '<div class="text-muted text-sm">등록된 시간표가 없습니다.</div>';
      return;
    }
    const days = ['월','화','수','목','금'];
    const grouped = {};
    schedule.forEach(s => {
      const d = days[s.day_of_week];
      if (!grouped[d]) grouped[d] = [];
      grouped[d].push(s);
    });

    el.innerHTML = `<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px">
      ${Object.entries(grouped).map(([day, classes]) =>
        classes.map(c => `
          <div style="background:var(--primary-light);border-radius:10px;padding:8px 12px;font-size:13px">
            <div style="font-weight:700;color:var(--primary)">${day} ${c.start_time}~${c.end_time}</div>
            <div style="font-weight:600;margin-top:2px">${c.subject}</div>
            ${c.classroom ? `<div style="font-size:11px;color:var(--text-muted)">${c.classroom}</div>` : ''}
          </div>`).join('')
      ).join('')}
    </div>`;
  } catch(e) {
    el.innerHTML = '';
  }
}

// ── 인바디 업로드 ────────────────────────────────
function setupInbodyUpload() {
  const area  = document.getElementById('inbodyUploadArea');
  const input = document.getElementById('inbodyFileInput');

  area.addEventListener('click', () => input.click());
  area.addEventListener('dragover', e => { e.preventDefault(); area.classList.add('drag-over'); });
  area.addEventListener('dragleave', () => area.classList.remove('drag-over'));
  area.addEventListener('drop', e => {
    e.preventDefault();
    area.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) uploadInbody(file);
  });
  input.addEventListener('change', e => {
    if (e.target.files[0]) uploadInbody(e.target.files[0]);
  });
}

async function uploadInbody(file) {
  const area = document.getElementById('inbodyUploadArea');
  const result = document.getElementById('inbodyResult');

  area.innerHTML = `<div class="loading-box"><div class="spinner"></div><div>AI가 인바디 결과지를 분석 중...</div></div>`;

  try {
    const data = await API.uploadInbodyPhoto(file);

    if (data.success && data.inbody) {
      showToast('✅ 인바디 데이터가 저장되었습니다!');
      const ib = data.inbody;
      result.innerHTML = `
        <div class="ai-card" style="margin-top:16px">
          <div class="ai-label">🤖 추출된 인바디 데이터</div>
          <div class="inbody-grid">
            ${ibItem('체중', ib.weight_kg, 'kg')}
            ${ibItem('골격근', ib.skeletal_muscle_kg, 'kg')}
            ${ibItem('체지방', ib.body_fat_kg, 'kg')}
            ${ibItem('체지방률', ib.body_fat_pct, '%')}
            ${ibItem('BMI', ib.bmi, '')}
            ${ibItem('기초대사량', ib.bmr_kcal, 'kcal')}
          </div>
        </div>`;
      loadInbody();
    }
  } catch(e) {
    showToast('업로드 실패: ' + e.message);
    result.innerHTML = `<div class="alert alert-warning" style="margin-top:12px">추출 실패: ${e.message}</div>`;
  }

  area.innerHTML = `
    <span class="upload-icon">📋</span>
    <div class="upload-title">인바디 결과지 사진을 올려주세요</div>
    <div class="upload-sub">Claude AI가 자동으로 수치를 추출합니다</div>`;
}

async function loadInbody() {
  const el = document.getElementById('inbodyView');
  try {
    const ib = await API.getInbody();
    if (!ib || !ib.weight_kg) {
      el.innerHTML = '<div class="text-muted text-sm">등록된 인바디 데이터가 없습니다.</div>';
      return;
    }
    el.innerHTML = `
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px">측정일: ${ib.measured_at || '-'}</div>
      <div class="inbody-grid">
        ${ibItem('체중', ib.weight_kg, 'kg')}
        ${ibItem('골격근', ib.skeletal_muscle_kg, 'kg')}
        ${ibItem('체지방', ib.body_fat_kg, 'kg')}
        ${ibItem('체지방률', ib.body_fat_pct, '%')}
        ${ibItem('BMI', ib.bmi, '')}
        ${ibItem('기초대사량', ib.bmr_kcal, 'kcal')}
      </div>`;
  } catch(e) {
    el.innerHTML = '';
  }
}

function ibItem(label, val, unit) {
  return `<div class="inbody-item">
    <div class="inbody-val">${val != null ? val : '-'}<span style="font-size:11px;font-weight:600;color:var(--text-muted)">${unit}</span></div>
    <div class="inbody-lbl">${label}</div>
  </div>`;
}
