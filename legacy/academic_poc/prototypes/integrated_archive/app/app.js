/**
 * SmartCare Hub: Multi-Channel IoT Control Engine
 * Connects directly to unified Firebase RTDB: mohamednael-467e0
 */

const FIREBASE_BASE_URL = "https://mohamednael-467e0-default-rtdb.firebaseio.com";
const SOCKETS_URL = `${FIREBASE_BASE_URL}/sockets.json`;
const SYSTEM_URL = `${FIREBASE_BASE_URL}/system.json`;

// DOM Elements
const statusBadge = document.getElementById("connection-status");
const txtStatus = document.getElementById("txt-status");
const liveTempDisplay = document.getElementById("live-temp-display");
const uptimeDisplay = document.getElementById("uptime-display");
const emergencyBtn = document.getElementById("emergency-btn");
const langToggleBtn = document.getElementById("lang-toggle-btn");

let currentLanguage = "ar";
let pollTimer = null;

// Localization Strings Dictionary
const I18N = {
  ar: {
    title: "منظومة المقابس الذكية الشاملة",
    subtitle: "SmartCare Multi-Channel IoT Safety & Power Strip",
    statusConnected: "متصل بالسحابة بنجاح",
    statusError: "انقطاع الاتصال بالسحابة",
    emergency: "إيقاف الطوارئ الشامل (All-Off)",
    currentTemp: "الحرارة الحالية:",
    on: "الحالة: يعمل",
    off: "الحالة: متوقف",
    langBtn: "English"
  },
  en: {
    title: "SmartCare Multi-Socket Hub",
    subtitle: "Multi-Channel IoT Safety & Power Distribution Strip",
    statusConnected: "Cloud Connected",
    statusError: "Cloud Disconnected",
    emergency: "Emergency All-Off Stop",
    currentTemp: "Current Temp:",
    on: "Status: Active (ON)",
    off: "Status: Inactive (OFF)",
    langBtn: "العربية"
  }
};

// 1. Fetch System Telemetry & Socket States
async function syncSystemState() {
  try {
    const [socketsRes, sysRes] = await Promise.all([
      fetch(SOCKETS_URL),
      fetch(SYSTEM_URL)
    ]);

    if (!socketsRes.ok) throw new Error("Sockets fetch error");
    const sockets = await socketsRes.json() || {};
    const system = await sysRes.json() || {};

    updateSocketUI(1, sockets.socket1, "🔌");
    updateSocketUI(2, sockets.socket2, "🚰");
    updateSocketUI(3, sockets.socket3, "📺");
    updateSocketUI(4, sockets.socket4, "❄️");

    if (sockets.socket1 && sockets.socket1.currentTemp !== undefined) {
      liveTempDisplay.textContent = Number(sockets.socket1.currentTemp).toFixed(1);
    }

    if (system.uptimeSeconds) {
      uptimeDisplay.textContent = `${system.uptimeSeconds} s`;
    }

    statusBadge.className = "status-badge connected";
    txtStatus.textContent = I18N[currentLanguage].statusConnected;
  } catch (err) {
    statusBadge.className = "status-badge error";
    txtStatus.textContent = I18N[currentLanguage].statusError;
    console.error("Cloud Sync Error:", err);
  }
}

// 2. Render Single Socket State
function updateSocketUI(channelNum, data, defaultIcon) {
  if (!data) return;
  const toggleBtn = document.getElementById(`s${channelNum}-toggle-btn`);
  const stateText = document.getElementById(`s${channelNum}-state-text`);
  const modeSelect = document.getElementById(`s${channelNum}-mode-select`);
  const safetyReason = document.getElementById(`s${channelNum}-safety-reason`);

  const isOn = data.status === "on";
  toggleBtn.className = `plug-btn ${isOn ? "on" : "off"}`;
  stateText.textContent = isOn ? I18N[currentLanguage].on : I18N[currentLanguage].off;

  if (document.activeElement !== modeSelect && data.mode) {
    modeSelect.value = data.mode;
  }

  if (data.lastSafetyReason) {
    safetyReason.textContent = `الأمان: ${data.lastSafetyReason}`;
  }

  // Populate channel specific fields if present
  if (channelNum === 1 && data.minTemp && data.maxTemp) {
    if (document.activeElement !== document.getElementById("s1-min-input")) {
      document.getElementById("s1-min-input").value = data.minTemp;
    }
    if (document.activeElement !== document.getElementById("s1-max-input")) {
      document.getElementById("s1-max-input").value = data.maxTemp;
    }
  } else if (channelNum === 2 && data.maxRuntimeMins) {
    if (document.activeElement !== document.getElementById("s2-max-runtime-input")) {
      document.getElementById("s2-max-runtime-input").value = data.maxRuntimeMins;
    }
  } else if (channelNum === 3 && data.autoOffHours) {
    if (document.activeElement !== document.getElementById("s3-auto-off-input")) {
      document.getElementById("s3-auto-off-input").value = data.autoOffHours;
    }
  } else if (channelNum === 4 && data.minTemp && data.maxTemp) {
    if (document.activeElement !== document.getElementById("s4-min-input")) {
      document.getElementById("s4-min-input").value = data.minTemp;
    }
    if (document.activeElement !== document.getElementById("s4-max-input")) {
      document.getElementById("s4-max-input").value = data.maxTemp;
    }
  }
}

