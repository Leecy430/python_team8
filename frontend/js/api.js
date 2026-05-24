/* =============================================
   api.js — FastAPI 백엔드 호출 클라이언트
   ============================================= */

const API = {
  base: '',  // 같은 서버에서 서빙되므로 빈 문자열

  async _get(path) {
    const res = await fetch(this.base + path);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || '요청 실패');
    }
    return res.json();
  },

  async _post(path, formData) {
    const res = await fetch(this.base + path, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || '요청 실패');
    }
    return res.json();
  },

  async _postParams(path) {
    const res = await fetch(this.base + path, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || '요청 실패');
    }
    return res.json();
  },

  // ── 대시보드 ─────────────────────────────
  getDashboard(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/dashboard${q}`);
  },

  getDates() {
    return this._get('/api/dashboard/dates');
  },

  // ── 걸음수 ───────────────────────────────
  getSteps(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/steps${q}`);
  },

  getStepsTimeseries(days = 30) {
    return this._get(`/api/steps/timeseries?days=${days}`);
  },

  // ── 수면 ─────────────────────────────────
  getSleep(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/sleep${q}`);
  },

  getSleepTimeseries(days = 30) {
    return this._get(`/api/sleep/timeseries?days=${days}`);
  },

  // ── 심박수 ───────────────────────────────
  getHeartrate(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/heartrate${q}`);
  },

  // ── 식단 ─────────────────────────────────
  getMeals(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/meals${q}`);
  },

  getMealRecommend(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/meals/recommend${q}`);
  },

  uploadFoodPhoto(file) {
    const fd = new FormData();
    fd.append('file', file);
    return this._post('/api/meals/photo', fd);
  },

  // ── 운동 ─────────────────────────────────
  getExerciseRecommend(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/exercise/recommend${q}`);
  },

  getExerciseFreeSlots() {
    return this._get('/api/exercise/free-slots');
  },

  saveExercise(name, duration_min, weight_kg = 70.0) {
    const q = new URLSearchParams({ name, duration_min, weight_kg });
    return this._postParams(`/api/exercise/save?${q}`);
  },

  // ── 날씨 ─────────────────────────────────
  getWeather(location = null) {
    const q = location ? `?location=${encodeURIComponent(location)}` : '';
    return this._get(`/api/weather${q}`);
  },

  // ── 산책 ─────────────────────────────────
  getWalkRecommend(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/api/walk/recommend${q}`);
  },

  getLocations() {
    return this._get('/api/walk/locations');
  },

  saveLocation(name, address, lat, lon, start_time = null, end_time = null) {
    const q = new URLSearchParams({ name, address, lat, lon });
    if (start_time) q.append('start_time', start_time);
    if (end_time) q.append('end_time', end_time);
    return this._postParams(`/api/walk/location?${q}`);
  },

  // ── 시간표 ───────────────────────────────
  getSchedule() {
    return this._get('/api/schedule');
  },


 getTodaySchedule(date = null) {
    const q = date ? `?date=${date}` : '';
    return this._get(`/today-schedule${q}`);
  },

  
  getScheduleFreeSlots() {
    return this._get('/api/schedule/free-slots');
  },

  uploadSchedulePhoto(file) {
    const fd = new FormData();
    fd.append('file', file);
    return this._post('/api/schedule/photo', fd);
  },

  // ── 인바디 ───────────────────────────────
  getInbody() {
    return this._get('/api/inbody');
  },

  uploadInbodyPhoto(file) {
    const fd = new FormData();
    fd.append('file', file);
    return this._post('/api/inbody/photo', fd);
  },

  // ── 옷차림 ───────────────────────────────
  getOutfit(location = null) {
    const q = location ? `?location=${encodeURIComponent(location)}` : '';
    return this._get(`/api/outfit${q}`);
  },
};

/* ── 공통 유틸 ─────────────────────────────── */

function showToast(msg, duration = 2800) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return `${d.getFullYear()}. ${d.getMonth()+1}. ${d.getDate()}.`;
}

function today() {
  const now = new Date();
  const kst = new Date(now.getTime() + 9*60*60*1000);
  return kst.toISOString().split('T')[0];
}

function fmtMin(min) {
  if (!min) return '-';
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return h > 0 ? `${h}시간 ${m}분` : `${m}분`;
}

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}
