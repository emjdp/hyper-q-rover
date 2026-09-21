// Q-ROVER 2차시 통합 대시보드
//
// 이 페이지는 서버 두 개에 동시에 붙어 있다.
//   포트 7000 : 이 페이지 + WebSocket (지금 이 파일)
//   포트 4912 : 박스가 그려진 영상 (아래 iframe)

const STOP_MM = 200; // 스케치의 STOP_MM 과 맞춰 둘 것 (화면 표시용)
const MAX_ROWS = 5;

const ui = new WebUI();
const rows = [];

// ── 연결 상태 ────────────────────────────────────────────
const connEl = document.getElementById('conn');
ui.on_connect(() => {
  connEl.textContent = '연결됨';
  connEl.className = 'badge on';
});
ui.on_disconnect(() => {
  connEl.textContent = '연결 끊김';
  connEl.className = 'badge off';
});

// ── 거리값 (MCU → Python → 여기) ─────────────────────────
let tofBlocked = false;

ui.on_message('distance', msg => {
  const mm = msg.distance_mm;
  const el = document.getElementById('distance');
  const note = document.getElementById('distanceNote');

  if (mm < 0) {
    // -1 은 "너무 멀다"는 뜻이다. "너무 가깝다"가 아니다.
    el.textContent = '범위 밖';
    note.textContent = '2m 이상이거나 검은/투명 물체';
    tofBlocked = false;
  } else {
    el.textContent = `${mm} mm`;
    note.textContent = `정지 기준 ${STOP_MM} mm`;
    tofBlocked = mm < STOP_MM;
  }
  render();
});

// ── 비전 판단 (Python이 MCU에 보낼 때 같이 보내준 것) ─────
let visionBlocked = false;

ui.on_message('vision', msg => {
  visionBlocked = !!msg.blocked;
  render();
});

function render() {
  setFlag('tofFlag', tofBlocked);
  setFlag('visionFlag', visionBlocked);

  const state = document.getElementById('state');
  if (tofBlocked || visionBlocked) {
    state.textContent = '정지';
    state.className = 'big state-stop';
  } else {
    state.textContent = '직진';
    state.className = 'big state-go';
  }
}

function setFlag(id, blocked) {
  const el = document.getElementById(id);
  el.textContent = blocked ? '막힘' : '통과';
  el.className = blocked ? 'flag blocked' : 'flag clear';
}

// ── 검출 목록 ────────────────────────────────────────────
ui.on_message('detection', msg => {
  rows.unshift(msg);
  if (rows.length > MAX_ROWS) rows.pop();

  const box = document.getElementById('detections');
  box.innerHTML = '';
  rows.forEach(r => {
    const pct = Math.floor(r.confidence * 1000) / 10;
    const div = document.createElement('div');
    div.className = 'det';
    div.innerHTML =
      `<span class="det-label">${r.content}</span>` +
      `<span class="det-pct">${pct}%</span>` +
      `<span class="det-time">${new Date(r.timestamp).toLocaleTimeString('ko-KR')}</span>`;
    box.appendChild(div);
  });
});

// ── Confidence 슬라이더 → 모델 ───────────────────────────
const slider = document.getElementById('confSlider');
const confValue = document.getElementById('confValue');

function pushThreshold() {
  const v = parseFloat(slider.value);
  confValue.textContent = v.toFixed(2);
  ui.send_message('override_th', v); // Python의 override_threshold()로 간다
}

slider.addEventListener('input', pushThreshold);
document.getElementById('confReset').addEventListener('click', () => {
  slider.value = '0.5';
  pushThreshold();
});
pushThreshold();

// ── 영상 iframe : 컨테이너가 뜰 때까지 재시도 ────────────
const frame = document.getElementById('videoFrame');
const placeholder = document.getElementById('videoPlaceholder');
const streamUrl = `http://${window.location.hostname}:4912/embed`;

frame.onload = () => {
  clearInterval(retry);
  placeholder.style.display = 'none';
  frame.style.display = 'block';
};

const retry = setInterval(() => {
  frame.src = streamUrl;
}, 1000);

render();