// 3. Command API Helper
async function putToFirebase(path, payload) {
  try {
    const res = await fetch(`${FIREBASE_BASE_URL}/${path}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    setTimeout(syncSystemState, 200);
  } catch (err) {
    console.error("Firebase write error:", err);
  }
}

// 4. Attach Event Handlers for All 4 Sockets
for (let ch = 1; ch <= 4; ch++) {
  const channel = ch;
  // Toggle Switch
  document.getElementById(`s${channel}-toggle-btn`).addEventListener("click", () => {
    const btn = document.getElementById(`s${channel}-toggle-btn`);
    const nextStatus = btn.classList.contains("on") ? "off" : "on";
    putToFirebase(`sockets/socket${channel}/status.json`, nextStatus);
  });

  // Mode Select
  document.getElementById(`s${channel}-mode-select`).addEventListener("change", (e) => {
    putToFirebase(`sockets/socket${channel}/mode.json`, e.target.value);
  });
}

// Save Channel 1 Settings
document.getElementById("s1-save-btn").addEventListener("click", () => {
  const minV = parseFloat(document.getElementById("s1-min-input").value);
  const maxV = parseFloat(document.getElementById("s1-max-input").value);
  putToFirebase("sockets/socket1/minTemp.json", minV);
  putToFirebase("sockets/socket1/maxTemp.json", maxV);
});

// Save Channel 2 Settings (Pump)
document.getElementById("s2-save-btn").addEventListener("click", () => {
  const val = parseInt(document.getElementById("s2-max-runtime-input").value, 10);
  putToFirebase("sockets/socket2/maxRuntimeMins.json", val);
});

// Save Channel 3 Settings (TV)
document.getElementById("s3-save-btn").addEventListener("click", () => {
  const val = parseInt(document.getElementById("s3-auto-off-input").value, 10);
  putToFirebase("sockets/socket3/autoOffHours.json", val);
});

// Save Channel 4 Settings (AC)
document.getElementById("s4-save-btn").addEventListener("click", () => {
  const minV = parseFloat(document.getElementById("s4-min-input").value);
  const maxV = parseFloat(document.getElementById("s4-max-input").value);
  putToFirebase("sockets/socket4/minTemp.json", minV);
  putToFirebase("sockets/socket4/maxTemp.json", maxV);
});

// 5. Master Emergency Shutdown Action
emergencyBtn.addEventListener("click", async () => {
  if (confirm("هل تؤكد تنفيذ إيقاف الطوارئ الشامل لجميع المقابس الأربعة فوراً؟\nConfirm Emergency All-Off?")) {
    await putToFirebase("system/emergencyShutdown.json", true);
    for (let i = 1; i <= 4; i++) {
      await putToFirebase(`sockets/socket${i}/status.json`, "off");
    }
    alert("🚨 تم إرسال أمر إيقاف الطوارئ الشامل لكافة القنوات!");
  }
});

// 6. Bilingual Switcher
langToggleBtn.addEventListener("click", () => {
  currentLanguage = currentLanguage === "ar" ? "en" : "ar";
  document.documentElement.dir = currentLanguage === "ar" ? "rtl" : "ltr";
  document.documentElement.lang = currentLanguage;

  document.getElementById("txt-title").textContent = I18N[currentLanguage].title;
  document.getElementById("txt-subtitle").textContent = I18N[currentLanguage].subtitle;
  document.getElementById("txt-emergency").textContent = I18N[currentLanguage].emergency;
  document.getElementById("txt-current-temp-label").textContent = I18N[currentLanguage].currentTemp;
  langToggleBtn.textContent = I18N[currentLanguage].langBtn;
  syncSystemState();
});

// Initial load & Polling
syncSystemState();
pollTimer = setInterval(syncSystemState, 2500);
