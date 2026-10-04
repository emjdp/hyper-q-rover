// Q-ROVER 3차시 대시보드 (2차시 화면에서 "로버 상태" 칸만 "조향"으로 바꿈)
//
// 이 페이지는 서버 두 개에 동시에 붙어 있다.
//   포트 7000 : 이 페이지 + WebSocket (지금 이 파일)
//   포트 4912 : 박스가 그려진 영상 (아래 iframe)

const STOP_MM = 150; // 스케치의 STOP_MM 과 맞춰 둘 것 (화면 표시용)
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
ui.on_message('distance', msg => {
  const mm = msg.distance_mm;
  const el = document.getElementById('distance');
  const note = document.getElementById('distanceNote');

  if (mm < 0) {
    // -1 은 "너무 멀다"는 뜻이다. "너무 가깝다"가 아니다.
    el.textContent = '범위 밖';
    note.textContent = '2m 이상이거나 검은/투명 물체';
  } else {
    el.textContent = `${mm} mm`;
    note.textContent = `정지 기준 ${STOP_MM} mm`;
  }
});

// ── 조향 (MCU가 실제로 쓴 값: 보임 · 오차 · 좌우 바퀴) ────
ui.on_message('steer', msg => {
  const seenEl = document.getElementById('seen');
  seenEl.textContent = msg.seen ? '목표 보임' : '안 보임';
  seenEl.className = msg.seen ? 'flag clear' : 'flag';

  const err = Math.max(-100, Math.min(100, msg.err));
  document.getElementById('err').textContent = msg.seen ? (err > 0 ? `+${err}` : `${err}`) : '—';
  document.getElementById('errMarker').style.left = `${50 + err / 2}%`;

  document.getElementById('pwmL').textContent = msg.left;
  document.getElementById('pwmR').textContent = msg.right;
});

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
