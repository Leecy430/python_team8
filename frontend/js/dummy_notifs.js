/* =============================================
   dummy_notifs.js — 임시 더미 알림 목록
   ============================================= */

// const STEPS_NOTIF = {
//   avatar: '🏃',
//   message: '창연님, 목표 걸음수를 채우시려면 인하대학교 한 바퀴는 도셔야합니다!! (3,500보 채워져요)',
//   type: 'warning',
// };

// const CLASS_NOTIF = {
//   avatar: '📚',
//   message: '내일 13:30에 파이썬기반응용프로그래밍 발표가 있으니 오늘은 어제와 달리 2시 전에 주무시는게 좋을 것 같아요!!',
//   type: 'info',
// };

// function sendDummyNotifs() {
//   // 걸음수 알림 — 히스토리에만 조용히 추가 (이미 읽은 것처럼)
//   addToHistory(STEPS_NOTIF);
//   renderHistory();

//   // 발표 알림 — 팝업 배너와 함께 새로 도착한 느낌으로
//   setTimeout(() => {
//     addToHistory(CLASS_NOTIF);
//     renderHistory();
//     showBanner(CLASS_NOTIF);
//   }, 1200);
// }

const ELEVATOR_NOTIF = {
  avatar: '🏢',
  message: '60주년 기념관은 곧 막히기 시작하니 미리 가서 엘리베이터를 탑승 할 수 있도록 하는게 좋을것 같아요',
  type: 'info',
};

function sendDummyNotifs() {
  setTimeout(() => {
    addToHistory(ELEVATOR_NOTIF);
    renderHistory();
    showBanner(ELEVATOR_NOTIF);
  }, 1200);
}
